"""Mechanism text from ChEMBL / Open Targets — research framing only."""

from __future__ import annotations

from typing import Any

UA_NOTE = "CrossAffinity/1.x (local research; Alexander Cecena)"


def mechanism_summary(drug: dict[str, Any], targets: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate human-readable mechanism stubs with provenance."""
    texts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for t in targets:
        mech = (t.get("mechanism") or "").strip()
        if not mech or mech.lower() in seen:
            continue
        seen.add(mech.lower())
        texts.append(
            {
                "text": mech,
                "action_type": t.get("action_type"),
                "gene": t.get("gene"),
                "source": t.get("source"),
            }
        )

    # Optional Open Targets enrichment when we have ChEMBL ID
    ot = None
    chembl_id = drug.get("chembl_id")
    if chembl_id:
        try:
            ot = _open_targets_diseases(chembl_id)
        except Exception as exc:
            ot = {"error": str(exc)}

    return {
        "mechanisms": texts,
        "open_targets": ot,
        "disclaimer": (
            "Mechanism statements are literature/database curations (ChEMBL / Open Targets). "
            "They are not clinical advice and do not imply efficacy or safety."
        ),
    }


def _open_targets_diseases(chembl_id: str, *, limit: int = 8) -> dict[str, Any]:
    import httpx

    query = """
    query DrugDiseases($id: String!) {
      drug(chemblId: $id) {
        id
        name
        linkedDiseases {
          count
          rows { id name }
        }
      }
    }
    """
    r = httpx.post(
        "https://api.platform.opentargets.org/api/v4/graphql",
        json={"query": query, "variables": {"id": chembl_id}},
        headers={"User-Agent": UA_NOTE},
        timeout=40,
    )
    r.raise_for_status()
    drug = ((r.json().get("data") or {}).get("drug")) or {}
    linked = drug.get("linkedDiseases") or {}
    rows = (linked.get("rows") or [])[:limit]
    return {
        "drug_name": drug.get("name"),
        "disease_count": linked.get("count"),
        "diseases": [{"id": d.get("id"), "name": d.get("name")} for d in rows],
        "note": "Associated diseases from Open Targets — hypothesis links, not indications for use.",
    }
