"""SQLite response cache under data/cache/."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from crossbind.config import DATA_DIR

CACHE_DIR = DATA_DIR / "cache"
DB_PATH = CACHE_DIR / "discovery.sqlite"


def _conn() -> sqlite3.Connection:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=30)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS entity_cache (
            kind TEXT NOT NULL,
            key TEXT NOT NULL,
            payload TEXT NOT NULL,
            fetched_at REAL NOT NULL,
            PRIMARY KEY (kind, key)
        )
        """
    )
    con.commit()
    return con


def get_json(kind: str, key: str, *, ttl_s: float = 7 * 86400) -> Any | None:
    key = (key or "").strip().lower()
    if not key:
        return None
    with _conn() as con:
        row = con.execute(
            "SELECT payload, fetched_at FROM entity_cache WHERE kind=? AND key=?",
            (kind, key),
        ).fetchone()
    if not row:
        return None
    payload, fetched_at = row
    if ttl_s > 0 and (time.time() - float(fetched_at)) > ttl_s:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def set_json(kind: str, key: str, value: Any) -> None:
    key = (key or "").strip().lower()
    if not key:
        return
    with _conn() as con:
        con.execute(
            """
            INSERT INTO entity_cache(kind, key, payload, fetched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(kind, key) DO UPDATE SET
                payload=excluded.payload,
                fetched_at=excluded.fetched_at
            """,
            (kind, key, json.dumps(value), time.time()),
        )
        con.commit()


def structures_dir() -> Path:
    d = CACHE_DIR / "structures"
    d.mkdir(parents=True, exist_ok=True)
    return d
