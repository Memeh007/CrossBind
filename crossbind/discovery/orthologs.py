"""Cross-species ortholog panel stubs (human, mouse, fly, planaria, dog, rabbit, cat)."""

from __future__ import annotations

from typing import Any

from crossbind.discovery.cache import get_json, set_json

# Product species panel for Alexander's translational workflow
SPECIES = [
    {"key": "human", "label": "Human", "taxon": 9606, "ensembl": "homo_sapiens"},
    {"key": "mouse", "label": "Mouse", "taxon": 10090, "ensembl": "mus_musculus"},
    {"key": "fly", "label": "Fruit fly", "taxon": 7227, "ensembl": "drosophila_melanogaster"},
    {"key": "dog", "label": "Dog", "taxon": 9615, "ensembl": "canis_lupus_familiaris"},
    {"key": "rabbit", "label": "Rabbit", "taxon": 9986, "ensembl": "oryctolagus_cuniculus"},
    {"key": "cat", "label": "Cat", "taxon": 9685, "ensembl": "felis_catus"},
    {
        "key": "planaria",
        "label": "Planaria (S. mediterranea)",
        "taxon": 79327,
        "ensembl": None,  # not in Ensembl Compara
    },
]


def ortholog_panel(*, gene: str | None = None, uniprot: str | None = None) -> dict[str, Any]:
    """Build ortholog table. Planaria is an honest miss unless later mapped."""
    gene = (gene or "").strip() or None
    cache_key = (gene or uniprot or "none").lower()
    cached = get_json("orthologs", cache_key, ttl_s=14 * 86400)
    if cached is not None:
        return cached

    rows: list[dict[str, Any]] = []
    for sp in SPECIES:
        row: dict[str, Any] = {
            "species": sp["key"],
            "label": sp["label"],
            "taxon": sp["taxon"],
            "status": "pending",
            "symbol": None,
            "id": None,
            "identity": None,
            "note": None,
        }
        if sp["key"] == "human":
            row.update(
                {
                    "status": "reference",
                    "symbol": gene,
                    "id": uniprot,
                    "note": "Query species / reference",
                }
            )
        elif sp["key"] == "planaria":
            row.update(
                {
                    "status": "unmapped",
                    "note": (
                        "Honest miss: S. mediterranea is not in Ensembl Compara. "
                        "Use PlanMine / OMA SCHMD / sequence search in a later slice."
                    ),
                }
            )
        elif gene and sp.get("taxon"):
            hit = _ensembl_ortholog(gene, int(sp["taxon"]), sp.get("ensembl") or "")
            if hit:
                row.update(hit)
                row["status"] = "mapped"
            else:
                row["status"] = "unmapped"
                row["note"] = "No orthologue returned by Ensembl Compara for this symbol."
        else:
            row["status"] = "stub"
            row["note"] = "Provide a human gene symbol to query Ensembl."
        rows.append(row)

    out = {
        "gene": gene,
        "uniprot": uniprot,
        "species": rows,
        "disclaimer": (
            "Orthologs do not imply identical pharmacology across species "
            "(especially planaria — large evolutionary distance)."
        ),
    }
    set_json("orthologs", cache_key, out)
    return out


def _ensembl_ortholog(gene: str, target_taxon: int, target_species: str) -> dict[str, Any] | None:
    cache_key = f"{gene}:{target_taxon}"
    cached = get_json("ensembl_ortho", cache_key, ttl_s=30 * 86400)
    if cached is not None:
        return cached or None

    hit: dict[str, Any] | None = None
    try:
        import httpx

        r = httpx.get(
            f"https://rest.ensembl.org/homology/symbol/human/{gene}",
            params={
                "type": "orthologues",
                "target_taxon": target_taxon,
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "CrossAffinity/1.x",
            },
            timeout=45,
        )
        if r.status_code == 200:
            hit = _parse_homology(r.json(), target_taxon)
        elif r.status_code == 400:
            hit = None
    except Exception:
        hit = None

    # Optional ensembl-rest client path
    if hit is None and target_species:
        try:
            from ensembl_rest import EnsemblClient

            client = EnsemblClient()
            data = client.homology_symbol(
                "human",
                gene,
                type="orthologues",
                target_taxon=target_taxon,
            )
            hit = _parse_homology(data, target_taxon)
        except Exception:
            pass

    set_json("ensembl_ortho", cache_key, hit or {})
    return hit


def _parse_homology(payload: dict, target_taxon: int) -> dict[str, Any] | None:
    blocks = payload.get("data") or []
    for block in blocks:
        for h in block.get("homologies") or []:
            if not str(h.get("type", "")).startswith("ortholog"):
                continue
            tgt = h.get("target") or {}
            if int(tgt.get("taxon_id") or 0) != int(target_taxon):
                continue
            return {
                "symbol": None,
                "id": tgt.get("id") or tgt.get("protein_id"),
                "identity": tgt.get("perc_id"),
                "note": f"Ensembl Compara {h.get('type')} (taxon {target_taxon})",
                "species_name": tgt.get("species"),
                "protein_id": tgt.get("protein_id"),
            }
    return None
