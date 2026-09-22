"""Track running docking engine subprocesses so cancel can terminate them."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Optional

_lock = threading.Lock()
_procs: dict[str, subprocess.Popen] = {}


def register(job_id: str, proc: subprocess.Popen) -> None:
    with _lock:
        old = _procs.get(job_id)
        _procs[job_id] = proc
    if old is not None and old.poll() is None:
        try:
            old.terminate()
        except Exception:
            pass


def unregister(job_id: str, proc: subprocess.Popen | None = None) -> None:
    with _lock:
        cur = _procs.get(job_id)
        if proc is None or cur is proc:
            _procs.pop(job_id, None)


def get(job_id: str) -> Optional[subprocess.Popen]:
    with _lock:
        return _procs.get(job_id)


def kill(job_id: str) -> bool:
    """Terminate a tracked engine process. Returns True if a live proc was signaled."""
    with _lock:
        proc = _procs.get(job_id)
    if proc is None:
        return False
    if proc.poll() is not None:
        unregister(job_id, proc)
        return False
    try:
        proc.terminate()
    except Exception:
        try:
            proc.kill()
        except Exception:
            return False
    try:
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    unregister(job_id, proc)
    return True


def cancel_requested(job_dir: Path) -> bool:
    return (job_dir / "CANCEL").is_file()


class JobCancelled(Exception):
    """Raised when a CANCEL flag is observed mid-pipeline."""


def check_cancel(job_dir: Path) -> None:
    if cancel_requested(job_dir):
        raise JobCancelled("Cancelled by user")
