"""Cross-species ortholog resolver (B7): Alliance -> DIOPT -> OrthoDB, Ensembl Compara, PlanMine.

Per-species source chain (first mapped source wins; the others become concordance evidence):

  mouse / rat / zebrafish / fly / worm : Alliance (stringent) -> DIOPT v9 -> OrthoDB v12
  dog / rabbit / cat                   : Ensembl Compara -> OrthoDB v12
  planaria (S. mediterranea)           : PlanMine RBH-style SQLite cache -> OrthoDB v12

% identity comes only from Ensembl Compara, and only when Ensembl's ortholog is the same
gene as the row's mapping. Network failures degrade to ``unavailable`` rows; they are never
cached and never replaced with a guessed ortholog.
"""

from __future__ import annotations

import concurrent.futures as cf
from typing import Any, Callable

from crossbind.discovery import planmine
from crossbind.discovery.cache import get_json, set_json

UA = "ddOS-CrossBind/B7 (orthologs; local research tool)"
TTL_SOURCE_S = 30 * 86400
TTL_PANEL_S = 14 * 86400
PANEL_TIMEOUT_S = 75

ROW_BANNER = "Orthologs support translational hypothesis, not dose or MoA transfer."
DISCLAIMER = (
    "An ortholog is a sequence/evolutionary mapping, not evidence of the same drug response, "
    "binding site, dose, or mechanism. Planaria rows come from PlanMine BLAST annotations "
    "(RBH-style, not Alliance-curated) and OrthoDB clustering — predicted mappings. "
    "Docking against a human structure is not evidence of planarian target engagement."
)

SPECIES = [
    {"key": "human", "label": "Human", "taxon": 9606, "chain": []},
    {"key": "mouse", "label": "Mouse", "taxon": 10090, "chain": ["alliance", "diopt", "orthodb"]},
    {"key": "rat", "label": "Rat", "taxon": 10116, "chain": ["alliance", "diopt", "orthodb"]},
    {"key": "zebrafish", "label": "Zebrafish", "taxon": 7955, "chain": ["alliance", "diopt", "orthodb"]},
    {"key": "fly", "label": "Fruit fly", "taxon": 7227, "chain": ["alliance", "diopt", "orthodb"]},
    {"key": "worm", "label": "Worm (C. elegans)", "taxon": 6239, "chain": ["alliance", "diopt", "orthodb"]},
    {"key": "dog", "label": "Dog", "taxon": 9615, "chain": ["ensembl_compara", "orthodb"]},
    {"key": "rabbit", "label": "Rabbit", "taxon": 9986, "chain": ["ensembl_compara", "orthodb"]},
    {"key": "cat", "label": "Cat", "taxon": 9685, "chain": ["ensembl_compara", "orthodb"]},
    {
        "key": "planaria",
        "label": "Planaria (S. mediterranea)",
        "taxon": 79327,
        "chain": ["planmine_rbh", "orthodb"],
    },
]

SOURCE_NAMES = {
    "alliance": "Alliance of Genome Resources",
    "diopt": "DIOPT v9 (DRSC)",
    "orthodb": "OrthoDB v12",
    "ensembl_compara": "Ensembl Compara",
    "planmine_rbh": "PlanMine BLAST (RBH-style)",
}
# Consensus resources integrate several prediction methods; everything else is single-method.
CONSENSUS_METHODS = {"alliance", "diopt"}

ORTHODB_BASE = "https://data.orthodb.org/v12"
# Human-lineage OrthoDB levels, most specific first.
ORTHODB_LEVELS = [
    (9604, "Hominidae"), (9443, "Primates"), (314146, "Euarchontoglires"),
    (1437010, "Boreoeutheria"), (9347, "Eutheria"), (32525, "Theria"), (40674, "Mammalia"),
    (32523, "Tetrapoda"), (8287, "Sarcopterygii"), (117571, "Euteleostomi"), (7742, "Vertebrata"),
    (89593, "Craniata"), (7711, "Chordata"), (33511, "Deuterostomia"), (33213, "Bilateria"),
    (33208, "Metazoa"), (2759, "Eukaryota"),
]

