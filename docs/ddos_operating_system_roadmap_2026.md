# ddOS — Drug Discovery Operating System roadmap (evidence-backed)

**Product name:** **ddOS** (Drug Discovery Operating System)  
**Python package (temporary):** `crossbind` (import path unchanged; repo/folder may remain CrossBind)  
**Author context:** Alexander Cecena — local-first research docking / Discover workbench  
**Researched / cited:** 2026-09-22 (PT)  
**Guiding constraint:** **library-first** — wrap mature PyPI / CLI tools; orchestration + UX + honesty, not reinvented chemistry.

---

## 1. Vision

**ddOS** is a privacy-first, local drug-discovery operating system: from drug identity → target evidence → structure provenance → pocket → multi-engine docking → interpretable interactions → ADMET triage → ranked study tables — without claiming experimental affinities from docking scores alone.

The UI product is **ddOS**. The Python package may remain `crossbind` until a deliberate rename is warranted. GitHub repo / Desktop folder **CrossBind** need not rename for this cut.

---

## 2. What we already have

Shipped in the CrossBind / `crossbind` codebase (v1.2.x → v1.3.0 rebrand):

| Capability | Notes |
|------------|--------|
| **Discover** | Drug name → PubChem / ChEMBL (± Open Targets fallback) → UniProt targets → PDB (RCSB) or AlphaFold DB → auto docking box → prepare & dock |
| **Dock** | SMILES / file / PubChem → RDKit → Meeko → Open Babel receptor PDBQT → **AutoDock Vina 1.2.x**; optional **GNINA** fields |
| **ADMET** | Post-dock RDKit descriptors / drug-likeness triage on job results |
| **IFP / interactions** | Residue contact table + honesty banner; ProLIF when available, geometric fallback |
| **Cancel / queue** | Job cancel + queue hygiene for stuck docking workers |
| **Evidence summary** | Deterministic binding-proof summary; optional local Ollama narration (no cloud LLM by default) |
| **3D viewer** | 3Dmol.js cartoon + sidechains, residue browser, box overlay, ranked poses |
| **Local-first** | FastAPI + Jinja2, binds `127.0.0.1:8787` by default |

Companion docs (pre-ddOS naming): `cross_affinity_discovery_os_blueprint.md`, `cross_affinity_library_first.md`, `cross_affinity_sota_docking_landscape_2026.md`, `cross_affinity_job_essentials_and_roadmap.md`.

---

## 3. Evidence-backed principles (with citations)

### 3.1 Docking scores ≠ experimental affinity

