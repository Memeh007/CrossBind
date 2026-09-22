"""End-to-end docking pipeline."""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from crossbind.config import resolve_gnina_bin, resolve_vina_bin
from crossbind.docking.gnina import run_gnina
from crossbind.docking.ligand import prepare_ligand
from crossbind.docking.process_registry import JobCancelled, check_cancel
from crossbind.docking.receptor import prepare_receptor
from crossbind.docking.rmsd import heavy_atom_rmsd
from crossbind.docking.vina import run_vina
from crossbind.analysis.admet import compute_admet
from crossbind.analysis.explain import build_explanation
from crossbind.analysis.interactions import annotate_interactions


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
    # Identity fields (Discover / manual) — persist into result.json
    job_title: str | None = None,
    ligand: dict[str, Any] | None = None,
    protein: dict[str, Any] | None = None,
    mechanism: str | None = None,
    job_id: str | None = None,
    pockets: list | None = None,
    pocket_rank_mode: str | None = None,
    top_k_pockets: int = 3,
    pocket_method: str | None = None,
) -> dict:
    log_lines: list[str] = []
    jid = job_id or job_dir.name

    def log(msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        log_lines.append(line)
        (job_dir / "job.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        if progress:
            progress(line)

    # Preserve identity / meta already written by app (queued result.json)
    prior: dict[str, Any] = {}
    prior_path = job_dir / "result.json"
    if prior_path.is_file():
        try:
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
        except Exception:
            prior = {}

    result: dict = {
        **prior,
        "status": "running",
        "id": prior.get("id") or jid,
        "compound_name": compound_name or prior.get("compound_name") or "ligand",
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
    if job_title is not None:
        result["job_title"] = job_title
    elif prior.get("job_title") and "job_title" not in result:
        result["job_title"] = prior["job_title"]
    if ligand is not None:
        result["ligand"] = ligand
    elif prior.get("ligand") is not None:
        result["ligand"] = prior["ligand"]
    if protein is not None:
        result["protein"] = protein
    elif prior.get("protein") is not None:
        result["protein"] = prior["protein"]
    if mechanism is not None:
        result["mechanism"] = mechanism
    elif "mechanism" in prior:
        result["mechanism"] = prior.get("mechanism")

    # Pocket provenance (Discover ligand-aware / P2Rank / holo)
    if pockets is not None:
        result["pockets"] = pockets
    elif prior.get("pockets") is not None:
        result["pockets"] = prior.get("pockets")
    if pocket_method is not None:
        result["pocket_method"] = pocket_method
    elif prior.get("pocket_method") is not None:
        result["pocket_method"] = prior.get("pocket_method")
    if prior.get("selected_pocket") is not None and "selected_pocket" not in result:
        result["selected_pocket"] = prior.get("selected_pocket")

    _write_meta(job_dir, result)

    try:
        job_dir.mkdir(parents=True, exist_ok=True)
        # Clear stale cancel flag only if caller forgot — leave CANCEL if user already cancelled
        check_cancel(job_dir)

        lig_pdbqt = job_dir / "ligand.pdbqt"
        rec_pdbqt = job_dir / "receptor.pdbqt"
        poses_out = job_dir / "poses.pdbqt"

        log("== CrossBind docking pipeline ==")
        check_cancel(job_dir)

        rank_mode = (pocket_rank_mode or prior.get("pocket_rank_mode") or "").lower().strip()
        pocket_list = pockets if pockets is not None else (prior.get("pockets") or [])

        if rank_mode in {"ligand_aware", "ligand_aware_vina", "auto"} and len(pocket_list) >= 1:
            from crossbind.discovery.ligand_aware import rank_pockets_for_ligand

            # Screen top-K pockets (lower exhaustiveness), then full dock on winner.
            screen_ex = min(max(int(exhaustiveness), 1), 4)
            screen_modes = min(max(int(num_modes), 1), 3)
            rank_res = rank_pockets_for_ligand(
                job_dir=job_dir,
                receptor_path=receptor_path,
                smiles=smiles,
                ligand_path=ligand_path,
                pockets=pocket_list,
                top_k=int(top_k_pockets or prior.get("top_k_pockets") or 3),
                exhaustiveness=screen_ex,
                num_modes=screen_modes,
                cpu=cpu,
                log=log,
                job_id=jid,
            )
            best = rank_res["selected_pocket"]
            center = tuple(float(x) for x in (best.get("center") or list(center)))
            size = tuple(float(x) for x in (best.get("size") or list(size)))
            result["center"] = list(center)
            result["size"] = list(size)
            result["pockets"] = rank_res["pockets"]
            result["selected_pocket"] = best
            result["pocket_method"] = "ligand_aware_vina"
            result["pocket_rank_label"] = rank_res.get("label")
            if isinstance(result.get("docking"), dict):
                result["docking"]["center"] = list(center)
                result["docking"]["size"] = list(size)
                result["docking"]["pocket_method"] = "ligand_aware_vina"
            _write_meta(job_dir, result)
            log(
                f"Ligand-aware screen picked {best.get('id')} "
                f"(screen affinity={best.get('docked_score')}). "
                "Running full dock on that box — label: best-ranked pocket "
                "for this ligand under Vina (not the true site, not Kd)."
            )

        prepare_ligand(
            smiles=smiles,
            ligand_path=ligand_path,
            out_pdbqt=lig_pdbqt,
            log=log,
        )
        check_cancel(job_dir)
        prepare_receptor(receptor_path, rec_pdbqt, log)
        check_cancel(job_dir)

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
                job_id=jid,
                job_dir=job_dir,
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
                job_id=jid,
                job_dir=job_dir,
            )
            result["vina_affinity"] = vres.affinity_kcal
            result["poses"] = vres.poses
            (job_dir / "engine_stdout.txt").write_text(vres.stdout, encoding="utf-8")
            log(f"Top pose vina_affinity = {vres.affinity_kcal} kcal/mol")

        check_cancel(job_dir)

        if reference_ligand and reference_ligand.is_file() and poses_out.is_file():
            log("Computing RMSD to reference ligand...")
            rms = heavy_atom_rmsd(reference_ligand, poses_out)
            result["rmsd_to_reference"] = rms
            log(f"RMSD to reference (Å) = {rms}")


        # Post-dock results science (ADMET + interactions) — never fail the job
        try:
            check_cancel(job_dir)
            log("Computing ADMET / drug-likeness (RDKit)...")
            smi = smiles
            if not smi:
                lig_meta = result.get("ligand") or prior.get("ligand") or {}
                smi = lig_meta.get("smiles") if isinstance(lig_meta, dict) else None
            if not smi and (job_dir / "resolved_smiles.txt").is_file():
                smi = (job_dir / "resolved_smiles.txt").read_text(encoding="utf-8").strip().split()[0]
            admet = compute_admet(
                smi,
                ligand_pdbqt=lig_pdbqt if lig_pdbqt.is_file() else None,
            )
            result["admet"] = admet
            if admet.get("ok"):
                log(
                    f"ADMET ok: MW={admet['descriptors'].get('mw', {}).get('value')} "
                    f"QED={admet['descriptors'].get('qed', {}).get('value')} "
                    f"Lipinski={'pass' if admet.get('rules', {}).get('lipinski', {}).get('pass') else 'fail'}"
                )
            else:
                log(f"ADMET warning: {admet.get('error')}")
        except Exception as admet_exc:
            log(f"ADMET warning (non-fatal): {admet_exc}")
            result["admet"] = {
                "ok": False,
                "error": str(admet_exc),
                "disclaimer": (
                    "Drug-likeness filters are research heuristics — not clinical ADMET."
                ),
            }

        try:
            check_cancel(job_dir)
            if poses_out.is_file() and rec_pdbqt.is_file():
                log("Annotating pose–protein interactions...")
                smi2 = smiles
                if not smi2:
                    lig_meta = result.get("ligand") or {}
                    smi2 = lig_meta.get("smiles") if isinstance(lig_meta, dict) else None
                interactions = annotate_interactions(
                    rec_pdbqt,
                    poses_out,
                    smiles=smi2,
                    top_n=num_modes or 9,
                )
                result["interactions"] = interactions
                if interactions.get("ok"):
                    n = len(interactions.get("top_pose") or [])
                    log(
                        f"Interactions ok via {interactions.get('tool')}: "
                        f"{n} contacts on top pose"
                    )
                else:
                    log(f"Interactions warning: {interactions.get('error')}")
            else:
                result["interactions"] = {
                    "ok": False,
                    "error": "poses or receptor missing",
                    "top_pose": [],
                    "by_pose": {},
                }
        except Exception as ix_exc:
            log(f"Interactions warning (non-fatal): {ix_exc}")
            result["interactions"] = {
                "ok": False,
                "error": str(ix_exc),
                "top_pose": [],
                "by_pose": {},
            }

        try:
            result["explanation"] = build_explanation(result)
            log("Evidence summary generated (deterministic).")
        except Exception as expl_exc:
            log(f"Explanation warning (non-fatal): {expl_exc}")
            result["explanation"] = (
                "Evidence summary unavailable. Docking score ≠ Kd; contacts are "
                "pose hypotheses; not medical advice."
            )

        result["status"] = "completed"
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["files"] = {
            "receptor_pdbqt": "receptor.pdbqt",
            "ligand_pdbqt": "ligand.pdbqt",
            "poses": "poses.pdbqt" if poses_out.is_file() else None,
            "log": "job.log",
        }
        log("DONE")
    except JobCancelled as exc:
        result["status"] = "cancelled"
        result["error"] = str(exc)
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        log(f"CANCELLED: {exc}")
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
