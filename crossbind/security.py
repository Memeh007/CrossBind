"""Path-safe upload helpers."""

from __future__ import annotations

import re
from pathlib import Path

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._+-]+")


def safe_filename(name: str, default: str = "upload.bin") -> str:
    base = Path(name or default).name  # strip directories
    base = _SAFE_NAME.sub("_", base).strip("._")
    if not base or base in {".", ".."}:
        return default
    return base[:180]


def safe_job_id(job_id: str) -> str:
    jid = re.sub(r"[^a-zA-Z0-9_-]", "", job_id or "")
    if not jid:
        raise ValueError("Invalid job id")
    return jid


def assert_under(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    root_r = root.resolve()
    try:
        resolved.relative_to(root_r)
    except ValueError as exc:
        raise PermissionError("Path escapes allowed root") from exc
    return resolved
