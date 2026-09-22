"""PDB via rcsb-api + Biopython; else AlphaFold DB via Biopython helper."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from crossbind.discovery.cache import get_json, set_json, structures_dir

UA_NOTE = "CrossAffinity/1.x (local research; Alexander Cecena)"


def recommend_structure(uniprot: str, *, prefer_pdb: bool = True) -> dict[str, Any]:
    """Pick best experimental PDB for UniProt, else AlphaFold CIF."""
    uniprot = (uniprot or "").strip().upper()
    if not uniprot:
        return {"ok": False, "error": "Empty UniProt accession", "provenance": None}

    cached = get_json("structure_rec", uniprot, ttl_s=14 * 86400)
    if cached and cached.get("path") and Path(cached["path"]).is_file():
        return cached

    pdb_ids: list[str] = []
    err_pdb = None
    if prefer_pdb:
        try:
            pdb_ids = search_pdb_by_uniprot(uniprot)
        except Exception as exc:
            err_pdb = str(exc)

    if pdb_ids:
        pdb_id = pdb_ids[0]
        path = download_pdb(pdb_id)
        out = {
            "ok": True,
            "provenance": "experimental_pdb",
            "label": "experimental",
            "pdb_id": pdb_id,
            "uniprot": uniprot,
            "candidates": pdb_ids[:12],
            "path": str(path),
            "format": path.suffix.lstrip("."),
            "warning": None,
            "pdb_search_error": err_pdb,
        }
        set_json("structure_rec", uniprot, out)
        return out

    # AlphaFold fallback
    try:
        af = download_alphafold(uniprot)
        out = {
            "ok": True,
            "provenance": "alphafold_db",
            "label": "predicted",
            "pdb_id": af.get("entry_id"),
            "uniprot": uniprot,
            "candidates": [],
            "path": af["path"],
            "format": Path(af["path"]).suffix.lstrip("."),
            "plddt_mean": af.get("plddt_mean"),
            "warning": (
                "Predicted AlphaFold model — not an experimental structure. "
                "Pocket/geometry may be unreliable for docking."
            ),
            "pdb_search_error": err_pdb,
            "pdb_candidates_empty": not pdb_ids,
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
    # Prefer newer / common IDs; take first page
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


def download_alphafold(uniprot: str) -> dict[str, Any]:
    """Use Biopython AlphaFold DB helpers; persist CIF locally."""
    from Bio.PDB import alphafold_db

    preds = list(alphafold_db.get_predictions(uniprot))
    if not preds:
        raise RuntimeError(f"No AlphaFold predictions for {uniprot}")
    # Prefer full-length / highest pLDDT
    pred = max(preds, key=lambda p: float(p.get("globalMetricValue") or 0))
    entry = pred.get("entryId") or pred.get("modelEntityId") or f"AF-{uniprot}-F1"
    out = structures_dir() / f"{entry}.cif"
    if not out.is_file() or out.stat().st_size < 100:
        # Prefer library download helper when available
        try:
            cif_path = alphafold_db.download_cif_for(pred, directory=str(structures_dir()))
            cif_path = Path(cif_path)
            if cif_path.resolve() != out.resolve():
                out.write_bytes(cif_path.read_bytes())
        except Exception:
            cif_url = pred.get("cifUrl")
            if not cif_url:
                raise
            r = httpx.get(cif_url, headers={"User-Agent": UA_NOTE}, timeout=90, follow_redirects=True)
            r.raise_for_status()
            out.write_bytes(r.content)
    return {
        "path": str(out),
        "entry_id": entry,
        "plddt_mean": pred.get("globalMetricValue"),
        "version": pred.get("latestVersion"),
    }
