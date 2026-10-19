"""Boot splash probe (/api/boot) — read-only local cache / engine state."""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from crossbind import app as app_mod
from crossbind.discovery import planmine


def test_boot_status_missing_caches_are_not_created(tmp_path):
    disc = tmp_path / "cache" / "discovery.sqlite"
    pm = tmp_path / "cache" / "planmine_smed_rbh.sqlite"
    out = app_mod._boot_status(discovery_db=disc, planmine_db=pm, jobs_dir=tmp_path / "jobs")
    assert out["caches"]["discovery"] == {"present": False, "entries": 0}
    assert out["caches"]["orthologs"]["present"] is False
    assert out["caches"]["orthologs"]["source"] == "planmine_rbh"
    assert out["jobs"] == 0
    assert not disc.exists() and not pm.exists()


def test_boot_status_reads_existing_caches(tmp_path):
    disc = tmp_path / "discovery.sqlite"
    con = sqlite3.connect(disc)
    con.execute("CREATE TABLE entity_cache (kind TEXT, key TEXT, payload TEXT, fetched_at REAL)")
    con.executemany("INSERT INTO entity_cache VALUES (?, ?, '{}', 0)", [("drug", "a"), ("drug", "b"), ("ot", "c")])
    con.commit()
    con.close()

    pm = tmp_path / "planmine.sqlite"
    planmine.connect(pm).close()

    jobs = tmp_path / "jobs"
    (jobs / "job1").mkdir(parents=True)
    (jobs / ".gitkeep").write_text("")

    out = app_mod._boot_status(discovery_db=disc, planmine_db=pm, jobs_dir=jobs)
    assert out["caches"]["discovery"] == {"present": True, "entries": 3}
    ortho = out["caches"]["orthologs"]
    assert ortho["present"] is True
    assert ortho["mode"] == "seed"
    assert ortho["symbols"] == len(planmine.SEED_SYMBOLS)
    assert out["jobs"] == 1


def test_boot_route_reports_engines_and_caches():
    r = TestClient(app_mod.app).get("/api/boot")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["app"] == "ddOS"
    for key in ("vina_ok", "p2rank_ok", "gnina_ok", "caches", "jobs"):
        assert key in body
    assert set(body["caches"]) == {"discovery", "orthologs"}
