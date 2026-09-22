"""Resolve protein queries (UniProt / gene / PDB) via library-first adapters."""

from __future__ import annotations

import re
from typing import Any

import httpx

from crossbind.discovery.structures import (
    UA_NOTE,
    download_pdb,
    recommend_structure,
    search_pdb_by_uniprot,
)

# PDB IDs: digit + 3 alnum (e.g. 6B1U)
_PDB_RE = re.compile(r"^[0-9][A-Za-z0-9]{3}$")
# Swiss-Prot / TrEMBL accessions (optional isoform suffix)
_UNIPROT_RE = re.compile(
    r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(?:-\d+)?$",
    re.IGNORECASE,
)

_SPECIES_TAXON = {
    "human": 9606,
    "homo sapiens": 9606,
    "mouse": 10090,
    "mus musculus": 10090,
}


def resolve_protein_query(q: str, *, species: str = "human") -> dict[str, Any]:
    """Detect PDB ID, UniProt accession, or gene symbol and resolve metadata + structures."""
    q = (q or "").strip()
    if not q:
        return {"ok": False, "error": "Empty query", "query": q}

    if _PDB_RE.match(q):
        return _resolve_pdb_id(q.upper())

    # Strip isoform for UniProt REST primary accession lookup
    base = q.split("-", 1)[0]
    if _UNIPROT_RE.match(q) or _UNIPROT_RE.match(base):
        return _resolve_uniprot(base.upper(), query=q)

    return _resolve_gene(q, species=species)


def list_structures_for_uniprot(uniprot: str) -> list[dict[str, Any]]:
    """Return structure candidates (experimental PDBs + AlphaFold fallback note)."""
    uniprot = (uniprot or "").strip().upper()
    if not uniprot:
        return []
    candidates: list[dict[str, Any]] = []
    pdb_ids: list[str] = []
    err = None
    try:
        pdb_ids = search_pdb_by_uniprot(uniprot)
    except Exception as exc:
        err = str(exc)
    # Prefer UniProt PDB cross-refs order when RCSB search is empty/slow
    if not pdb_ids:
        try:
            meta = fetch_uniprot_meta(uniprot)
            pdb_ids = list(meta.get("pdb_ids") or [])
        except Exception:
            pass
    for i, pid in enumerate(pdb_ids[:24]):
        candidates.append(
            {
                "pdb_id": pid,
                "provenance": "experimental_pdb",
                "label": "experimental",
                "rank": i + 1,
            }
        )
    if not candidates:
        candidates.append(
            {
                "pdb_id": None,
                "provenance": "alphafold_db",
                "label": "predicted",
                "rank": 1,
                "note": "No experimental PDB found — AlphaFold will be used if available.",
                "search_error": err,
            }
        )
    return candidates


def fetch_uniprot_meta(uniprot: str) -> dict[str, Any]:
    """Fetch gene / organism / name / PDB xrefs from UniProt REST."""
    uniprot = uniprot.strip().upper()
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot}.json"
    r = httpx.get(url, headers={"User-Agent": UA_NOTE, "Accept": "application/json"}, timeout=45)
    if r.status_code == 404:
        raise LookupError(f"UniProt accession not found: {uniprot}")
    r.raise_for_status()
    d = r.json()
    genes = d.get("genes") or []
    gene = None
    if genes:
        gn = genes[0].get("geneName") or {}
        gene = gn.get("value")
    pn = (
        ((d.get("proteinDescription") or {}).get("recommendedName") or {}).get("fullName") or {}
    ).get("value")
    if not pn:
        alts = (d.get("proteinDescription") or {}).get("submissionNames") or []
        if alts:
            pn = ((alts[0].get("fullName") or {}).get("value"))
    organism = (d.get("organism") or {}).get("scientificName")
    taxon = (d.get("organism") or {}).get("taxonId")
    pdb_ids = [
        x.get("id")
        for x in (d.get("uniProtKBCrossReferences") or [])
        if x.get("database") == "PDB" and x.get("id")
    ]
    function = None
    for c in d.get("comments") or []:
        if c.get("commentType") == "FUNCTION":
            texts = c.get("texts") or []
            if texts and texts[0].get("value"):
                function = texts[0]["value"]
                break
    if function and len(function) > 480:
        function = function[:477].rstrip() + "…"

    return {
        "uniprot": d.get("primaryAccession") or uniprot,
        "uniprot_id": d.get("uniProtkbId"),
        "gene": gene,
        "protein_name": pn,
        "organism": organism,
        "taxon": taxon,
        "pdb_ids": [str(x).upper() for x in pdb_ids],
        "entry_type": d.get("entryType"),
        "function": function,
    }


