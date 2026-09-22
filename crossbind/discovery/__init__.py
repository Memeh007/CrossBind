"""Cross Affinity discovery layer — library-first adapters (Slice 1)."""

from __future__ import annotations

from crossbind.discovery.drug import resolve_drug
from crossbind.discovery.orthologs import ortholog_panel
from crossbind.discovery.pharmacology import mechanism_summary
from crossbind.discovery.pocket import auto_docking_box
from crossbind.discovery.structures import recommend_structure
from crossbind.discovery.targets import resolve_targets

__all__ = [
    "resolve_drug",
    "resolve_targets",
    "recommend_structure",
    "auto_docking_box",
    "mechanism_summary",
    "ortholog_panel",
    "run_discovery",
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
    gene = None
    if preferred:
        for trow in targets:
            if trow.get("uniprot") == preferred and trow.get("gene"):
                gene = trow["gene"]
                break
    if not gene:
        for trow in targets:
            if trow.get("gene"):
                gene = trow["gene"]
                break
    orthos = ortholog_panel(gene=gene, uniprot=preferred)
    return {
        "drug": drug,
        "targets": targets,
        "structure": structure,
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
