"""Redock / RMSD helper when a reference ligand is provided."""

from __future__ import annotations

from pathlib import Path


def heavy_atom_rmsd(ref_path: Path, pose_path: Path) -> float | None:
    """Compute heavy-atom RMSD between reference and first pose (best effort)."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, rdMolAlign
    except ImportError:
        return None

    ref = _load_any(ref_path)
    mob = _load_any(pose_path)
    if ref is None or mob is None:
        return None

    ref = Chem.RemoveHs(ref)
    mob = Chem.RemoveHs(mob)
    if ref.GetNumAtoms() != mob.GetNumAtoms():
        # try match by SMARTS / atom order best-effort
        try:
            rms = rdMolAlign.GetBestRMS(mob, ref)
            return float(rms)
        except Exception:
            return None
    try:
        rms = AllChem.CalcRMS(mob, ref)
        return float(rms)
    except Exception:
        try:
            return float(rdMolAlign.GetBestRMS(mob, ref))
        except Exception:
            return None


def _load_any(path: Path):
    from rdkit import Chem

    s = path.suffix.lower()
    if s == ".pdbqt":
        # Strip PDBQT extras to PDB-like for RDKit
        lines = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(("ATOM", "HETATM")):
                lines.append(line[:66].ljust(66) + "\n")
            elif line.startswith("ENDMDL"):
                break
        block = "".join(lines)
        return Chem.MolFromPDBBlock(block, removeHs=False)
    if s == ".pdb":
        return Chem.MolFromPDBFile(str(path), removeHs=False)
    if s == ".sdf":
        suppl = Chem.SDMolSupplier(str(path), removeHs=False)
        return next((m for m in suppl if m is not None), None)
    if s == ".mol":
        return Chem.MolFromMolFile(str(path), removeHs=False)
    return None