def _resolve_uniprot(uniprot: str, *, query: str | None = None) -> dict[str, Any]:
    try:
        meta = fetch_uniprot_meta(uniprot)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "query": query or uniprot, "kind": "uniprot"}
    candidates = list_structures_for_uniprot(meta["uniprot"])
    return {
        "ok": True,
        "kind": "uniprot",
        "query": query or uniprot,
        "gene": meta.get("gene"),
        "uniprot": meta.get("uniprot"),
        "organism": meta.get("organism"),
        "protein_name": meta.get("protein_name"),
        "taxon": meta.get("taxon"),
        "function": meta.get("function"),
        "candidates": candidates,
        "selected_pdb": (candidates[0].get("pdb_id") if candidates else None),
    }


def _resolve_gene(symbol: str, *, species: str = "human") -> dict[str, Any]:
    import mygene

    taxon = _SPECIES_TAXON.get(species.lower().strip(), species)
    mg = mygene.MyGeneInfo()
    # Prefer Swiss-Prot UniProt accessions
    res = mg.query(
        symbol,
        species=taxon if isinstance(taxon, int) else species,
        fields="symbol,name,taxid,uniprot,ensembl.gene",
        size=8,
    )
    hits = list(res.get("hits") or [])
    if not hits:
        return {
            "ok": False,
            "error": f"No MyGene hit for gene '{symbol}' (species={species})",
            "query": symbol,
            "kind": "gene",
        }

    # Prefer exact symbol match with Swiss-Prot
    def score(h: dict) -> tuple:
        sym = (h.get("symbol") or "").upper()
        want = symbol.upper()
        exact = 0 if sym == want else 1
        up = h.get("uniprot") or {}
        has_sp = 0 if (isinstance(up, dict) and up.get("Swiss-Prot")) else 1
        return (exact, has_sp, -float(h.get("_score") or 0))

    hits.sort(key=score)
    hit = hits[0]
    uniprot = _uniprot_from_mygene(hit)
    if not uniprot:
        return {
            "ok": False,
            "error": f"MyGene hit for '{symbol}' has no UniProt accession",
            "query": symbol,
            "kind": "gene",
            "mygene_hit": {"symbol": hit.get("symbol"), "name": hit.get("name")},
        }
    out = _resolve_uniprot(uniprot, query=symbol)
    out["kind"] = "gene"
    out["gene"] = out.get("gene") or hit.get("symbol") or symbol
    if not out.get("protein_name"):
        out["protein_name"] = hit.get("name")
    out["mygene_id"] = hit.get("_id")
    return out


def _uniprot_from_mygene(hit: dict) -> str | None:
    up = hit.get("uniprot")
    if isinstance(up, str) and up.strip():
        return up.strip().upper()
    if isinstance(up, dict):
        sp = up.get("Swiss-Prot")
        if isinstance(sp, list) and sp:
            return str(sp[0]).upper()
        if isinstance(sp, str) and sp.strip():
            return sp.strip().upper()
        tr = up.get("TrEMBL")
        if isinstance(tr, list) and tr:
            return str(tr[0]).upper()
        if isinstance(tr, str) and tr.strip():
            return tr.strip().upper()
    return None


