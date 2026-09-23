"""Isolated PoseBusters smoke — run BEFORE wiring into FastAPI job runner (AGENTS §2.7).

Usage (same venv as run.bat):
  .\\venv\\Scripts\\python.exe scripts\\smoke_posebusters.py path\\to\\protein.pdb path\\to\\ligand.sdf
"""
from __future__ import annotations
import sys
from pathlib import Path

def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: smoke_posebusters.py <protein.pdb> <ligand.sdf>")
        return 2
    protein, ligand = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        from posebusters import PoseBusters
    except ImportError as e:
        print("FAIL: posebusters not importable in this venv:", e)
        print("Install: pip install posebusters")
        print("Do NOT wire B2 into FastAPI until this smoke passes.")
        return 1
    # ddOS: predictive / non-cognate dock — no crystal mol_true (use dock, not redock)
    bust = PoseBusters(config="dock")
    df = bust.bust(mol_pred=str(ligand), mol_true=None, mol_cond=str(protein))
    print(df)
    print("OK: PoseBusters ran in this environment")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

