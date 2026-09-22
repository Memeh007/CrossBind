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


def holo_ligand_pocket(
    structure_path: str | Path,
    *,
    padding: float = 8.0,
    min_size: float = 12.0,
    max_size: float = 40.0,
) -> dict[str, Any] | None:
    """Return a pocket from co-crystallized HETATM ligand, or None if apo/unknown."""
    path = Path(structure_path)
    coords = _ligand_coords(path)
    if not coords:
        return None
    cx, cy, cz, sx, sy, sz, resn, chain = _box_from_coords(coords, padding, min_size, max_size)
    return {
        "id": f"holo_{resn}_{chain}",
        "rank": 0,
        "score": None,
        "probability": None,
        "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
        "size": [round(sx, 3), round(sy, 3), round(sz, 3)],
        "residues": [],
        "method": "holo_ligand",
        "source": "holo_ligand",
        "ligand_resn": resn,
        "ligand_chain": chain,
        "nonzero": True,
        "label": f"Holo crystal ligand {resn} (chain {chain})",
    }


def resolve_pockets(
    structure_path: str | Path,
    *,
    structure: dict | None = None,
    prefer_holo: bool = True,
    run_p2rank_when_holo: bool = False,
    top_k: int = 5,
    default_size: float = 22.0,
) -> dict[str, Any]:
    """Propose docking pockets with honesty about method.

    Preference order:
    1. Co-crystallized (holo) ligand site when present in the PDB.
    2. P2Rank hypotheses (``-c alphafold`` for AF/predicted structures).
    3. Centroid / existing auto-box fallback when P2Rank is missing.

    Never labeled as “the true site” — callers should present
    “best-ranked pocket for this ligand under Vina” after ligand-aware ranking.
    """
    from crossbind.discovery.p2rank import (
        is_alphafold_provenance,
        p2rank_available,
        run_p2rank,
    )

    path = Path(structure_path)
    pockets: list[dict[str, Any]] = []
    warnings: list[str] = []
    p2rank_ok = p2rank_available()
    af = is_alphafold_provenance(structure)
    p2rank_config = "alphafold" if af else "default"

    holo = holo_ligand_pocket(path) if prefer_holo else None
    if holo:
        pockets.append(holo)
        warnings.append(
            "Preferring co-crystallized (holo) ligand site when present. "
            "This is still a hypothesis for a *different* query ligand — "
            "not proof of the true binding site."
        )

    should_run_p2rank = p2rank_ok and (not holo or run_p2rank_when_holo or af)
    # For apo / AF / unknown: P2Rank is the primary proposer
    if not holo and p2rank_ok:
        should_run_p2rank = True
    if holo and not run_p2rank_when_holo and not af:
        should_run_p2rank = False

    if should_run_p2rank:
        try:
            predicted = run_p2rank(path, alphafold=af, visualizations=False)
            for p in predicted[: max(top_k, 1)]:
                p = dict(p)
                p["label"] = (
                    f"P2Rank {p.get('id')} (score={p.get('score')}, "
                    f"config={p.get('p2rank_config') or p2rank_config})"
                )
                pockets.append(p)
        except Exception as exc:
            warnings.append(f"P2Rank failed — using fallback. ({exc})")
            p2rank_ok = False

    if not pockets:
        # Graceful fallback to existing auto-box
        fb = auto_docking_box(path, default_size=default_size)
        method = fb.get("method") or "centroid_fallback"
        if method == "ligand_centroid":
            # Should have been caught as holo; treat as holo for consistency
            pocket_method = "holo_ligand"
        elif method == "protein_centroid":
            pocket_method = "centroid_fallback"
        else:
            pocket_method = "centroid_fallback"
        selected = {
            "id": "fallback",
            "rank": 1,
            "score": None,
            "probability": None,
            "center": fb.get("center"),
            "size": fb.get("size"),
            "residues": [],
            "method": pocket_method,
            "source": method,
            "ligand_resn": fb.get("ligand_resn"),
            "ligand_chain": fb.get("ligand_chain"),
            "nonzero": fb.get("nonzero"),
            "label": f"Fallback ({method})",
            "warning": fb.get("warning"),
        }
        if not p2rank_available():
            warnings.append(
                "P2Rank not installed — using centroid / crystal-ligand auto-box. "
                "Install P2Rank (Java 17+): https://github.com/rdk/p2rank — "
                "see README Windows notes or docs/ligand_aware_pockets.md."
            )
        if fb.get("warning"):
            warnings.append(fb["warning"])
        return {
            "ok": True,
            "pockets": [selected],
            "selected_pocket": selected,
            "pocket_method": pocket_method,
            "p2rank_available": p2rank_available(),
            "p2rank_config": None,
            "warning": " ".join(warnings) if warnings else None,
            # Backward-compatible flat fields (Discover UI / dock):
            "method": pocket_method,
            "center": selected.get("center"),
            "size": selected.get("size"),
            "ligand_resn": selected.get("ligand_resn"),
            "ligand_chain": selected.get("ligand_chain"),
            "nonzero": selected.get("nonzero", True),
        }

    # Default selection: holo if present, else top P2Rank
    selected = pockets[0]
    pocket_method = selected.get("method") or selected.get("source") or "p2rank"
    if pocket_method == "ligand_centroid":
        pocket_method = "holo_ligand"

    flat = {
        "ok": True,
        "pockets": pockets,
        "selected_pocket": selected,
        "pocket_method": pocket_method,
        "p2rank_available": p2rank_available(),
        "p2rank_config": p2rank_config if any(p.get("source") == "p2rank" for p in pockets) else None,
        "warning": " ".join(warnings) if warnings else None,
        "method": pocket_method,
        "center": selected.get("center"),
        "size": selected.get("size"),
        "ligand_resn": selected.get("ligand_resn"),
        "ligand_chain": selected.get("ligand_chain"),
        "nonzero": selected.get("nonzero", True),
        "honesty": (
            "Pockets are ranked hypotheses — never “the true site”. "
            "After ligand-aware docking, the UI labels the winner as "
            "best-ranked pocket for this ligand under Vina (not Kd)."
        ),
    }
    return flat


def select_pocket_by_id(pocket_payload: dict[str, Any], pocket_id: str | None) -> dict[str, Any]:
    """Return pocket_payload with selected_pocket updated to pocket_id (if found)."""
    out = dict(pocket_payload or {})
    pockets = list(out.get("pockets") or [])
    if not pocket_id or not pockets:
        return out
    for p in pockets:
        if str(p.get("id")) == str(pocket_id):
            out["selected_pocket"] = p
            out["method"] = p.get("method") or p.get("source")
            out["pocket_method"] = out["method"]
            out["center"] = p.get("center")
            out["size"] = p.get("size")
            out["ligand_resn"] = p.get("ligand_resn")
            out["ligand_chain"] = p.get("ligand_chain")
            return out
    return out
