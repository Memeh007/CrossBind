"""Receptor preparation: PDB -> rigid PDBQT (repair then Open Babel)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def prepare_receptor(receptor_path: Path, out_pdbqt: Path, log) -> Path:
    suffix = receptor_path.suffix.lower()
    if suffix == ".pdbqt":
        log("Receptor already PDBQT — copying")
        out_pdbqt.write_bytes(receptor_path.read_bytes())
        return out_pdbqt

    if suffix != ".pdb":
        raise ValueError("Receptor must be .pdb or .pdbqt")

    work_pdb = receptor_path
    repaired = out_pdbqt.with_name(out_pdbqt.stem + "_fixed.pdb")
    try:
        work_pdb = _maybe_pdbfixer(receptor_path, repaired, log)
    except Exception as fix_err:
        log(f"pdbfixer skipped ({fix_err}); using original PDB")
        work_pdb = receptor_path

    log("Preparing receptor PDB -> PDBQT (rigid)")

    try:
        return _prepare_with_pybel(work_pdb, out_pdbqt, log)
    except Exception as py_err:
        log(f"Open Babel Python bindings unavailable ({py_err}); trying CLI")

    return _prepare_with_obabel_cli(work_pdb, out_pdbqt, log)


def _maybe_pdbfixer(receptor_path: Path, out_pdb: Path, log) -> Path:
    """Optional OpenMM pdbfixer repair before PDBQT (missing atoms / nonstandard)."""
    try:
        from pdbfixer import PDBFixer
        from openmm.app import PDBFile
    except ImportError as e:
        raise RuntimeError("pdbfixer/openmm not installed") from e

    fixer = PDBFixer(filename=str(receptor_path))
    fixer.findMissingResidues()
    fixer.findNonstandardResidues()
    fixer.replaceNonstandardResidues()
    fixer.removeHeterogens(keepWater=False)
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()
    try:
        fixer.addMissingHydrogens(7.0)
    except Exception:
        pass
    with open(out_pdb, "w", encoding="utf-8") as fh:
        PDBFile.writeFile(fixer.topology, fixer.positions, fh)
    log("Receptor repaired via pdbfixer (missing atoms / nonstandard residues)")
    return out_pdb


def _prepare_with_pybel(receptor_path: Path, out_pdbqt: Path, log) -> Path:
    try:
        from openbabel import openbabel as ob
    except ImportError:
        import openbabel as ob  # type: ignore

    conv = ob.OBConversion()
    conv.SetInAndOutFormats("pdb", "pdbqt")
    conv.SetOptions("r", conv.OUTOPTIONS)
    mol = ob.OBMol()
    if not conv.ReadFile(mol, str(receptor_path)):
        raise RuntimeError("Open Babel failed to read receptor PDB")
    if not conv.WriteFile(mol, str(out_pdbqt)):
        raise RuntimeError("Open Babel failed to write receptor PDBQT")
    log("Receptor PDBQT written via Open Babel bindings")
    return out_pdbqt


def _prepare_with_obabel_cli(receptor_path: Path, out_pdbqt: Path, log) -> Path:
    obabel = shutil.which("obabel") or shutil.which("obabel.exe")
    if not obabel:
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python314" / "Scripts" / "obabel.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python312" / "Scripts" / "obabel.exe",
            Path(r"C:\Program Files\OpenBabel-3.1.1\obabel.exe"),
            Path(r"C:\Program Files\OpenBabel 3.1.1\obabel.exe"),
        ]
        for c in candidates:
            if c.is_file():
                obabel = str(c)
                break
    if not obabel:
        raise RuntimeError(
            "Open Babel is required to convert PDB->PDBQT. "
            "Install Open Babel (https://openbabel.org) or upload a pre-made .pdbqt receptor."
        )
    cmd = [obabel, str(receptor_path), "-O", str(out_pdbqt), "-xr"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not out_pdbqt.is_file():
        raise RuntimeError(
            f"obabel failed (code {proc.returncode}): {proc.stderr or proc.stdout}"
        )
    log("Receptor PDBQT written via obabel CLI")
    return out_pdbqt
