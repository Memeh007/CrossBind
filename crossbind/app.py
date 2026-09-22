"""Cross Affinity FastAPI application — local molecular docking."""

from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from crossbind import __version__
from crossbind.config import (
    ALLOWED_LIGAND_EXT,
    ALLOWED_RECEPTOR_EXT,
    HOST,
    JOBS_DIR,
    PORT,
    UPLOAD_MAX_BYTES,
    ensure_dirs,
    resolve_gnina_bin,
    resolve_vina_bin,
)
from crossbind.docking.pipeline import run_docking_job
from crossbind.jobs import job_dir, list_jobs, new_job_id, read_log, read_result
from crossbind.pubchem import name_to_smiles
from crossbind.discovery import refresh_for_target, resolve_protein_query, run_discovery
from crossbind.discovery.structure_convert import StructureConvertError, ensure_receptor_pdb, receptor_convert_meta
from crossbind.discovery.pocket import auto_docking_box
from crossbind.discovery.cache import structures_dir
from crossbind.job_identity import identity_from_discovery, identity_from_manual
from crossbind.residues import parse_residues
from crossbind.security import assert_under, safe_filename

PKG = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PKG / "templates"))

app = FastAPI(title="Cross Affinity", version=__version__, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(PKG / "static")), name="static")

ensure_dirs()


def _engine_status() -> dict:
    v = resolve_vina_bin()
    g = resolve_gnina_bin()
    return {
        "vina_bin": v,
        "vina_ok": bool(v and (Path(v).is_file() or shutil.which(v))),
        "gnina_bin": g,
        "gnina_ok": bool(g and (Path(g).is_file() or shutil.which(g))),
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "version": __version__,
            "engines": _engine_status(),
            "jobs": list_jobs(20),
        },
    )


@app.get("/api/health")
async def health():
    return {"ok": True, "app": "Cross Affinity", "version": __version__, **_engine_status()}


@app.post("/api/pubchem")
async def api_pubchem(name: str = Form(...)):
    try:
        smi = name_to_smiles(name)
        return {"name": name, "smiles": smi}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/dock")
