"""Auto docking-box: ligand centroid + padding, else protein centroid with warning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Common solvent / buffer residues to ignore as "reference ligands"
_IGNORE_RESN = {
    "HOH", "WAT", "H2O", "DOD", "TIP", "SOL",
    "SO4", "PO4", "NO3", "CL", "NA", "K", "MG", "CA", "ZN", "MN", "FE", "CU",
    "GOL", "EDO", "PEG", "PGE", "PG4", "DMS", "ACT", "ACE", "NH2", "FMT",
}


def auto_docking_box(
    structure_path: str | Path,
    *,
    padding: float = 8.0,
    default_size: float = 22.0,
    min_size: float = 12.0,
    max_size: float = 40.0,
) -> dict[str, Any]:
    """Compute center/size for Vina from crystal ligand or protein centroid."""
    path = Path(structure_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    coords_lig = _ligand_coords(path)
    if coords_lig:
        cx, cy, cz, sx, sy, sz, resn, chain = _box_from_coords(coords_lig, padding, min_size, max_size)
        return {
            "method": "ligand_centroid",
            "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
            "size": [round(sx, 3), round(sy, 3), round(sz, 3)],
            "ligand_resn": resn,
            "ligand_chain": chain,
            "warning": None,
            "nonzero": True,
        }

    coords_prot = _protein_coords(path)
    if not coords_prot:
        return {
            "method": "fallback_origin",
            "center": [0.0, 0.0, 0.0],
            "size": [default_size, default_size, default_size],
            "warning": "Could not parse atoms; box left at origin — set manually before docking.",
            "nonzero": False,
        }

    cx, cy, cz, _, _, _, _, _ = _box_from_coords(coords_prot, 0.0, default_size, default_size)
    return {
        "method": "protein_centroid",
        "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
        "size": [default_size, default_size, default_size],
        "warning": (
            "No crystal ligand found — using protein centroid. "
            "Verify the box covers the intended pocket before docking."
        ),
        "nonzero": abs(cx) + abs(cy) + abs(cz) > 1e-3,
    }


def _box_from_coords(
    coords: list[tuple[float, float, float, str, str]],
    padding: float,
    min_size: float,
    max_size: float,
) -> tuple[float, float, float, float, float, float, str, str]:
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    cz = sum(zs) / len(zs)
    sx = min(max((max(xs) - min(xs)) + 2 * padding, min_size), max_size)
    sy = min(max((max(ys) - min(ys)) + 2 * padding, min_size), max_size)
    sz = min(max((max(zs) - min(zs)) + 2 * padding, min_size), max_size)
    resn = coords[0][3]
    chain = coords[0][4]
    return cx, cy, cz, sx, sy, sz, resn, chain


def _ligand_coords(path: Path) -> list[tuple[float, float, float, str, str]]:
    """Collect non-solvent HETATM coords; pick the largest ligand group."""
    groups: dict[tuple[str, str, str], list[tuple[float, float, float, str, str]]] = {}
    suffix = path.suffix.lower()
    if suffix in {".cif", ".mmcif"}:
        groups = _het_groups_cif(path)
    else:
        groups = _het_groups_pdb(path)
    if not groups:
        return []
    # Largest atom count wins (druglike pocket ligand heuristic)
    best = max(groups.values(), key=len)
    if len(best) < 3:
        return []
    return best


def _het_groups_pdb(path: Path) -> dict[tuple[str, str, str], list]:
    groups: dict[tuple[str, str, str], list] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("HETATM"):
            continue
        resn = line[17:20].strip().upper()
        if resn in _IGNORE_RESN or len(resn) == 0:
            continue
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except ValueError:
            continue
        chain = line[21].strip() or "_"
        resi = line[22:26].strip()
        key = (chain, resi, resn)
        groups.setdefault(key, []).append((x, y, z, resn, chain))
    return groups


def _het_groups_cif(path: Path) -> dict[tuple[str, str, str], list]:
    """Lightweight mmCIF HETATM extract via Biopython when available."""
    groups: dict[tuple[str, str, str], list] = {}
    try:
        from Bio.PDB.MMCIFParser import MMCIFParser

        parser = MMCIFParser(QUIET=True)
        structure = parser.get_structure("rec", str(path))
        for model in structure:
            for chain in model:
                for residue in chain:
                    hetflag = residue.id[0]
                    if hetflag == " " or hetflag == "W":
                        continue
                    resn = residue.get_resname().strip().upper()
                    if resn in _IGNORE_RESN:
                        continue
                    key = (chain.id, str(residue.id[1]), resn)
                    for atom in residue:
                        coord = atom.get_coord()
                        groups.setdefault(key, []).append(
                            (float(coord[0]), float(coord[1]), float(coord[2]), resn, chain.id)
                        )
    except Exception:
        # Fallback: regex-ish scan of _atom_site loops is brittle; return empty
        return {}
    return groups


def _protein_coords(path: Path) -> list[tuple[float, float, float, str, str]]:
    coords: list[tuple[float, float, float, str, str]] = []
    suffix = path.suffix.lower()
    if suffix in {".cif", ".mmcif"}:
        try:
            from Bio.PDB.MMCIFParser import MMCIFParser

            parser = MMCIFParser(QUIET=True)
            structure = parser.get_structure("rec", str(path))
            for model in structure:
                for chain in model:
                    for residue in chain:
                        if residue.id[0] != " ":
                            continue
                        for atom in residue:
                            if atom.get_name().strip() != "CA":
                                continue
                            c = atom.get_coord()
                            coords.append(
                                (float(c[0]), float(c[1]), float(c[2]), residue.get_resname(), chain.id)
                            )
            return coords
        except Exception:
            pass
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM"):
            continue
        if line[12:16].strip() != "CA":
            continue
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except ValueError:
            continue
        resn = line[17:20].strip()
        chain = line[21].strip() or "_"
        coords.append((x, y, z, resn, chain))
    return coords
