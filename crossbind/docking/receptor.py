"""Receptor preparation: PDB → rigid PDBQT via Open Babel (or passthrough)."""

from __future__ import annotations

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

    log("Preparing receptor PDB → PDBQT (rigid)")

    # Prefer pybel / openbabel Python bindings
    try:
        return _prepare_with_pybel(receptor_path, out_pdbqt, log)
    except Exception as py_err:
        log(f"Open Babel Python bindings unavailable ({py_err}); trying CLI")

    return _prepare_with_obabel_cli(receptor_path, out_pdbqt, log)


def _prepare_with_pybel(receptor_path: Path, out_pdbqt: Path, log) -> Path:
    try:
        from openbabel import openbabel as ob
    except ImportError:
        import openbabel as ob  # type: ignore

    conv = ob.OBConversion()
    conv.SetInAndOutFormats("pdb", "pdbqt")
    # rigid receptor
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
        raise RuntimeError(
            "Open Babel is required to convert PDB→PDBQT. "
            "Install Open Babel (https://openbabel.org) or upload a pre-made .pdbqt receptor."
        )
    # argv-list only
    cmd = [obabel, str(receptor_path), "-O", str(out_pdbqt), "-xr"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not out_pdbqt.is_file():
        raise RuntimeError(
            f"obabel failed (code {proc.returncode}): {proc.stderr or proc.stdout}"
        )
    log("Receptor PDBQT written via obabel CLI")
    return out_pdbqt
