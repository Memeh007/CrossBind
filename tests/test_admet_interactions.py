"""Unit tests: ADMET on metformin + geometry interactions on synthetic pose."""

from __future__ import annotations

from pathlib import Path

from crossbind.analysis.admet import compute_admet
from crossbind.analysis.interactions import annotate_interactions, _split_pdbqt_models

METFORMIN = "CN(C)C(=N)NC(=N)N"  # common tautomer
# PubChem-ish alternate also used in jobs:
METFORMIN_ALT = "CN(C)C(=N)N=C(N)N"


def test_admet_metformin():
    r = compute_admet(METFORMIN)
    assert r["ok"] is True
    assert r["error"] is None
    d = r["descriptors"]
    assert 120 < d["mw"]["value"] < 140  # C4H11N5 ~ 129
    assert d["hbd"]["value"] >= 3
    assert d["hba"]["value"] >= 2
    assert d["qed"]["value"] is not None
    assert "lipinski" in r["rules"]
    assert "disclaimer" in r and "heuristic" in r["disclaimer"].lower()


def test_admet_metformin_alt_smiles():
    r = compute_admet(METFORMIN_ALT)
    assert r["ok"] is True
    d_mw = r["descriptors"]["mw"]["value"]
    assert d_mw
    assert 120 < d_mw < 140


def test_admet_invalid():
    r = compute_admet("not_a_smiles!!!")
    assert r["ok"] is False
    assert r["error"]


def test_split_pdbqt_models():
    text = "MODEL 1\nATOM      1  C   UNL     1       0.000   0.000   0.000  1.00  0.00    -0.000 C\nENDMDL\nMODEL 2\nATOM      1  C   UNL     1       1.000   0.000   0.000  1.00  0.00    -0.000 C\nENDMDL\n"
    models = _split_pdbqt_models(text)
    assert len(models) == 2


def test_geometry_interactions_synthetic(tmp_path: Path):
    # Tiny receptor: ASP with OD1 near origin + hydrophobic LEU
    rec = tmp_path / "receptor.pdbqt"
    rec.write_text(
        "\n".join(
            [
                "ATOM      1  N   ASP A   1       0.000   0.000   0.000  1.00  0.00           N",
                "ATOM      2  CA  ASP A   1       1.000   0.000   0.000  1.00  0.00           C",
                "ATOM      3  CB  ASP A   1       1.500   1.200   0.000  1.00  0.00           C",
                "ATOM      4  CG  ASP A   1       2.000   2.000   0.000  1.00  0.00           C",
                "ATOM      5  OD1 ASP A   1       2.500   2.500   0.800  1.00  0.00           OA",
                "ATOM      6  OD2 ASP A   1       2.500   2.500  -0.800  1.00  0.00           OA",
                "ATOM      7  N   LEU A   2       5.000   0.000   0.000  1.00  0.00           N",
                "ATOM      8  CA  LEU A   2       6.000   0.000   0.000  1.00  0.00           C",
                "ATOM      9  CB  LEU A   2       6.500   1.200   0.000  1.00  0.00           C",
                "ATOM     10  CG  LEU A   2       7.200   1.800   0.500  1.00  0.00           C",
                "ATOM     11  CD1 LEU A   2       8.000   2.500   0.500  1.00  0.00           C",
                "ATOM     12  CD2 LEU A   2       7.500   1.200   1.800  1.00  0.00           C",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    # Ligand: donor H near ASP OD1 + carbon near LEU
    poses = tmp_path / "poses.pdbqt"
    poses.write_text(
        "\n".join(
            [
                "MODEL 1",
                "REMARK SMILES CN",
                "ROOT",
                "ATOM      1  N   UNL     1       2.200   2.200   0.900  1.00  0.00    -0.300 NA",
                "ATOM      2  H   UNL     1       2.350   2.350   0.850  1.00  0.00    +0.150 HD",
                "ATOM      3  C   UNL     1       7.000   2.000   0.600  1.00  0.00    +0.100 C",
                "ENDROOT",
                "TORSDOF 0",
                "ENDMDL",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    r = annotate_interactions(rec, poses, smiles="CN", top_n=1, prefer_prolif=False)
    assert r["ok"] is True
    assert r["tool"] == "rdkit_geometry"
    types = {row["type"] for row in r["top_pose"]}
    assert "HBDonor" in types or "HBAcceptor" in types or "Hydrophobic" in types or "Anionic" in types
    assert r["contact_residues"]
