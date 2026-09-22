"""Deterministic evidence summary + residue parse helpers."""

from __future__ import annotations

from crossbind.analysis.explain import (
    build_explanation,
    compact_evidence,
    enrich_contact,
    narrate_with_ollama,
    parse_residue_label,
)


def test_parse_residue_label_asp88():
    p = parse_residue_label("ASP88.A")
    assert p["resn"] == "ASP"
    assert p["resi"] == "88"
    assert p["chain"] == "A"


def test_enrich_contact():
    r = enrich_contact(
        {"residue": "ASP88.A", "type": "HBDonor", "distance_A": 2.12, "detail": "lig→OD1"},
        method="rdkit_geometry",
    )
    assert r["resn"] == "ASP"
    assert r["resi"] == "88"
    assert r["chain"] == "A"
    assert r["method"] == "rdkit_geometry"


def test_build_explanation_contains_contacts_and_caveats():
    result = {
        "job_title": "metformin × demo · 6B1U",
        "vina_affinity": -6.4,
        "engine": "vina",
        "pocket_method": "crystal_ligand",
        "admet": {
            "ok": True,
            "descriptors": {
                "mw": {"value": 129.2},
                "logp": {"value": -1.2},
                "qed": {"value": 0.35},
            },
            "rules": {"lipinski": {"pass": True, "fails": []}},
        },
        "interactions": {
            "ok": True,
            "tool": "rdkit_geometry",
            "cutoffs_A": {"hbond": 3.5, "hydrophobic": 4.5, "salt": 4.0, "pi": 5.5},
            "contact_residues": ["ASP88.A", "TYR123.A"],
            "top_pose": [
                {
                    "residue": "ASP88.A",
                    "type": "HBDonor",
                    "distance_A": 2.12,
                    "detail": "lig→OD1",
                }
            ],
        },
    }
    text = build_explanation(result)
    assert "ASP88.A" in text
    assert "HBDonor" in text
    assert "2.12" in text
    assert "vina" in text.lower() or "vina_affinity" in text
    assert "≠" in text or "Kd" in text
    assert "medical advice" in text.lower()
    assert "crystal_ligand" in text


def test_compact_evidence_shape():
    ev = compact_evidence(
        {
            "job_title": "t",
            "vina_affinity": -1.0,
            "interactions": {"ok": True, "top_pose": [], "contact_residues": []},
            "admet": {"ok": False},
            "protein": {},
            "ligand": {},
        }
    )
    assert "caveats" in ev
    assert "interactions" in ev


def test_narrate_falls_back_without_ollama():
    result = {
        "job_title": "x",
        "vina_affinity": -1.0,
        "engine": "vina",
        "pocket_method": "protein_centroid",
        "interactions": {"ok": False, "error": "none"},
        "admet": {"ok": False},
    }
    out = narrate_with_ollama(result)
    assert out["ok"] is False
    assert out["source"] == "deterministic"
    assert "Local LLM not available" in (out["message"] or "")
    assert "medical advice" in out["narration"].lower()
