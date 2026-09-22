# ddOS (Drug Discovery Operating System)

**Repository / folder:** CrossBind · **Python package:** `crossbind` (import path unchanged)

**Local drug-discovery workbench for researchers** — *biology × compute*.

**ddOS** is a standalone open-source web app (FastAPI + Jinja2) that prepares ligands and receptors and runs **AutoDock Vina 1.2.x** on your machine. Slice 1 adds a **Discover** flow (drug → targets → structure → auto-box → dock). Optional **GNINA** CNN scores are supported as separate fields. It is **not** Munroe Lab software and does **not** claim equivalence to ICM (Molsoft) affinities.

Product name is **ddOS**; the package folder remains `crossbind` for now. See `docs/ddos_operating_system_roadmap_2026.md`.

Author: **Alexander Cecena** ([Memeh007](https://github.com/Memeh007)) · License: **MIT**

---

## Features

- Upload receptor **PDB / PDBQT**
- Ligand via **SMILES**, file (SDF/MOL/MOL2/PDB/PDBQT), or **PubChem name → SMILES** (retry + CACTUS fallback)
- Pipeline: RDKit (AddHs → Embed → MMFF) → **Meeko** PDBQT → Open Babel receptor PDBQT → **Vina** CLI
- Optional **GNINA** engine (`GNINA_BIN`) with `vina_affinity` vs `gnina_cnn_score` / `gnina_cnn_affinity`
- Docking box controls, exhaustiveness, CPU threads, job log, results table, pose downloads
- **Signature GUI:** 3Dmol.js viewer — cartoon + all amino-acid sidechains toggle, searchable residue list (chain/resi/resn) with click-to-highlight, docking box overlay, ranked poses
- **Residue binding proof** on the job page: contact table (residue, chain/res, type, distance, atom detail, method), geometric cutoffs, honesty banner, deterministic evidence summary, optional local Ollama narration (`OLLAMA_HOST` / `OLLAMA_MODEL`; no cloud LLMs by default)
- Redock **RMSD** helper when a reference ligand is provided
- Binds **127.0.0.1** by default (port **8787**)


## Discover (Slice 1)

Vertical slice for research triage (demo drug: **metformin**):

1. Drug name → **PubChemPy** CID / SMILES / InChIKey (RDKit sanitize)
2. **ChEMBL** mechanisms/targets (Open Targets GraphQL fallback when ChEMBL is down)
3. Best structure: **rcsb-api** PDB by UniProt, else **Biopython** AlphaFold DB CIF
4. Auto docking box (crystal ligand centroid + padding, else protein centroid with warning)
5. **Prepare & dock** reuses the existing Meeko / Vina pipeline
6. Ortholog panel stubs: human, mouse, fly, dog, rabbit, cat, planaria (**honest miss** if unmapped)

```bash
# after venv + requirements
python scripts/smoke_discover_metformin.py
pytest tests/test_drug_metformin.py -q
uvicorn crossbind.app:app --host 127.0.0.1 --port 8787
# open http://127.0.0.1:8787/discover
```

Docs: `docs/ddos_operating_system_roadmap_2026.md`, `docs/cross_affinity_discovery_os_blueprint.md`, `docs/cross_affinity_library_first.md`.

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
2. Download `vina_1.2.x_windows_x86_64.exe` (or similar), rename/copy to `CrossBind\bin\vina.exe`, **or** set:
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
cd CrossBind
run.bat
```

Or:

```bash
cd CrossBind
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
| `CROSSBIND_HOST` | Bind host (default `127.0.0.1`) |
| `CROSSBIND_PORT` | Port (default `8787`) |
| `CROSSBIND_DATA` | Override data directory |
| `CROSSBIND_UPLOAD_MAX` | Max upload bytes |

## Project layout

```
CrossBind/
  crossbind/             # Python package (UI product name: ddOS; folder still crossbind)
    discovery/           # Slice 1 adapters (drug, targets, structures, pocket, …)
    docking/             # Meeko / Vina / GNINA pipeline
  data/jobs/             # Job storage (gitignored)
  data/cache/            # SQLite + structure cache (gitignored blobs)
  docs/                  # ddOS roadmap + discovery blueprint + library-first catalog
  scripts/               # Smoke scripts
  tests/
  bin/                   # Optional local vina/gnina binaries (gitignored)
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

Remote: **https://github.com/Memeh007/CrossBind**

```bash
git remote add origin https://github.com/Memeh007/CrossBind.git
git push -u origin main
```

## Disclaimer

Research / educational software. Docking scores guide hypotheses; they are not clinical or regulatory decisions.