Classical docking scores (including AutoDock Vina) are **ranking / pose-generation tools**, not calibrated Kd/IC50 predictors. Kinome-scale docking-informed ML work shows that learning from docked poses substantially improves affinity prediction relative to treating raw docking scores as affinity ([Schifferstein, Bernatavicius & Janssen, *J. Chem. Inf. Model.* 2024](https://doi.org/10.1021/acs.jcim.4c01260) — docking-informed ML for kinome-wide affinity; DOI [10.1021/acs.jcim.4c01260](https://pubs.acs.org/doi/10.1021/acs.jcim.4c01260)).

**ddOS rule:** never label Vina (or DiffDock confidence) as Kd; keep score fields named and provenance-tagged.

### 3.2 GNINA CNN improves virtual-screening enrichment vs Vina (many settings)

GNINA adds CNN rescoring / refinement on a Vina-family search. Virtual screening evaluations and GNINA 1.0 / 1.3 papers report improved enrichment and ranking vs empirical Vina scoring in many benchmarks ([McNutt et al., GNINA 1.0, *J. Cheminform.* 2021](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-021-00522-2); [Sunseri & Koes, *Molecules* 2021 — Virtual Screening with Gnina 1.0](https://www.mdpi.com/1420-3049/26/23/7369); [McNutt et al., GNINA 1.3, *J. Cheminform.* 2025](https://doi.org/10.1186/s13321-025-00973-x); [gnina/gnina](https://github.com/gnina/gnina)).

**ddOS rule:** promote GNINA to a first-class engine path; store `vina_affinity` and CNN fields separately.

### 3.3 DiffDock / DiffDock-L — generative pose / blind docking; confidence ≠ affinity

DiffDock is a diffusion generative model for ligand poses with a **confidence** score for pose quality — explicitly **not** binding affinity ([Corso et al., DiffDock](https://doi.org/10.48550/arxiv.2210.01776); [DiffDock README FAQ](https://github.com/gcorso/DiffDock); DiffDock-L generalization work). Docs and practitioner notes (e.g. ProteinIQ / DiffDock skill references) reiterate: rescore with GNINA / Vina / MM/GBSA / FEP for affinity-oriented ranking.

**ddOS rule:** DiffDock is an optional pose path; confidence is a pose-quality badge, never an affinity column.

### 3.4 P2Rank for pocket finding

P2Rank is a fast ML pocket predictor suitable for pipelines ([Krivák & Hoksza, *J. Cheminform.* 2018](https://doi.org/10.1186/s13321-018-0285-8)). PrankWeb 3 adds AlphaFold-oriented workflows ([Jakubec et al., *NAR* 2022 — PrankWeb 3](https://doi.org/10.1093/nar/gkac389)). For AF / NMR / cryo-EM inputs, use P2Rank **`-c alphafold`** so pLDDT-in-B-factor is not treated as crystallographic B-factor ([rdk/p2rank](https://github.com/rdk/p2rank)).

**ddOS rule:** pockets are hypotheses; store method, config (`alphafold` vs default), scores, residues, and source structure id.

### 3.5 AlphaFold as docking target — pocket look ≠ pose success

AF models can look accurate globally while **pose success drops sharply** vs crystal:

- eLife GPCR-focused evaluation: AF2 docking success far below experimental structures (e.g. ~15% AF2 vs ~44% experimental with Glide SP in that study) ([He et al., *eLife* 89386](https://doi.org/10.7554/elife.89386) / [https://elifesciences.org/articles/89386](https://elifesciences.org/articles/89386)).
- AutoDock-GPU evaluation on PDBbind-derived AF2 targets: ~**17%** success vs ~**41%** crystal redocking (RMSD &lt; 2 Å) ([Holcomb et al., evaluation of AF2 as docking targets](https://pmc.ncbi.nlm.nih.gov/articles/PMC9794023/)).

**ddOS rule:** structure provenance honesty banners (experimental PDB vs AFDB); prefer holo PDB when available; warn on AF docking.

### 3.6 MM/GBSA / FEP for shortlist ranking

After docking triage, physics-based free-energy methods improve relative ranking for small analog sets. See free-energy / FEP reviews in drug discovery ([Expert Opin. Drug Discov. 2024 free-energy review](https://www.tandfonline.com/doi/full/10.1080/17460441.2024.2369593) — cite the specific review used in implementation notes) and OpenBioSim **ligand_fep_workflows** / OpenFE ecosystem for open pipelines ([OpenBioSim](https://www.openbiosim.org/), OpenFE docs).

**ddOS rule:** MM/GBSA / FEP are **P2 shortlist** tools, not Discover defaults.

### 3.7 ADMET triage

Early in silico ADMET filters candidates before wet lab. Practical stack:

- [SwissADME](http://www.swissadme.ch/)
- [ADMETlab 3.0](https://admetlab3.scbdd.com/)
- [ADMET-AI](https://admet.ai.greenstonebio.com/) ([Swanson et al.](https://github.com/swansonk14/admet_ai))

Workflow-oriented reviews in 2025–2026 Sci Pharm / methods literature emphasize integrated ADMET → target → docking pipelines (label outputs as computational triage, not clinical evidence).

**ddOS rule:** keep RDKit local descriptors now; wrap ADMET-AI / server APIs as optional workers with model/version provenance.

### 3.8 Knowledge graph — Open Targets + ChEMBL MoA

Target tractability and mechanism-of-action evidence: Open Targets Platform GraphQL ([platform-docs.opentargets.org](https://platform-docs.opentargets.org/)) plus ChEMBL mechanisms (`chembl-webresource-client`). Prefer curated MoA ≫ single assay ≫ text-mined association.

### 3.9 Peer platforms (patterns to steal, not clone)

| Peer | Pattern |
|------|---------|
| **PocketDock** | P2Rank + Vina + ADMET + MM/GBSA-style refinement pipeline |
| **PickyBinder** | Nextflow benchmark spanning Vina / GNINA / DiffDock / P2Rank |
| **DockThor-VS** | Job naming, redock RMSD culture, VS-oriented UX |

### 3.10 2026 open-source docking workflow review

Workflow-centered survey of open docking + AI SBDD:  
[Open-Source Molecular Docking and AI-Augmented Structure-Based Drug Design… *Int. J. Mol. Sci.* 2026, 27(7), 3302](https://www.mdpi.com/1422-0067/27/7/3302) · [PMC13073925](https://pmc.ncbi.nlm.nih.gov/articles/PMC13073925/).

Use this as the north-star checklist: prep → site → engines → validation → AI rescoring — with honesty about limits.

---

## 4. Prioritized ddOS slices (P0–P2)

Library-first: wrap CLIs/containers; record tool versions; do not reimplement pocket ML, CNN docking, or FEP engines.

### P0 — Credibility foundations

| Slice | Tool-to-wrap | Outcome |
|-------|--------------|---------|
| P2Rank pockets + ligand-aware Vina | `rdk/p2rank` CLI; `-c alphafold` for AF; Vina top-K | **Shipped v1.3.1** — holo prefer / P2Rank / centroid fallback; ligand-aware best-ranked under Vina |
| Multi-PDB ensemble picker | RCSB search + metadata | Prefer holo / resolution / organism-matched |
| Redock RMSD when holo | Existing `rmsd.py` + crystal ligand | Pass/fail vs ~2 Å heuristic (benchmark, not guarantee) |
| Batch ligands → study table | Job batch + CSV/HTML study view | Ligand × structure scores matrix |
| Structure provenance banners | Result `provenance` enum | AF vs PDB honesty always visible |

### P1 — Multi-engine + biology dossier

| Slice | Tool-to-wrap | Outcome |
|-------|--------------|---------|
| First-class GNINA | `GNINA_BIN` path as peer to Vina | CNN score/affinity columns + UI engine toggle |
| DiffDock optional path | DiffDock / DiffDock-L container | Pose + confidence; no affinity claim |
| ProLIF viz | `prolif` | IFP fingerprints / interaction plots |
| Open Targets tractability dossier | OT GraphQL | Target card: MoA, diseases, tractability |
| Consensus rank (Vina+GNINA) | Local rank fusion | Transparent consensus, not “true affinity” |

### P2 — Physics shortlist + scale

| Slice | Tool-to-wrap | Outcome |
|-------|--------------|---------|
| OpenMM minimize + MM/GBSA | OpenMM + open tooling | Post-dock refine / rescore shortlist |
| OpenBioSim FEP for analogs | OpenBioSim / OpenFE ligand FEP workflows | Relative ΔΔG for close analogs |
| Ultralarge library hooks | Space / Enamine-style APIs or local chunks | Async screen jobs, not interactive Discover |
| Species ortholog docking | Ensembl / OMA / OrthoDB adapters | Honest ortholog miss; dock when mapped |

---

## 5. Explicit non-goals

- **Claiming Kd / IC50 / experimental ΔG from Vina** (or DiffDock confidence).
- **Bundled hallucinating LLM as biology authority** — optional local Ollama may narrate evidence already computed; it must not invent targets, pockets, or affinities.
- **Reinventing chemistry libraries** — no custom H-bond detectors, SMILES parsers, or pocket ML when RDKit / ProLIF / P2Rank / GNINA exist.
- **Equivalence claims** to ICM, Glide, FEP+, or Munroe Lab software.
- **Forced rename** of GitHub repo / Desktop folder CrossBind or import path `crossbind` in this cut.

---

## 6. Suggested UI IA for ddOS

| Nav | Role |
|-----|------|
| **Discover** | Drug → targets → structure → dock (today’s vertical slice) |
| **Screen** | Batch / library virtual screening jobs |
| **Study** | Multi-ligand / multi-structure comparison tables |
| **Jobs** | Queue, cancel, logs, status |
| **Structures** | Cached PDB/AF ensemble browser + provenance |
| **Health** | Engines (Vina/GNINA/…), versions, data paths |

Current sidebar (Discover | Dock | Jobs | Health) maps toward this IA: **Dock** evolves into Screen/Study entry points; **Structures** is new.

---

## 7. Version / branding note

- **Product:** ddOS — Drug Discovery Operating System  
- **Package:** `crossbind` (temporary)  
- **Version at rebrand:** 1.3.0  

---

*Evidence links verified 2026-09-22 (PT) via publisher / PMC / GitHub sources listed above. Prefer DOIs in academic citations; prefer primary tool docs for operational flags (e.g. P2Rank `-c alphafold`).*