DIOPT_ID_PREFIX = {"MGI": "MGI:", "RGD": "RGD:", "FlyBase": "FB:", "WormBase": "WB:", "ZFIN": "ZFIN:"}
_CONF_RANK = {"high": 0, "moderate": 1, "low": 2}


class SourceError(RuntimeError):
    pass


def _http_json(
    url: str,
    *,
    params: Any = None,
    json_body: Any = None,
    timeout: float = 25.0,
) -> Any:
    import httpx

    headers = {"Accept": "application/json", "User-Agent": UA}
    try:
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            r = httpx.post(url, json=json_body, headers=headers, timeout=timeout)
        else:
            r = httpx.get(url, params=params, headers=headers, timeout=timeout, follow_redirects=True)
    except Exception as exc:
        raise SourceError(f"{type(exc).__name__}: {exc}") from exc
    if r.status_code != 200:
        raise SourceError(f"HTTP {r.status_code}")
    try:
        return r.json()
    except ValueError as exc:
        raise SourceError("non-JSON response") from exc


def _cached(kind: str, key: str, fetch: Callable[[], Any]) -> Any:
    hit = get_json(kind, key, ttl_s=TTL_SOURCE_S)
    if hit is not None:
        return hit
    value = fetch()
    set_json(kind, key, value)
    return value


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "error": None, "data": data}


def _fail(exc: Exception | str) -> dict[str, Any]:
    return {"ok": False, "error": str(exc), "data": None}


def _curie(db: str, raw: Any) -> str:
    s = str(raw)
    prefix = DIOPT_ID_PREFIX.get(db, "")
    return s if not prefix or s.startswith(prefix) else prefix + s


def _bare(curie: str | None) -> str:
    s = (curie or "").strip()
    for p in ("FB:", "WB:", "ZFIN:"):
        if s.startswith(p):
            return s[len(p):]
    return s


# --- human identity (HGNC REST; MyGene fallback) ------------------------------------------


def _resolve_human(gene: str | None, uniprot: str | None) -> dict[str, Any]:
    key = (gene or uniprot or "").upper()

    def fetch() -> dict[str, Any]:
        docs: list[dict] = []
        if gene:
            docs = (_http_json(f"https://rest.genenames.org/fetch/symbol/{gene}").get("response") or {}).get(
                "docs"
            ) or []
        if not docs and uniprot:
            docs = (
                _http_json(f"https://rest.genenames.org/fetch/uniprot_ids/{uniprot}").get("response") or {}
            ).get("docs") or []
        if not docs:
            return {}
        d = docs[0]
        return {
            "symbol": d.get("symbol"),
            "hgnc_id": d.get("hgnc_id"),
            "entrez_id": d.get("entrez_id"),
            "ensembl_gene_id": d.get("ensembl_gene_id"),
            "uniprot": (d.get("uniprot_ids") or [None])[0],
            "source": "hgnc",
        }

    try:
        ident = _cached("hgnc_gene", key, fetch)
    except SourceError as exc:
        ident = _mygene_identity(gene) or {"error": str(exc)}
    out = dict(ident or {})
    out.setdefault("symbol", gene)
    if uniprot:
        out["uniprot"] = out.get("uniprot") or uniprot
    return out


def _mygene_identity(gene: str | None) -> dict[str, Any] | None:
    if not gene:
        return None
    try:
        import mygene

        res = mygene.MyGeneInfo().query(
            f"symbol:{gene}", species="human", fields="symbol,HGNC,entrezgene,ensembl.gene,uniprot", size=1
        )
        h = (res.get("hits") or [None])[0]
        if not h:
            return None
        ens = h.get("ensembl") or {}
        if isinstance(ens, list):
            ens = ens[0] if ens else {}
        up = (h.get("uniprot") or {}).get("Swiss-Prot")
        return {
            "symbol": h.get("symbol"),
            "hgnc_id": f"HGNC:{h['HGNC']}" if h.get("HGNC") else None,
            "entrez_id": str(h["entrezgene"]) if h.get("entrezgene") else None,
            "ensembl_gene_id": ens.get("gene"),
            "uniprot": up[0] if isinstance(up, list) else up,
            "source": "mygene",
        }
    except Exception:
        return None


