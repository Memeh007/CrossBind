# Cross Affinity

**Local molecular docking for researchers** — branded molecule with living atom/bond physics on boot. — *biology × compute*.

Cross Affinity is a standalone open-source web app (FastAPI + Jinja2) that prepares ligands and receptors and runs **AutoDock Vina 1.2.x** on your machine. Optional **GNINA** CNN scores are supported as separate fields. It is **not** Munroe Lab software and does **not** claim equivalence to ICM (Molsoft) affinities.

Author: **Alexander Cecena** ([Memeh007](https://github.com/Memeh007)) · License: **MIT**

---

## Features

- Upload receptor **PDB / PDBQT**
- Ligand via **SMILES**, file (SDF/MOL/MOL2/PDB/PDBQT), or **PubChem name → SMILES** (retry + CACTUS fallback)
- Pipeline: RDKit (AddHs → Embed → MMFF) → **Meeko** PDBQT → Open Babel receptor PDBQT → **Vina** CLI
- Optional **GNINA** engine (`GNINA_BIN`) with `vina_affinity` vs `gnina_cnn_score` / `gnina_cnn_affinity`
- Docking box controls, exhaustiveness, CPU threads, job log, results table, pose downloads
- **Signature GUI:** 3Dmol.js viewer — cartoon + all amino-acid sidechains toggle, searchable residue list (chain/resi/resn) with click-to-highlight, docking box overlay, ranked poses
- Redock **RMSD** helper when a reference ligand is provided
- Binds **127.0.0.1** by default (port **8787**)

## Scoring honesty

| Engine | Score fields | Notes |
|--------|--------------|-------|
| AutoDock Vina 1.2.x | `vina_affinity` (kcal/mol) | Default. Different function than ICM. |
| GNINA (optional) | `vina_affinity`, `gnina_cnn_score`, `gnina_cnn_affinity` | CNN rescoring; still not ICM. |

Absolute kcal/mol values are **not interchangeable** across engines or with commercial packages. Validate with redocking RMSD and experiment.

## Requirements

- Python **3.11+** (3.12 recommended)
- **AutoDock Vina 1.2.x** binary ([releases](https://github.com/ccsb-scripps/AutoDock-Vina/releases))
- **Open Babel** (Python bindings *or* `obabel` on `PATH`) — or upload receptors already as `.pdbqt`
- Optional: **GNINA** binary

### Windows notes

1. Install Python from [python.org](https://www.python.org/downloads/) (check “Add to PATH”).
2. Download `vina_1.2.x_windows_x86_64.exe` (or similar), rename/copy to `Cross Affinity\bin\vina.exe`, **or** set:
   ```bat
   set VINA_BIN=C:\path\to\vina.exe
   ```
3. Install [Open Babel](https://openbabel.org/) and ensure `obabel.exe` is on PATH, **or** convert receptors to PDBQT ahead of time.
4. Double-click `run.bat`.

### Linux notes

```bash
# Vina: place binary on PATH or export VINA_BIN=/path/to/vina
# Open Babel:
sudo apt install openbabel libopenbabel-dev   # Debian/Ubuntu example

chmod +x run.sh
./run.sh
```

## Quick start

```bat
cd Cross Affinity
run.bat
```

Or:

```bash
cd Cross Affinity
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
export VINA_BIN=/path/to/vina   # or set VINA_BIN on Windows
uvicorn crossbind.app:app --host 127.0.0.1 --port 8787
```

Open **http://127.0.0.1:8787**

## Environment variables

| Variable | Purpose |
|----------|---------|
| `VINA_BIN` | Full path to Vina executable (default: search `bin/`, PATH) |
| `GNINA_BIN` | Full path to GNINA (optional) |
| `CROSS AFFINITY_HOST` | Bind host (default `127.0.0.1`) |
| `CROSS AFFINITY_PORT` | Port (default `8787`) |
| `CROSS AFFINITY_DATA` | Override data directory |
| `CROSS AFFINITY_UPLOAD_MAX` | Max upload bytes |

## Project layout

```
Cross Affinity/
  crossbind/           # Python package (app, docking pipeline, templates, static)
  data/jobs/           # Job storage (gitignored)
  bin/                 # Optional local vina/gnina binaries (gitignored)
  run.bat / run.sh
  requirements.txt
  README.md  SECURITY.md  LICENSE
```

## Pipeline (reference)

1. SMILES → RDKit `AddHs` → `EmbedMolecule` → `MMFFOptimize`
2. Meeko `MoleculePreparation` + `PDBQTWriterLegacy` → `ligand.pdbqt`
3. Open Babel PDB → PDBQT (rigid receptor)
4. Vina CLI: `--receptor --ligand --center_* --size_* --exhaustiveness --out`
5. Parse top pose affinity from stdout

Subprocess calls use **argv lists only** (no shell).

## GitHub

Prepared for publication under **Memeh007/crossbind** or **Memeh007/Cross Affinity**. This repo is initialized locally; create the remote when ready (do not force-push).

```bash
git remote add origin https://github.com/Memeh007/Cross Affinity.git
git push -u origin main
```

## Disclaimer

Research / educational software. Docking scores guide hypotheses; they are not clinical or regulatory decisions.

## Make it better (roadmap)

- Prefer **GNINA** when installed; show Vina + CNN side-by-side and optional consensus rank
- **Auto-box** from uploaded reference ligand / selected residues
- **Batch dock** from a SMILES CSV (queue jobs)
- Explicit **protonation / pH** prep notes (and Open Babel options) in the UI
- Always-on **redock RMSD report card** when a crystal pose is supplied
- One-click **demo fixture** (public PDB + ligand) for first-run
- Portfolio card + short LinkedIn clip of the boot → dock loop
- Multi-conformer ligand ensemble (often improves pose quality)

## Branding

- Product name: **Cross Affinity** (Python package folder remains crossbind for imports).
- Runtime logo: crossbind/static/img/logo-molecule.svg — real <circle> / <line> atoms & bonds, animated by molecule-orbs.js (independent node drift, bond stretch, 4.5s breathe + glow; core ligand anchored).
- CrossAffinityIcon.svg in the repo root is a VTracer raster-trace (~7.5MB, 15k paths). Keep as art reference; do not load it in the browser boot screen.