async def dock(
    request: Request,
    compound_name: str = Form("ligand"),
    smiles: str = Form(""),
    pubchem_name: str = Form(""),
    engine: str = Form("vina"),
    center_x: float = Form(0.0),
    center_y: float = Form(0.0),
    center_z: float = Form(0.0),
    size_x: float = Form(20.0),
    size_y: float = Form(20.0),
    size_z: float = Form(20.0),
    exhaustiveness: int = Form(8),
    num_modes: int = Form(9),
    cpu: int = Form(0),
    receptor: UploadFile = File(...),
    ligand_file: Annotated[Optional[UploadFile], File()] = None,
    reference_ligand: Annotated[Optional[UploadFile], File()] = None,
):
    jid = new_job_id()
    jdir = job_dir(jid)
    jdir.mkdir(parents=True, exist_ok=True)

    # Save receptor (PDB / PDBQT / CIF / mmCIF)
    rec_name = safe_filename(receptor.filename or "receptor.pdb", "receptor.pdb")
    rec_ext = Path(rec_name).suffix.lower()
    if rec_ext not in ALLOWED_RECEPTOR_EXT:
        raise HTTPException(400, f"Receptor must be one of {sorted(ALLOWED_RECEPTOR_EXT)}")
    raw_path = jdir / f"upload_receptor_raw{rec_ext}"
    rec_bytes = await receptor.read()
    if len(rec_bytes) > UPLOAD_MAX_BYTES:
        raise HTTPException(400, "Receptor file too large")
    raw_path.write_bytes(rec_bytes)
    if rec_ext in {".cif", ".mmcif"}:
        rec_path = jdir / "upload_receptor.pdb"
        try:
            ensure_receptor_pdb(raw_path, rec_path)
        except StructureConvertError as exc:
            raise HTTPException(400, str(exc)) from exc
        rec_ext = ".pdb"
    else:
        rec_path = jdir / f"upload_receptor{rec_ext}"
        shutil.copy(raw_path, rec_path)

    # Resolve SMILES
    smi = (smiles or "").strip()
    if not smi and pubchem_name.strip():
        try:
            smi = name_to_smiles(pubchem_name.strip())
            (jdir / "resolved_smiles.txt").write_text(smi, encoding="utf-8")
        except Exception as exc:
            raise HTTPException(400, f"Name→SMILES failed: {exc}") from exc

    lig_path = None
    if ligand_file and ligand_file.filename:
        ln = safe_filename(ligand_file.filename, "ligand.sdf")
        lext = Path(ln).suffix.lower()
        if lext not in ALLOWED_LIGAND_EXT:
            raise HTTPException(400, f"Ligand must be one of {sorted(ALLOWED_LIGAND_EXT)}")
        lig_path = jdir / f"upload_ligand{lext}"
        lb = await ligand_file.read()
        if len(lb) > UPLOAD_MAX_BYTES:
            raise HTTPException(400, "Ligand file too large")
        lig_path.write_bytes(lb)

    if not smi and not lig_path:
        raise HTTPException(400, "Provide SMILES, a PubChem name, or a ligand file")

    ref_path = None
    if reference_ligand and reference_ligand.filename:
        rn = safe_filename(reference_ligand.filename, "reference.pdb")
        ref_path = jdir / f"reference{Path(rn).suffix.lower()}"
        rb = await reference_ligand.read()
        ref_path.write_bytes(rb)

    # Also keep original PDB for viewer if provided
    if rec_ext == ".pdb":
        shutil.copy(rec_path, jdir / "receptor.pdb")

    cname = compound_name.strip() or "ligand"
    ident = identity_from_manual(
        compound_name=cname,
        smiles=smi or None,
        receptor_filename=rec_name,
    )
    # If PubChem resolved, stash SMILES on ligand block
    if smi:
        ident["ligand"]["smiles"] = smi
    meta = {
        "id": jid,
        "status": "queued",
        "compound_name": cname,
        "job_title": ident["job_title"],
        "ligand": ident["ligand"],
        "protein": ident["protein"],
        "mechanism": None,
        "engine": engine,
        "center": [center_x, center_y, center_z],
        "size": [size_x, size_y, size_z],
        "source": "manual",
        "vina_affinity": None,
        "gnina_cnn_score": None,
        "gnina_cnn_affinity": None,
        "rmsd_to_reference": None,
        "poses": [],
        "error": None,
    }
    (jdir / "result.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _thread_run():
        run_docking_job(
            jdir,
            receptor_path=rec_path,
            smiles=smi or None,
            ligand_path=lig_path,
            center=(center_x, center_y, center_z),
            size=(size_x, size_y, size_z),
            exhaustiveness=int(exhaustiveness),
            num_modes=int(num_modes),
            cpu=int(cpu),
            engine=engine,
            reference_ligand=ref_path,
            compound_name=cname,
            job_title=ident["job_title"],
            ligand=ident["ligand"],
            protein=ident["protein"],
            mechanism=None,
        )

    threading.Thread(target=_thread_run, daemon=True).start()
    return RedirectResponse(url=f"/job/{jid}", status_code=303)


def _normalize_job_result(result: dict) -> dict:
    """Ensure optional score keys exist so Jinja format filters never see Undefined."""
    if not isinstance(result, dict):
        return {"status": "unknown", "error": "Invalid result.json"}
    out = dict(result)
    for key in (
        "vina_affinity",
        "gnina_cnn_score",
        "gnina_cnn_affinity",
        "rmsd_to_reference",
        "error",
        "poses",
        "ligand",
        "protein",
        "mechanism",
        "job_title",
        "compound_name",
        "status",
        "source",
    ):
        out.setdefault(key, None if key != "poses" else [])
    if out.get("poses") is None:
        out["poses"] = []
    if out.get("ligand") is None:
        out["ligand"] = {}
    if out.get("protein") is None:
        out["protein"] = {}
    return out


@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_page(request: Request, job_id: str):
    try:
        result = _normalize_job_result(read_result(job_id))
    except Exception as exc:
        raise HTTPException(404, str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "job.html",
        {
            "job_id": job_id,
            "result": result,
            "log": read_log(job_id),
            "version": __version__,
            "engines": _engine_status(),
        },
    )


@app.get("/api/job/{job_id}")
async def api_job(job_id: str):
    try:
        result = read_result(job_id)
        result["log"] = read_log(job_id)
        return result
    except Exception as exc:
        raise HTTPException(404, str(exc)) from exc


def _truncate_residues_for_viewer(residues: list[dict], max_aa: int = 400, per_chain: int = 200):
    """Keep all HETATM/ligands; cap AA residues so the DOM cannot explode the viewport."""
    hets = [r for r in residues if not r.get("is_aa")]
    aas = [r for r in residues if r.get("is_aa")]
    total_aa = len(aas)
    by_chain: dict[str, list] = {}
    for r in aas:
        by_chain.setdefault(r["chain"], []).append(r)
    capped: list[dict] = []
    for chain in sorted(by_chain.keys()):
        capped.extend(by_chain[chain][:per_chain])
    if len(capped) > max_aa:
        capped = capped[:max_aa]
    shown_aa = len(capped)
    out = hets + capped

    def sort_key(item: dict):
        try:
            ri = int("".join(c for c in str(item["resi"]) if c.isdigit() or c == "-") or "0")
        except ValueError:
            ri = 0
        return (item["chain"], 0 if item.get("is_aa") else 1, ri, item["resn"])

    out.sort(key=sort_key)
    return out, {
        "residue_truncated": shown_aa < total_aa,
        "aa_shown": shown_aa,
        "aa_total": total_aa,
        "het_count": len(hets),
        "total_all": len(residues),
    }


@app.get("/viewer/{job_id}", response_class=HTMLResponse)
async def viewer_page(request: Request, job_id: str):
    try:
        result = read_result(job_id)
        jdir = job_dir(job_id)
    except Exception as exc:
        raise HTTPException(404, str(exc)) from exc

    # Prefer PDB for residue viz; fall back to pdbqt
    rec_src = jdir / "receptor.pdb"
    if not rec_src.is_file():
        rec_src = jdir / "upload_receptor.pdb"
    if not rec_src.is_file():
        rec_src = jdir / "receptor.pdbqt"

    all_residues = parse_residues(rec_src) if rec_src.is_file() else []
    residues, trunc_meta = _truncate_residues_for_viewer(all_residues)
    aa_only = [r for r in residues if r["is_aa"]]

    return templates.TemplateResponse(
        request,
        "viewer.html",
        {
            "job_id": job_id,
            "result": result,
            "residues": residues,
            "aa_residues": aa_only,
            "residue_truncated": trunc_meta["residue_truncated"],
            "aa_shown": trunc_meta["aa_shown"],
            "aa_total": trunc_meta["aa_total"],
            "version": __version__,
            "box": {
                "center": result.get("center") or [0, 0, 0],
                "size": result.get("size") or [20, 20, 20],
            },
            "engines": _engine_status(),
        },
    )


@app.get("/api/job/{job_id}/residues")
async def api_residues(job_id: str):
    jdir = job_dir(job_id)
    for name in ("receptor.pdb", "upload_receptor.pdb", "receptor.pdbqt"):
        p = jdir / name
        if p.is_file():
            return parse_residues(p)
    return []


@app.get("/api/job/{job_id}/file/{filename}")
async def api_file(job_id: str, filename: str):
    allowed = {
        "receptor.pdb",
        "receptor.pdbqt",
        "upload_receptor.pdb",
        "upload_receptor.pdbqt",
        "ligand.pdbqt",
        "poses.pdbqt",
        "job.log",
        "engine_stdout.txt",
        "result.json",
        "reference.pdb",
        "reference.pdbqt",
        "reference.sdf",
        "reference.mol",
    }
    # also allow reference* with safe suffix
    fname = safe_filename(filename)
    if fname not in allowed and not fname.startswith("reference"):
        raise HTTPException(404, "File not allowed")
    jdir = job_dir(job_id)
    path = assert_under(jdir / fname, jdir)
    if not path.is_file():
        # try upload_receptor variants
        raise HTTPException(404, "File not found")
    media = "chemical/x-pdb" if path.suffix in {".pdb", ".pdbqt"} else "text/plain"
    return FileResponse(path, media_type=media, filename=fname)


@app.get("/api/job/{job_id}/structure")
async def api_structure(job_id: str, kind: str = "receptor", prefer: str = ""):
    """Return structure text for 3Dmol.

    For receptors: if PDB is >1.5MB (or prefer=pdbqt), serve PDBQT first for faster parse.
    """
    jdir = job_dir(job_id)
    pdb_names = ["receptor.pdb", "upload_receptor.pdb"]
    pdbqt_names = ["receptor.pdbqt", "upload_receptor.pdbqt"]
    if kind == "receptor":
        prefer_qt = (prefer or "").lower() == "pdbqt"
        large_pdb = False
        for n in pdb_names:
            p = jdir / n
            if p.is_file() and p.stat().st_size > int(1.5 * 1024 * 1024):
                large_pdb = True
                break
        if prefer_qt or large_pdb:
            names = pdbqt_names + pdb_names
        else:
            names = pdb_names + pdbqt_names
    elif kind == "poses":
        names = ["poses.pdbqt"]
    elif kind == "ligand":
        names = ["ligand.pdbqt"]
    else:
        raise HTTPException(400, "kind must be receptor|poses|ligand")
    for n in names:
        p = jdir / n
        if p.is_file():
            return JSONResponse(
                {
                    "filename": n,
                    "format": "pdb" if p.suffix == ".pdb" else "pdbqt",
                    "data": p.read_text(encoding="utf-8", errors="replace"),
                }
            )
    raise HTTPException(404, f"No {kind} structure")



@app.get("/discover", response_class=HTMLResponse)
async def discover_page(request: Request):
    return templates.TemplateResponse(
        request,
        "discover.html",
        {
            "version": __version__,
            "engines": _engine_status(),
        },
    )


@app.post("/api/discover")
async def api_discover(name: str = Form(...), uniprot: str = Form("")):
    try:
        result = run_discovery(name.strip(), uniprot=(uniprot or "").strip() or None)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/discover/protein")
async def api_discover_protein(query: str = Form(...), species: str = Form("human")):
    """Resolve UniProt / gene / PDB ID into a study-protein card + structure candidates."""
    try:
        result = resolve_protein_query(query.strip(), species=(species or "human").strip() or "human")
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error") or "Not found")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/discover/select-target")
async def api_discover_select_target(
    discovery_json: str = Form(...),
    uniprot: str = Form(""),
    pdb_id: str = Form(""),
):
    """Re-fetch structure + pocket + orthologs for a chosen protein / PDB."""
    try:
        payload = json.loads(discovery_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid discovery_json: {exc}") from exc
    up = (uniprot or "").strip() or None
    pid = (pdb_id or "").strip() or None
    if not up and not pid:
        raise HTTPException(400, "Provide uniprot or pdb_id")
    try:
        updated = refresh_for_target(payload, uniprot=up, pdb_id=pid)
        return updated
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc



@app.post("/api/discover/upload-structure")
async def api_discover_upload_structure(
    structure_file: UploadFile = File(...),
    uniprot: str = Form(""),
    gene: str = Form(""),
    label: str = Form("uploaded"),
):
    """Accept AlphaFold/predicted PDB or CIF; cache it and return structure + pocket."""
    try:
        fname = safe_filename(structure_file.filename or "upload.pdb", "upload.pdb")
        ext = Path(fname).suffix.lower()
        if ext not in ALLOWED_RECEPTOR_EXT:
            raise HTTPException(400, f"Structure must be one of {sorted(ALLOWED_RECEPTOR_EXT)}")
        raw = await structure_file.read()
        if len(raw) > UPLOAD_MAX_BYTES:
            raise HTTPException(400, "Structure file too large")
        if len(raw) < 50:
            raise HTTPException(400, "Structure file empty or too small")

        dest_dir = structures_dir() / "uploads"
        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = new_job_id()
        raw_path = dest_dir / f"{stamp}_{fname}"
        raw_path.write_bytes(raw)

        if ext in {".cif", ".mmcif"}:
            pdb_path = dest_dir / f"{stamp}_{Path(fname).stem}.pdb"
            try:
                ensure_receptor_pdb(
                    raw_path,
                    pdb_path,
                    uniprot=(uniprot or "").strip().upper() or None,
                )
            except StructureConvertError as exc:
                raise HTTPException(400, str(exc)) from exc
            path = pdb_path
            fmt = "pdb"
        else:
            path = raw_path
            fmt = ext.lstrip(".")

        pocket = auto_docking_box(path)
        up = (uniprot or "").strip().upper() or None
        g = (gene or "").strip() or None
        lab = (label or "uploaded").strip() or "uploaded"
        structure = {
            "ok": True,
            "provenance": "user_upload",
            "label": "uploaded" if lab in {"uploaded", "upload", ""} else lab,
            "pdb_id": None,
            "uniprot": up,
            "path": str(path),
            "format": fmt,
            "warning": (
                "User-uploaded structure (e.g. AlphaFold predicted). "
                "Not an experimental PDB — verify the docking box before interpreting scores."
            ),
            "method": "user upload (predicted or experimental)",
            "resolution_A": None,
            "plddt_mean": None,
            "filename": fname,
        }
        return {
            "ok": True,
            "structure": structure,
            "pocket": pocket,
            "selected_uniprot": up,
            "selected_protein": {
                "gene": g,
                "uniprot": up,
                "protein_name": g or up or fname,
                "organism": None,
                "function": None,
                "mechanism": None,
                "method": structure["method"],
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Upload failed: {exc}") from exc


@app.post("/api/discover/dock")
async def api_discover_dock(
    discovery_json: str = Form(...),
    engine: str = Form("vina"),
    exhaustiveness: int = Form(8),
    num_modes: int = Form(9),
    cpu: int = Form(0),
):
    """Create a docking job from a Discover payload (receptor path + SMILES + auto-box)."""
    try:
        payload = json.loads(discovery_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid discovery_json: {exc}") from exc

    try:
        return await _discover_dock_inner(
            payload, engine=engine, exhaustiveness=exhaustiveness, num_modes=num_modes, cpu=cpu
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Discover dock failed: {exc}") from exc


async def _discover_dock_inner(payload, *, engine, exhaustiveness, num_modes, cpu):
    drug = payload.get("drug") or {}
    structure = payload.get("structure") or {}
    pocket = payload.get("pocket") or {}
    smi = (drug.get("smiles") or "").strip()
    rec_src = structure.get("path")
    if not smi:
        raise HTTPException(400, "Discovery payload missing SMILES")
    if not rec_src or not Path(rec_src).is_file():
        raise HTTPException(400, "Discovery payload missing receptor structure file")

    center = pocket.get("center") or [0.0, 0.0, 0.0]
    size = pocket.get("size") or [22.0, 22.0, 22.0]
    if len(center) != 3 or len(size) != 3:
        raise HTTPException(400, "Invalid pocket center/size")

    ident = identity_from_discovery(payload)

    jid = new_job_id()
    jdir = job_dir(jid)
    jdir.mkdir(parents=True, exist_ok=True)

    src = Path(rec_src)
    # Copy into job dir; convert CIF/mmCIF→PDB (prefer AF PDB / gemmi / Biopython)
    try:
        if src.suffix.lower() in {".cif", ".mmcif"}:
            rec_path = jdir / "upload_receptor.pdb"
            meta_ids = receptor_convert_meta(structure)
            ensure_receptor_pdb(
                src,
                rec_path,
                uniprot=meta_ids.get("uniprot") or payload.get("selected_uniprot"),
                entry_id=meta_ids.get("entry_id"),
                pdb_url=meta_ids.get("pdb_url"),
            )
        else:
            rec_ext = src.suffix.lower() if src.suffix.lower() in ALLOWED_RECEPTOR_EXT else ".pdb"
            rec_path = jdir / f"upload_receptor{rec_ext}"
            shutil.copy(src, rec_path)
        if rec_path.suffix.lower() == ".pdb":
            shutil.copy(rec_path, jdir / "receptor.pdb")
    except StructureConvertError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Receptor prepare failed: {exc}") from exc

    (jdir / "resolved_smiles.txt").write_text(smi, encoding="utf-8")
    (jdir / "discovery.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    compound = ident.get("compound_name") or (drug.get("input") or "ligand").strip() or "ligand"
    cx, cy, cz = float(center[0]), float(center[1]), float(center[2])
    sx, sy, sz = float(size[0]), float(size[1]), float(size[2])

    meta = {
        "id": jid,
        "status": "queued",
        "compound_name": compound,
        "job_title": ident.get("job_title"),
        "ligand": ident.get("ligand"),
        "protein": ident.get("protein"),
        "mechanism": ident.get("mechanism"),
        "honesty": ident.get("honesty") or (payload.get("honesty")),
        "engine": engine,
        "center": [cx, cy, cz],
        "size": [sx, sy, sz],
        "source": "discover",
        "structure_provenance": structure.get("provenance"),
        "pocket_method": pocket.get("method"),
        "vina_affinity": None,
        "gnina_cnn_score": None,
        "gnina_cnn_affinity": None,
        "rmsd_to_reference": None,
        "poses": [],
        "error": None,
        "docking": {
            "engine": engine,
            "scoring": "vina" if (engine or "vina").lower() == "vina" else engine,
            "center": [cx, cy, cz],
            "size": [sx, sy, sz],
            "exhaustiveness": int(exhaustiveness),
            "num_modes": int(num_modes),
            "cpu": int(cpu),
            "pocket_method": pocket.get("method"),
            "ligand_prep": "meeko",
        },
    }
    (jdir / "result.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _thread_run():
        run_docking_job(
            jdir,
            receptor_path=rec_path,
            smiles=smi,
            ligand_path=None,
            center=(cx, cy, cz),
            size=(sx, sy, sz),
            exhaustiveness=int(exhaustiveness),
            num_modes=int(num_modes),
            cpu=int(cpu),
            engine=engine,
            reference_ligand=None,
            compound_name=compound,
            job_title=ident.get("job_title"),
            ligand=ident.get("ligand"),
            protein=ident.get("protein"),
            mechanism=ident.get("mechanism"),
        )

    threading.Thread(target=_thread_run, daemon=True).start()
    return JSONResponse({
        "ok": True,
        "job_id": jid,
        "job_title": ident.get("job_title"),
        "redirect": f"/job/{jid}",
    })


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_list(request: Request):
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {"jobs": list_jobs(100), "version": __version__, "engines": _engine_status()},
    )


def main():
    import uvicorn

    ensure_dirs()
    uvicorn.run(
        "crossbind.app:app",
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