# --- source adapters ----------------------------------------------------------------------


def alliance_orthologs(hgnc_id: str) -> dict[str, Any]:
    """Alliance gene->orthologs (stringent filter). Hits grouped by NCBI taxon."""

    def fetch() -> dict[str, list[dict[str, Any]]]:
        payload = _http_json(
            f"https://www.alliancegenome.org/api/gene/{hgnc_id}/orthologs",
            params={"stringencyFilter": "stringent", "limit": 500},
        )
        by_taxon: dict[str, list[dict[str, Any]]] = {}
        for r in payload.get("results") or []:
            g = r.get("geneToGeneOrthologyGenerated") or {}
            obj = g.get("objectGene") or {}
            taxon = str(((obj.get("taxon") or {}).get("curie") or "").replace("NCBITaxon:", ""))
            matched = [m.get("name") for m in g.get("predictionMethodsMatched") or []]
            not_matched = [m.get("name") for m in g.get("predictionMethodsNotMatched") or []]
            by_taxon.setdefault(taxon, []).append(
                {
                    "id": obj.get("primaryExternalId"),
                    "symbol": (obj.get("geneSymbol") or {}).get("displayText"),
                    "best": (g.get("isBestScore") or {}).get("name") == "Yes",
                    "best_rev": (g.get("isBestScoreReverse") or {}).get("name") == "Yes",
                    "confidence": (g.get("confidence") or {}).get("name"),
                    "methods": matched,
                    "methods_called": len(matched) + len(not_matched),
                }
            )
        return by_taxon

    try:
        return _ok(_cached("alliance_ortho", hgnc_id, fetch))
    except SourceError as exc:
        return _fail(exc)


def diopt_orthologs(entrez_id: str, taxon: int) -> dict[str, Any]:
    """DIOPT v9 human Entrez -> target species orthologs with method-count scores."""

    def fetch() -> list[dict[str, Any]]:
        payload = _http_json(
            f"https://www.flyrnai.org/tools/diopt/web/diopt_api/v9/get_orthologs_from_entrez/9606/{entrez_id}/{taxon}/none"
        )
        hits = []
        for v in ((payload.get("results") or {}).get(str(entrez_id)) or {}).values():
            hits.append(
                {
                    "id": _curie(v.get("species_specific_geneid_type") or "", v.get("species_specific_geneid")),
                    "symbol": v.get("symbol"),
                    "score": v.get("score"),
                    "max_score": v.get("max_score"),
                    "best": v.get("best_score") == "Yes",
                    "best_rev": v.get("best_score_rev") == "Yes",
                    "confidence": v.get("confidence"),
                }
            )
        return hits

    try:
        return _ok(_cached("diopt_ortho", f"{entrez_id}:{taxon}", fetch))
    except SourceError as exc:
        return _fail(exc)


def ensembl_orthologs(ensembl_gene_id: str, taxa: list[int]) -> dict[str, Any]:
    """Ensembl Compara homology by human gene id; symbols via POST /lookup/id."""

    def fetch() -> dict[str, list[dict[str, Any]]]:
        params = [("type", "orthologues"), ("sequence", "none"), ("cigar_line", "0")]
        params += [("target_taxon", str(t)) for t in taxa]
        payload = _http_json(
            f"https://rest.ensembl.org/homology/id/human/{ensembl_gene_id}", params=params, timeout=45
        )
        rows = []
        for block in payload.get("data") or []:
            for h in block.get("homologies") or []:
                if not str(h.get("type", "")).startswith("ortholog"):
                    continue
                tgt = h.get("target") or {}
                rows.append(
                    {
                        "taxon": str(tgt.get("taxon_id")),
                        "id": tgt.get("id"),
                        "protein_id": tgt.get("protein_id"),
                        "type": h.get("type"),
                        "perc_id": (h.get("source") or {}).get("perc_id"),
                        "perc_id_target": tgt.get("perc_id"),
                        "taxonomy_level": h.get("taxonomy_level"),
                        "symbol": None,
                    }
                )
        ids = [r["id"] for r in rows if r["id"]]
        if ids:
            try:
                looked = _http_json("https://rest.ensembl.org/lookup/id", json_body={"ids": ids}, timeout=30)
                for r in rows:
                    r["symbol"] = ((looked or {}).get(r["id"]) or {}).get("display_name")
            except SourceError:
                pass
        by_taxon: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            by_taxon.setdefault(r["taxon"], []).append(r)
        return by_taxon

    try:
        return _ok(_cached("ensembl_ortho_v2", ensembl_gene_id, fetch))
    except SourceError as exc:
        return _fail(exc)


