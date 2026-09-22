"""PDB via rcsb-api + Biopython; else AlphaFold DB via Biopython helper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from crossbind.discovery.cache import get_json, set_json, structures_dir

UA_NOTE = "CrossAffinity/1.x (local research; Alexander Cecena)"

# Warn when AlphaFold global pLDDT is below this
_LOW_PLDDT = 70.0


def recommend_structure(
    uniprot: str,
    *,
    prefer_pdb: bool = True,
    pdb_id: str | None = None,
) -> dict[str, Any]:
    """Pick best experimental PDB for UniProt, else AlphaFold CIF.

    If ``pdb_id`` is set, force that experimental structure (still keyed by UniProt).
    """
    uniprot = (uniprot or "").strip().upper()
    force_pdb = (pdb_id or "").strip().upper() or None
    if not uniprot and not force_pdb:
        return {"ok": False, "error": "Empty UniProt accession", "provenance": None}

    cache_key = f"{uniprot}:{force_pdb}" if force_pdb else uniprot
    if uniprot and not force_pdb:
        cached = get_json("structure_rec", uniprot, ttl_s=14 * 86400)
        if cached and cached.get("path") and Path(cached["path"]).is_file():
            return _upgrade_cached_af_to_pdb(cached)
    elif force_pdb and uniprot:
        cached = get_json("structure_rec", cache_key, ttl_s=14 * 86400)
        if cached and cached.get("path") and Path(cached["path"]).is_file():
            return cached

    pdb_ids: list[str] = []
    err_pdb = None
    if prefer_pdb and uniprot and not force_pdb:
        try:
            pdb_ids = search_pdb_by_uniprot(uniprot)
        except Exception as exc:
            err_pdb = str(exc)

    if force_pdb:
        path = download_pdb(force_pdb)
        meta = fetch_pdb_entry_meta(force_pdb)
        out = {
            "ok": True,
            "provenance": "experimental_pdb",
            "label": "experimental",
            "pdb_id": force_pdb,
            "uniprot": uniprot or None,
            "candidates": [force_pdb] + [p for p in pdb_ids if p != force_pdb][:11],
            "path": str(path),
            "format": path.suffix.lstrip("."),
            "warning": None,
            "pdb_search_error": err_pdb,
            "method": meta.get("method"),
            "resolution_A": meta.get("resolution_A"),
            "title": meta.get("title"),
        }
        if uniprot:
            set_json("structure_rec", cache_key, out)
        return out

    if pdb_ids:
        chosen = pdb_ids[0]
        path = download_pdb(chosen)
        meta = fetch_pdb_entry_meta(chosen)
        out = {
            "ok": True,
            "provenance": "experimental_pdb",
            "label": "experimental",
            "pdb_id": chosen,
            "uniprot": uniprot,
            "candidates": pdb_ids[:12],
            "path": str(path),
            "format": path.suffix.lstrip("."),
            "warning": None,
            "pdb_search_error": err_pdb,
            "method": meta.get("method"),
            "resolution_A": meta.get("resolution_A"),
            "title": meta.get("title"),
        }
        set_json("structure_rec", uniprot, out)
        return out

    # AlphaFold fallback
    try:
        af = download_alphafold(uniprot)
        plddt = af.get("plddt_mean")
        warn = (
            "Predicted AlphaFold model — not an experimental structure. "
            "Pocket/geometry may be unreliable for docking."
        )
        try:
            plddt_f = float(plddt) if plddt is not None else None
        except (TypeError, ValueError):
            plddt_f = None
        if plddt_f is not None and plddt_f < _LOW_PLDDT:
            warn += f" Low mean pLDDT ({plddt_f:.1f} < {_LOW_PLDDT:.0f}) — treat coordinates cautiously."
        out = {
            "ok": True,
            "provenance": "alphafold_db",
            "label": "predicted",
            "pdb_id": af.get("entry_id"),
            "uniprot": uniprot,
            "candidates": [],
            "path": af["path"],
            "format": Path(af["path"]).suffix.lstrip("."),
            "plddt_mean": plddt,
            "warning": warn,
            "pdb_search_error": err_pdb,
            "pdb_candidates_empty": not pdb_ids,
            "method": "AlphaFold prediction",
            "resolution_A": None,
        }
        set_json("structure_rec", uniprot, out)
        return out
    except Exception as exc:
        return {
            "ok": False,
            "error": f"No PDB or AlphaFold structure for {uniprot}: {exc}",
            "provenance": None,
            "pdb_search_error": err_pdb,
        }


def search_pdb_by_uniprot(uniprot: str) -> list[str]:
    """Search RCSB for polymer entities linked to a UniProt accession."""
    from rcsbapi.search import AttributeQuery, NestedAttributeQuery

    q = NestedAttributeQuery(
        AttributeQuery(
            "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
            "exact_match",
            uniprot,
        ),
        AttributeQuery(
            "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_name",
            "exact_match",
            "UniProt",
        ),
    )
    ids = list(q())
    return [str(i).upper() for i in ids]


def download_pdb(pdb_id: str) -> Path:
    pdb_id = pdb_id.upper().strip()
    out = structures_dir() / f"{pdb_id}.pdb"
    if out.is_file() and out.stat().st_size > 100:
        return out
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    r = httpx.get(url, headers={"User-Agent": UA_NOTE}, timeout=60, follow_redirects=True)
    r.raise_for_status()
    out.write_bytes(r.content)
    return out


def fetch_pdb_entry_meta(pdb_id: str) -> dict[str, Any]:
    """Resolution / experimental method / title from RCSB data API (best-effort)."""
    pdb_id = pdb_id.upper().strip()
    cached = get_json("pdb_meta", pdb_id, ttl_s=30 * 86400)
    if cached:
        return cached
    out: dict[str, Any] = {"pdb_id": pdb_id, "method": None, "resolution_A": None, "title": None}
    try:
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
        r = httpx.get(url, headers={"User-Agent": UA_NOTE}, timeout=45)
        if r.status_code == 200:
            d = r.json()
            out["title"] = (d.get("struct") or {}).get("title")
            exptl = d.get("exptl") or []
            if exptl and isinstance(exptl, list):
                out["method"] = exptl[0].get("method")
            reso = (d.get("rcsb_entry_info") or {}).get("resolution_combined")
            if isinstance(reso, list) and reso:
                out["resolution_A"] = float(reso[0])
            elif isinstance(reso, (int, float)):
                out["resolution_A"] = float(reso)
    except Exception as exc:
        out["error"] = str(exc)
    set_json("pdb_meta", pdb_id, out)
    return out


def download_alphafold(uniprot: str) -> dict[str, Any]:
    """Use Biopython AlphaFold DB helpers; prefer PDB (dockable), else CIF."""
    from Bio.PDB import alphafold_db

    preds = list(alphafold_db.get_predictions(uniprot))
    if not preds:
        raise RuntimeError(f"No AlphaFold predictions for {uniprot}")
    pred = max(preds, key=lambda p: float(p.get("globalMetricValue") or 0))
    entry = pred.get("entryId") or pred.get("modelEntityId") or f"AF-{uniprot}-F1"
    out_pdb = structures_dir() / f"{entry}.pdb"
    out_cif = structures_dir() / f"{entry}.cif"
    pdb_url = pred.get("pdbUrl")
    cif_url = pred.get("cifUrl")

    # Prefer PDB for the docking pipeline (avoids mmCIF→PDB convert failures)
    if out_pdb.is_file() and out_pdb.stat().st_size > 100:
        chosen = out_pdb
    else:
        chosen = None
        if pdb_url:
            try:
                r = httpx.get(pdb_url, headers={"User-Agent": UA_NOTE}, timeout=90, follow_redirects=True)
                r.raise_for_status()
                if len(r.content) > 100 and b"ATOM" in r.content[:8000]:
                    out_pdb.write_bytes(r.content)
                    chosen = out_pdb
            except Exception:
                chosen = None
        if chosen is None:
            # Fall back to CIF (dock route converts)
            if not out_cif.is_file() or out_cif.stat().st_size < 100:
                try:
                    cif_path = alphafold_db.download_cif_for(pred, directory=str(structures_dir()))
                    cif_path = Path(cif_path)
                    if cif_path.resolve() != out_cif.resolve():
                        out_cif.write_bytes(cif_path.read_bytes())
                except Exception:
                    if not cif_url:
                        raise
                    r = httpx.get(cif_url, headers={"User-Agent": UA_NOTE}, timeout=90, follow_redirects=True)
                    r.raise_for_status()
                    out_cif.write_bytes(r.content)
            chosen = out_cif

    return {
        "path": str(chosen),
        "entry_id": entry,
        "plddt_mean": pred.get("globalMetricValue"),
        "version": pred.get("latestVersion"),
        "pdb_url": pdb_url,
        "cif_url": cif_url,
    }


def _upgrade_cached_af_to_pdb(cached: dict[str, Any]) -> dict[str, Any]:
    """If a cached AlphaFold hit points at CIF, prefer a PDB sibling / re-download."""
    path = Path(cached.get("path") or "")
    if not path.is_file():
        return cached
    if path.suffix.lower() not in {".cif", ".mmcif"}:
        return cached
    pdb_sib = path.with_suffix(".pdb")
    if pdb_sib.is_file() and pdb_sib.stat().st_size > 100:
        out = dict(cached)
        out["path"] = str(pdb_sib)
        out["format"] = "pdb"
        return out
    stem = path.name[:-4] if path.name.endswith(".cif") else path.stem
    matches = sorted(path.parent.glob(f"{stem}*.pdb"), key=lambda p: p.stat().st_mtime, reverse=True)
    if matches:
        out = dict(cached)
        out["path"] = str(matches[0])
        out["format"] = "pdb"
        return out
    uniprot = (cached.get("uniprot") or "").strip().upper()
    if uniprot and cached.get("provenance") == "alphafold_db":
        try:
            af = download_alphafold(uniprot)
            out = dict(cached)
            out["path"] = af["path"]
            out["format"] = Path(af["path"]).suffix.lstrip(".")
            out["pdb_id"] = af.get("entry_id") or out.get("pdb_id")
            out["plddt_mean"] = af.get("plddt_mean", out.get("plddt_mean"))
            if af.get("pdb_url"):
                out["pdb_url"] = af["pdb_url"]
            set_json("structure_rec", uniprot, out)
            return out
        except Exception:
            return cached
    return cached