def _resolve_pdb_id(pdb_id: str) -> dict[str, Any]:
    pdb_id = pdb_id.upper().strip()
    try:
        path = download_pdb(pdb_id)
    except Exception as exc:
        return {"ok": False, "error": f"Could not download PDB {pdb_id}: {exc}", "query": pdb_id, "kind": "pdb"}

    uniprot = None
    gene = None
    protein_name = None
    organism = None
    try:
        uniprot, gene, protein_name, organism = _pdb_to_uniprot_meta(pdb_id)
    except Exception:
        pass

    candidates = [{"pdb_id": pdb_id, "provenance": "experimental_pdb", "label": "experimental", "rank": 1}]
    if uniprot:
        # Include siblings so user can switch
        siblings = [c for c in list_structures_for_uniprot(uniprot) if c.get("pdb_id") != pdb_id]
        candidates.extend(siblings[:20])
        function = None
        try:
            meta = fetch_uniprot_meta(uniprot)
            gene = gene or meta.get("gene")
            protein_name = protein_name or meta.get("protein_name")
            organism = organism or meta.get("organism")
            function = meta.get("function")
        except Exception:
            function = None
    else:
        function = None

    return {
        "ok": True,
        "kind": "pdb",
        "query": pdb_id,
        "gene": gene,
        "uniprot": uniprot,
        "organism": organism,
        "protein_name": protein_name or f"PDB entry {pdb_id}",
        "function": function,
        "candidates": candidates,
        "selected_pdb": pdb_id,
        "path": str(path),
        "provenance": "experimental_pdb",
        "label": "experimental",
    }


def _pdb_to_uniprot_meta(pdb_id: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Best-effort UniProt / gene from RCSB polymer entities."""
    entry_url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
    r = httpx.get(entry_url, headers={"User-Agent": UA_NOTE}, timeout=45)
    r.raise_for_status()
    entry = r.json()
    title = (entry.get("struct") or {}).get("title")
    entity_ids = (entry.get("rcsb_entry_container_identifiers") or {}).get("polymer_entity_ids") or []
    uniprot = None
    for eid in entity_ids:
        eu = f"https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb_id}/{eid}"
        er = httpx.get(eu, headers={"User-Agent": UA_NOTE}, timeout=45)
        if er.status_code != 200:
            continue
        ids = (er.json().get("rcsb_polymer_entity_container_identifiers") or {})
        ups = ids.get("uniprot_ids") or []
        if ups:
            uniprot = str(ups[0]).upper()
            break
    return uniprot, None, title, None


def structure_for_selection(
    *,
    uniprot: str | None = None,
    pdb_id: str | None = None,
) -> dict[str, Any]:
    """Recommend / force a structure for docking from UniProt and/or PDB id."""
    uniprot = (uniprot or "").strip().upper() or None
    pdb_id = (pdb_id or "").strip().upper() or None
    if not uniprot and not pdb_id:
        return {"ok": False, "error": "Provide uniprot or pdb_id", "provenance": None}
    if pdb_id and not uniprot:
        # Direct PDB path
        try:
            path = download_pdb(pdb_id)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "provenance": None}
        up, _, title, _ = (None, None, None, None)
        try:
            up, _, title, _ = _pdb_to_uniprot_meta(pdb_id)
        except Exception:
            pass
        return {
            "ok": True,
            "provenance": "experimental_pdb",
            "label": "experimental",
            "pdb_id": pdb_id,
            "uniprot": up,
            "candidates": [pdb_id],
            "path": str(path),
            "format": "pdb",
            "warning": None,
            "title": title,
        }
    return recommend_structure(uniprot, pdb_id=pdb_id)


__all__ = [
    "resolve_protein_query",
    "list_structures_for_uniprot",
    "fetch_uniprot_meta",
    "structure_for_selection",
]
