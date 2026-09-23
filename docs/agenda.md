# ddOS Agenda — what we are actually building

**Product:** **ddOS** (Drug Discovery Operating System)  
**Repo / folder:** CrossBind · **Python package (for now):** `crossbind`  
**Author:** Alexander Cecena  
**Status:** Living north-star. **Standing agent contract (read before every code change):** [AGENTS.md](../AGENTS.md) at repo root. Update this file whenever vision or priorities change.  
**Rule:** Do **not** start UI redesign until Alexander explicitly says go (see §8).

This file exists so we never drift back into “just another docking form.” ddOS is an **operating system for pre–wet-lab discovery**: biology × compute × interpretation × visualization that makes every biological process *legible*.

---

## 1. One-sentence mission

Build a **local-first drug discovery OS** that takes a drug (or idea) → maps targets & mechanisms → resolves structures & pockets → docks with honest scores → **shows binding as a living physical event** → explains residue-level evidence → triages ADMET → connects human pharmacology and cross-species orthologs — wrapping the **best existing scientific libraries and AIs**, not reinventing chemistry.

---

## 2. What “OS” means here (not a single tool)

| Layer | Job in ddOS |
|-------|-------------|
| **Identity** | Resolve drugs, targets, genes, UniProt, diseases (PubChem, ChEMBL, Open Targets, UniProt) |
| **Structure** | PDB / AlphaFold / uploads with **provenance banners** (crystal ≠ AF pose success) |
| **Site** | Holo ligand site → P2Rank pockets → **ligand-aware** top-K ranking for *this* drug |
| **Dock / pose** | Vina (+ optional GNINA, DiffDock-class pose AIs later) — scores ≠ Kd |
| **Physics & proof** | Contacts, H-bonds, hydrophobics, clashes — measurable, plotable, 3D-highlightable |
| **Biology context** | Pathways, mechanisms, tissue/disease links, orthologs (fly, planaria, mouse, dog, rabbit, cat…) |
| **ADMET / triage** | Early filters (RDKit + optional ADMET-AI / link-outs) |
| **Study desk** | Jobs, ensembles, batch ligands, comparable tables, exportable evidence packs |
| **Intelligence** | Optional **local** narration bound to measured evidence only; never a bundled LLM as biology truth |

ddOS is the **orchestrator + UX + honesty layer**. Chemistry engines stay external, mature, and cited.

---

## 3. Non-negotiable product principles

1. **Library-first** — wrap RDKit, Meeko, Vina/GNINA, P2Rank, ProLIF/PLIP, Open Targets, Biopython, etc. Do not rewrite pocket ML or force fields.
2. **Honesty over hype** — Vina/GNINA/DiffDock-confidence are **not** Kd/IC50. AF docking gets warnings. Pockets are hypotheses. Label ligand-aware winners as “best-ranked under engine X.”
3. **Local-first / privacy-first** — default `127.0.0.1`; no cloud LLM biology claims by default.
4. **Evidence you can point at** — every claim ties to a residue, distance, atom pair, score field, or database ID.
5. **Visualization is science, not decoration** — if docking “looks boring,” the product is incomplete. Binding must be **seen** (site, contacts, pose ensemble, motion cues that respect physics metaphors without fake dynamics pretending to be MD).
6. **Infer depth** — when building features, ask: *Would a computational chemist / translational biologist trust and learn from this screen?* If not, deepen biology or viz before polish chrome.
7. **No UI redesign without explicit go-ahead** from Alexander.

---

## 4. What already exists (do not forget / regress)

Shipped baseline (v1.3.x):

- Discover: drug → targets/mechanisms → structure (PDB/AF/upload) → pockets (holo / P2Rank / centroid) → ligand-aware top-K Vina ranking → dock
- Dock workbench: SMILES / file / PubChem → prep → Vina (+ optional GNINA fields)
- Job desk: queue, cancel, restart, ADMET-ish RDKit triage, residue contact proof, evidence summary, optional Ollama narrate
- 3Dmol viewer: cartoon, sidechains, box, poses, contact highlights
- Brand: **ddOS**; boot uses text-free `boot-logo.png`; package folder still `crossbind`
- Engines on Desktop: Vina OK, P2Rank 2.5.1 + OpenJDK 17 OK

Companion docs: `ddos_operating_system_roadmap_2026.md`, `ligand_aware_pockets.md`, library-first / SOTA docking notes.

---

## 5. The gap Alexander is pointing at (interpret this literally)

### 5.1 UI / “physics” / living docking (deferred until go-ahead)

Current analysis reads as a **static report**. Target experience:

- **Where** docking is happening: pocket volume lit, box as a real spatial object, camera framed on the site
- **What** is binding: ligand pose with clear CPK/ball-stick; protein context; residue glow for H-bond / hydrophobic / π-stack / clash
- **How confident / what method**: P2Rank vs holo vs ligand-aware rank, engine badge, AF warning chip
- **Process storytelling**: staged reveal (structure → pocket proposals → ranked sites → pose → contacts) so the *biological process* is understandable, not just a number
- **Creative OS aesthetic**: dense instrument UI for discovery (not generic SaaS cards). Design-system inspiration from product galleries (e.g. Mobbin flows for dashboards / scientific tools) — **steal patterns, not pixels**; never scrape copyrighted UI assets into the repo
- Optional later: short pose morph / contact pulse animations; MD trajectory only when a real trajectory exists (no fake physics)