def orthodb_orthologs(query: str, taxa: list[int]) -> dict[str, Any]:
    """OrthoDB v12: human gene by UniProt/symbol, then orthologs at the most specific shared level."""
    level_rank = {tid: i for i, (tid, _) in enumerate(ORTHODB_LEVELS)}
    level_name = dict(ORTHODB_LEVELS)

    def fetch() -> dict[str, Any]:
        found = _http_json(f"{ORTHODB_BASE}/genesearch", params={"query": query})
        org = (found.get("organism") or {}).get("name")
        gid = ((found.get("gene") or {}).get("gene_id") or {}).get("param")
        if org != "Homo sapiens" or not gid:
            return {"human_gene": None, "by_taxon": {}}
        species = ",".join(f"{t}_0" for t in taxa)
        payload = _http_json(f"{ORTHODB_BASE}/orthologs", params={"id": gid, "species": species})
        best: dict[str, dict[str, Any]] = {}
        for r in payload.get("data") or []:
            taxon = str(r.get("taxon_id") or "").split("_")[0]
            clade = int(r.get("clade_id") or 0)
            rank = level_rank.get(clade, len(ORTHODB_LEVELS))
            gene = r.get("gene") or {}
            cur = best.get(taxon)
            if cur is None or rank < cur["rank"]:
                best[taxon] = {"rank": rank, "clade_id": clade, "genes": []}
                cur = best[taxon]
            if rank == cur["rank"]:
                cur["genes"].append({"id": gene.get("id"), "odb_id": gene.get("param")})
        by_taxon = {
            t: {
                "level": v["clade_id"],
                "level_name": level_name.get(v["clade_id"], str(v["clade_id"])),
                "genes": v["genes"],
            }
            for t, v in best.items()
        }
        return {"human_gene": gid, "by_taxon": by_taxon}

    try:
        return _ok(_cached("orthodb_ortho", query, fetch))
    except SourceError as exc:
        return _fail(exc)


# --- row builders -------------------------------------------------------------------------


def _base_row(sp: dict[str, Any], query_id: str | None) -> dict[str, Any]:
    return {
        "species": sp["key"],
        "label": sp["label"],
        "taxon": sp["taxon"],
        "status": "unavailable",
        "symbol": None,
        "id": None,
        "query_id": query_id,
        "ortholog_id": None,
        "identity": None,
        "identity_target": None,
        "identity_source": None,
        "method": None,
        "source": None,
        "confidence": None,
        "predicted": None,
        "relationship": None,
        "evidence": [],
        "note": None,
        "banner": ROW_BANNER,
    }


def _mapped(row: dict[str, Any], *, method: str, id_: str | None, symbol: str | None, **extra: Any) -> None:
    row.update(
        {
            "status": "mapped",
            "method": method,
            "source": SOURCE_NAMES[method],
            "id": id_,
            "ortholog_id": id_,
            "symbol": symbol,
            "predicted": method not in CONSENSUS_METHODS,
        }
    )
    row.update(extra)


def _pick_alliance(hits: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        hits,
        key=lambda h: (
            not (h["best"] and h["best_rev"]),
            not h["best"],
            _CONF_RANK.get(h.get("confidence") or "", 3),
            -len(h.get("methods") or []),
        ),
    )[0]


