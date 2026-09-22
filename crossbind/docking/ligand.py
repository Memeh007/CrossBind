"""Ligand preparation: SMILES/file → 3D → Meeko PDBQT."""

from __future__ import annotations

from pathlib import Path


def smiles_to_mol(smiles: str):
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError("Invalid SMILES string")
    mol = Chem.AddHs(mol)
    conf_id = AllChem.EmbedMolecule(mol, randomSeed=42)
    if conf_id < 0:
        # fallback embedding
        conf_id = AllChem.EmbedMolecule(mol, useRandomCoords=True, randomSeed=42)
    if conf_id < 0:
        raise RuntimeError("RDKit failed to embed 3D conformer")
    try:
        AllChem.MMFFOptimizeMolecule(mol)
    except Exception:
        AllChem.UFFOptimizeMolecule(mol)
    return mol


def load_ligand_file(path: Path):
    from rdkit import Chem
    from rdkit.Chem import AllChem

    suffix = path.suffix.lower()
    mol = None
    if suffix in {".smi", ".smiles"}:
        text = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0]
        smiles = text.split()[0]
        return smiles_to_mol(smiles)
    if suffix == ".sdf":
        suppl = Chem.SDMolSupplier(str(path), removeHs=False)
        mol = next((m for m in suppl if m is not None), None)
    elif suffix == ".mol":
        mol = Chem.MolFromMolFile(str(path), removeHs=False)
    elif suffix == ".mol2":
        mol = Chem.MolFromMol2File(str(path), removeHs=False)
    elif suffix == ".pdb":
        mol = Chem.MolFromPDBFile(str(path), removeHs=False)
    elif suffix == ".pdbqt":
        # Already prepared — return None sentinel; caller copies file
        return None
    else:
        raise ValueError(f"Unsupported ligand format: {suffix}")

    if mol is None:
        raise ValueError(f"Could not parse ligand file: {path.name}")

    if mol.GetNumConformers() == 0:
        mol = Chem.AddHs(mol)
        if AllChem.EmbedMolecule(mol, randomSeed=42) < 0:
            raise RuntimeError("Failed to embed ligand from file")
        try:
            AllChem.MMFFOptimizeMolecule(mol)
        except Exception:
            AllChem.UFFOptimizeMolecule(mol)
    else:
        mol = Chem.AddHs(mol, addCoords=True)
    return mol


def mol_to_pdbqt(mol, out_path: Path) -> Path:
    from meeko import MoleculePreparation, PDBQTWriterLegacy

    preparator = MoleculePreparation()
    setups = preparator.prepare(mol)
    if not setups:
        raise RuntimeError("Meeko failed to generate a ligand setup")
    pdbqt_str, is_ok, error_msg = PDBQTWriterLegacy.write_string(setups[0])
    if not is_ok:
        raise RuntimeError(f"Meeko PDBQT writer failed: {error_msg}")
    out_path.write_text(pdbqt_str, encoding="utf-8")
    return out_path


def prepare_ligand(
    *,
    smiles: str | None = None,
    ligand_path: Path | None = None,
    out_pdbqt: Path,
    log,
) -> Path:
    if ligand_path and ligand_path.suffix.lower() == ".pdbqt":
        log("Ligand already PDBQT — copying")
        out_pdbqt.write_bytes(ligand_path.read_bytes())
        return out_pdbqt

    if smiles:
        log("SMILES → RDKit AddHs → EmbedMolecule → MMFFOptimize")
        mol = smiles_to_mol(smiles)
    elif ligand_path:
        log(f"Loading ligand file: {ligand_path.name}")
        mol = load_ligand_file(ligand_path)
        if mol is None:
            out_pdbqt.write_bytes(ligand_path.read_bytes())
            return out_pdbqt
    else:
        raise ValueError("Provide SMILES or a ligand file")

    log("Meeko MoleculePreparation → PDBQT")
    return mol_to_pdbqt(mol, out_pdbqt)
