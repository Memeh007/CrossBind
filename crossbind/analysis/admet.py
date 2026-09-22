"""RDKit ADMET / drug-likeness descriptors for Cross Affinity jobs.

Filters (Lipinski, Veber, Ghose) are research heuristics for triage — not clinical ADMET.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


DISCLAIMER = (
    "Drug-likeness filters (Lipinski, Veber, Ghose) and RDKit physchem descriptors "
    "are research heuristics for triage — not clinical ADMET, PK, or toxicity predictions."
)


def _mol_from_smiles(smiles: str):
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles[:80]!r}")
    return mol


def _mol_from_pdbqt(path: Path, smiles: str | None = None):
    """Best-effort: prefer SMILES template; else parse REMARK SMILES from PDBQT."""
    from rdkit import Chem

    text = path.read_text(encoding="utf-8", errors="replace")
    smi = smiles
    if not smi:
        for line in text.splitlines():
            if line.startswith("REMARK SMILES ") and "IDX" not in line:
                smi = line.replace("REMARK SMILES", "", 1).strip()
                break
    if smi:
        return _mol_from_smiles(smi)
    # Last resort: strip PDBQT quirks → PDB-ish and let RDKit guess (often weak)
    pdb_lines = []
    for line in text.splitlines():
        if line.startswith(("ATOM", "HETATM")):
            # Drop autodock type columns past column 66 for PDB parser
            pdb_lines.append(line[:66].rstrip())
    if not pdb_lines:
        raise ValueError(f"No atoms in PDBQT: {path}")
    mol = Chem.MolFromPDBBlock("\n".join(pdb_lines) + "\n", removeHs=False, sanitize=False)
    if mol is None:
        raise ValueError(f"Could not parse ligand from {path.name}")
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        raise ValueError(f"Sanitize failed for {path.name}: {exc}") from exc
    return Chem.RemoveHs(mol)


def compute_admet(
    smiles: str | None = None,
    *,
    ligand_pdbqt: Path | str | None = None,
) -> dict[str, Any]:
    """Return descriptors + pass/fail flags with units and honesty disclaimer.

    Never raises for expected chemistry failures — returns ``ok: False`` + ``error``.
    """
    out: dict[str, Any] = {
        "ok": False,
        "tool": "rdkit",
        "tool_version": None,
        "smiles": smiles,
        "descriptors": {},
        "rules": {},
        "disclaimer": DISCLAIMER,
        "error": None,
    }
    try:
        from rdkit import Chem
        from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors

        out["tool_version"] = getattr(Chem, "rdBase", Chem).__dict__.get(
            "rdkitVersion", None
        ) or getattr(__import__("rdkit"), "__version__", "unknown")

        mol = None
        if smiles and smiles.strip():
            mol = _mol_from_smiles(smiles)
            out["smiles"] = Chem.MolToSmiles(mol)
        elif ligand_pdbqt:
            path = Path(ligand_pdbqt)
            mol = _mol_from_pdbqt(path, smiles=smiles)
            out["smiles"] = Chem.MolToSmiles(Chem.RemoveHs(mol)) if mol else smiles
        else:
            out["error"] = "Need SMILES or ligand.pdbqt"
            return out

        mw = float(Descriptors.MolWt(mol))
        logp = float(Crippen.MolLogP(mol))
        tpsa = float(Descriptors.TPSA(mol))
        hbd = int(Lipinski.NumHDonors(mol))
        hba = int(Lipinski.NumHAcceptors(mol))
        rotb = int(Lipinski.NumRotatableBonds(mol))
        heavy = int(Lipinski.HeavyAtomCount(mol))
        mr = float(Crippen.MolMR(mol))
        try:
            qed = float(QED.qed(mol))
        except Exception:
            qed = None

        desc = {
            "mw": {"value": round(mw, 2), "unit": "Da", "label": "Molecular weight"},
            "logp": {"value": round(logp, 3), "unit": "log10", "label": "cLogP (Crippen)"},
            "tpsa": {"value": round(tpsa, 2), "unit": "Å²", "label": "TPSA"},
            "hbd": {"value": hbd, "unit": "count", "label": "H-bond donors"},
            "hba": {"value": hba, "unit": "count", "label": "H-bond acceptors"},
            "rotb": {"value": rotb, "unit": "count", "label": "Rotatable bonds"},
            "heavy_atoms": {"value": heavy, "unit": "count", "label": "Heavy atoms"},
            "mr": {"value": round(mr, 2), "unit": "cm³/mol", "label": "Molar refractivity"},
            "qed": {"value": round(qed, 3) if qed is not None else None, "unit": "0–1", "label": "QED"},
        }
        out["descriptors"] = desc

        lipinski_fails = []
        if mw > 500:
            lipinski_fails.append("MW>500")
        if logp > 5:
            lipinski_fails.append("LogP>5")
        if hbd > 5:
            lipinski_fails.append("HBD>5")
        if hba > 10:
            lipinski_fails.append("HBA>10")

        veber_fails = []
        if rotb > 10:
            veber_fails.append("rotB>10")
        if tpsa > 140:
            veber_fails.append("TPSA>140")

        ghose_fails = []
        if not (160 <= mw <= 480):
            ghose_fails.append("MW not in 160–480")
        if not (-0.4 <= logp <= 5.6):
            ghose_fails.append("LogP not in −0.4–5.6")
        if not (20 <= heavy <= 70):
            ghose_fails.append("atoms not in 20–70")
        if not (40 <= mr <= 130):
            ghose_fails.append("MR not in 40–130")

        out["rules"] = {
            "lipinski": {
                "pass": len(lipinski_fails) == 0,
                "violations": len(lipinski_fails),
                "fails": lipinski_fails,
                "note": "Rule of Five (heuristic)",
            },
            "veber": {
                "pass": len(veber_fails) == 0,
                "fails": veber_fails,
                "note": "Veber oral bioavailability heuristic",
            },
            "ghose": {
                "pass": len(ghose_fails) == 0,
                "fails": ghose_fails,
                "note": "Ghose filter (optional; often strict for fragments)",
                "optional": True,
            },
        }
        out["ok"] = True
        return out
    except Exception as exc:
        out["error"] = str(exc)
        out["ok"] = False
        return out
