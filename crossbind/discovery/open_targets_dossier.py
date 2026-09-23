"""Open Targets Platform GraphQL dossier for Discover target cards.

Library-first HTTP GraphQL. Cached. Never invents tractability or disease links.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from crossbind.discovery.cache import get_json, set_json

log = logging.getLogger(__name__)

OT_GRAPHQL = "https://api.platform.opentargets.org/api/v4/graphql"
UA = "ddOS/1.3.2 (local CrossBind; Open Targets dossier)"

_SEARCH_Q = """
query searchTarget($q: String!) {
  search(queryString: $q, entityNames: ["target"], page: {index: 0, size: 5}) {
    hits {
      id
      entity
      name
      object {
        ... on Target {
          id
          approvedSymbol
          approvedName
        }
      }
    }
  }
}
"""

_DOSSIER_Q = """
query targetDossier($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
    tractability {
      label
      modality
      value
    }
    associatedDiseases(page: {index: 0, size: 8}) {
      rows {
        score
        disease {
          id
          name
        }
      }
    }
  }
}
"""


def _post_graphql(query: str, variables: dict[str, Any], *, timeout: float = 25.0) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        OT_GRAPHQL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": UA,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Open Targets returned non-object JSON")
    if payload.get("errors"):
        err0 = payload["errors"][0]
        msg = err0.get("message") if isinstance(err0, dict) else str(err0)
        raise RuntimeError(f"Open Targets GraphQL error: {msg}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Open Targets response missing data")
    return data


def _resolve_ensembl_id(*, gene: str | None, uniprot: str | None) -> tuple[str | None, str | None]:
    queries: list[str] = []
    if gene:
        queries.append(gene.strip())
    if uniprot:
        queries.append(uniprot.strip().upper())
    for q in queries:
        if not q:
            continue
        cache_key = f"ensembl:{q.lower()}"
        cached = get_json("ot_ensembl", cache_key, ttl_s=30 * 86400)
        if isinstance(cached, dict) and cached.get("ensembl_id"):
            return cached["ensembl_id"], cached.get("match_note")
        try:
            data = _post_graphql(_SEARCH_Q, {"q": q})
        except Exception as exc:
            log.info("OT search failed for %s: %s", q, exc)
            continue
        hits = ((data.get("search") or {}).get("hits")) or []
        best = None
        gene_u = (gene or "").strip().upper()
        for h in hits:
            obj = h.get("object") or {}
            sym = (obj.get("approvedSymbol") or h.get("name") or "").upper()
            eid = obj.get("id") or h.get("id")
            if not eid:
                continue
            if gene_u and sym == gene_u:
                best = (eid, f"symbol match for {gene}")
                break
            if best is None:
                best = (eid, f"search hit for {q}")
        if best:
            set_json("ot_ensembl", cache_key, {"ensembl_id": best[0], "match_note": best[1]})
            return best
    return None, None


def fetch_target_dossier(
    *,
    gene: str | None = None,
    uniprot: str | None = None,
    ensembl_id: str | None = None,
) -> dict[str, Any]:
    """Fetch a compact Open Targets dossier for Discover (honest empty/error)."""
    gene = (gene or "").strip() or None
    uniprot = (uniprot or "").strip().upper() or None
    ensembl_id = (ensembl_id or "").strip().upper() or None

    out: dict[str, Any] = {
        "ok": False,
        "source": "open_targets_platform",
        "api": OT_GRAPHQL,
        "gene": gene,
        "uniprot": uniprot,
        "ensembl_id": ensembl_id,
        "approved_symbol": None,
        "approved_name": None,
        "tractability": [],
        "disease_associations": [],
        "error": None,
        "cached": False,
        "honesty": (
            "Open Targets associations and tractability labels are curated/inferred "
            "platform evidence — not experimental proof that this ligand binds."
        ),
    }

    cache_key = (ensembl_id or gene or uniprot or "").lower()
    if cache_key:
        cached = get_json("ot_dossier", cache_key, ttl_s=14 * 86400)
        if isinstance(cached, dict) and cached.get("ok"):
            cached = dict(cached)
            cached["cached"] = True
            return cached

    note = None
    if not ensembl_id:
        ensembl_id, note = _resolve_ensembl_id(gene=gene, uniprot=uniprot)
        out["ensembl_id"] = ensembl_id
        if note:
            out["match_note"] = note

    if not ensembl_id:
        out["error"] = (
            "Could not resolve an Ensembl gene id from "
            f"gene={gene!r} uniprot={uniprot!r} via Open Targets search."
        )
        return out

    try:
        data = _post_graphql(_DOSSIER_Q, {"ensemblId": ensembl_id})
    except urllib.error.HTTPError as exc:
        out["error"] = f"Open Targets HTTP {exc.code}"
        return out
    except Exception as exc:
        out["error"] = str(exc)
        return out

    tgt = data.get("target")
    if not tgt:
        out["error"] = f"No Open Targets target for {ensembl_id}"
        return out

    out["approved_symbol"] = tgt.get("approvedSymbol")
    out["approved_name"] = tgt.get("approvedName")
    out["ensembl_id"] = tgt.get("id") or ensembl_id

    tract = []
    for row in tgt.get("tractability") or []:
        if not isinstance(row, dict):
            continue
        if row.get("value") is False:
            continue
        tract.append(
            {
                "label": row.get("label"),
                "modality": row.get("modality"),
                "value": row.get("value"),
            }
        )
    out["tractability"] = tract[:24]

    diseases = []
    for row in ((tgt.get("associatedDiseases") or {}).get("rows")) or []:
        if not isinstance(row, dict):
            continue
        dis = row.get("disease") or {}
        score = row.get("score")
        try:
            score_f = float(score) if score is not None else None
        except (TypeError, ValueError):
            score_f = None
        diseases.append(
            {
                "disease_id": dis.get("id"),
                "disease_name": dis.get("name"),
                "score": round(score_f, 4) if score_f is not None else None,
            }
        )
    out["disease_associations"] = diseases
    out["ok"] = True
    out["error"] = None
    if cache_key:
        set_json("ot_dossier", cache_key, {k: v for k, v in out.items() if k != "cached"})
    return out
