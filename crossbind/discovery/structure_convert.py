"""Ensure docking receptors are PDB (convert mmCIF / prefer AlphaFold PDB)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

from crossbind.discovery.structures import UA_NOTE


class StructureConvertError(RuntimeError):
    """Raised when a receptor cannot be materialized as PDB."""


def ensure_receptor_pdb(
    src: str | Path,
    dest: Path,
    *,
    uniprot: str | None = None,
    entry_id: str | None = None,
    pdb_url: str | None = None,
) -> Path:
    """Copy or convert ``src`` into ``dest`` as PDB. Always writes ``dest``."""
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not src.is_file():
        raise StructureConvertError(f"Receptor file not found: {src}")

    suffix = src.suffix.lower()
    if suffix in {".pdb", ".ent"}:
        shutil.copy(src, dest)
        return dest

    if suffix not in {".cif", ".mmcif"}:
        # Allow .pdbqt etc. to pass through with original extension handled by caller
        raise StructureConvertError(
            f"Unsupported receptor format for dock convert: {suffix or '(none)'}"
        )

    errors: list[str] = []

    # 1) Sibling / alternate AlphaFold PDB already on disk
    for candidate in _pdb_candidates_nearby(src, entry_id=entry_id, uniprot=uniprot):
        if candidate.is_file() and candidate.stat().st_size > 100:
            shutil.copy(candidate, dest)
            return dest

    # 2) Download AlphaFold PDB if we have a URL or can guess one
    try:
        if _try_download_af_pdb(dest, entry_id=entry_id, uniprot=uniprot, pdb_url=pdb_url):
            return dest
    except Exception as exc:
        errors.append(f"AlphaFold PDB download: {exc}")

    # 3) gemmi
    try:
        _convert_gemmi(src, dest)
        if dest.is_file() and dest.stat().st_size > 100:
            return dest
        errors.append("gemmi wrote empty PDB")
    except Exception as exc:
        errors.append(f"gemmi: {exc}")

    # 4) Biopython MMCIFParser → PDBIO
    try:
        _convert_biopython(src, dest)
        if dest.is_file() and dest.stat().st_size > 100:
            return dest
        errors.append("Biopython wrote empty PDB")
    except Exception as exc:
        errors.append(f"Biopython: {exc}")

    # 5) Open Babel CLI if present
    try:
        _convert_obabel(src, dest)
        if dest.is_file() and dest.stat().st_size > 100:
            return dest
        errors.append("obabel wrote empty PDB")
    except Exception as exc:
        errors.append(f"obabel: {exc}")

    if dest.is_file():
        dest.unlink(missing_ok=True)
    raise StructureConvertError(
        "Could not convert mmCIF/CIF to PDB. " + " | ".join(errors) if errors else "unknown failure"
    )


def _pdb_candidates_nearby(
    src: Path,
    *,
    entry_id: str | None,
    uniprot: str | None,
) -> list[Path]:
    out: list[Path] = []
    out.append(src.with_suffix(".pdb"))
    stem = src.name
    # AF-P43304-2-F1.cif ↔ AF-P43304-2-F1-model_v6.cif / .pdb
    if stem.endswith(".cif"):
        base = stem[:-4]
        parent = src.parent
        out.append(parent / f"{base}.pdb")
        for p in parent.glob(f"{base}-model_v*.pdb"):
            out.append(p)
        for p in parent.glob(f"{base}*.pdb"):
            out.append(p)
    if entry_id:
        parent = src.parent
        out.append(parent / f"{entry_id}.pdb")
        for p in parent.glob(f"{entry_id}-model_v*.pdb"):
            out.append(p)
    if uniprot:
        parent = src.parent
        for p in parent.glob(f"AF-{uniprot}*.pdb"):
            out.append(p)
    # de-dupe preserving order
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in out:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def _try_download_af_pdb(
    dest: Path,
    *,
    entry_id: str | None,
    uniprot: str | None,
    pdb_url: str | None,
) -> bool:
    urls: list[str] = []
    if pdb_url:
        urls.append(pdb_url)
    eid = (entry_id or "").strip()
    if eid and not eid.startswith("AF-") and uniprot:
        eid = f"AF-{uniprot}-F1"
    if eid:
        # Try common versioned filenames (newest first)
        for ver in ("6", "5", "4", "3"):
            urls.append(f"https://alphafold.ebi.ac.uk/files/{eid}-model_v{ver}.pdb")
        urls.append(f"https://alphafold.ebi.ac.uk/files/{eid}.pdb")
    if uniprot and not eid:
        for ver in ("6", "5", "4"):
            urls.append(f"https://alphafold.ebi.ac.uk/files/AF-{uniprot}-F1-model_v{ver}.pdb")

    # de-dupe
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        try:
            r = httpx.get(url, headers={"User-Agent": UA_NOTE}, timeout=90, follow_redirects=True)
            if r.status_code == 200 and len(r.content) > 100 and b"ATOM" in r.content[:5000]:
                dest.write_bytes(r.content)
                # also cache next to structures dir if dest is a job path — caller copies
                return True
        except Exception:
            continue
    return False


def _convert_gemmi(src: Path, dest: Path) -> None:
    import gemmi

    st = gemmi.read_structure(str(src))
    # Large models: write_pdb handles standard polymer; keep hydrogens if present
    st.write_pdb(str(dest))


def _convert_biopython(src: Path, dest: Path) -> None:
    from Bio.PDB.MMCIFParser import MMCIFParser
    from Bio.PDB.PDBIO import PDBIO, Select

    class _PolymerSelect(Select):
        def accept_model(self, model):  # noqa: ANN001
            return model.id == 0 or True

        def accept_residue(self, residue):  # noqa: ANN001
            hetflag = residue.id[0]
            # Standard polymer residues only (skip waters / large ligands that break PDB)
            if hetflag.strip() and hetflag != " ":
                return False
            return True

        def accept_atom(self, atom):  # noqa: ANN001
            # Skip disordered altlocs except A / first
            if atom.is_disordered() and atom.get_altloc() not in (" ", "A", "1"):
                return False
            return True

    parser = MMCIFParser(QUIET=True)
    structure_obj = parser.get_structure("rec", str(src))
    # Keep only first model to avoid huge multi-model dumps
    models = list(structure_obj.get_models())
    if len(models) > 1:
        for m in models[1:]:
            structure_obj.detach_child(m.id)

    io = PDBIO()
    io.set_structure(structure_obj)
    io.save(str(dest), _PolymerSelect())


def _convert_obabel(src: Path, dest: Path) -> None:
    obabel = shutil.which("obabel") or shutil.which("obabel.exe")
    if not obabel:
        raise RuntimeError("obabel not on PATH")
    proc = subprocess.run(
        [obabel, str(src), "-O", str(dest)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "obabel failed")[:500])


def receptor_convert_meta(structure: dict[str, Any] | None) -> dict[str, str | None]:
    """Pull identifiers useful for AlphaFold PDB fetch from a Discover structure dict."""
    st = structure or {}
    return {
        "uniprot": (st.get("uniprot") or None),
        "entry_id": (st.get("pdb_id") or st.get("entry_id") or None),
        "pdb_url": (st.get("pdb_url") or None),
    }
