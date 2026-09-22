"""ChEMBL mechanisms/targets + mygene UniProt mapping; Open Targets fallback."""

from __future__ import annotations

import time
from typing import Any

from crossbind.discovery.cache import get_json, set_json

UA_NOTE = "CrossAffinity/1.x (local research; Alexander Cecena)"


def resolve_targets(drug: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ranked target rows with optional UniProt accessions."""
    chembl_id = drug.get("chembl_id")
    cache_key = chembl_id or drug.get("inchikey") or drug.get("input") or ""
    cached = get_json("targets", cache_key)
    if cached is not None:
        return cached

    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    if chembl_id:
        try:
            rows = _chembl_mechanisms(chembl_id)
        except Exception as exc:
            errors.append(f"chembl: {exc}")

    if not rows and chembl_id:
        try:
            rows = _open_targets_mechanisms(chembl_id)
        except Exception as exc:
            errors.append(f"open_targets: {exc}")

    # Enrich with UniProt via mygene
    for row in rows:
        if row.get("uniprot"):
            continue
        gene = row.get("gene")
        if not gene:
            continue
        acc = _uniprot_for_gene(gene)
        if acc:
            row["uniprot"] = acc

    # Prefer rows with UniProt; de-prioritize MT-* mitochondrial genes for docking structures
    def _rank(r: dict) -> tuple:
        gene = (r.get("gene") or "")
        mt = 1 if gene.upper().startswith("MT-") else 0
        has_u = 0 if r.get("uniprot") else 1
        return (has_u, mt, gene)

    rows.sort(key=_rank)

    if errors and not rows:
        # Honest empty with error context
        set_json("targets", cache_key, [])
        return []

    set_json("targets", cache_key, rows)
    return rows


def _chembl_mechanisms(chembl_id: str) -> list[dict[str, Any]]:
    from chembl_webresource_client.new_client import new_client

    mechs = list(new_client.mechanism.filter(molecule_chembl_id=chembl_id)[:50])
    out: list[dict[str, Any]] = []
    for m in mechs:
        tid = m.get("target_chembl_id")
        gene = None
        uniprot = None
        tname = m.get("target_name") or m.get("mechanism_of_action")
        if tid:
            try:
                t = new_client.target.get(tid)
                comps = t.get("target_components") or []
                for c in comps:
                    for xref in c.get("target_component_xrefs") or []:
                        if (xref.get("xref_src_db") or "").upper() == "UNIPROT":
                            uniprot = xref.get("xref_id") or uniprot
                    gene = gene or c.get("gene_symbol") or c.get("component_synonym")
                tname = t.get("pref_name") or tname
            except Exception:
                pass
        out.append(
            {
                "source": "chembl",
                "mechanism": m.get("mechanism_of_action"),
                "action_type": m.get("action_type"),
                "target_chembl_id": tid,
                "target_name": tname,
                "gene": gene,
                "uniprot": uniprot,
                "direct": m.get("direct_interaction"),
            }
        )
    return out


def _open_targets_mechanisms(chembl_id: str) -> list[dict[str, Any]]:
    import httpx

    query = """
    query DrugMoA($id: String!) {
      drug(chemblId: $id) {
        id
        name
        mechanismsOfAction {
          rows {
            mechanismOfAction
            actionType
            targets { id approvedSymbol }
          }
        }
      }
    }
    """
    r = httpx.post(
        "https://api.platform.opentargets.org/api/v4/graphql",
        json={"query": query, "variables": {"id": chembl_id}},
        headers={"User-Agent": UA_NOTE},
        timeout=40,
    )
    r.raise_for_status()
    data = r.json().get("data") or {}
    drug = data.get("drug") or {}
    rows_in = ((drug.get("mechanismsOfAction") or {}).get("rows")) or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows_in:
        mech = row.get("mechanismOfAction")
        for t in row.get("targets") or []:
            gene = t.get("approvedSymbol")
            key = f"{gene}|{mech}"
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "source": "open_targets",
                    "mechanism": mech,
                    "action_type": row.get("actionType"),
                    "target_chembl_id": None,
                    "target_name": gene,
                    "gene": gene,
                    "ensembl_id": t.get("id"),
                    "uniprot": None,
                    "direct": None,
                }
            )
    return out


def _uniprot_for_gene(gene: str) -> str | None:
    gene = (gene or "").strip()
    if not gene:
        return None
    cached = get_json("uniprot_gene", gene, ttl_s=30 * 86400)
    if cached is not None:
        return cached.get("uniprot")
    acc = None
    try:
        import mygene

        mg = mygene.MyGeneInfo()
        res = mg.query(gene, species="human", fields="uniprot,symbol", size=1)
        hits = res.get("hits") or []
        if hits:
            u = hits[0].get("uniprot") or {}
            if isinstance(u, dict):
                swiss = u.get("Swiss-Prot")
                if isinstance(swiss, list):
                    acc = swiss[0] if swiss else None
                else:
                    acc = swiss
                if not acc:
                    trembl = u.get("TrEMBL")
                    if isinstance(trembl, list):
                        acc = trembl[0] if trembl else None
                    else:
                        acc = trembl
            elif isinstance(u, str):
                acc = u
    except Exception:
        acc = None
    set_json("uniprot_gene", gene, {"uniprot": acc})
    return acc
