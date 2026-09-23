"""Science tracks A1 (contacts) + A3 (Open Targets dossier)."""

from __future__ import annotations

from pathlib import Path

import pytest

from crossbind.analysis.explain import enrich_contact
from crossbind.analysis.interactions import _stamp_contacts, annotate_interactions


def test_stamp_contacts_ids_and_method():
    rows = [
        {"residue": "ASP88.A", "type": "HBAcceptor", "distance_A": 2.9, "detail": "OD1"},
        {"residue": "TYR123.A", "type": "Hydrophobic", "distance_A": 3.8},
    ]
    out = _stamp_contacts(rows, method="geometric", pose=1)
    assert len(out) == 2
    assert out[0]["id"]
    assert out[0]["method"] == "geometric"
    assert out[0]["resn"] == "ASP"
    assert out[0]["resi"] == "88"
    assert out[0]["chain"] == "A"


def test_enrich_contact_normalizes_method():
    r = enrich_contact(
        {"residue": "SER45.B", "type": "HBDonor", "distance_A": 3.1},
        method="rdkit_geometry",
    )
    assert r["method"] == "geometric"
    assert r["id"]
    assert r["resn"] == "SER"
    assert r["chain"] == "B"


def test_geometry_annotate_assigns_ids(tmp_path: Path):
    rec = tmp_path / "rec.pdbqt"
    lig = tmp_path / "poses.pdbqt"
    rec.write_text(
        "ATOM      1  N   ASP A  88      0.000   0.000   0.000  0.00  0.00    -0.000 N\n"
        "ATOM      2  OD1 ASP A  88      1.200   0.200   0.100  0.00  0.00    -0.000 OA\n"
        "ATOM      3  CG  ASP A  88      0.800   0.000   0.000  0.00  0.00    -0.000 C\n"
        "END\n",
        encoding="utf-8",
    )
    lig.write_text(
        "MODEL 1\n"
        "ATOM      1  N1  LIG L   1      1.500   0.300   0.100  0.00  0.00    -0.000 N\n"
        "ATOM      2  C1  LIG L   1      2.500   1.000   0.500  0.00  0.00    -0.000 C\n"
        "ENDMDL\n",
        encoding="utf-8",
    )
    r = annotate_interactions(rec, lig, smiles="CN", top_n=1, prefer_prolif=False)
    assert r["ok"] is True
    assert r.get("method") == "geometric"
    top = r.get("top_pose") or []
    assert top, "expected at least one geometric contact on synthetic pose"
    assert top[0].get("id")
    assert top[0].get("method") == "geometric"


def test_open_targets_dossier_live_or_skip():
    from crossbind.discovery.open_targets_dossier import fetch_target_dossier

    d = fetch_target_dossier(gene="EGFR")
    if not d.get("ok"):
        pytest.skip(f"Open Targets unavailable: {d.get('error')}")
    assert d["approved_symbol"] == "EGFR"
    assert d["ensembl_id"]
    assert isinstance(d.get("tractability"), list)
    assert isinstance(d.get("disease_associations"), list)
    assert d.get("honesty")
