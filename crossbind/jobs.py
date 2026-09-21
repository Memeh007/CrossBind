"""Job directory helpers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from crossbind.config import JOBS_DIR, ensure_dirs
from crossbind.security import assert_under, safe_job_id


def new_job_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]


def job_dir(job_id: str) -> Path:
    ensure_dirs()
    jid = safe_job_id(job_id)
    path = (JOBS_DIR / jid).resolve()
    assert_under(path, JOBS_DIR)
    return path


def list_jobs(limit: int = 50) -> list[dict]:
    ensure_dirs()
    items = []
    for p in sorted(JOBS_DIR.iterdir(), reverse=True):
        if not p.is_dir():
            continue
        meta = {"id": p.name, "status": "unknown"}
        rj = p / "result.json"
        if rj.is_file():
            try:
                meta.update(json.loads(rj.read_text(encoding="utf-8")))
            except Exception:
                pass
        meta["id"] = p.name
        items.append(meta)
        if len(items) >= limit:
            break
    return items


def read_result(job_id: str) -> dict:
    d = job_dir(job_id)
    rj = d / "result.json"
    if not rj.is_file():
        return {"id": job_id, "status": "missing"}
    data = json.loads(rj.read_text(encoding="utf-8"))
    data["id"] = job_id
    return data


def read_log(job_id: str) -> str:
    p = job_dir(job_id) / "job.log"
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")
