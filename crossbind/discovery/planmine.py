"""PlanMine (S. mediterranea) ortholog cache — local SQLite built from PlanMine BLAST annotations.

PlanMine (InterMine) stores, for every planarian transcript contig, its best BLAST hit
per reference proteome (contig -> RefSeq protein, with e-value) and links contigs to
genome gene models (SMESG ids). We cache the Homo sapiens slice of that table plus the
contig -> gene links, then resolve a human symbol at gene level:

  forward:  human symbol G  -> contigs whose best human hit is G -> SMESG gene(s)
  reverse:  SMESG gene S    -> best human hit across all of S's contigs
  reciprocal (RBH-style)    =  reverse best of S* is G

Both directions come from PlanMine's precomputed contig->RefSeq BLAST table; this is
not an independent reverse BLAST. Build / refresh the cache with
``scripts/build_planmine_rbh_cache.py``. A small committed seed (metformin-axis genes)
initialises the DB so Discover works offline on first run.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

from crossbind.discovery.cache import CACHE_DIR

PLANMINE_URL = os.environ.get(
    "CROSSBIND_PLANMINE_URL", "http://planmine.mpinat.mpg.de/planmine"
).rstrip("/")
DB_PATH = CACHE_DIR / "planmine_smed_rbh.sqlite"
SEED_PATH = Path(__file__).resolve().parent / "data" / "planmine_smed_seed.json"

ORGANISM = "Schmidtea mediterranea"
REFERENCE_SPECIES = "Homo sapiens"
EVALUE_MAX = 1e-10
_CHUNK = 200

# Metformin-axis genes shipped in the seed (AMPK, LKB1, mTORC1/2, insulin/IGF, Complex I,
# mGPD, OCT/MATE transporters, sirtuin/FOXO nutrient sensing).
SEED_SYMBOLS = [
    "PRKAA1", "PRKAA2", "PRKAB1", "PRKAB2", "PRKAG1", "PRKAG2", "PRKAG3",
    "STK11", "MTOR", "RPTOR", "RICTOR", "INSR", "IGF1R", "FOXO3", "SIRT1",
    "NDUFS1", "NDUFS2", "NDUFV1", "GPD2", "SLC22A1", "SLC22A2", "SLC47A1",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS blast_hit (
    contig TEXT NOT NULL,
    assembly TEXT,
    contig_length INTEGER,
    refseq TEXT NOT NULL,
    symbol TEXT NOT NULL,
    symbol_line TEXT,
    evalue REAL,
    PRIMARY KEY (contig, refseq)
);
CREATE INDEX IF NOT EXISTS ix_blast_hit_symbol ON blast_hit(symbol);
CREATE TABLE IF NOT EXISTS contig_gene (
    contig TEXT NOT NULL,
    gene TEXT NOT NULL,
    PRIMARY KEY (contig, gene)
);
CREATE INDEX IF NOT EXISTS ix_contig_gene_gene ON contig_gene(gene);
CREATE TABLE IF NOT EXISTS queried_symbol (
    symbol TEXT PRIMARY KEY,
    fetched_at REAL,
    n_hits INTEGER,
    source TEXT
);
"""


class PlanMineError(RuntimeError):
    pass


def db_path() -> Path:
    return Path(os.environ.get("CROSSBIND_PLANMINE_DB") or DB_PATH)


def connect(path: Path | None = None, *, seed: bool = True) -> sqlite3.Connection:
    """Open (and initialise) the cache. Empty DBs are filled from the committed seed."""
    p = Path(path or db_path())
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p), timeout=30)
    con.executescript(_SCHEMA)
    if seed and _get_meta(con, "built_at") is None and SEED_PATH.is_file():
        load_seed(con, SEED_PATH)
    return con