### 5.2 Biology libraries (depth)

- Target dossiers: Open Targets tractability / disease / pathways  
- Structures: multi-PDB ensemble, holo preference, AF honesty  
- Orthologs: real mappings where APIs allow; honest miss for planaria etc.  
- Pharmacology stubs → real mechanism & safety link-outs over time  

### 5.3 Best-in-class AIs / tools to **wrap** (not retrain from scratch)

| Need | Prefer wrapping |
|------|-----------------|
| Cheminformatics | **RDKit** |
| Classical dock | **AutoDock Vina** / Smina |
| CNN dock / rescore | **GNINA** |
| Generative / blind pose | **DiffDock-L** (confidence ≠ affinity) |
| Pockets | **P2Rank** (`-c alphafold` when needed) |
| Interaction proof + viz | **ProLIF** (2D network + 3D), PLIP as fallback |
| 3D view | **3Dmol.js** now; evaluate **NGL** if we outgrow it |
| Target intelligence | **Open Targets**, ChEMBL |
| ADMET | RDKit now; **ADMET-AI** / SwissADME-style link-outs later |
| Free energy (later) | OpenMM / OpenFE / OpenBioSim workflows |
| Local narrative | Ollama **evidence-bound only** |

---

## 6. Inferred ddOS end-state (north star)

A researcher can:

1. Name a drug or paste a SMILES.  
2. See **why** biology cares (targets, mechanisms, diseases) with sources.  
3. Pick or upload a protein structure with clear provenance.  
4. Watch **pocket hypotheses** appear; optionally auto-rank for *this* ligand.  
5. Run dock / pose AI and **see** the pose lock into the site with contact physics overlays.  
6. Read a proof panel that a skeptic can verify in 3D.  
7. Triage ADMET and compare analogs in a study table.  
8. Jump to orthologs for translational / model-organism thinking.  
9. Export an evidence pack for lab follow-up — without ddOS pretending the computer already did the wet lab.

That is a **Drug Discovery Operating System**, not a Vina wrapper with a dark theme.

---

## 7. Priority agenda (execution order)

### Now (docs / alignment) — **this file**
- [x] Capture mission, principles, gap, libraries, north star  
- [ ] Keep this file updated when Alexander corrects vision  

### Next (after agenda OK; still **before** full UI pass unless he says go)
- [ ] Deepen **job/viewer truth**: ProLIF-quality interaction objects feeding both table and 3D highlight  
- [ ] Pocket story in results: method, rank, ligand-aware scores visible beside the pose  
- [ ] Structure provenance chips everywhere AF vs crystal appears  

### UI / visualization epic (**blocked** until explicit “go”)
- [ ] Instrument-style Discover + Job + Viewer redesign (creative, biology-correct, not generic)  
- [ ] Living docking narrative (site focus, contact pulses, staged process)  
- [ ] Design language inspired by researched product UIs (Mobbin etc.) without scraping assets  

### Science epic (parallel-safe, library wraps)
- [ ] First-class GNINA path  
- [ ] Optional DiffDock-L pose path  
- [ ] Open Targets tractability dossier on selected targets  
- [ ] Multi-PDB / ensemble + batch ligands  
- [ ] Later: MM/GBSA / FEP shortlist; richer ortholog docking  

### Non-goals
- Bundled cloud LLM as oracle  
- Claiming Kd from docking  
- Reimplementing P2Rank / Vina / ProLIF  
- UI redesign without Alexander’s go-ahead  

---

## 8. Working agreement with Alexander

1. **Agenda before chrome** — big direction lives here and in the evidence roadmap.  
2. **Ask before UI** — no visual redesign / “physics UI” implementation until he says begin.  
3. **Infer aggressively on science & architecture** — propose wraps, honesty rules, viz *concepts*; implement after alignment when UI-shaped.  
4. **Show sources** — papers/tools cited when prioritizing engines.  

---

## 9. Immediate ask

Alexander: read this agenda. Correct anything wrong.  
When you want the **UI / living docking** epic to start, say so explicitly — until then we deepen science, proof, and docs only.

---

*Last updated: 2026-09-22 (PT) — initial agenda capture from product conversation (living viz, biology depth, wrap best AIs, OS-scale discovery).*



----r

**UI taste lock:** [AGENTS.md](../AGENTS.md) §7 + [DESIGN.md](DESIGN.md) (from UIRoot Taste Skill / Originkit / DESIGN.md catalogs). No UI build until explicit go.




**Whole-product agent bible:** [DDOS_OS_SPEC.md](DDOS_OS_SPEC.md) — journeys, feature matrix, library stack, UIRoot map. Agents: read with AGENTS.md.

---

## Living engineering queue (2026-09-22)

See **`docs/ddos_pipeline_upgrade_queue_2026-09.md`** (merged from structure + biology research memos). Default next lane: **B1 GNINA → B2 PoseBusters → B3 ADMET-AI**. Companions: `docs/ddos_research_structure_2026.md`, `docs/ddos_research_biology_2026.md`.

