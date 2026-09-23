"""Pose–protein interaction annotation (ProLIF preferred, RDKit/geometry fallback)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Distance cutoffs (Å) for geometry fallback
HBOND_DIST = 3.5
HYDROPHOBIC_DIST = 4.5
SALT_DIST = 4.0
PI_DIST = 5.5

# PDBQT autodock atom types → element
_AD_TO_ELEM = {
    "H": "H", "HD": "H", "HS": "H",
    "C": "C", "A": "C",
    "N": "N", "NA": "N", "NS": "N",
    "OA": "O", "OS": "O", "O": "O",
    "S": "S", "SA": "S",
    "P": "P",
    "F": "F", "Cl": "Cl", "CL": "Cl", "Br": "Br", "BR": "Br", "I": "I",
    "MG": "Mg", "MN": "Mn", "ZN": "Zn", "CA": "Ca", "FE": "Fe",
}



def _receptor_has_hydrogens(path: Path) -> bool:
    """Meeko/Vina receptor PDBQT usually has no H — ProLIF then is slow/fragile."""
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith(("ATOM", "HETATM")):
                continue
            parts = line.split()
            ad = (parts[-1] if parts else "").upper()
            name = line[12:16].strip().upper() if len(line) >= 16 else ""
            if ad in ("H", "HD", "HS") or name.startswith("H"):
                return True
    except Exception:
        return False
    return False


def _prolif_available() -> bool:
    try:
        import prolif  # noqa: F401
        import MDAnalysis  # noqa: F401
        return True
    except Exception:
        return False



def _parse_residue_parts(label: str | None) -> dict[str, Any]:
    """Best-effort parse of 'ASP88.A' / 'A.ASP88' / ProLIF-ish labels."""
    raw = (label or "").strip()
    out = {"residue": raw, "resn": "", "resi": "", "chain": ""}
    if not raw:
        return out
    m = re.match(r"^([A-Za-z]{1,4})\s*(-?\d+)(?:\.([A-Za-z0-9]))?$", raw)
    if m:
        out["resn"] = m.group(1).upper()
        out["resi"] = m.group(2)
        out["chain"] = (m.group(3) or "").upper()
        return out
    m = re.match(r"^([A-Za-z0-9])[.:]([A-Za-z]{1,4})\s*(-?\d+)$", raw)
    if m:
        out["chain"] = m.group(1).upper()
        out["resn"] = m.group(2).upper()
        out["resi"] = m.group(3)
        return out
    m = re.match(r"^([A-Za-z]{1,4})\s*[.:]\s*(-?\d+)$", raw)
    if m:
        out["resn"] = m.group(1).upper()
        out["resi"] = m.group(2)
        return out
    out["resn"] = raw
    return out


def _stamp_contacts(
    rows: list[dict[str, Any]],
    *,
    method: str,
    pose: int | str = 1,
) -> list[dict[str, Any]]:
    """Attach stable ids + structured residue fields for table↔3D sync.

    method is ``prolif`` or ``geometric`` (never a Kd claim).
    """
    method = "prolif" if method == "prolif" else "geometric"
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows or []):
        r = dict(row) if isinstance(row, dict) else {"residue": str(row)}
        parts = _parse_residue_parts(str(r.get("residue") or ""))
        r.setdefault("resn", parts["resn"])
        r.setdefault("resi", parts["resi"])
        r.setdefault("chain", parts["chain"])
        r["method"] = method
        cid = r.get("id")
        if not cid:
            chain = r.get("chain") or "X"
            resi = r.get("resi") or i
            itype = str(r.get("type") or "contact").replace(" ", "")
            cid = f"p{pose}-{chain}{resi}-{itype}-{i}"
        r["id"] = cid
        out.append(r)
    return out



def _split_pdbqt_models(text: str) -> list[str]:
    """Split multi-MODEL PDBQT into per-pose strings (without MODEL/ENDMDL wrappers needed)."""
    models: list[str] = []
    current: list[str] = []
    in_model = False
    has_model = False
    for line in text.splitlines():
        if line.startswith("MODEL"):
            has_model = True
            in_model = True
            current = []
            continue
        if line.startswith("ENDMDL"):
            if current:
                models.append("\n".join(current) + "\n")
            current = []
            in_model = False
            continue
        if has_model:
            if in_model:
                current.append(line)
        else:
            current.append(line)
    if not has_model and current:
        models.append("\n".join(current) + "\n")
    elif current:
        models.append("\n".join(current) + "\n")
    return models


def _parse_pdbqt_atoms(block: str) -> list[dict[str, Any]]:
    atoms = []
    for line in block.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        if len(line) < 54:
            continue
        try:
            name = line[12:16].strip()
            resn = line[17:20].strip().upper()
            chain = (line[21].strip() or "A")
            resi_s = line[22:26].strip()
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except (ValueError, IndexError):
            continue
        # Autodock type is often at end
        parts = line.split()
        ad_type = parts[-1] if parts else "C"
        elem = _AD_TO_ELEM.get(ad_type, _AD_TO_ELEM.get(ad_type.upper(), None))
        if elem is None:
            # Fallback from atom name
            m = re.match(r"([A-Za-z]+)", name)
            raw = (m.group(1) if m else "C").upper()
            if raw.startswith("CL"):
                elem = "Cl"
            elif raw.startswith("BR"):
                elem = "Br"
            elif raw[0] in "CNOSPHFI":
                elem = raw[0] if raw[0] != "H" or len(raw) == 1 else raw[0]
            else:
                elem = "C"
        try:
            resi = int("".join(c for c in resi_s if c.isdigit() or c == "-") or "0")
        except ValueError:
            resi = 0
        atoms.append(
            {
                "name": name,
                "resn": resn,
                "chain": chain,
                "resi": resi,
                "resi_raw": resi_s,
                "x": x,
                "y": y,
                "z": z,
                "elem": elem,
                "ad_type": ad_type,
            }
        )
    return atoms


def _dist(a: dict, b: dict) -> float:
    dx = a["x"] - b["x"]
    dy = a["y"] - b["y"]
    dz = a["z"] - b["z"]
    return (dx * dx + dy * dy + dz * dz) ** 0.5


# Residue chemistry for geometry fallback
_DONOR_RES = {
    "ARG": {"NE", "NH1", "NH2"},
    "ASN": {"ND2"},
    "GLN": {"NE2"},
    "HIS": {"ND1", "NE2"},
    "LYS": {"NZ"},
    "SER": {"OG"},
    "THR": {"OG1"},
    "TYR": {"OH"},
    "TRP": {"NE1"},
    "CYS": {"SG"},
}
_ACCEPTOR_RES = {
    "ASP": {"OD1", "OD2"},
    "GLU": {"OE1", "OE2"},
    "ASN": {"OD1"},
    "GLN": {"OE1"},
    "HIS": {"ND1", "NE2"},
    "SER": {"OG"},
    "THR": {"OG1"},
    "TYR": {"OH"},
    "CYS": {"SG"},
}
_BACKBONE_N = {"N"}
_BACKBONE_O = {"O", "OXT"}
_HYDROPHOBIC_RES = {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "PRO", "TYR"}
_HYDROPHOBIC_ELEMS = {"C"}
_NEG = {"ASP", "GLU"}
_POS = {"ARG", "LYS", "HIS"}
_AROM = {"PHE", "TYR", "TRP", "HIS"}


def _is_protein_atom(a: dict) -> bool:
    # Standard AA three-letter + common
    aa = {
        "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
        "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL",
        "MSE", "SEC", "PYL",
    }
    return a["resn"] in aa


def _ligand_donor_acceptor(atoms: list[dict]) -> tuple[list[dict], list[dict]]:
    """Use PDBQT autodock types: HD = donor H, NA/OA/N/OA = acceptor-ish."""
    donors = []
    acceptors = []
    for a in atoms:
        ad = (a.get("ad_type") or "").upper()
        elem = a["elem"]
        if ad in ("HD", "HS") or (elem == "H" and ad.startswith("H")):
            donors.append(a)
        if ad in ("NA", "OA", "OS", "NS", "SA") or elem in ("N", "O", "S", "F"):
            if elem != "H":
                acceptors.append(a)
        # Polar N/O without H type still acceptors
        if elem in ("N", "O") and ad not in ("HD", "HS"):
            if a not in acceptors:
                acceptors.append(a)
    return donors, acceptors


def _protein_donor_acceptor(atoms: list[dict]) -> tuple[list[dict], list[dict]]:
    donors, acceptors = [], []
    for a in atoms:
        if not _is_protein_atom(a):
            continue
        name = a["name"].upper()
        resn = a["resn"]
        if name in _BACKBONE_N or name in _DONOR_RES.get(resn, set()):
            donors.append(a)
        if name in _BACKBONE_O or name in _ACCEPTOR_RES.get(resn, set()):
            acceptors.append(a)
    return donors, acceptors


def _residue_label(a: dict) -> str:
    return f"{a['resn']}{a['resi']}.{a['chain']}"


def _geometry_interactions(lig_atoms: list[dict], rec_atoms: list[dict]) -> list[dict]:
    hits: list[dict] = []
    seen: set[tuple] = set()

    def add(res_label: str, itype: str, dist: float, detail: str = "") -> None:
        key = (res_label, itype)
        if key in seen:
            return
        # Keep closest of same type later — for now allow one per residue+type
        seen.add(key)
        hits.append(
            {
                "residue": res_label,
                "type": itype,
                "distance_A": round(dist, 2),
                "detail": detail or None,
            }
        )

    lig_don, lig_acc = _ligand_donor_acceptor(lig_atoms)
    rec_don, rec_acc = _protein_donor_acceptor(rec_atoms)

    # H-bonds: ligand donor ↔ protein acceptor
    for ld in lig_don:
        for ra in rec_acc:
            d = _dist(ld, ra)
            if d <= HBOND_DIST:
                add(_residue_label(ra), "HBDonor", d, f"lig→{ra['name']}")
    # ligand acceptor ↔ protein donor
    for la in lig_acc:
        for rd in rec_don:
            d = _dist(la, rd)
            if d <= HBOND_DIST:
                add(_residue_label(rd), "HBAcceptor", d, f"lig←{rd['name']}")

    # Hydrophobic: C···C close to hydrophobic residues
    lig_c = [a for a in lig_atoms if a["elem"] in _HYDROPHOBIC_ELEMS]
    for ra in rec_atoms:
        if not _is_protein_atom(ra):
            continue
        if ra["resn"] not in _HYDROPHOBIC_RES and ra["elem"] != "C":
            continue
        if ra["elem"] not in _HYDROPHOBIC_ELEMS:
            continue
        # skip backbone carbonyl C somewhat — still OK for contacts
        for lc in lig_c:
            d = _dist(lc, ra)
            if d <= HYDROPHOBIC_DIST:
                add(_residue_label(ra), "Hydrophobic", d, ra["name"])
                break

    # Salt bridges (rough): charged residue sidechain ↔ polar lig N/O
    lig_chargedish = [a for a in lig_atoms if a["elem"] in ("N", "O") and a.get("ad_type", "").upper() in ("N", "NA", "OA", "NZ")]
    # broader: any N/O on ligand near charged sidechain
    lig_no = [a for a in lig_atoms if a["elem"] in ("N", "O")]
    for ra in rec_atoms:
        if ra["resn"] not in (_NEG | _POS):
            continue
        name = ra["name"].upper()
        charged_atoms = _ACCEPTOR_RES.get(ra["resn"], set()) | _DONOR_RES.get(ra["resn"], set())
        if name not in charged_atoms:
            continue
        for la in lig_no:
            d = _dist(la, ra)
            if d <= SALT_DIST:
                itype = "Anionic" if ra["resn"] in _NEG else "Cationic"
                add(_residue_label(ra), itype, d, name)
                break

    # π contacts (centroid-ish of aromatic ring atoms)
    arom_atoms = [a for a in rec_atoms if a["resn"] in _AROM and a["elem"] == "C"]
    by_res: dict[str, list] = {}
    for a in arom_atoms:
        by_res.setdefault(_residue_label(a), []).append(a)
    lig_arom_c = [a for a in lig_atoms if a["elem"] == "C" and (a.get("ad_type") or "").upper() in ("A", "C")]
    for label, rats in by_res.items():
        if len(rats) < 3:
            continue
        cx = sum(a["x"] for a in rats) / len(rats)
        cy = sum(a["y"] for a in rats) / len(rats)
        cz = sum(a["z"] for a in rats) / len(rats)
        centroid = {"x": cx, "y": cy, "z": cz}
        for la in lig_arom_c or lig_c:
            d = _dist(la, centroid)
            if d <= PI_DIST:
                add(label, "PiStacking", d, "ring-centroid")
                break

    hits.sort(key=lambda h: (h["type"], h["distance_A"] or 99))
    return hits


def _annotate_prolif(
    receptor_pdbqt: Path,
    poses_pdbqt: Path,
    smiles: str | None,
    top_n: int,
) -> dict[str, Any] | None:
    """Return interactions dict using ProLIF, or None if it fails."""
    try:
        import tempfile

        import MDAnalysis as mda
        import prolif as plf
        from rdkit import Chem
    except Exception as exc:
        log.warning("ProLIF import failed: %s", exc)
        return None

    try:
        # Convert PDBQT receptor → PDB for MDA
        rec_text = receptor_pdbqt.read_text(encoding="utf-8", errors="replace")
        rec_pdb_lines = []
        for line in rec_text.splitlines():
            if line.startswith(("ATOM", "HETATM")):
                rec_pdb_lines.append(line[:66].rstrip())
            elif line.startswith("TER"):
                rec_pdb_lines.append("TER")
        rec_pdb_lines.append("END")

        pose_text = poses_pdbqt.read_text(encoding="utf-8", errors="replace")
        models = _split_pdbqt_models(pose_text)
        if not models:
            return None

        # Build RDKit ligand from SMILES + coords from first pose for template
        if not smiles:
            for line in pose_text.splitlines():
                if line.startswith("REMARK SMILES ") and "IDX" not in line:
                    smiles = line.replace("REMARK SMILES", "", 1).strip()
                    break

        by_pose: dict[str, list] = {}
        contact_residues: list[str] = []

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            rec_pdb = td_path / "rec.pdb"
            rec_pdb.write_text("\n".join(rec_pdb_lines) + "\n", encoding="utf-8")
            u = mda.Universe(str(rec_pdb))
            # PDBQT→PDB often lacks element column; ProLIF/RDKitConverter needs it
            try:
                u.guess_TopologyAttrs(context="default", to_guess=["elements"])
            except Exception:
                try:
                    from MDAnalysis.topology import guessers
                    u.add_TopologyAttr("elements", guessers.guess_types(u.atoms.names))
                except Exception as guess_exc:
                    log.warning("MDA element guess failed: %s", guess_exc)
            protein_ag = u.select_atoms("protein")
            if protein_ag.n_atoms == 0:
                protein_ag = u.atoms

            for i, model in enumerate(models[:top_n]):
                lig_atoms = _parse_pdbqt_atoms(model)
                if not lig_atoms:
                    continue
                # Write pose as PDB
                lig_pdb = td_path / f"lig_{i}.pdb"
                lines = []
                for j, a in enumerate(lig_atoms, 1):
                    elem = a["elem"][:2]
                    lines.append(
                        f"HETATM{j:5d} {a['name']:>4s} LIG L   1    "
                        f"{a['x']:8.3f}{a['y']:8.3f}{a['z']:8.3f}  1.00  0.00          {elem:>2s}"
                    )
                lines.append("END")
                lig_pdb.write_text("\n".join(lines) + "\n", encoding="utf-8")

                # Prefer rdkit mol with bond orders from SMILES
                if smiles:
                    template = Chem.MolFromSmiles(smiles)
                    pose_mol = Chem.MolFromPDBFile(str(lig_pdb), removeHs=False)
                    if template is not None and pose_mol is not None:
                        try:
                            pose_mol = Chem.AssignBondOrdersFromTemplate(template, pose_mol)
                        except Exception:
                            pass
                    lig = plf.Molecule.from_rdkit(pose_mol) if pose_mol else plf.Molecule.from_rdkit(
                        Chem.MolFromPDBFile(str(lig_pdb), removeHs=False)
                    )
                else:
                    lig = plf.Molecule.from_rdkit(Chem.MolFromPDBFile(str(lig_pdb), removeHs=False))

                try:
                    prot = plf.Molecule.from_mda(protein_ag, force=True)
                except TypeError:
                    prot = plf.Molecule.from_mda(protein_ag, inferrer=None)
                fp = plf.Fingerprint()
                fp.run_from_iterable([lig], prot)
                rows = []
                try:
                    df = fp.to_dataframe()
                    # MultiIndex columns: (ligand, protein, interaction)
                    if df is not None and not df.empty:
                        # first frame
                        for col in df.columns:
                            if len(col) >= 3:
                                _lig, prot_res, itype = col[0], col[1], col[2]
                                val = df[col].iloc[0]
                                if val:
                                    res_str = str(prot_res)
                                    rows.append(
                                        {
                                            "residue": res_str,
                                            "type": str(itype),
                                            "distance_A": None,
                                            "detail": None,
                                        }
                                    )
                                    if res_str not in contact_residues:
                                        contact_residues.append(res_str)
                except Exception as exc:
                    log.warning("ProLIF dataframe export failed pose %s: %s", i + 1, exc)
                    # Fallback to ifp dict
                    try:
                        ifp = fp.ifp[0]
                        for (lres, pres), ints in ifp.items():
                            for itype, metadata in ints.items():
                                res_str = str(pres)
                                dist = None
                                if metadata and isinstance(metadata, (list, tuple)) and metadata:
                                    m0 = metadata[0]
                                    if isinstance(m0, dict) and "distance" in m0:
                                        dist = round(float(m0["distance"]), 2)
                                rows.append(
                                    {
                                        "residue": res_str,
                                        "type": str(itype),
                                        "distance_A": dist,
                                        "detail": None,
                                    }
                                )
                                if res_str not in contact_residues:
                                    contact_residues.append(res_str)
                    except Exception as exc2:
                        log.warning("ProLIF ifp fallback failed: %s", exc2)

                by_pose[str(i + 1)] = _stamp_contacts(rows, method="prolif", pose=i + 1)

        if not by_pose:
            return None

        top_detail = by_pose.get("1", [])
        summary = []
        for mode, rows in by_pose.items():
            counts: dict[str, int] = {}
            for r in rows:
                counts[r["type"]] = counts.get(r["type"], 0) + 1
            summary.append({"mode": int(mode), "n_interactions": len(rows), "counts": counts})

        ver = getattr(plf, "__version__", "unknown")
        return {
            "ok": True,
            "tool": "prolif",
            "method": "prolif",
            "tool_version": ver,
            "vicinity_cutoff_A": 6.0,
            "types": ["Hydrophobic", "HBDonor", "HBAcceptor", "PiStacking", "Anionic", "Cationic", "CationPi", "PiCation", "VdWContact"],
            "by_pose": by_pose,
            "top_pose": top_detail,
            "summary": summary,
            "contact_residues": contact_residues,
            "error": None,
        }
    except Exception as exc:
        log.warning("ProLIF annotation failed: %s", exc)
        return None


def _annotate_geometry(
    receptor_pdbqt: Path,
    poses_pdbqt: Path,
    top_n: int,
) -> dict[str, Any]:
    rec_atoms = _parse_pdbqt_atoms(receptor_pdbqt.read_text(encoding="utf-8", errors="replace"))
    models = _split_pdbqt_models(poses_pdbqt.read_text(encoding="utf-8", errors="replace"))
    by_pose: dict[str, list] = {}
    contact_residues: list[str] = []
    for i, model in enumerate(models[:top_n]):
        lig = _parse_pdbqt_atoms(model)
        rows = _geometry_interactions(lig, rec_atoms)
        by_pose[str(i + 1)] = _stamp_contacts(rows, method="geometric", pose=i + 1)
        for r in rows:
            if r["residue"] not in contact_residues:
                contact_residues.append(r["residue"])
    summary = []
    for mode, rows in by_pose.items():
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["type"]] = counts.get(r["type"], 0) + 1
        summary.append({"mode": int(mode), "n_interactions": len(rows), "counts": counts})
    return {
        "ok": True,
        "tool": "rdkit_geometry",
        "method": "geometric",
        "tool_version": None,
        "vicinity_cutoff_A": max(HBOND_DIST, HYDROPHOBIC_DIST, SALT_DIST, PI_DIST),
        "types": ["HBDonor", "HBAcceptor", "Hydrophobic", "Anionic", "Cationic", "PiStacking"],
        "cutoffs_A": {
            "hbond": HBOND_DIST,
            "hydrophobic": HYDROPHOBIC_DIST,
            "salt": SALT_DIST,
            "pi": PI_DIST,
        },
        "by_pose": by_pose,
        "top_pose": by_pose.get("1", []),
        "summary": summary,
        "contact_residues": contact_residues,
        "error": None,
        "note": "Geometry fallback (distance cutoffs). Install prolif+mdanalysis for richer IFPs.",
    }



def _ensure_stamped_result(result: dict[str, Any]) -> dict[str, Any]:
    if not result or not result.get("ok"):
        return result
    method = result.get("method") or (
        "prolif" if result.get("tool") == "prolif" else "geometric"
    )
    result["method"] = method
    by_pose = result.get("by_pose") or {}
    new_by = {}
    for k, rows in by_pose.items():
        if rows and isinstance(rows, list) and rows and not rows[0].get("id"):
            new_by[str(k)] = _stamp_contacts(rows, method=method, pose=k)
        else:
            # still ensure method field
            new_by[str(k)] = [
                {**dict(r), "method": r.get("method") or method}
                if isinstance(r, dict) else r
                for r in (rows or [])
            ]
    result["by_pose"] = new_by
    top = result.get("top_pose") or new_by.get("1") or []
    if top and isinstance(top, list) and top and not (isinstance(top[0], dict) and top[0].get("id")):
        top = _stamp_contacts(top, method=method, pose=1)
    result["top_pose"] = top
    return result


def annotate_interactions(
    receptor_pdbqt: Path | str,
    poses_pdbqt: Path | str,
    *,
    smiles: str | None = None,
    top_n: int = 9,
    prefer_prolif: bool = True,
) -> dict[str, Any]:
    """Annotate docked poses vs receptor. Never raises — returns ok/error fields."""
    rec = Path(receptor_pdbqt)
    poses = Path(poses_pdbqt)
    base: dict[str, Any] = {
        "ok": False,
        "tool": None,
        "tool_version": None,
        "by_pose": {},
        "top_pose": [],
        "summary": [],
        "contact_residues": [],
        "error": None,
    }
    if not rec.is_file():
        base["error"] = f"Missing receptor: {rec}"
        return base
    if not poses.is_file():
        base["error"] = f"Missing poses: {poses}"
        return base

    if prefer_prolif and _prolif_available() and _receptor_has_hydrogens(rec):
        result = _annotate_prolif(rec, poses, smiles, top_n)
        if result and result.get("ok"):
            return _ensure_stamped_result(result)
        # fall through to geometry
    elif prefer_prolif and _prolif_available():
        log.info(
            "ProLIF skipped: receptor PDBQT has no hydrogens "
            "(typical Vina prep); using geometry fallback"
        )

    try:
        return _ensure_stamped_result(_annotate_geometry(rec, poses, top_n))
    except Exception as exc:
        base["error"] = str(exc)
        return base
