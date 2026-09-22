"""Drug name → CID / SMILES / InChIKey via PubChemPy + RDKit sanitize."""

from __future__ import annotations

import time
from typing import Any

from rdkit import Chem

from crossbind.discovery.cache import get_json, set_json

UA_NOTE = "CrossAffinity/1.x (local research; Alexander Cecena)"

# Seed CIDs for common compounds when PubChem is busy
_KNOWN_CID = {
    "metformin": 4091,
    "aspirin": 2244,
    "ibuprofen": 3672,
}


def resolve_drug(name: str, *, retries: int = 3) -> dict[str, Any]:
    """Resolve a compound name to PubChem identity + RDKit-canonical SMILES."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Empty compound name")

    cached = get_json("drug", name)
    if cached:
        return cached

    last_err: Exception | None = None
    compounds = []
    try:
        import pubchempy as pcp
    except ImportError as exc:
        pcp = None
        last_err = exc

    if pcp is not None:
        for attempt in range(retries):
            try:
                compounds = pcp.get_compounds(name, "name")
                if compounds:
                    break
            except Exception as exc:
                last_err = exc
                time.sleep(0.8 * (attempt + 1))

        if not compounds and name.isdigit():
            try:
                compounds = pcp.get_compounds(int(name), "cid")
            except Exception as exc:
                last_err = exc

        if not compounds:
            known = _KNOWN_CID.get(name.lower())
            if known:
                try:
                    compounds = pcp.get_compounds(known, "cid")
                except Exception as exc:
                    last_err = exc

    if compounds:
        primary = compounds[0]
        smiles_raw = (
            getattr(primary, "smiles", None)
            or getattr(primary, "connectivity_smiles", None)
            or getattr(primary, "isomeric_smiles", None)
            or getattr(primary, "canonical_smiles", None)
        )
        if not smiles_raw:
            raise RuntimeError(f"PubChem returned no SMILES for {name!r}")
        mol = Chem.MolFromSmiles(smiles_raw)
        if mol is None:
            raise ValueError(f"RDKit could not parse SMILES from PubChem: {smiles_raw!r}")
        Chem.SanitizeMol(mol)
        smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
        inchikey = Chem.MolToInchiKey(mol) if hasattr(Chem, "MolToInchiKey") else primary.inchikey
        chembl_id = _chembl_id_for(name, inchikey or primary.inchikey)
        out = {
            "input": name,
            "cid": int(primary.cid),
            "smiles": smiles,
            "smiles_pubchem": smiles_raw,
            "inchikey": inchikey or primary.inchikey,
            "iupac_name": getattr(primary, "iupac_name", None),
            "molecular_formula": getattr(primary, "molecular_formula", None),
            "chembl_id": chembl_id,
            "candidates": [
                {
                    "cid": int(c.cid),
                    "smiles": getattr(c, "smiles", None) or getattr(c, "connectivity_smiles", None),
                    "inchikey": c.inchikey,
                }
                for c in compounds[:8]
            ],
            "source": "pubchempy",
            "ambiguous": len(compounds) > 1,
        }
        set_json("drug", name, out)
        return out

    # Fallback: legacy CACTUS / PUG (already in crossbind.pubchem)
    from crossbind.pubchem import name_to_smiles

    try:
        smiles_raw = name_to_smiles(name)
    except Exception as exc:
        raise RuntimeError(
            f"Could not resolve {name!r} via PubChemPy or CACTUS"
            + (f": PubChemPy={last_err}; CACTUS={exc}" if last_err else f": {exc}")
        ) from exc

    mol = Chem.MolFromSmiles(smiles_raw)
    if mol is None:
        # strip salts
        parts = smiles_raw.split(".")
        parts = sorted(parts, key=len, reverse=True)
        mol = Chem.MolFromSmiles(parts[0])
    if mol is None:
        raise ValueError(f"RDKit could not parse fallback SMILES: {smiles_raw!r}")
    Chem.SanitizeMol(mol)
    smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
    inchikey = Chem.MolToInchiKey(mol)
    cid = _KNOWN_CID.get(name.lower())
    chembl_id = _chembl_id_for(name, inchikey)
    out = {
        "input": name,
        "cid": cid,
        "smiles": smiles,
        "smiles_pubchem": smiles_raw,
        "inchikey": inchikey,
        "iupac_name": None,
        "molecular_formula": None,
        "chembl_id": chembl_id,
        "candidates": [],
        "source": "cactus_fallback",
        "ambiguous": False,
        "note": f"PubChemPy unavailable ({last_err}); used CACTUS/legacy fallback",
    }
    set_json("drug", name, out)
    return out


def _chembl_id_for(name: str, inchikey: str | None) -> str | None:
    """Best-effort ChEMBL ID via official client, UniChem, or Open Targets."""
    cache_key = (inchikey or name).lower()
    hit = get_json("chembl_id", cache_key, ttl_s=30 * 86400)
    if hit is not None:
        return hit.get("chembl_id")

    chembl_id = None
    # Prefer InChIKey lookup (stable)
    if inchikey:
        chembl_id = _chembl_by_inchikey(inchikey)
    if not chembl_id and inchikey:
        chembl_id = _chembl_via_unichem(inchikey)
    if not chembl_id:
        chembl_id = _chembl_by_name(name)
    if not chembl_id:
        chembl_id = _chembl_via_open_targets_search(name)

    set_json("chembl_id", cache_key, {"chembl_id": chembl_id})
    return chembl_id


def _chembl_via_unichem(inchikey: str) -> str | None:
    """UniChem src_id 1 = ChEMBL (no ChEMBL API required)."""
    try:
        import httpx

        r = httpx.get(
            f"https://www.ebi.ac.uk/unichem/rest/inchikey/{inchikey}",
            headers={"User-Agent": UA_NOTE},
            timeout=25,
        )
        if r.status_code != 200:
            return None
        for row in r.json():
            if str(row.get("src_id")) == "1":
                cid = row.get("src_compound_id")
                if cid and not str(cid).startswith("CHEMBL"):
                    return f"CHEMBL{cid}"
                return cid
    except Exception:
        return None
    return None


def _chembl_via_open_targets_search(name: str) -> str | None:
    try:
        import httpx

        query = """
        query Search($q: String!) {
          search(queryString: $q) { hits { id entity } }
        }
        """
        r = httpx.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": query, "variables": {"q": name}},
            headers={"User-Agent": UA_NOTE},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        for hit in ((r.json().get("data") or {}).get("search") or {}).get("hits") or []:
            if hit.get("entity") == "drug" and str(hit.get("id", "")).startswith("CHEMBL"):
                return hit["id"]
    except Exception:
        return None
    return None


def _chembl_by_inchikey(inchikey: str) -> str | None:
    try:
        from chembl_webresource_client.new_client import new_client

        rows = list(
            new_client.molecule.filter(molecule_structures__standard_inchi_key=inchikey).only(
                "molecule_chembl_id"
            )[:3]
        )
        if rows:
            return rows[0].get("molecule_chembl_id")
    except Exception:
        pass
    try:
        import httpx

        r = httpx.get(
            "https://www.ebi.ac.uk/chembl/api/data/molecule.json",
            params={"molecule_structures__standard_inchi_key": inchikey, "limit": 3},
            headers={"Accept": "application/json", "User-Agent": UA_NOTE},
            timeout=25,
        )
        if r.status_code == 200:
            mols = r.json().get("molecules") or []
            if mols:
                return mols[0].get("molecule_chembl_id")
    except Exception:
        pass
    return None


def _chembl_by_name(name: str) -> str | None:
    try:
        from chembl_webresource_client.new_client import new_client

        rows = list(new_client.molecule.search(name)[:5])
        for row in rows:
            syns = " ".join(
                s.get("molecule_synonym", "") if isinstance(s, dict) else str(s)
                for s in (row.get("molecule_synonyms") or [])
            ).lower()
            pref = (row.get("pref_name") or "").lower()
            if name.lower() in pref or name.lower() in syns or pref == name.lower():
                return row.get("molecule_chembl_id")
        if rows:
            return rows[0].get("molecule_chembl_id")
    except Exception:
        pass
    try:
        import httpx

        r = httpx.get(
            "https://www.ebi.ac.uk/chembl/api/data/molecule/search.json",
            params={"q": name},
            headers={"Accept": "application/json", "User-Agent": UA_NOTE},
            timeout=25,
        )
        if r.status_code == 200:
            mols = r.json().get("molecules") or []
            if mols:
                return mols[0].get("molecule_chembl_id")
    except Exception:
        pass
    return None
