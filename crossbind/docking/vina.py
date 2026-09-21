"""AutoDock Vina 1.2.x CLI runner (argv-list only)."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VinaResult:
    affinity_kcal: float | None
    poses_path: Path
    stdout: str
    poses: list[dict] = field(default_factory=list)


_POSE_ROW = re.compile(
    r"^\s*(\d+)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
    re.MULTILINE,
)


def run_vina(
    *,
    vina_bin: str,
    receptor_pdbqt: Path,
    ligand_pdbqt: Path,
    out_poses: Path,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    exhaustiveness: int = 8,
    num_modes: int = 9,
    cpu: int = 0,
    log=None,
) -> VinaResult:
    if not Path(vina_bin).is_file() and not _on_path(vina_bin):
        raise FileNotFoundError(
            f"Vina binary not found: {vina_bin!r}. "
            "Set VINA_BIN to the full path of vina / vina.exe "
            "(download AutoDock Vina 1.2.x from https://github.com/ccsb-scripps/AutoDock-Vina/releases)."
        )

    cmd = [
        vina_bin,
        "--receptor",
        str(receptor_pdbqt),
        "--ligand",
        str(ligand_pdbqt),
        "--center_x",
        str(center[0]),
        "--center_y",
        str(center[1]),
        "--center_z",
        str(center[2]),
        "--size_x",
        str(size[0]),
        "--size_y",
        str(size[1]),
        "--size_z",
        str(size[2]),
        "--exhaustiveness",
        str(int(exhaustiveness)),
        "--num_modes",
        str(int(num_modes)),
        "--out",
        str(out_poses),
    ]
    if cpu and int(cpu) > 0:
        cmd.extend(["--cpu", str(int(cpu))])

    if log:
        log(f"Running Vina: {' '.join(cmd[:3])} ...")

    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
    }
    if sys.platform == "win32":
        # Hide console flash on Windows
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    proc = subprocess.run(cmd, **kwargs)  # argv list — never shell=True
    stdout = proc.stdout or ""
    if proc.returncode != 0:
        raise RuntimeError(f"Vina exited with code {proc.returncode}:\n{stdout[-4000:]}")

    poses = []
    for m in _POSE_ROW.finditer(stdout):
        poses.append(
            {
                "mode": int(m.group(1)),
                "affinity": float(m.group(2)),
                "rmsd_lb": float(m.group(3)),
                "rmsd_ub": float(m.group(4)),
            }
        )
    top = poses[0]["affinity"] if poses else None
    if top is None:
        # fallback: first mode line only
        m = re.search(r"^\s*1\s+([-+]?\d*\.?\d+)", stdout, re.MULTILINE)
        top = float(m.group(1)) if m else None

    return VinaResult(affinity_kcal=top, poses_path=out_poses, stdout=stdout, poses=poses)


def _on_path(name: str) -> bool:
    import shutil

    return shutil.which(name) is not None
