"""Unit tests for P2Rank predictions CSV parser + pocket fallback without binary."""

from __future__ import annotations

from pathlib import Path

import pytest

from crossbind.discovery.p2rank import parse_predictions_csv, parse_predictions_file, p2rank_available
from crossbind.discovery.pocket import resolve_pockets, auto_docking_box

FIXTURE = Path(__file__).parent / "fixtures" / "1fbl.pdb_predictions.csv"


def test_parse_predictions_fixture():
    pockets = parse_predictions_file(FIXTURE)
    assert len(pockets) >= 3
    top = pockets[0]
    assert top["id"] == "pocket1"
    assert top["rank"] == 1
    assert top["score"] == pytest.approx(9.77, rel=1e-3)
    assert top["center"][0] == pytest.approx(70.527, abs=5e-3)
    assert top["center"][1] == pytest.approx(83.4375, abs=5e-3)
    assert top["center"][2] == pytest.approx(-11.51, abs=5e-2)
    assert "A_103" in top["residues"]
    assert top["size"] == [22.0, 22.0, 22.0]
    assert top["method"] == "p2rank"


def test_parse_predictions_csv_strips_padding():
    text = FIXTURE.read_text(encoding="utf-8")
    pockets = parse_predictions_csv(text)
    assert pockets[0]["probability"] == pytest.approx(0.525, rel=1e-3)


def test_resolve_pockets_fallback_without_p2rank(tmp_path):
    """Smoke: when P2Rank is missing, resolve_pockets still returns a usable box."""
    # Minimal CA-only PDB (protein centroid fallback)
    pdb = tmp_path / "tiny.pdb"
    pdb.write_text(
        "ATOM      1  CA  ALA A   1      11.000  12.000  13.000  1.00 20.00           C\n"
        "ATOM      2  CA  ALA A   2      14.000  12.000  13.000  1.00 20.00           C\n"
        "ATOM      3  CA  ALA A   3      11.000  15.000  13.000  1.00 20.00           C\n"
        "END\n",
        encoding="utf-8",
    )
    # Force "no p2rank" path by using apo structure without binary
    result = resolve_pockets(pdb, structure={"label": "experimental", "provenance": "experimental_pdb"})
    assert result.get("center") and len(result["center"]) == 3
    assert result.get("size") and len(result["size"]) == 3
    assert result.get("selected_pocket")
    assert result["pocket_method"] in {"centroid_fallback", "holo_ligand", "p2rank"}
    if not p2rank_available():
        assert result["pocket_method"] == "centroid_fallback"
        assert result.get("p2rank_available") is False
        assert result.get("warning") and "P2Rank" in result["warning"]


def test_auto_docking_box_still_works(tmp_path):
    pdb = tmp_path / "lig.pdb"
    pdb.write_text(
        "HETATM    1  C1  LIG A 501      1.000   2.000   3.000  1.00 20.00           C\n"
        "HETATM    2  C2  LIG A 501      2.000   2.000   3.000  1.00 20.00           C\n"
        "HETATM    3  C3  LIG A 501      1.500   2.500   3.500  1.00 20.00           C\n"
        "END\n",
        encoding="utf-8",
    )
    box = auto_docking_box(pdb)
    assert box["method"] == "ligand_centroid"
    assert box["ligand_resn"] == "LIG"
