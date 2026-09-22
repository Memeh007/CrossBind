"""Optional GNINA runner — scores kept separate from Vina affinity."""

from __future__ import annotations

import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from crossbind.docking.process_registry import (
    JobCancelled,
    cancel_requested,
    register,
    unregister,
)


@dataclass
class GninaResult:
    vina_affinity: float | None
    cnn_score: float | None
    cnn_affinity: float | None
    poses_path: Path
    stdout: str
    poses: list[dict] = field(default_factory=list)


def run_gnina(
    *,
    gnina_bin: str,
    receptor_pdbqt: Path,
    ligand_pdbqt: Path,
    out_poses: Path,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    exhaustiveness: int = 8,
    num_modes: int = 9,
    cpu: int = 0,
    log: Optional[Callable[[str], None]] = None,
    job_id: str | None = None,
    job_dir: Path | None = None,
) -> GninaResult:
    if not Path(gnina_bin).is_file():
        import shutil

        if not shutil.which(gnina_bin):
            raise FileNotFoundError(
                f"GNINA binary not found: {gnina_bin!r}. Set GNINA_BIN or install gnina."
            )

    cmd = [
        gnina_bin,
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
        log("Running GNINA (CNN rescoring)...")

    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    proc = subprocess.Popen(cmd, **kwargs)
    if job_id:
        register(job_id, proc)

    chunks: list[str] = []

    def _reader() -> None:
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                chunks.append(line)
        except Exception:
            pass

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()

    try:
        while True:
            if job_dir is not None and cancel_requested(job_dir):
                try:
                    proc.terminate()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                raise JobCancelled("Cancelled by user during GNINA")
            ret = proc.poll()
            if ret is not None:
                break
            time.sleep(0.35)
        reader.join(timeout=10)
    finally:
        if job_id:
            unregister(job_id, proc)

    stdout = "".join(chunks)
    if proc.returncode != 0:
        if job_dir is not None and cancel_requested(job_dir):
            raise JobCancelled("Cancelled by user during GNINA")
        raise RuntimeError(f"GNINA exited with code {proc.returncode}:\n{stdout[-4000:]}")

    poses = []
    row = re.compile(
        r"^\s*(\d+)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)",
        re.MULTILINE,
    )
    for m in row.finditer(stdout):
        poses.append(
            {
                "mode": int(m.group(1)),
                "vina_affinity": float(m.group(2)),
                "cnn_score": float(m.group(3)),
                "cnn_affinity": float(m.group(4)),
            }
        )

    top_vina = poses[0]["vina_affinity"] if poses else None
    top_cnn = poses[0]["cnn_score"] if poses else None
    top_cnn_aff = poses[0]["cnn_affinity"] if poses else None

    return GninaResult(
        vina_affinity=top_vina,
        cnn_score=top_cnn,
        cnn_affinity=top_cnn_aff,
        poses_path=out_poses,
        stdout=stdout,
        poses=poses,
    )