def _pick_diopt(hits: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(hits, key=lambda h: (not (h["best"] and h["best_rev"]), not h["best"], -(h.get("score") or 0)))[0]


def _same_gene(a_id: str | None, a_sym: str | None, b_id: str | None, b_sym: str | None) -> bool:
    if a_id and b_id and _bare(a_id).lower() == _bare(b_id).lower():
        return True
    return bool(a_sym and b_sym and a_sym.lower() == b_sym.lower())


def _direction(best: bool, best_rev: bool) -> str:
    if best and best_rev:
        return "best-best (reciprocal)"
    if best:
        return "best forward only"
    if best_rev:
        return "best reverse only"
    return "not best-scoring"


def _fmt_e(x: Any) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "?"
    return "0" if v == 0 else f"{v:.0e}"


def _attach_identity(row: dict[str, Any], ens_hits: list[dict[str, Any]]) -> None:
    if ens_hits and not any(_same_gene(row["id"], row["symbol"], h.get("id"), h.get("symbol")) for h in ens_hits):
        names = ", ".join(sorted({h.get("symbol") or h.get("id") or "?" for h in ens_hits})[:3])
        row["note"] = (row.get("note") or "") + f" Ensembl Compara lists a different gene ({names}); no % id shown."
        return
    for h in ens_hits:
        if _same_gene(row["id"], row["symbol"], h.get("id"), h.get("symbol")) and h.get("perc_id") is not None:
            row["identity"] = round(float(h["perc_id"]), 1)
            if h.get("perc_id_target") is not None:
                row["identity_target"] = round(float(h["perc_id_target"]), 1)
            row["identity_source"] = "ensembl_compara"
            if row["method"] != "ensembl_compara":
                row["evidence"].append(
                    {"method": "ensembl_compara", "id": h.get("id"), "symbol": h.get("symbol"), "detail": h.get("type")}
                )
            return


def _orthodb_concordance(row: dict[str, Any], odb: dict[str, Any] | None) -> bool:
    if not odb:
        return False
    for g in odb.get("genes") or []:
        if _same_gene(row["id"], row["symbol"], g.get("id"), g.get("id")):
            row["evidence"].append(
                {"method": "orthodb", "id": g.get("id"), "detail": f"OrthoDB v12 OG at {odb['level_name']}"}
            )
            return True
    return False


def _orthodb_row(row: dict[str, Any], odb: dict[str, Any]) -> None:
    genes = odb.get("genes") or []
    g = genes[0]
    gid = g.get("id") or ""
    display = gid if gid and " " not in gid else g.get("odb_id")
    _mapped(
        row,
        method="orthodb",
        id_=display,
        symbol=None,
        confidence="moderate" if len(genes) == 1 else "low",
        relationship="one-to-one at level" if len(genes) == 1 else f"one-to-many ({len(genes)} genes)",
        orthodb_level=odb.get("level_name"),
    )
    extra = f"; also {', '.join(x.get('id') or x.get('odb_id') for x in genes[1:4])}" if len(genes) > 1 else ""
    row["note"] = f"OrthoDB v12 orthogroup at {odb.get('level_name')} level (OrthoLoger clustering){extra}."


def _model_org_row(sp, row, results) -> None:
    taxon = str(sp["taxon"])
    alli, ensl, odb = results.get("alliance"), results.get("ensembl_compara"), results.get("orthodb")
    dio = results.get(f"diopt:{taxon}")
    a_hits = ((alli or {}).get("data") or {}).get(taxon) or [] if alli and alli["ok"] else []
    d_hits = (dio or {}).get("data") or [] if dio and dio["ok"] else []
    e_hits = ((ensl or {}).get("data") or {}).get(taxon) or [] if ensl and ensl["ok"] else []
    o_tax = (((odb or {}).get("data") or {}).get("by_taxon") or {}).get(taxon) if odb and odb["ok"] else None

    if a_hits:
        h = _pick_alliance(a_hits)
        _mapped(
            row,
            method="alliance",
            id_=h["id"],
            symbol=h["symbol"],
            confidence=h.get("confidence"),
            relationship=_direction(h["best"], h["best_rev"]),
        )
        others = [x["symbol"] for x in a_hits if x is not h]
        row["note"] = (
            f"Alliance stringent: {len(h['methods'])}/{h['methods_called']} methods agree; "
            f"{_direction(h['best'], h['best_rev'])}."
            + (f" Other Alliance orthologs: {', '.join(others[:4])}." if others else "")
        )
        if d_hits:
            d = _pick_diopt(d_hits)
            if _same_gene(h["id"], h["symbol"], d["id"], d["symbol"]):
                row["evidence"].append(
                    {"method": "diopt", "id": d["id"], "symbol": d["symbol"],
                     "detail": f"DIOPT {d['score']}/{d['max_score']} ({d.get('confidence')}); "
                               "shares DIOPT 9.1 inputs with Alliance — not independent"}
                )
            else:
                row["note"] += f" DIOPT top hit differs: {d['symbol']} ({d['score']}/{d['max_score']})."
    elif d_hits:
        d = _pick_diopt(d_hits)
        _mapped(
            row,
            method="diopt",
            id_=d["id"],
            symbol=d["symbol"],
            confidence=d.get("confidence"),
            relationship=_direction(d["best"], d["best_rev"]),
        )
        row["note"] = f"DIOPT {d['score']}/{d['max_score']} methods; {_direction(d['best'], d['best_rev'])}."
    elif o_tax and o_tax.get("genes"):
        _orthodb_row(row, o_tax)

    if row["status"] == "mapped":
        _attach_identity(row, e_hits)
        if row["method"] != "orthodb":
            _orthodb_concordance(row, o_tax)
        return
    _miss(row, sp, results)


def _ensembl_species_row(sp, row, results) -> None:
    taxon = str(sp["taxon"])
    ensl, odb = results.get("ensembl_compara"), results.get("orthodb")
    e_hits = ((ensl or {}).get("data") or {}).get(taxon) or [] if ensl and ensl["ok"] else []
    o_tax = (((odb or {}).get("data") or {}).get("by_taxon") or {}).get(taxon) if odb and odb["ok"] else None
    if e_hits:
        h = sorted(e_hits, key=lambda x: (x.get("type") != "ortholog_one2one", -(x.get("perc_id") or 0)))[0]
        _mapped(
            row,
            method="ensembl_compara",
            id_=h["id"],
            symbol=h.get("symbol"),
            confidence="moderate" if h.get("type") == "ortholog_one2one" else "low",
            relationship=(h.get("type") or "").replace("ortholog_", ""),
        )
        _attach_identity(row, [h])
        row["note"] = (
            f"Ensembl Compara gene-tree {row['relationship']} (level {h.get('taxonomy_level')}); "
            f"% id = share of human protein identical"
            + (f", {row['identity_target']}% of target." if row.get("identity_target") is not None else ".")
        )
        _orthodb_concordance(row, o_tax)
        return
    if o_tax and o_tax.get("genes"):
        _orthodb_row(row, o_tax)
        return
    _miss(row, sp, results)


def _planaria_row(sp, row, results, symbol: str | None) -> None:
    pm = results.get("planmine_rbh") or _fail("not run")
    odb = results.get("orthodb")
    o_tax = (((odb or {}).get("data") or {}).get("by_taxon") or {}).get(str(sp["taxon"])) if odb and odb["ok"] else None
    pm_data = pm.get("data") or {}
    hit = pm_data.get("hit") if pm["ok"] else None
    row["planmine_cache"] = pm_data.get("cache")

    if hit:
        gid = hit.get("gene") or hit.get("contig")
        _mapped(row, method="planmine_rbh", id_=gid, symbol=None, identity=None)
        concordant = _orthodb_concordance(row, o_tax) if hit.get("gene") else False
        rev = ", ".join(hit.get("reverse_best_symbols") or []) or "—"
        row.update(
            {
                "evalue": hit.get("evalue"),
                "reciprocal": hit.get("reciprocal"),
                "best_contig": hit.get("contig"),
                "confidence": "moderate" if hit.get("reciprocal") and concordant else "low",
                "relationship": "reciprocal best (RBH-style)" if hit.get("reciprocal") else "forward best only (co-ortholog)",
            }
        )
        level = "gene model" if hit.get("gene") else "transcript contig (no gene model link)"
        parts = [
            f"PlanMine BLAST: contig {hit['contig']} best human hit {symbol} ({hit['refseq']}, e={_fmt_e(hit['evalue'])}); "
            f"{hit['n_contigs']} contig(s) across {len(hit['assemblies'])} assemblies -> {level}.",
        ]
        if hit.get("reciprocal"):
            parts.append(f"Reverse best human hit of {gid} is {symbol} (reciprocal).")
        else:
            parts.append(
                f"Reverse best human hit of {gid} is {rev} (e={_fmt_e(hit['reverse_best_evalue'])}) — "
                f"not reciprocal; likely one planarian gene for several human paralogs."
            )
        parts.append("OrthoDB v12 concordant." if concordant else "No OrthoDB v12 concordance.")
        if hit.get("tied_genes"):
            row["ambiguous"] = True
            parts.append(
                f"Ambiguous: equally scoring gene models {', '.join(hit['tied_genes'][:4])} "
                f"(picked by own predicted-transcript hit)."
            )
        elif hit.get("other_genes"):
            parts.append(f"Weaker gene models: {', '.join(hit['other_genes'])}.")
        row["note"] = " ".join(parts)
        return

    if o_tax and o_tax.get("genes"):
        _orthodb_row(row, o_tax)
        pm_reason = (
            f"PlanMine: no contig with {symbol} as best human hit at e<={planmine.EVALUE_MAX:.0e}."
            if pm["ok"]
            else f"PlanMine unavailable ({pm.get('error')})."
        )
        row["note"] += " " + pm_reason
        return
    _miss(row, sp, results, symbol=symbol)


def _miss(row: dict[str, Any], sp: dict[str, Any], results: dict[str, Any], *, symbol: str | None = None) -> None:
    checked, failed = [], []
    for m in sp["chain"]:
        if m == "diopt":
            r = results.get(f"diopt:{sp['taxon']}")
        else:
            r = results.get(m)
        if r is None:
            failed.append(f"{SOURCE_NAMES[m]} (not queried)")
        elif r["ok"]:
            checked.append(SOURCE_NAMES[m])
        else:
            failed.append(f"{SOURCE_NAMES[m]} ({r.get('error')})")
    if checked:
        row["status"] = "unmapped"
        msg = f"Honest miss: no ortholog returned by {', '.join(checked)}."
        if sp["key"] == "planaria":
            msg = (
                f"Honest miss: no S. mediterranea contig in PlanMine has {symbol} as best human BLAST hit "
                f"(e<={planmine.EVALUE_MAX:.0e}) and OrthoDB v12 lists no S. mediterranea gene."
                if len(checked) == 2
                else msg
            )
    else:
        row["status"] = "unavailable"
        msg = "No source reachable."
    if failed:
        msg += f" Unavailable: {'; '.join(failed)}."
    row["note"] = msg


# --- panel --------------------------------------------------------------------------------


def ortholog_panel(*, gene: str | None = None, uniprot: str | None = None) -> dict[str, Any]:
    """Species x ortholog table for a human target; method-tagged rows with honest statuses."""
    gene = (gene or "").strip().upper() or None
    uniprot = (uniprot or "").strip().upper() or None
    cache_key = f"{gene or ''}|{uniprot or ''}"
    cached = get_json("orthologs_b7", cache_key, ttl_s=TTL_PANEL_S)
    if cached is not None:
        return cached

    ident = _resolve_human(gene, uniprot) if (gene or uniprot) else {}
    symbol = ident.get("symbol") or gene
    taxa = [sp["taxon"] for sp in SPECIES if sp["key"] != "human"]
    model_taxa = [sp["taxon"] for sp in SPECIES if "alliance" in sp["chain"]]
    ens_taxa = [sp["taxon"] for sp in SPECIES if sp["key"] not in ("human", "planaria")]

    jobs: dict[str, Callable[[], dict[str, Any]]] = {}
    if ident.get("hgnc_id"):
        jobs["alliance"] = lambda: alliance_orthologs(ident["hgnc_id"])
    if ident.get("entrez_id"):
        for t in model_taxa:
            jobs[f"diopt:{t}"] = (lambda tt: lambda: diopt_orthologs(ident["entrez_id"], tt))(t)
    if ident.get("ensembl_gene_id"):
        jobs["ensembl_compara"] = lambda: ensembl_orthologs(ident["ensembl_gene_id"], ens_taxa)
    odb_query = ident.get("uniprot") or uniprot
    if odb_query:
        jobs["orthodb"] = lambda: orthodb_orthologs(odb_query, taxa)
    if symbol:
        jobs["planmine_rbh"] = lambda: _planmine_job(symbol)

    results: dict[str, dict[str, Any]] = {}
    if jobs:
        with cf.ThreadPoolExecutor(max_workers=min(10, len(jobs))) as pool:
            futs = {pool.submit(fn): name for name, fn in jobs.items()}
            done, pending = cf.wait(futs, timeout=PANEL_TIMEOUT_S)
            for f in done:
                try:
                    results[futs[f]] = f.result()
                except Exception as exc:
                    results[futs[f]] = _fail(exc)
            for f in pending:
                results[futs[f]] = _fail(f"timed out after {PANEL_TIMEOUT_S}s")
                f.cancel()
    if symbol and not ident.get("hgnc_id"):
        reason = ident.get("error") or f"HGNC has no entry for '{symbol}'"
        for name in ("alliance", "ensembl_compara"):
            results.setdefault(name, _fail(f"human identity unresolved: {reason}"))
        for t in model_taxa:
            results.setdefault(f"diopt:{t}", _fail(f"human identity unresolved: {reason}"))

    rows: list[dict[str, Any]] = []
    for sp in SPECIES:
        row = _base_row(sp, ident.get("uniprot") or uniprot or symbol)
        if sp["key"] == "human":
            row.update(
                {
                    "status": "reference",
                    "symbol": symbol,
                    "id": ident.get("hgnc_id") or uniprot,
                    "uniprot": ident.get("uniprot") or uniprot,
                    "ensembl_gene_id": ident.get("ensembl_gene_id"),
                    "entrez_id": ident.get("entrez_id"),
                    "note": "Query species / reference",
                }
            )
            row.pop("banner")
        elif not symbol and not uniprot:
            row["note"] = "No human gene symbol or UniProt accession resolved for this target."
        elif sp["key"] == "planaria":
            _planaria_row(sp, row, results, symbol)
        elif "alliance" in sp["chain"]:
            _model_org_row(sp, row, results)
        else:
            _ensembl_species_row(sp, row, results)
        rows.append(row)

    sources = []
    for name in ("alliance", "diopt", "ensembl_compara", "orthodb", "planmine_rbh"):
        rs = [v for k, v in results.items() if k == name or k.startswith(f"{name}:")]
        if not rs:
            sources.append({"method": name, "name": SOURCE_NAMES[name], "status": "not_queried"})
            continue
        errs = sorted({r["error"] for r in rs if not r["ok"]})
        sources.append(
            {
                "method": name,
                "name": SOURCE_NAMES[name],
                "status": "ok" if not errs else ("partial" if len(errs) < len(rs) else "unavailable"),
                "error": "; ".join(errs) or None,
            }
        )

    planaria = next((r for r in rows if r["species"] == "planaria"), {})
    out = {
        "gene": symbol,
        "uniprot": ident.get("uniprot") or uniprot,
        "hgnc_id": ident.get("hgnc_id"),
        "species": rows,
        "sources": sources,
        "versions": {
            "orthodb": "v12",
            "diopt": "v9 API",
            "planmine": {k: v for k, v in (planaria.get("planmine_cache") or {}).items()
                         if k in ("planmine_release", "planmine_api", "built_at", "mode")},
        },
        "banner": ROW_BANNER,
        "disclaimer": DISCLAIMER,
    }
    if (symbol or uniprot) and not any(r["status"] == "unavailable" for r in rows):
        set_json("orthologs_b7", cache_key, out)
    return out


def _planmine_job(symbol: str) -> dict[str, Any]:
    res = planmine.planaria_lookup(symbol)
    if res.get("ok"):
        return _ok(res)
    out = _fail(res.get("error") or "PlanMine lookup failed")
    out["data"] = res
    return out
