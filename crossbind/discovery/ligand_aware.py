"""Ligand-aware pocket ranking: dock query ligand into top-K pockets with Vina.

Picks the pocket with the most negative Vina affinity. Labels are honest:
this is “best-ranked pocket for this ligand under Vina”, not the true site,
and not experimental Kd.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable

from crossbind.config import resolve_vina_bin
from crossbind.docking.ligand import prepare_ligand
from crossbind.docking.receptor import prepare_receptor
from crossbind.docking.vina import run_vina


def rank_pockets_for_ligand(
    *,
    job_dir: Path,
    receptor_path: Path,
    smiles: str | None,
    ligand_path: Path | None = None,
    pockets: list[dict[str, Any]],
    top_k: int = 3,
    exhaustiveness: int = 4,
    num_modes: int = 3,
    cpu: int = 0,
    log: Callable[[str], None] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Dock ligand into up to top_k pockets; return best by Vina affinity.

    Persists per-pocket ``p2rank_score`` (or prior score) + ``docked_score``.
    """
    def _log(msg: str) -> None:
        if log:
            log(msg)

    vina_bin = resolve_vina_bin()
    if not vina_bin:
        raise FileNotFoundError(
            "Vina binary required for ligand-aware pocket ranking. Set VINA_BIN."
        )

    # Prefer non-holo P2Rank pockets for ranking when present; include all ranked
    candidates = [dict(p) for p in (pockets or [])[:]]
    # Keep order: holo first in list is fine — user asked top-K; take first K
    # After holo-preferred propose, for ligand-aware we rank the top-K of the list
    # but skip nothing — docking into holo site for THIS ligand is valid.
    selected_list = candidates[: max(1, int(top_k))]
    if not selected_list:
        raise ValueError("No pockets to rank")

    job_dir = Path(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    work = job_dir / "pocket_rank"
    work.mkdir(parents=True, exist_ok=True)

    lig_pdbqt = work / "ligand.pdbqt"
    rec_pdbqt = work / "receptor.pdbqt"
    _log("== Ligand-aware pocket ranking (Vina) ==")
    _log(
        f"Docking into top-{len(selected_list)} pockets; "
        "best = most negative Vina affinity (not Kd)."
    )
    prepare_ligand(smiles=smiles, ligand_path=ligand_path, out_pdbqt=lig_pdbqt, log=_log)
    prepare_receptor(receptor_path, rec_pdbqt, _log)

    ranked: list[dict[str, Any]] = []
    for idx, pocket in enumerate(selected_list):
        center = pocket.get("center") or [0.0, 0.0, 0.0]
        size = pocket.get("size") or [22.0, 22.0, 22.0]
        cx, cy, cz = float(center[0]), float(center[1]), float(center[2])
        sx, sy, sz = float(size[0]), float(size[1]), float(size[2])
        out_poses = work / f"poses_{idx + 1}_{_safe_id(pocket.get('id') or idx)}.pdbqt"
        _log(
            f"Pocket {idx + 1}/{len(selected_list)}: {pocket.get('id')} "
            f"center=({cx:.2f},{cy:.2f},{cz:.2f}) prior_score={pocket.get('score')}"
        )
        try:
            vres = run_vina(
                vina_bin=vina_bin,
                receptor_pdbqt=rec_pdbqt,
                ligand_pdbqt=lig_pdbqt,
                out_poses=out_poses,
                center=(cx, cy, cz),
                size=(sx, sy, sz),
                exhaustiveness=int(exhaustiveness),
                num_modes=int(num_modes),
                cpu=int(cpu),
                log=_log,
                job_id=job_id,
                job_dir=job_dir,
            )
            affinity = vres.affinity_kcal
        except Exception as exc:
            _log(f"  Vina failed for pocket {pocket.get('id')}: {exc}")
            affinity = None
            out_poses = None

        entry = dict(pocket)
        entry["p2rank_score"] = pocket.get("score")
        entry["docked_score"] = affinity
        entry["vina_affinity"] = affinity
        entry["poses_path"] = str(out_poses) if out_poses else None
        ranked.append(entry)
        _log(f"  → vina_affinity={affinity}")

    # More negative is better; None sorts last
    def sort_key(e: dict[str, Any]) -> tuple:
        a = e.get("docked_score")
        if a is None:
            return (1, 0.0)
        return (0, float(a))

    ranked_sorted = sorted(ranked, key=sort_key)
    best = ranked_sorted[0]
    if best.get("docked_score") is None:
        raise RuntimeError(
            "Ligand-aware ranking failed for all pockets (no Vina affinities). "
            "Check VINA_BIN and receptor/ligand prep."
        )

    # Copy winning poses into job root for the rest of the pipeline / viewer
    winner_poses = best.get("poses_path")
    final_poses = job_dir / "poses.pdbqt"
    if winner_poses and Path(winner_poses).is_file():
        shutil.copy(winner_poses, final_poses)
    shutil.copy(lig_pdbqt, job_dir / "ligand.pdbqt")
    shutil.copy(rec_pdbqt, job_dir / "receptor.pdbqt")

    _log(
        f"Selected pocket {best.get('id')} with vina_affinity={best.get('docked_score')} "
        "(best-ranked pocket for this ligand under Vina — not the true site, not Kd)."
    )

    return {
        "selected_pocket": best,
        "pockets": ranked_sorted,
        "pocket_method": "ligand_aware_vina",
        "vina_affinity": best.get("docked_score"),
        "center": best.get("center"),
        "size": best.get("size"),
        "label": (
            "best-ranked pocket for this ligand under Vina "
            f"(pocket {best.get('id')}, affinity={best.get('docked_score')})"
        ),
        "honesty": (
            "Ligand-aware ranking docks the query ligand into top-K pocket hypotheses "
            "and picks the most negative Vina score. This is not experimental Kd and "
            "is not claimed to be the true binding site."
        ),
    }


def _safe_id(value: Any) -> str:
    s = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(value))
    return s[:48] or "pocket"
