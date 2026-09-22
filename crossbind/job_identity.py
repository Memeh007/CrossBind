"""Human-readable ligand × protein identity for docking jobs."""

from __future__ import annotations

from typing import Any


def ligand_block(drug: dict | None = None, *, compound_name: str | None = None) -> dict[str, Any]:
    """Normalize ligand fields from a Discover drug dict or manual dock form."""
    drug = drug or {}
    name = (
        compound_name
        or drug.get("input")
        or drug.get("name")
        or "ligand"
    )
    return {
        "compound_name": str(name).strip() or "ligand",
        "cid": drug.get("cid"),
        "chembl_id": drug.get("chembl_id"),
        "smiles": drug.get("smiles"),
        "inchikey": drug.get("inchikey"),
        "molecular_formula": drug.get("molecular_formula"),
        "iupac_name": drug.get("iupac_name"),
    }


def protein_block(
    *,
    gene: str | None = None,
    uniprot: str | None = None,
    protein_name: str | None = None,
    organism: str | None = None,
    structure: dict | None = None,
    function: str | None = None,
) -> dict[str, Any]:
    """Normalize protein + structure provenance for result.json / UI."""
    st = structure or {}
    provenance = st.get("provenance")
    label = st.get("label")
    if not label and provenance == "experimental_pdb":
        label = "experimental"
    elif not label and provenance == "alphafold_db":
        label = "predicted"
    pdb_or_af = st.get("pdb_id")
    return {
        "gene": gene,
        "uniprot": uniprot or st.get("uniprot"),
        "protein_name": protein_name,
        "organism": organism,
        "function": function,
        "pdb_id": pdb_or_af if label == "experimental" or provenance == "experimental_pdb" else None,
        "alphafold_id": pdb_or_af if label == "predicted" or provenance == "alphafold_db" else (
            pdb_or_af if provenance == "alphafold_db" else None
        ),
        "structure_id": pdb_or_af,
        "provenance": provenance,
        "label": label,
        "method": st.get("method"),
        "resolution_A": st.get("resolution_A"),
        "plddt_mean": st.get("plddt_mean"),
        "path": st.get("path"),
        "warning": st.get("warning"),
    }


def build_job_title(ligand: dict | None, protein: dict | None) -> str:
    """e.g. 'metformin × GPD2 (P43304) · PDB 5Z62' or 'metformin × PRKAA1 · AF-Q13131-F1'."""
    lig = ligand or {}
    prot = protein or {}
    left = lig.get("compound_name") or "ligand"
    gene = prot.get("gene")
    uniprot = prot.get("uniprot")
    if gene and uniprot:
        mid = f"{gene} ({uniprot})"
    elif gene:
        mid = str(gene)
    elif uniprot:
        mid = str(uniprot)
    else:
        mid = prot.get("protein_name") or "protein"

    label = (prot.get("label") or "").lower()
    sid = prot.get("structure_id") or prot.get("pdb_id") or prot.get("alphafold_id")
    if sid and (label == "experimental" or prot.get("provenance") == "experimental_pdb"):
        right = f"PDB {sid}"
    elif sid and (label == "predicted" or prot.get("provenance") == "alphafold_db" or str(sid).startswith("AF-")):
        right = str(sid) if str(sid).startswith("AF-") else f"AF-{sid}"
    elif sid:
        right = str(sid)
    else:
        right = None

    if right:
        return f"{left} × {mid} · {right}"
    return f"{left} × {mid}"


def mechanism_for_uniprot(targets: list | None, uniprot: str | None) -> str | None:
    if not uniprot or not targets:
        return None
    for t in targets:
        if (t.get("uniprot") or "").upper() == uniprot.upper():
            return t.get("mechanism") or None
    return None


def identity_from_discovery(payload: dict) -> dict[str, Any]:
    """Build ligand/protein/mechanism/job_title from a Discover payload."""
    drug = payload.get("drug") or {}
    structure = payload.get("structure") or {}
    selected = payload.get("selected_protein") or {}
    uniprot = (
        selected.get("uniprot")
        or payload.get("selected_uniprot")
        or structure.get("uniprot")
    )
    gene = selected.get("gene")
    if not gene and uniprot:
        for t in payload.get("targets") or []:
            if (t.get("uniprot") or "").upper() == str(uniprot).upper() and t.get("gene"):
                gene = t["gene"]
                break
    protein_name = selected.get("protein_name")
    organism = selected.get("organism")
    function = selected.get("function")
    ligand = ligand_block(drug)
    protein = protein_block(
        gene=gene,
        uniprot=uniprot,
        protein_name=protein_name,
        organism=organism,
        structure=structure,
        function=function,
    )
    # If alphafold id wrongly set for experimental, fix from provenance
    if protein.get("provenance") == "experimental_pdb":
        protein["pdb_id"] = structure.get("pdb_id")
        protein["alphafold_id"] = None
        protein["structure_id"] = structure.get("pdb_id")
        protein["label"] = "experimental"
    elif protein.get("provenance") == "alphafold_db":
        protein["alphafold_id"] = structure.get("pdb_id")
        protein["pdb_id"] = None
        protein["structure_id"] = structure.get("pdb_id")
        protein["label"] = "predicted"

    mech = selected.get("mechanism") or mechanism_for_uniprot(payload.get("targets"), uniprot)
    title = build_job_title(ligand, protein)
    predicted = (protein.get("provenance") == "alphafold_db") or (protein.get("label") == "predicted")
    honesty = {
        "not_medical_advice": True,
        "computational_hypotheses": True,
        "score_not_experimental_affinity": True,
        "structure_is_predicted": bool(predicted),
        "ortholog_not_identical_pharmacology": True,
        "message": (
            "Research triage only — not clinical advice. "
            "Docking scores are engine-specific ranks, not measured Kd/IC50."
        ),
    }
    return {
        "ligand": ligand,
        "protein": protein,
        "mechanism": mech,
        "job_title": title,
        "compound_name": ligand.get("compound_name"),
        "honesty": honesty,
    }


def identity_from_manual(
    *,
    compound_name: str,
    smiles: str | None = None,
    receptor_filename: str | None = None,
) -> dict[str, Any]:
    ligand = ligand_block({}, compound_name=compound_name)
    if smiles:
        ligand["smiles"] = smiles
    protein = {
        "gene": None,
        "uniprot": None,
        "protein_name": receptor_filename or "uploaded receptor",
        "organism": None,
        "function": None,
        "pdb_id": None,
        "alphafold_id": None,
        "structure_id": None,
        "provenance": "user_upload",
        "label": "uploaded",
        "method": None,
        "resolution_A": None,
        "plddt_mean": None,
        "path": None,
        "warning": None,
    }
    title = f"{ligand['compound_name']} × {protein['protein_name']}"
    return {
        "ligand": ligand,
        "protein": protein,
        "mechanism": None,
        "job_title": title,
        "compound_name": ligand["compound_name"],
    }
