"""Cross Affinity discovery layer — library-first adapters (Slice 1)."""

from __future__ import annotations

from typing import Any

from crossbind.discovery.drug import resolve_drug
from crossbind.discovery.orthologs import ortholog_panel
from crossbind.discovery.pharmacology import mechanism_summary
from crossbind.discovery.pocket import auto_docking_box
from crossbind.discovery.protein_lookup import (
    fetch_uniprot_meta,
    resolve_protein_query,
    structure_for_selection,
)
from crossbind.discovery.structures import recommend_structure
from crossbind.discovery.targets import resolve_targets
from crossbind.job_identity import identity_from_discovery, mechanism_for_uniprot

__all__ = [
    "resolve_drug",
    "resolve_targets",
    "recommend_structure",
    "auto_docking_box",
    "mechanism_summary",
    "ortholog_panel",
    "run_discovery",
    "refresh_for_target",
    "resolve_protein_query",
]


_DOCK_PREF = (
    "GPD2", "PRKAA1", "PRKAA2", "PRKAB1", "PRKAG1", "PRKAG2",
    "NDUFS2", "NDUFS1", "NDUFA10", "NDUFB8",
)


def _pick_uniprot(targets: list) -> str | None:
    """Prefer well-studied metformin-linked genes with UniProt for docking."""
    by_gene = {(t.get("gene") or "").upper(): t for t in targets if t.get("uniprot")}
    for g in _DOCK_PREF:
        if g in by_gene:
            return by_gene[g]["uniprot"]
    for trow in targets:
        if trow.get("uniprot") and not (trow.get("gene") or "").upper().startswith("MT-"):
            return trow["uniprot"]
    for trow in targets:
        if trow.get("uniprot"):
            return trow["uniprot"]
    return None


def _gene_for_uniprot(targets: list, uniprot: str | None) -> str | None:
    if not uniprot:
        return None
    for trow in targets:
        if (trow.get("uniprot") or "").upper() == uniprot.upper() and trow.get("gene"):
            return trow["gene"]
    return None


def _selected_protein_card(
    *,
    uniprot: str | None,
    gene: str | None = None,
    structure: dict | None = None,
    mechanism: str | None = None,
) -> dict[str, Any]:
    """Enrich a selected-protein card (function blurb, organism, name)."""
    card: dict[str, Any] = {
        "gene": gene,
        "uniprot": uniprot,
        "protein_name": None,
        "organism": None,
        "function": None,
        "mechanism": mechanism,
        "structure_label": (structure or {}).get("label"),
        "structure_id": (structure or {}).get("pdb_id"),
        "provenance": (structure or {}).get("provenance"),
        "method": (structure or {}).get("method"),
        "resolution_A": (structure or {}).get("resolution_A"),
        "plddt_mean": (structure or {}).get("plddt_mean"),
        "warning": (structure or {}).get("warning"),
    }
    if uniprot:
        try:
            meta = fetch_uniprot_meta(uniprot)
            card["gene"] = card["gene"] or meta.get("gene")
            card["protein_name"] = meta.get("protein_name")
            card["organism"] = meta.get("organism")
            card["function"] = meta.get("function")
            card["uniprot"] = meta.get("uniprot") or uniprot
        except Exception as exc:
            card["meta_error"] = str(exc)
    return card


def run_discovery(name: str, *, uniprot: str | None = None) -> dict:
    """Vertical slice: drug → targets → structure → pocket → mechanisms → orthologs."""
    drug = resolve_drug(name)
    targets = resolve_targets(drug)
    preferred = uniprot or _pick_uniprot(targets)
    structure = recommend_structure(preferred) if preferred else {
        "ok": False,
        "error": "No UniProt accession available for structure lookup",
        "provenance": None,
    }
    pocket = None
    if structure.get("ok") and structure.get("path"):
        pocket = auto_docking_box(structure["path"])
    pharm = mechanism_summary(drug, targets)
    gene = _gene_for_uniprot(targets, preferred)
    if not gene:
        for trow in targets:
            if trow.get("gene"):
                gene = trow["gene"]
                break
    orthos = ortholog_panel(gene=gene, uniprot=preferred)
    mech = mechanism_for_uniprot(targets, preferred)
    selected_protein = _selected_protein_card(
        uniprot=preferred, gene=gene, structure=structure, mechanism=mech
    )
    structure_candidates = []
    if preferred:
        try:
            from crossbind.discovery.protein_lookup import list_structures_for_uniprot
            structure_candidates = list_structures_for_uniprot(preferred)
        except Exception:
            structure_candidates = [
                {"pdb_id": structure.get("pdb_id"), "provenance": structure.get("provenance"), "label": structure.get("label")}
            ] if structure.get("pdb_id") else []
    out = {
        "drug": drug,
        "targets": targets,
        "selected_uniprot": preferred,
        "selected_protein": selected_protein,
        "structure": structure,
        "structure_candidates": structure_candidates,
        "pocket": pocket,
        "pharmacology": pharm,
        "orthologs": orthos,
        "honesty": {
            "not_medical_advice": True,
            "computational_hypotheses": True,
            "message": (
                "Not medical advice. Targets, mechanisms, and docking boxes are "
                "computational hypotheses for research triage — not clinical claims."
            ),
        },
    }
    # Attach a preview job title for the UI
    ident = identity_from_discovery(out)
    out["job_title_preview"] = ident.get("job_title")
    return out


