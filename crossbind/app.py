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

    # Save receptor
    rec_name = safe_filename(receptor.filename or "receptor.pdb", "receptor.pdb")
    rec_ext = Path(rec_name).suffix.lower()
    if rec_ext not in ALLOWED_RECEPTOR_EXT:
        raise HTTPException(400, f"Receptor must be one of {sorted(ALLOWED_RECEPTOR_EXT)}")
    rec_path = jdir / f"upload_receptor{rec_ext}"
    rec_bytes = await receptor.read()
    if len(rec_bytes) > UPLOAD_MAX_BYTES:
        raise HTTPException(400, "Receptor file too large")
    rec_path.write_bytes(rec_bytes)

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

    # Always mirror receptor for viewer (even if docking fails mid-pipeline)
    if rec_ext == ".pdb":
        shutil.copy(rec_path, jdir / "receptor.pdb")
    elif rec_ext == ".pdbqt":
        shutil.copy(rec_path, jdir / "receptor.pdbqt")

    meta = {
        "id": jid,
        "status": "queued",
        "compound_name": compound_name.strip() or "ligand",
        "engine": engine,
        "center": [center_x, center_y, center_z],
        "size": [size_x, size_y, size_z],
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
            compound_name=compound_name.strip() or "ligand",
        )

    threading.Thread(target=_thread_run, daemon=True).start()
    return RedirectResponse(url=f"/job/{jid}", status_code=303)


@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_page(request: Request, job_id: str):
    try:
        result = read_result(job_id)
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

    residues = parse_residues(rec_src) if rec_src.is_file() else []
    aa_only = [r for r in residues if r["is_aa"]]

    return templates.TemplateResponse(
        request,
        "viewer.html",
        {
            "job_id": job_id,
            "result": result,
            "residues": residues,
            "aa_residues": aa_only,
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
async def api_structure(job_id: str, kind: str = "receptor"):
    """Return structure text for 3Dmol."""
    jdir = job_dir(job_id)
    mapping = {
        "receptor": ["receptor.pdb", "upload_receptor.pdb", "receptor.pdbqt", "upload_receptor.pdbqt"],
        "poses": ["poses.pdbqt"],
        "ligand": ["ligand.pdbqt"],
    }
    names = mapping.get(kind)
    if not names:
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
