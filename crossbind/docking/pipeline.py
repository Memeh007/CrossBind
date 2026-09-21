"""End-to-end docking pipeline."""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from crossbind.config import resolve_gnina_bin, resolve_vina_bin
from crossbind.docking.gnina import run_gnina
from crossbind.docking.ligand import prepare_ligand
from crossbind.docking.receptor import prepare_receptor
from crossbind.docking.rmsd import heavy_atom_rmsd
from crossbind.docking.vina import run_vina


def run_docking_job(
    job_dir: Path,
    *,
    receptor_path: Path,
    smiles: str | None,
    ligand_path: Path | None,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    exhaustiveness: int = 8,
    num_modes: int = 9,
    cpu: int = 0,
    engine: str = "vina",
    reference_ligand: Path | None = None,
    compound_name: str = "ligand",
    progress: Callable[[str], None] | None = None,
) -> dict:
    log_lines: list[str] = []

    def log(msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        log_lines.append(line)
        (job_dir / "job.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        if progress:
            progress(line)

    result: dict = {
        "status": "running",
        "compound_name": compound_name,
        "engine": engine,
        "center": list(center),
        "size": list(size),
        "exhaustiveness": exhaustiveness,
        "vina_affinity": None,
        "gnina_cnn_score": None,
        "gnina_cnn_affinity": None,
        "poses": [],
        "rmsd_to_reference": None,
        "error": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_meta(job_dir, result)

    try:
        job_dir.mkdir(parents=True, exist_ok=True)
        lig_pdbqt = job_dir / "ligand.pdbqt"
        rec_pdbqt = job_dir / "receptor.pdbqt"
        poses_out = job_dir / "poses.pdbqt"

        log("== CrossBind docking pipeline ==")
        prepare_ligand(
            smiles=smiles,
            ligand_path=ligand_path,
            out_pdbqt=lig_pdbqt,
            log=log,
        )
        prepare_receptor(receptor_path, rec_pdbqt, log)

        eng = (engine or "vina").lower().strip()
        if eng == "gnina":
            gbin = resolve_gnina_bin()
            if not gbin:
                raise FileNotFoundError(
                    "GNINA requested but GNINA_BIN is not set / not found. "
                    "Install GNINA or choose the Vina engine."
                )
            gres = run_gnina(
                gnina_bin=gbin,
                receptor_pdbqt=rec_pdbqt,
                ligand_pdbqt=lig_pdbqt,
                out_poses=poses_out,
                center=center,
                size=size,
                exhaustiveness=exhaustiveness,
                num_modes=num_modes,
                cpu=cpu,
                log=log,
            )
            result["vina_affinity"] = gres.vina_affinity
            result["gnina_cnn_score"] = gres.cnn_score
            result["gnina_cnn_affinity"] = gres.cnn_affinity
            result["poses"] = gres.poses
            (job_dir / "engine_stdout.txt").write_text(gres.stdout, encoding="utf-8")
            log(
                f"Top pose: vina_affinity={gres.vina_affinity}  "
                f"gnina_cnn_score={gres.cnn_score}  gnina_cnn_affinity={gres.cnn_affinity}"
            )
        else:
            vbin = resolve_vina_bin()
            if not vbin:
                raise FileNotFoundError(
                    "AutoDock Vina binary not found. Set environment variable VINA_BIN "
                    "to the full path of vina (Linux) or vina.exe (Windows). "
                    "Download: https://github.com/ccsb-scripps/AutoDock-Vina/releases — "
                    "or place the binary in CrossBind/bin/."
                )
            vres = run_vina(
                vina_bin=vbin,
                receptor_pdbqt=rec_pdbqt,
                ligand_pdbqt=lig_pdbqt,
                out_poses=poses_out,
                center=center,
                size=size,
                exhaustiveness=exhaustiveness,
                num_modes=num_modes,
                cpu=cpu,
                log=log,
            )
            result["vina_affinity"] = vres.affinity_kcal
            result["poses"] = vres.poses
            (job_dir / "engine_stdout.txt").write_text(vres.stdout, encoding="utf-8")
            log(f"Top pose vina_affinity = {vres.affinity_kcal} kcal/mol")

        if reference_ligand and reference_ligand.is_file() and poses_out.is_file():
            log("Computing RMSD to reference ligand...")
            rms = heavy_atom_rmsd(reference_ligand, poses_out)
            result["rmsd_to_reference"] = rms
            log(f"RMSD to reference (Å) = {rms}")

        result["status"] = "completed"
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["files"] = {
            "receptor_pdbqt": "receptor.pdbqt",
            "ligand_pdbqt": "ligand.pdbqt",
            "poses": "poses.pdbqt" if poses_out.is_file() else None,
            "log": "job.log",
        }
        log("DONE")
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        log(f"FAILED: {exc}")
        log(traceback.format_exc()[-2000:])

    _write_meta(job_dir, result)
    return result


def _write_meta(job_dir: Path, result: dict) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