def refresh_for_target(
    payload: dict,
    *,
    uniprot: str | None = None,
    pdb_id: str | None = None,
) -> dict:
    """Re-fetch structure, pocket, orthologs for a chosen UniProt and/or PDB id.

    Always updates selected_uniprot / selected_protein from the request (and targets
    list) even if structure fetch partially fails — so the UI selection sticks.
    """
    payload = dict(payload or {})
    uniprot = (uniprot or "").strip().upper() or None
    pdb_id = (pdb_id or "").strip().upper() or None
    if not uniprot and not pdb_id:
        raise ValueError("Provide uniprot or pdb_id")

    targets = payload.get("targets") or []
    # Commit selection identity first (before slow network) so callers always see it.
    gene = _gene_for_uniprot(targets, uniprot)
    mech = mechanism_for_uniprot(targets, uniprot)

    structure: dict[str, Any]
    try:
        structure = structure_for_selection(uniprot=uniprot, pdb_id=pdb_id)
    except Exception as exc:
        structure = {
            "ok": False,
            "error": str(exc),
            "provenance": None,
            "uniprot": uniprot,
            "pdb_id": pdb_id,
        }
    if structure.get("ok") and structure.get("uniprot") and not uniprot:
        uniprot = structure["uniprot"]
        gene = gene or _gene_for_uniprot(targets, uniprot)
        mech = mechanism_for_uniprot(targets, uniprot)

    pocket = None
    if structure.get("ok") and structure.get("path"):
        try:
            pocket = auto_docking_box(structure["path"])
        except Exception as exc:
            pocket = {"ok": False, "warning": f"Pocket failed: {exc}", "center": None, "size": None}

    try:
        selected_protein = _selected_protein_card(
            uniprot=uniprot, gene=gene, structure=structure, mechanism=mech
        )
    except Exception as exc:
        selected_protein = {
            "gene": gene,
            "uniprot": uniprot,
            "mechanism": mech,
            "meta_error": str(exc),
            "structure_label": (structure or {}).get("label"),
            "structure_id": (structure or {}).get("pdb_id"),
        }
    if not gene:
        gene = selected_protein.get("gene")
    # Prefer gene from the suggested-targets list when present
    list_gene = _gene_for_uniprot(targets, uniprot)
    if list_gene:
        selected_protein["gene"] = list_gene
        gene = list_gene

    try:
        orthos = ortholog_panel(gene=gene, uniprot=uniprot)
    except Exception as exc:
        orthos = {"disclaimer": f"Ortholog lookup failed: {exc}", "species": []}

    structure_candidates = []
    if uniprot:
        try:
            from crossbind.discovery.protein_lookup import list_structures_for_uniprot
            structure_candidates = list_structures_for_uniprot(uniprot)
        except Exception:
            if structure.get("pdb_id"):
                structure_candidates = [{
                    "pdb_id": structure.get("pdb_id"),
                    "provenance": structure.get("provenance"),
                    "label": structure.get("label"),
                }]

    payload["selected_uniprot"] = uniprot
    payload["selected_protein"] = selected_protein
    payload["structure"] = structure
    payload["structure_candidates"] = structure_candidates
    payload["pocket"] = pocket
    payload["orthologs"] = orthos
    try:
        ident = identity_from_discovery(payload)
        payload["job_title_preview"] = ident.get("job_title")
    except Exception:
        drug_name = ((payload.get("drug") or {}).get("input") or "ligand")
        payload["job_title_preview"] = f"{drug_name} × {gene or uniprot or 'target'}"
    return payload
