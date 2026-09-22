"""Smoke: metformin name → CID / SMILES via PubChemPy adapter."""

from __future__ import annotations

from crossbind.discovery.drug import resolve_drug
from crossbind.pubchem import name_to_smiles


def test_resolve_metformin_cid_smiles():
    drug = resolve_drug("metformin")
    assert drug["cid"] == 4091
    assert drug["smiles"]
    assert "N" in drug["smiles"]  # guanide nitrogens
    assert drug["inchikey"]
    # ChEMBL id when UniChem/OT reachable
    if drug.get("chembl_id"):
        assert drug["chembl_id"].startswith("CHEMBL")


def test_name_to_smiles_metformin():
    smi = name_to_smiles("metformin")
    assert isinstance(smi, str) and len(smi) > 5
