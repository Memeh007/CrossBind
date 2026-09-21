"""Parse amino-acid residues from PDB/PDBQT for the residue browser."""

from __future__ import annotations

from pathlib import Path

# Standard amino acid three-letter codes
AA = {
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL",
    "SEC", "PYL", "MSE",  # common variants
}


def parse_residues(path: Path) -> list[dict]:
    """Return unique residues: chain, resi, resn, atom_count, center xyz."""
    seen: dict[tuple, dict] = {}
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        if len(line) < 54:
            continue
        try:
            resn = line[17:20].strip().upper()
            chain = line[21].strip() or "_"
            resi = line[22:26].strip()
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except (ValueError, IndexError):
            continue
        key = (chain, resi, resn)
        if key not in seen:
            seen[key] = {
                "chain": chain,
                "resi": resi,
                "resn": resn,
                "is_aa": resn in AA,
                "atom_count": 0,
                "sx": 0.0,
                "sy": 0.0,
                "sz": 0.0,
            }
        r = seen[key]
        r["atom_count"] += 1
        r["sx"] += x
        r["sy"] += y
        r["sz"] += z

    out = []
    for r in seen.values():
        n = max(r["atom_count"], 1)
        out.append(
            {
                "chain": r["chain"],
                "resi": r["resi"],
                "resn": r["resn"],
                "is_aa": r["is_aa"],
                "atom_count": r["atom_count"],
                "x": round(r["sx"] / n, 3),
                "y": round(r["sy"] / n, 3),
                "z": round(r["sz"] / n, 3),
                "label": f"{r['chain']}:{r['resn']}{r['resi']}",
            }
        )

    def sort_key(item: dict):
        try:
            ri = int("".join(c for c in item["resi"] if c.isdigit() or c == "-") or "0")
        except ValueError:
            ri = 0
        return (item["chain"], ri, item["resn"])

    out.sort(key=sort_key)
    return out