def _get_meta(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(con: sqlite3.Connection, **kv: Any) -> None:
    con.executemany(
        "INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        [(k, str(v)) for k, v in kv.items()],
    )
    con.commit()


def cache_meta(con: sqlite3.Connection) -> dict[str, Any]:
    meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    meta["n_blast_hits"] = con.execute("SELECT COUNT(*) FROM blast_hit").fetchone()[0]
    meta["n_symbols_cached"] = con.execute("SELECT COUNT(*) FROM queried_symbol").fetchone()[0]
    return meta


def assembly_of(contig: str) -> str:
    parts = contig.split("_")
    return "_".join(parts[:3]) if len(parts) >= 3 else contig


def symbol_from_line(line: str | None) -> str:
    """PlanMine symbol field is 'OFFICIAL alias1 alias2 …'; the first token is the HGNC symbol."""
    return (line or "").strip().split(" ")[0].upper()


def insert_hits(con: sqlite3.Connection, rows: Iterable[tuple]) -> int:
    """rows: (contig, contig_length, refseq, symbol_line, evalue)."""
    data = [
        (c, assembly_of(c), length, refseq, symbol_from_line(line), line, ev)
        for c, length, refseq, line, ev in rows
        if c and refseq and symbol_from_line(line)
    ]
    con.executemany(
        """INSERT OR REPLACE INTO blast_hit
           (contig, assembly, contig_length, refseq, symbol, symbol_line, evalue)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        data,
    )
    return len(data)


def insert_contig_genes(con: sqlite3.Connection, rows: Iterable[tuple[str, str]]) -> int:
    data = [(c, g) for c, g in rows if c and g]
    con.executemany("INSERT OR IGNORE INTO contig_gene(contig, gene) VALUES (?, ?)", data)
    return len(data)


def mark_symbol(con: sqlite3.Connection, symbol: str, n_hits: int, source: str) -> None:
    con.execute(
        """INSERT INTO queried_symbol(symbol, fetched_at, n_hits, source) VALUES (?, ?, ?, ?)
           ON CONFLICT(symbol) DO UPDATE SET fetched_at=excluded.fetched_at,
             n_hits=excluded.n_hits, source=excluded.source""",
        (symbol.upper(), time.time(), int(n_hits), source),
    )


def is_covered(con: sqlite3.Connection, symbol: str) -> bool:
    if _get_meta(con, "complete") == "1":
        return True
    row = con.execute("SELECT 1 FROM queried_symbol WHERE symbol=?", (symbol.upper(),)).fetchone()
    return row is not None


# --- seed (committed JSON) ---------------------------------------------------------------


def load_seed(con: sqlite3.Connection, path: Path) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    insert_hits(con, [tuple(r) for r in data.get("blast_hits") or []])
    insert_contig_genes(con, [tuple(r) for r in data.get("contig_gene") or []])
    for sym, n in (data.get("symbols") or {}).items():
        mark_symbol(con, sym, n, "seed")
    meta = dict(data.get("meta") or {})
    meta.setdefault("built_at", meta.get("exported_at") or "seed")
    meta["mode"] = "seed"
    set_meta(con, **meta)
    con.commit()


def export_seed(con: sqlite3.Connection, symbols: list[str], path: Path) -> dict[str, Any]:
    """Write the slice of the cache needed to resolve ``symbols`` (forward + reverse rows)."""
    syms = [s.upper() for s in symbols]
    contigs: set[str] = set()
    for s in syms:
        contigs.update(r[0] for r in con.execute("SELECT contig FROM blast_hit WHERE symbol=?", (s,)))
    genes = _genes_for_contigs(con, contigs)
    all_contigs = set(contigs) | _contigs_for_genes(con, genes)
    hits = _hits_for_contigs(con, all_contigs)
    links = [
        r for r in con.execute("SELECT contig, gene FROM contig_gene").fetchall() if r[1] in genes
    ]
    counts = {
        s: con.execute("SELECT COUNT(*) FROM blast_hit WHERE symbol=?", (s,)).fetchone()[0] for s in syms
    }
    meta = {k: v for k, v in cache_meta(con).items() if k in ("planmine_url", "planmine_release", "planmine_api")}
    meta["exported_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out = {
        "meta": meta,
        "symbols": counts,
        "blast_hits": sorted(
            [h["contig"], h["contig_length"], h["refseq"], h["symbol_line"], h["evalue"]] for h in hits
        ),
        "contig_gene": sorted([list(r) for r in links]),
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(out, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"symbols": len(syms), "blast_hits": len(hits), "contig_gene": len(links)}


# --- resolution (pure SQL over the cache) ------------------------------------------------


def _hits_for_contigs(con: sqlite3.Connection, contigs: Iterable[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    lst = list(contigs)
    for i in range(0, len(lst), 500):
        chunk = lst[i : i + 500]
        q = ",".join("?" * len(chunk))
        for row in con.execute(
            f"""SELECT contig, assembly, contig_length, refseq, symbol, symbol_line, evalue
                FROM blast_hit WHERE contig IN ({q})""",
            chunk,
        ):
            out.append(dict(zip(
                ("contig", "assembly", "contig_length", "refseq", "symbol", "symbol_line", "evalue"), row
            )))
    return out


def _genes_for_contigs(con: sqlite3.Connection, contigs: Iterable[str]) -> set[str]:
    lst = list(contigs)
    genes: set[str] = set()
    for i in range(0, len(lst), 500):
        chunk = lst[i : i + 500]
        q = ",".join("?" * len(chunk))
        genes.update(r[0] for r in con.execute(f"SELECT gene FROM contig_gene WHERE contig IN ({q})", chunk))
    return genes


def _contigs_for_genes(con: sqlite3.Connection, genes: Iterable[str]) -> set[str]:
    lst = list(genes)
    contigs: set[str] = set()
    for i in range(0, len(lst), 500):
        chunk = lst[i : i + 500]
        q = ",".join("?" * len(chunk))
        contigs.update(r[0] for r in con.execute(f"SELECT contig FROM contig_gene WHERE gene IN ({q})", chunk))
    return contigs


def _ev(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 1.0


def resolve_symbol(
    con: sqlite3.Connection,
    symbol: str,
    *,
    evalue_max: float = EVALUE_MAX,
    prefer_genes: Iterable[str] = (),
) -> dict[str, Any] | None:
    """Gene-level RBH-style mapping for one human symbol, or None if PlanMine has no hit.

    ``prefer_genes`` (unversioned SMESG ids, e.g. from OrthoDB) only breaks ties between
    gene models with the same best forward e-value.
    """
    sym = symbol.upper()
    prefer = {g.split(".")[0] for g in prefer_genes}
    fwd = [
        dict(zip(("contig", "assembly", "contig_length", "refseq", "evalue"), r))
        for r in con.execute(
            "SELECT contig, assembly, contig_length, refseq, evalue FROM blast_hit WHERE symbol=? AND evalue<=?",
            (sym, evalue_max),
        )
    ]
    if not fwd:
        return None
    gene_of: dict[str, set[str]] = {}
    for c in {h["contig"] for h in fwd}:
        gene_of[c] = _genes_for_contigs(con, [c])

    # Best forward evidence per SMESG gene (contigs without a gene model stay contig-level).
    per_target: dict[str, dict[str, Any]] = {}
    for h in fwd:
        targets = gene_of.get(h["contig"]) or {""}
        for g in targets:
            key = g or h["contig"]
            t = per_target.setdefault(
                key,
                {"key": key, "gene": g or None, "contigs": set(), "assemblies": set(), "best": None, "own_ev": 1.0},
            )
            t["contigs"].add(h["contig"])
            t["assemblies"].add(h["assembly"])
            # SMEST* rows are the gene model's own predicted transcripts — the most direct evidence.
            if g and h["contig"].startswith("SMEST"):
                t["own_ev"] = min(t["own_ev"], _ev(h["evalue"]))
            b = t["best"]
            if b is None or (_ev(h["evalue"]), -(h["contig_length"] or 0)) < (
                _ev(b["evalue"]), -(b["contig_length"] or 0)
            ):
                t["best"] = h

    def rank(t: dict[str, Any]) -> tuple:
        return (
            _ev(t["best"]["evalue"]),
            0 if t["gene"] and t["gene"].split(".")[0] in prefer else 1,
            t["own_ev"],
            -len(t["contigs"]),
            -(t["best"]["contig_length"] or 0),
            t["key"],
        )

    ordered = sorted(per_target.values(), key=rank)
    top = ordered[0]
    tied = [
        t["gene"].split(".")[0]
        for t in ordered[1:]
        if t["gene"] and _ev(t["best"]["evalue"]) == _ev(top["best"]["evalue"])
    ]

    # Reverse: best human hit across every contig of the chosen gene model.
    rev_contigs = _contigs_for_genes(con, [top["gene"]]) if top["gene"] else set(top["contigs"])
    rev_hits = _hits_for_contigs(con, rev_contigs | set(top["contigs"]))
    best_rev_ev = min((_ev(h["evalue"]) for h in rev_hits), default=1.0)
    rev_symbols = sorted({h["symbol"] for h in rev_hits if _ev(h["evalue"]) == best_rev_ev})
    reciprocal = sym in rev_symbols
    best = top["best"]
    return {
        "gene": top["gene"].split(".")[0] if top["gene"] else None,
        "gene_versioned": top["gene"],
        "contig": best["contig"],
        "contig_length": best["contig_length"],
        "refseq": best["refseq"],
        "evalue": _ev(best["evalue"]),
        "assemblies": sorted(top["assemblies"]),
        "n_contigs": len(top["contigs"]),
        "reciprocal": reciprocal,
        "reverse_best_symbols": rev_symbols,
        "reverse_best_evalue": best_rev_ev,
        "other_genes": [t["gene"].split(".")[0] for t in ordered[1:4] if t["gene"]],
        "tied_genes": tied,
        "own_transcript_evalue": top["own_ev"] if top["own_ev"] < 1.0 else None,
        "evalue_max": evalue_max,
    }


# --- live PlanMine fill (InterMine path queries) -----------------------------------------


def _post_query(xml: str, *, timeout: float = 30.0) -> list[list[Any]]:
    import httpx

    try:
        r = httpx.post(
            f"{PLANMINE_URL}/service/query/results",
            data={"query": xml, "format": "json"},
            headers={"User-Agent": "ddOS-CrossBind/B7 (orthologs)"},
            timeout=timeout,
        )
    except Exception as exc:
        raise PlanMineError(f"PlanMine unreachable: {exc}") from exc
    if r.status_code != 200:
        raise PlanMineError(f"PlanMine HTTP {r.status_code}")
    try:
        payload = r.json()
    except ValueError as exc:
        raise PlanMineError("PlanMine returned non-JSON") from exc
    if payload.get("error"):
        raise PlanMineError(f"PlanMine error: {payload['error']}")
    return payload.get("results") or []


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _one_of(path: str, values: Iterable[str]) -> str:
    vals = "".join(f"<value>{_xml_escape(v)}</value>" for v in values)
    return f'<constraint path="{path}" op="ONE OF">{vals}</constraint>'


_HIT_VIEW = (
    "Contig.primaryIdentifier Contig.length Contig.blastHits.blastDomain.primaryIdentifier "
    "Contig.blastHits.blastDomain.symbol Contig.blastHits.score"
)
_ORG = f'<constraint path="Contig.organism.name" op="=" value="{ORGANISM}"/>'
_REF = f'<constraint path="Contig.blastHits.blastDomain.species" op="=" value="{REFERENCE_SPECIES}"/>'


def _q_hits_for_symbol(symbol: str) -> list[tuple]:
    xml = (
        f'<query model="genomic" view="{_HIT_VIEW}">'
        f'<constraint path="Contig.blastHits.blastDomain.symbol" op="CONTAINS" value="{_xml_escape(symbol)}"/>'
        f"{_ORG}{_REF}</query>"
    )
    return [tuple(r) for r in _post_query(xml) if symbol_from_line(r[3]) == symbol.upper()]


def _q_hits_for_contigs(contigs: list[str]) -> list[tuple]:
    out: list[tuple] = []
    for i in range(0, len(contigs), _CHUNK):
        xml = (
            f'<query model="genomic" view="{_HIT_VIEW}">'
            f'{_one_of("Contig.primaryIdentifier", contigs[i : i + _CHUNK])}{_REF}</query>'
        )
        out.extend(tuple(r) for r in _post_query(xml))
    return out


_ASSOC_VIEW = "Association.contig.primaryIdentifier Association.association.primaryIdentifier"
_ASSOC_GENE = '<constraint path="Association.type" op="=" value="associatedGene"/>'


def _q_genes_for_contigs(contigs: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i in range(0, len(contigs), _CHUNK):
        xml = (
            f'<query model="genomic" view="{_ASSOC_VIEW}">{_ASSOC_GENE}'
            f'{_one_of("Association.contig.primaryIdentifier", contigs[i : i + _CHUNK])}</query>'
        )
        out.extend((r[0], r[1]) for r in _post_query(xml))
    return out


def _q_contigs_for_genes(genes: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i in range(0, len(genes), _CHUNK):
        xml = (
            f'<query model="genomic" view="{_ASSOC_VIEW}">{_ASSOC_GENE}'
            f'{_one_of("Association.association.primaryIdentifier", genes[i : i + _CHUNK])}</query>'
        )
        out.extend((r[0], r[1]) for r in _post_query(xml))
    return out


def fetch_symbol(con: sqlite3.Connection, symbol: str) -> int:
    """Pull forward hits, gene links, and reverse hits for one symbol from live PlanMine."""
    sym = symbol.upper()
    fwd = _q_hits_for_symbol(sym)
    insert_hits(con, fwd)
    contigs = sorted({r[0] for r in fwd})
    if contigs:
        links = _q_genes_for_contigs(contigs)
        insert_contig_genes(con, links)
        genes = sorted({g for _, g in links})
        if genes:
            sibling_links = _q_contigs_for_genes(genes)
            insert_contig_genes(con, sibling_links)
            siblings = sorted({c for c, _ in sibling_links} - set(contigs))
            if siblings:
                insert_hits(con, _q_hits_for_contigs(siblings))
    mark_symbol(con, sym, len(fwd), "live")
    if _get_meta(con, "built_at") is None:
        set_meta(con, built_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), mode="live")
    if _get_meta(con, "planmine_release") is None:
        set_meta(con, **planmine_versions())
    set_meta(con, planmine_url=PLANMINE_URL)
    con.commit()
    return len(fwd)


def fetch_all(con: sqlite3.Connection, *, progress=print) -> dict[str, int]:
    """Bulk build: every S. mediterranea contig with a Homo sapiens BLAST hit + all gene links."""
    xml = f'<query model="genomic" view="{_HIT_VIEW}">{_ORG}{_REF}</query>'
    hits = _post_query(xml, timeout=900)
    n_hits = insert_hits(con, [tuple(r) for r in hits])
    progress(f"blast hits: {n_hits}")
    xml = (
        f'<query model="genomic" view="{_ASSOC_VIEW}">{_ASSOC_GENE}'
        f'<constraint path="Association.contig.organism.name" op="=" value="{ORGANISM}"/></query>'
    )
    links = _post_query(xml, timeout=900)
    n_links = insert_contig_genes(con, [(r[0], r[1]) for r in links])
    progress(f"contig->gene links: {n_links}")
    set_meta(
        con,
        complete="1",
        mode="full",
        built_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        planmine_url=PLANMINE_URL,
    )
    con.commit()
    return {"blast_hits": n_hits, "contig_gene": n_links}


def planmine_versions() -> dict[str, str]:
    import httpx

    out: dict[str, str] = {}
    for key, path in (("planmine_api", "/service/version"), ("planmine_release", "/service/version/release")):
        try:
            r = httpx.get(f"{PLANMINE_URL}{path}", timeout=15)
            if r.status_code == 200:
                out[key] = r.text.strip().strip('"')
        except Exception:
            pass
    return out


# --- public entry -------------------------------------------------------------------------


def planaria_lookup(
    symbol: str | None, *, allow_live: bool | None = None, prefer_genes: Iterable[str] = ()
) -> dict[str, Any]:
    """Cache-first PlanMine lookup. Returns {ok, covered, hit, error, source, cache}."""
    if allow_live is None:
        allow_live = os.environ.get("CROSSBIND_PLANMINE_LIVE", "1") != "0"
    sym = (symbol or "").strip().upper()
    if not sym:
        return {"ok": False, "covered": False, "hit": None, "error": "no human gene symbol", "source": None}
    try:
        con = connect()
    except sqlite3.Error as exc:
        return {"ok": False, "covered": False, "hit": None, "error": f"PlanMine cache error: {exc}", "source": None}
    try:
        source = "cache"
        error = None
        if not is_covered(con, sym):
            if allow_live:
                try:
                    fetch_symbol(con, sym)
                    source = "live"
                except PlanMineError as exc:
                    error = str(exc)
            else:
                error = "symbol not in local PlanMine cache and live PlanMine disabled"
        covered = is_covered(con, sym)
        hit = resolve_symbol(con, sym, prefer_genes=prefer_genes) if covered else None
        return {
            "ok": covered,
            "covered": covered,
            "hit": hit,
            "error": None if covered else error,
            "source": source,
            "cache": {k: v for k, v in cache_meta(con).items() if k != "planmine_url"},
        }
    finally:
        con.close()
