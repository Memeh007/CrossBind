"""Deterministic evidence summaries + optional local Ollama narration.

Honesty: docking scores and geometric contacts are computational hypotheses.
Bundling or calling an LLM does NOT guarantee non-fiction — unconstrained
models hallucinate biology. Narration is optional, evidence-bound, and local-only
by default (no cloud LLMs).
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger(__name__)

# Residue label from geometry / ProLIF: "ASP88.A" or "ASP 88.A" / ProLIF-ish
_RES_RE = re.compile(
    r"^([A-Za-z]{1,4})\s*(-?\d+)(?:\.([A-Za-z0-9]))?$"
)

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"

LLM_UNAVAILABLE_MSG = (
    "Local LLM not available — showing evidence summary only. "
    "Install Ollama for optional narration."
)

NARRATE_SYSTEM = (
    "You are a research assistant for CrossBind molecular docking results. "
    "ONLY use the provided JSON evidence. Do not invent residues, distances, "
    "pathways, binding constants, clinical claims, or wet-lab findings. "
    "If something is unknown or missing, say unknown. "
    "Label the entire output as a research hypothesis based on a docked pose. "
    "Docking score is not Kd or experimental affinity. "
    "Contacts are geometric hypotheses from the pose, not crystallographic density "
    "or assay proof. Never give medical advice."
)


def parse_residue_label(label: str | None) -> dict[str, Any]:
    """Parse 'ASP88.A' → {resn, resi, chain, label}."""
    raw = (label or "").strip()
    out: dict[str, Any] = {
        "label": raw,
        "resn": "",
        "resi": "",
        "chain": "",
    }
    if not raw:
        return out
    m = _RES_RE.match(raw)
    if m:
        out["resn"] = m.group(1).upper()
        out["resi"] = m.group(2)
        out["chain"] = (m.group(3) or "").upper()
        return out
    # ProLIF sometimes: ASP:88 or A.ASP88
    m2 = re.match(r"^([A-Za-z0-9])[.:]([A-Za-z]{1,4})\s*(-?\d+)$", raw)
    if m2:
        out["chain"] = m2.group(1).upper()
        out["resn"] = m2.group(2).upper()
        out["resi"] = m2.group(3)
        return out
    m3 = re.match(r"^([A-Za-z]{1,4})\s*[.:]\s*(-?\d+)$", raw)
    if m3:
        out["resn"] = m3.group(1).upper()
        out["resi"] = m3.group(2)
        return out
    out["resn"] = raw
    return out


def enrich_contact(row: dict[str, Any], *, method: str | None = None) -> dict[str, Any]:
    """Add resn/resi/chain/method fields for UI tables."""
    r = dict(row) if isinstance(row, dict) else {"residue": str(row)}
    parsed = parse_residue_label(str(r.get("residue") or ""))
    r.setdefault("resn", parsed["resn"])
    r.setdefault("resi", parsed["resi"])
    r.setdefault("chain", parsed["chain"])
    if method and not r.get("method"):
        r["method"] = method
    return r


def enrich_interactions(interactions: dict[str, Any] | None) -> dict[str, Any] | None:
    if not interactions or not isinstance(interactions, dict):
        return interactions
    out = dict(interactions)
    method = out.get("tool") or "geometry"
    if out.get("top_pose"):
        out["top_pose"] = [enrich_contact(r, method=method) for r in out["top_pose"]]
    by_pose = out.get("by_pose") or {}
    if isinstance(by_pose, dict):
        out["by_pose"] = {
            str(k): [enrich_contact(r, method=method) for r in (v or [])]
            for k, v in by_pose.items()
        }
    return out


def _fmt_affinity(val: Any) -> str:
    try:
        return f"{float(val):.3f} kcal/mol"
    except (TypeError, ValueError):
        return "unknown"


def _admet_summary(admet: dict[str, Any] | None) -> str:
    if not admet or not isinstance(admet, dict):
        return "ADMET not available."
    if not admet.get("ok"):
        err = admet.get("error") or "unavailable"
        return f"ADMET unavailable ({err})."
    desc = admet.get("descriptors") or {}
    rules = admet.get("rules") or {}
    lip = rules.get("lipinski") or {}
    qed = (desc.get("qed") or {}).get("value")
    mw = (desc.get("mw") or {}).get("value")
    logp = (desc.get("logp") or {}).get("value")
    bits = []
    if mw is not None:
        bits.append(f"MW {mw}")
    if logp is not None:
        bits.append(f"LogP {logp}")
    if qed is not None:
        bits.append(f"QED {qed}")
    lip_s = "pass" if lip.get("pass") else "fail"
    if lip.get("fails"):
        lip_s += f" ({', '.join(lip['fails'])})"
    bits.append(f"Lipinski {lip_s}")
    return "ADMET/drug-likeness (heuristic): " + "; ".join(bits) + "."


def _contact_lines(contacts: list[dict[str, Any]], limit: int = 8) -> list[str]:
    lines = []
    for c in contacts[:limit]:
        e = enrich_contact(c)
        res = e.get("residue") or f"{e.get('resn')}{e.get('resi')}.{e.get('chain')}"
        itype = e.get("type") or "contact"
        dist = e.get("distance_A")
        dist_s = f"{float(dist):.2f} Å" if dist is not None else "n/a"
        detail = e.get("detail") or ""
        extra = f" ({detail})" if detail else ""
        lines.append(f"{res} {itype} at {dist_s}{extra}")
    return lines


def compact_evidence(result: dict[str, Any]) -> dict[str, Any]:
    """Compact JSON payload for LLM — only structured fields, no free prose."""
    ix = result.get("interactions") or {}
    admet = result.get("admet") or {}
    protein = result.get("protein") or {}
    ligand = result.get("ligand") or {}
    top = list(ix.get("top_pose") or [])[:12]
    return {
        "job_title": result.get("job_title") or result.get("compound_name"),
        "job_id": result.get("id"),
        "status": result.get("status"),
        "engine": result.get("engine"),
        "vina_affinity": result.get("vina_affinity"),
        "gnina_cnn_score": result.get("gnina_cnn_score"),
        "pocket_method": result.get("pocket_method"),
        "structure_provenance": result.get("structure_provenance")
        or protein.get("provenance")
        or protein.get("label"),
        "protein": {
            "gene": protein.get("gene"),
            "uniprot": protein.get("uniprot"),
            "pdb_id": protein.get("pdb_id") or protein.get("structure_id"),
            "organism": protein.get("organism"),
        },
        "ligand": {
            "compound_name": ligand.get("compound_name") or result.get("compound_name"),
            "cid": ligand.get("cid"),
            "smiles": ligand.get("smiles"),
        },
        "interactions": {
            "ok": ix.get("ok"),
            "tool": ix.get("tool"),
            "cutoffs_A": ix.get("cutoffs_A"),
            "vicinity_cutoff_A": ix.get("vicinity_cutoff_A"),
            "contact_residues": (ix.get("contact_residues") or [])[:24],
            "top_pose_contacts": [
                {
                    "residue": c.get("residue"),
                    "type": c.get("type"),
                    "distance_A": c.get("distance_A"),
                    "detail": c.get("detail"),
                }
                for c in top
            ],
        },
        "admet": {
            "ok": admet.get("ok"),
            "lipinski_pass": (admet.get("rules") or {}).get("lipinski", {}).get("pass"),
            "qed": ((admet.get("descriptors") or {}).get("qed") or {}).get("value"),
            "mw": ((admet.get("descriptors") or {}).get("mw") or {}).get("value"),
            "logp": ((admet.get("descriptors") or {}).get("logp") or {}).get("value"),
        },
        "caveats": [
            "Docking score is not experimental Kd/Ki/IC50.",
            "Contacts are pose geometry hypotheses, not crystallographic density.",
            "Not medical advice.",
        ],
    }


def build_explanation(result: dict[str, Any], *, top_n_contacts: int = 8) -> str:
    """Deterministic plain-English paragraphs from structured result fields only."""
    title = result.get("job_title") or result.get("compound_name") or "This docking job"
    engine = result.get("engine") or "unknown engine"
    affinity = result.get("vina_affinity")
    pocket = result.get("pocket_method") or "unspecified"
    paragraphs: list[str] = []

    p1 = (
        f"{title} was docked with {engine}. "
        f"Reported vina_affinity is {_fmt_affinity(affinity)}. "
        f"Docking box / pocket method: {pocket}."
    )
    paragraphs.append(p1)
    paragraphs.append(_admet_summary(result.get("admet")))

    ix = result.get("interactions") or {}
    if ix.get("ok") and (ix.get("top_pose") or ix.get("contact_residues")):
        residues = ix.get("contact_residues") or []
        tool = ix.get("tool") or "geometry"
        cut = ix.get("cutoffs_A") or {}
        cut_bits = []
        if cut.get("hbond") is not None:
            cut_bits.append(f"hbond ≤{cut['hbond']} Å")
        if cut.get("hydrophobic") is not None:
            cut_bits.append(f"hydrophobic ≤{cut['hydrophobic']} Å")
        if cut.get("salt") is not None:
            cut_bits.append(f"salt ≤{cut['salt']} Å")
        if cut.get("pi") is not None:
            cut_bits.append(f"π ≤{cut['pi']} Å")
        if not cut_bits and ix.get("vicinity_cutoff_A") is not None:
            cut_bits.append(f"vicinity ≤{ix['vicinity_cutoff_A']} Å")
        cut_s = "; ".join(cut_bits) if cut_bits else "tool defaults"
        contacts = list(ix.get("top_pose") or [])
        lines = _contact_lines(contacts, limit=top_n_contacts)
        res_s = ", ".join(residues[:16]) if residues else "none listed"
        p_ix = (
            f"Top-pose contacts annotated with {tool} (cutoffs: {cut_s}). "
            f"Unique contact residues: {res_s}."
        )
        if lines:
            p_ix += " Closest / listed contacts: " + "; ".join(lines) + "."
        paragraphs.append(p_ix)
    elif ix.get("error"):
        paragraphs.append(f"Interaction annotation unavailable: {ix.get('error')}.")
    else:
        paragraphs.append("No pose–protein interaction annotation in this result yet.")

    paragraphs.append(
        "Caveats: docking score ≠ experimental Kd/Ki/IC50; listed contacts are "
        "computational hypotheses from the docked pose geometry (not crystallographic "
        "density or a binding assay); this summary is for research triage only and is "
        "not medical advice."
    )
    return "\n\n".join(paragraphs)


def ollama_host() -> str:
    return (os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).rstrip("/")


def ollama_model() -> str:
    return (os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL).strip() or DEFAULT_OLLAMA_MODEL


def ollama_reachable(timeout: float = 1.5) -> bool:
    url = ollama_host() + "/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False


def narrate_with_ollama(
    result: dict[str, Any],
    *,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Call local Ollama chat API with evidence-only prompt.

    Returns {ok, narration, source, message, model, host}.
    On failure, ok=False and narration is the deterministic explanation.
    """
    explanation = result.get("explanation") or build_explanation(result)
    evidence = compact_evidence(result)
    host = ollama_host()
    model = ollama_model()
    base = {
        "ok": False,
        "narration": explanation,
        "source": "deterministic",
        "message": LLM_UNAVAILABLE_MSG,
        "model": model,
        "host": host,
        "explanation": explanation,
    }
    if not ollama_reachable():
        return base

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": NARRATE_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Write a short research-hypothesis narration (2–4 paragraphs) "
                    "strictly from this evidence JSON:\n"
                    + json.dumps(evidence, indent=2, default=str)
                ),
            },
        ],
    }
    url = host + "/api/chat"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        msg = (body.get("message") or {}).get("content") or body.get("response") or ""
        text = str(msg).strip()
        if not text:
            base["message"] = "Local LLM returned empty text — showing evidence summary only."
            return base
        disclaimer = (
            "\n\n[LLM narration — evidence-bound research hypothesis only; "
            "not experimental proof or medical advice.]"
        )
        return {
            "ok": True,
            "narration": text + disclaimer,
            "source": "ollama",
            "message": None,
            "model": model,
            "host": host,
            "explanation": explanation,
        }
    except urllib.error.HTTPError as exc:
        log.warning("Ollama HTTP error: %s", exc)
        base["message"] = f"{LLM_UNAVAILABLE_MSG} (HTTP {exc.code})"
        return base
    except Exception as exc:
        log.warning("Ollama narrate failed: %s", exc)
        base["message"] = f"{LLM_UNAVAILABLE_MSG} ({exc})"
        return base
