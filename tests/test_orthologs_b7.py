"""B7 ortholog resolver — offline tests on captured PRKAA1 responses + PlanMine fixture."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from crossbind.discovery import cache, orthologs, planmine

FIX = Path(__file__).parent / "fixtures" / "orthologs"
ALLOWED_METHODS = {"alliance", "diopt", "orthodb", "ensembl_compara", "planmine_rbh"}


def _load(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def _router(url: str, *, params=None, json_body=None, timeout=None):
    if "genenames.org/fetch/symbol/PRKAA1" in url:
        return _load("hgnc_PRKAA1.json")
    if "alliancegenome.org/api/gene/HGNC:9376/orthologs" in url:
        return _load("alliance_HGNC_9376.json")
    if "diopt_api/v9/get_orthologs_from_entrez/9606/5562/" in url:
        return _load(f"diopt_5562_{url.rstrip('/').split('/')[-2]}.json")
    if "rest.ensembl.org/homology/id/human/ENSG00000132356" in url:
        return _load("ensembl_homology_ENSG00000132356.json")
    if "rest.ensembl.org/lookup/id" in url:
        return _load("ensembl_lookup.json")
    if "orthodb.org/v12/genesearch" in url and (params or {}).get("query") == "Q13131":
        return _load("orthodb_genesearch_Q13131.json")
    if "orthodb.org/v12/orthologs" in url:
        return _load("orthodb_orthologs_PRKAA1.json")
    raise orthologs.SourceError(f"unexpected URL in test: {url}")


def _offline(*_a, **_k):
    raise orthologs.SourceError("ConnectError: network disabled in test")


def _planmine_offline(*_a, **_k):
    raise planmine.PlanMineError("PlanMine unreachable: network disabled in test")


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    """Fresh discovery cache + PlanMine DB seeded from the small test fixture; no network."""
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "cache" / "discovery.sqlite")
    pm_db = tmp_path / "planmine.sqlite"
    monkeypatch.setenv("CROSSBIND_PLANMINE_DB", str(pm_db))
    monkeypatch.setenv("CROSSBIND_PLANMINE_LIVE", "0")
    monkeypatch.setattr(planmine, "SEED_PATH", FIX / "planmine_smed_fixture.json")
    monkeypatch.setattr(planmine, "_post_query", _planmine_offline)
    monkeypatch.setattr(orthologs, "_http_json", _router)
    return tmp_path


def _rows(panel):
    return {r["species"]: r for r in panel["species"]}


def test_prkaa1_panel_maps_all_species(isolated):
    panel = orthologs.ortholog_panel(gene="PRKAA1", uniprot="Q13131")
    rows = _rows(panel)
    assert list(rows) == [sp["key"] for sp in orthologs.SPECIES]
    assert rows["human"]["status"] == "reference"
    assert rows["human"]["id"] == "HGNC:9376"
    for key in ("mouse", "rat", "zebrafish", "fly", "worm", "dog", "rabbit", "cat", "planaria"):
        assert rows[key]["status"] == "mapped", (key, rows[key]["note"])
        assert rows[key]["method"] in ALLOWED_METHODS
        assert rows[key]["banner"] == orthologs.ROW_BANNER
        assert rows[key]["ortholog_id"] == rows[key]["id"]

    mouse = rows["mouse"]
    assert (mouse["method"], mouse["id"], mouse["symbol"]) == ("alliance", "MGI:2145955", "Prkaa1")
    assert mouse["predicted"] is False
    assert mouse["identity"] == pytest.approx(98.7, abs=0.1)
    assert mouse["identity_source"] == "ensembl_compara"
    assert {e["method"] for e in mouse["evidence"]} >= {"diopt", "ensembl_compara"}

    fly = rows["fly"]
    assert fly["id"] == "FB:FBgn0023169"
    assert fly["relationship"] == "best forward only"
    # Ensembl's fly orthologues are different genes — identity must not be borrowed from them.
    assert fly["identity"] is None
    assert "different gene" in fly["note"]

    dog = rows["dog"]
    assert dog["method"] == "ensembl_compara" and dog["predicted"] is True
    assert dog["identity"] == pytest.approx(99.6, abs=0.1)
    assert dog["symbol"] == "PRKAA1"


def test_planaria_row_is_rbh_style_and_flagged(isolated):
    rows = _rows(orthologs.ortholog_panel(gene="PRKAA1", uniprot="Q13131"))
    pl = rows["planaria"]
    assert pl["method"] == "planmine_rbh"
    assert pl["id"] == "SMESG000055720"
    assert pl["predicted"] is True
    assert pl["reciprocal"] is False
    assert pl["confidence"] == "low"
    assert pl["identity"] is None
    assert "PRKAA2" in pl["note"] and "not reciprocal" in pl["note"]
    assert any(e["method"] == "orthodb" and e["id"] == "SMESG000055720" for e in pl["evidence"])


def test_panel_cached_second_call(isolated, monkeypatch):
    first = orthologs.ortholog_panel(gene="PRKAA1", uniprot="Q13131")
    monkeypatch.setattr(orthologs, "_http_json", _offline)
    t = time.perf_counter()
    second = orthologs.ortholog_panel(gene="PRKAA1", uniprot="Q13131")
    assert (time.perf_counter() - t) < 0.1
    assert second == first


def test_network_down_degrades_to_honest_unavailable(isolated, monkeypatch):
    monkeypatch.setattr(orthologs, "_http_json", _offline)
    monkeypatch.setattr(orthologs, "_mygene_identity", lambda gene: None)
    panel = orthologs.ortholog_panel(gene="PRKAA1", uniprot="Q13131")
    rows = _rows(panel)
    for key in ("mouse", "rat", "zebrafish", "fly", "worm", "dog", "rabbit", "cat"):
        assert rows[key]["status"] == "unavailable"
        assert rows[key]["id"] is None and rows[key]["method"] is None
        assert "Unavailable" in rows[key]["note"]
    # Planaria still resolves from the local PlanMine cache with no network at all.
    assert rows["planaria"]["status"] == "mapped"
    assert rows["planaria"]["method"] == "planmine_rbh"
    assert any(s["status"] == "unavailable" for s in panel["sources"])
    # Degraded panels are not cached: the next call retries the sources.
    assert cache.get_json("orthologs_b7", "PRKAA1|Q13131", ttl_s=0) is None


def test_one_source_down_falls_back_and_caches_short(isolated, monkeypatch):
    def router(url, **kw):
        if "rest.ensembl.org" in url:
            raise orthologs.SourceError("HTTP 503")
        return _router(url, **kw)

    monkeypatch.setattr(orthologs, "_http_json", router)
    panel = orthologs.ortholog_panel(gene="PRKAA1", uniprot="Q13131")
    rows = _rows(panel)
    assert panel["degraded"] is True
    assert rows["dog"]["status"] == "mapped" and rows["dog"]["method"] == "orthodb"
    assert rows["mouse"]["identity"] is None
    assert cache.get_json("orthologs_b7", "PRKAA1|Q13131", ttl_s=0) is None
    assert cache.get_json("orthologs_b7_degraded", "PRKAA1|Q13131", ttl_s=3600) == panel


def test_short_ensembl_model_flagged_partial():
    sp = next(s for s in orthologs.SPECIES if s["key"] == "rabbit")
    hit = {"id": "ENSOCUG00000031162", "symbol": None, "type": "ortholog_one2one",
           "perc_id": 23.9, "perc_id_target": 59.8, "taxonomy_level": "Eutheria"}
    row = orthologs._base_row(sp, "P54619")
    orthologs._ensembl_species_row(sp, row, {"ensembl_compara": orthologs._ok({"9986": [hit]}), "orthodb": None})
    assert row["status"] == "mapped" and row["identity"] == 23.9
    assert row["partial_model"] is True and row["confidence"] == "low"
    assert "partial gene model" in row["note"]


def test_http_json_retries_once_on_transient_status(monkeypatch):
    import httpx

    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        code = 503 if len(calls) == 1 else 200
        return httpx.Response(code, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(orthologs.time, "sleep", lambda s: None)
    assert orthologs._http_json("https://example.invalid/x") == {"ok": True}
    assert len(calls) == 2


def test_planaria_honest_miss_when_no_source_maps(isolated, monkeypatch):
    def router(url, **kw):
        if "orthodb.org/v12/orthologs" in url:
            data = [r for r in _load("orthodb_orthologs_PRKAA1.json")["data"] if r["taxon_id"] != "79327_0"]
            return {"data": data, "status": "ok"}
        if "genenames.org/fetch/symbol/PRKAB1" in url:
            doc = dict(_load("hgnc_PRKAA1.json")["response"]["docs"][0], symbol="PRKAB1")
            return {"response": {"docs": [doc]}}
        return _router(url.replace("PRKAB1", "PRKAA1"), **kw)

    monkeypatch.setattr(orthologs, "_http_json", router)
    pl = _rows(orthologs.ortholog_panel(gene="PRKAB1", uniprot="Q13131"))["planaria"]
    assert pl["status"] == "unmapped"
    assert pl["id"] is None and pl["method"] is None
    assert "Honest miss" in pl["note"] and "PlanMine" in pl["note"]


def test_planaria_unavailable_when_not_cached_and_offline(isolated, monkeypatch):
    res = planmine.planaria_lookup("NOTAGENE1")
    assert res["ok"] is False and res["hit"] is None
    assert "live PlanMine disabled" in res["error"]
    monkeypatch.setenv("CROSSBIND_PLANMINE_LIVE", "1")
    res = planmine.planaria_lookup("NOTAGENE1")
    assert res["ok"] is False and "unreachable" in res["error"]


def test_planmine_resolution_from_fixture(isolated):
    con = planmine.connect()
    try:
        a1 = planmine.resolve_symbol(con, "PRKAA1")
        a2 = planmine.resolve_symbol(con, "PRKAA2")
        g1 = planmine.resolve_symbol(con, "PRKAG1")
        assert planmine.is_covered(con, "PRKAB1")
        assert planmine.resolve_symbol(con, "PRKAB1") is None
    finally:
        con.close()
    assert a1["gene"] == a2["gene"] == "SMESG000055720"
    assert a1["reciprocal"] is False and a1["reverse_best_symbols"] == ["PRKAA2"]
    assert a2["reciprocal"] is True and a2["evalue"] == 0.0
    assert g1["reciprocal"] is True and g1["gene"] == "SMESG000037126"


def test_planmine_live_fill_parses_intermine_rows(isolated, monkeypatch):
    def fake(xml, **_k):
        if "Contig.blastHits.blastDomain.symbol" in xml and 'op="CONTAINS"' in xml:
            return [
                ["dd_Smed_v6_1_0_1", 2000, "NP_000001.1", "FAKE1 alias", 1e-80],
                ["dd_Smed_v6_2_0_1", 300, "NP_000009.1", "FAKE10 other", 1e-20],
            ]
        if "Association.contig.primaryIdentifier" in xml:
            return [["dd_Smed_v6_1_0_1", "SMESG000000001.1"]]
        if "Association.association.primaryIdentifier" in xml:
            return [["dd_Smed_v6_1_0_1", "SMESG000000001.1"], ["ox_Smed_v2_9", "SMESG000000001.1"]]
        if "Contig.primaryIdentifier" in xml:
            return [["ox_Smed_v2_9", 1500, "NP_000001.1", "FAKE1 alias", 1e-60]]
        raise AssertionError(xml)

    monkeypatch.setattr(planmine, "_post_query", fake)
    monkeypatch.setattr(planmine, "planmine_versions", lambda: {"planmine_release": "test"})
    con = planmine.connect()
    try:
        assert planmine.fetch_symbol(con, "FAKE1") == 1  # FAKE10 filtered by exact first token
        hit = planmine.resolve_symbol(con, "FAKE1")
    finally:
        con.close()
    assert hit["gene"] == "SMESG000000001" and hit["reciprocal"] is True
    assert hit["n_contigs"] == 1 and hit["contig"] == "dd_Smed_v6_1_0_1"


def test_committed_seed_covers_metformin_axis(tmp_path, monkeypatch):
    con = planmine.connect(tmp_path / "seed.sqlite")
    try:
        meta = planmine.cache_meta(con)
        assert meta["mode"] == "seed" and meta.get("planmine_release")
        for sym in planmine.SEED_SYMBOLS:
            assert planmine.is_covered(con, sym), sym
        hit = planmine.resolve_symbol(con, "MTOR")
        assert hit and hit["reciprocal"] is True
    finally:
        con.close()


def test_no_gene_gives_unavailable_rows(isolated):
    panel = orthologs.ortholog_panel(gene=None, uniprot=None)
    for r in panel["species"][1:]:
        assert r["status"] == "unavailable" and r["id"] is None
