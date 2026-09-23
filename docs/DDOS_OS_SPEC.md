# ddOS Operating Spec — agent bible (read with AGENTS.md)

**Audience:** Grok Bot, Cursor, and any coding agent working on this repo.  
**Product:** **ddOS** — Drug Discovery Operating System  
**Repo folder:** `CrossBind` · **Python package:** `crossbind/` (do not casually rename) · **Owner:** Alexander Cecena (`Memeh007`)  
**Local app:** `http://127.0.0.1:8787` via `run.bat` on Windows Desktop  
**Companion contracts:** [`AGENTS.md`](../AGENTS.md) (standing rules) · [`agenda.md`](agenda.md) (north-star prose) · [`DESIGN.md`](DESIGN.md) (visual taste) · [`ddos_operating_system_roadmap_2026.md`](ddos_operating_system_roadmap_2026.md) (evidence citations)

This document is the **whole-product mental model**. If you only skim one long file after `AGENTS.md`, skim this. Infer missing features toward this OS — do not shrink ddOS back into “a docking form.”

**UI implementation remains GATED** until Alexander says go (`AGENTS.md` §3 / §7.5). Updating these docs is always allowed.

---

## A. What Alexander is making (plain language)

He is building a **local operating system for pre–wet-lab drug discovery**:

1. Start from a **drug or chemical idea**.
2. Discover **what biology it might touch** (targets, mechanisms, diseases).
3. Pull or upload **protein structures** (crystal PDB preferred; AlphaFold allowed with warnings).
4. Find **where it might bind** (holo site, P2Rank pockets, then **ligand-aware** ranking for *this* molecule).
5. **Dock / pose** with best open engines (Vina now; GNINA / DiffDock-class next).
6. **Show binding as a living, inspectable event** — not a boring kcal/mol number — with residue-level proof.
7. Triage **ADMET / drug-likeness**, connect **human pharmacology** and **cross-species orthologs** (fly, planaria, mouse, dog, rabbit, cat, …).
8. Keep everything **honest** (scores ≠ Kd), **local-first**, and **library-first** (wrap SOTA tools; don’t reinvent chemistry).

The UI must eventually feel like a **scientific instrument OS** (UIRoot Taste Skill: anti-slop Soft+Minimalist), with motion that explains biology — not purple AI-SaaS chrome.

---

## B. UIRoot.com — what it offers & how ddOS uses it

[UIRoot](https://uiroot.com/) is a curated directory of UI/UX tools. We do **not** vendor the site. We **absorb categories** so agents know the modern frontend landscape and avoid generic output.

### B.1 Categories to know

| UIRoot category | What it is | ddOS use |
|-----------------|------------|----------|
| **DESIGN.md** | Agent-readable design contracts (Taste Skill, getdesign.md, DesignMD, Open Design, TypeUI, Impeccable, …) | Our `docs/DESIGN.md` + Taste anti-slop; analyze refs Alexander provides into DESIGN.md |
| **UI Component** | Component kits (Originkit, Magic UI, Aceternity, SmoothUI, Base UI, Radix-class, shadcn ecosystems, ThreeUI, BoardUI, sound kits, …) | Pattern + optional deps; prefer headless/accessible base + ddOS skin; 3D kits only for molecular stage |
| **Animation tools** | GSAP, Rive, Lottie, anime.js, Jitter, … | Semantic motion only (process storytelling); not ambient fluff |
| **Design systems** | Storybook, zeroheight, Backlight, Supernova, Create UI, … | Optional later for component QA; not a blocker for v1 Jinja app |
| **AI tools** | Uizard, Recraft, Moda, … | Optional for mock generation; never paste as production science UI without DESIGN.md pass |
| **Patterns & backgrounds** | Gradients, grains, shader backgrounds | Use sparingly; scientific calm > decorative noise |
| **Mockups / delivery** | Zeplin, Shots, Rotato-class | Marketing/portfolio only — not in-app |

### B.2 Flagship tools Alexander called out

- **Taste Skill** — inject “good taste”; kill generic AI frontends; Soft / Minimalist / Redesign / Image-to-code / Output-complete modes. **Default bias for ddOS.**
- **Originkit** — free animated components (Framer/React/MCP). Steal **motion ideas**; don’t make ddOS a landing-page component zoo.
- **DESIGN.md ecosystem** — write tokens & rules agents can follow; keep `docs/DESIGN.md` authoritative.

### B.3 UIRoot hard constraints

- Patterns only — **no scraping** copyrighted UI into the repo.
- Anti-slop is mandatory when UI is authorized (`AGENTS.md` §7, `DESIGN.md`).
- ddOS identity ≠ “another shadcn dashboard.” Instrument OS for discovery.

---

## C. End-to-end user journeys (design the whole app)

### C1. Discover (primary)
Drug name → identity (PubChem/ChEMBL) → target/mechanism list → select protein → structure (PDB/AF/upload) → pocket strip (holo/P2Rank/ligand-aware) → prepare & dock → job.

### C2. Manual Dock
Upload receptor + ligand (SMILES/file/name) → box/exhaustiveness → Vina/(GNINA) → job.

### C3. Job / Proof / Viewer
Status + cancel/restart → affinity table → ADMET → **residue proof** ↔ **3D stage** synced → evidence summary → optional local narrate → exports.

### C4. Study desk (target state)
Compare jobs, batch ligands, multi-PDB ensemble, export evidence pack for lab.

### C5. Biology context (target state)
Open Targets dossier, pathways, disease links, ortholog panel with honest misses.

Every journey must remain **legible as a biological process**, not a form wizard with no meaning.

---

## D. Feature matrix — shipped vs build next

Legend: **S** = shipped · **N** = next (science OK without UI go) · **U** = needs UI authorization · **L** = later

| Feature | Status | Notes / libraries |
|---------|--------|-------------------|
| Drug resolve (name→SMILES/CID) | S | PubChemPy, RDKit sanitize, CACTUS fallback |
| Target/mechanism suggest | S | ChEMBL; Open Targets GraphQL fallback |
| Protein search (UniProt/gene/PDB) | S | UniProt, RCSB |
| Structure fetch PDB / AF / upload | S | rcsb-api, AlphaFold DB, CIF→PDB |
| Holo pocket preference | S | Crystal ligand site |
| P2Rank pockets (+ AF config) | S | P2Rank CLI, Java 17 |
| Ligand-aware top-K pocket rank | S | Vina into top-K; honest labels |
| Vina dock pipeline | S | RDKit, Meeko, Open Babel, Vina 1.2.x |
| Optional GNINA fields | S/partial | Wire first-class path | N |
| Job queue cancel/restart | S | |
| RDKit ADMET / drug-likeness | S | Expand w/ ADMET-AI later | N/L |
| Residue contacts + evidence text | S | ProLIF when present; geometric fallback | N deepen |
| 3Dmol viewer + highlights | S | Living viz / physics UI | U |
| Ortholog panel stubs | S | Real mappings | N |
| Boot ddOS + text-free logo | S | |
| DiffDock-L optional pose path | L/N | confidence ≠ affinity |
| Open Targets tractability dossier | N | |
| Multi-PDB / ensemble dock | N | |
| Batch ligands / virtual screen table | N | |
| MM/GBSA or OpenFE shortlist | L | after dock triage |
| Species docking from orthologs | L | |
| DESIGN.md instrument UI pass | U | UIRoot taste |
| Staged living docking narrative | U | |
| Storybook / design-system workshop | L | |

---

## E. Library & AI stack to wrap (SOTA, library-first)

### E.1 Chemistry & prep
- **RDKit** — molecules, descriptors, fingerprints, depictions  
- **Meeko** — ligand PDBQT  
- **Open Babel** — receptor PDBQT / format bridges  

### E.2 Docking & pose
- **AutoDock Vina 1.2.x** — default dock  
- **GNINA** — CNN score/affinity fields (separate columns)  
- **DiffDock-L** (optional) — generative poses; confidence ≠ Kd  
- Later: Smina/Gnina variants as needed  

### E.3 Sites & structures
- **P2Rank** — pockets; `-c alphafold` for AF  
- **RCSB / rcsb-api**, **AlphaFold DB**, **Biopython**  

### E.4 Interactions & viz
- **ProLIF** — IFPs, 2D networks, 3D interaction viz hooks  
- **PLIP** — fallback interaction profiles  
- **3Dmol.js** (now) / evaluate **NGL** if we outgrow it  

### E.5 Knowledge graphs / pharmacology
- **ChEMBL**, **PubChem**, **UniProt**  
- **Open Targets** — disease, tractability, pathways  
- Ortholog sources (Ensembl Compara where available; honest miss otherwise)  

### E.6 ADMET & triage
- RDKit filters now  
- **ADMET-AI** / SwissADME-style link-outs later  

### E.7 Physics (later shortlist)
- **OpenMM**, **OpenFE** / OpenBioSim FEP workflows — never default Discover  

### E.8 Local intelligence
- **Ollama** optional — narrate **only** from measured evidence JSON  
- No bundled cloud LLM as biology oracle  

---

## F. Honesty & safety (always)

1. Docking / CNN / DiffDock-confidence **≠** experimental affinity.  
2. AF banner whenever structure is predicted.  
3. Pocket method + ligand-aware rank labeled as hypotheses.  
4. No fake MD trajectories.  
5. Local-first; ask before cloud deps.  
6. Don’t commit secrets, huge binaries (`bin/p2rank/`), or scraped UI assets.

---

## G. Information architecture (whole app)

| Route / area | Role |
|--------------|------|
| `/discover` | Primary OS flow |
| `/` (Dock) | Manual instrument |
| `/jobs` | Study queue |
| `/job/{id}` | Proof + ADMET + log |
| `/viewer/{id}` | 3D stage |
| `/api/health` | Engine truth (vina/p2rank/gnina) |

Required UI objects in any future redesign: provenance chip, pocket strip, docking stage, proof table synced to 3D, honesty banners, engine badge, job timeline (`DESIGN.md` §8).

---

## H. How agents should infer work

When Alexander says “make it better” / “SOTA” / “more like an OS” without specifying a ticket:

1. Read `AGENTS.md` + **this file**.  
2. Prefer **N** items in §D (science/proof/engines/biology) over chrome.  
3. For UI ideas, update `DESIGN.md` / this spec — **don’t implement** until go.  
4. Choose libraries from §E; cite briefly in PR/commit body.  
5. Ask only when blocked by UI gate, secrets, or destructive ops.

---

## I. Definition of done (SOTA ddOS slice)

A skeptical computational chemist can:

- Trace drug → target evidence with IDs  
- See structure provenance  
- Understand why a pocket was chosen (method + ligand-aware scores)  
- Inspect pose and **click residues** that match a proof table  
- Know that scores are not Kd  
- Export enough to plan a wet-lab follow-up  

Until visualization makes binding **felt and verified**, the OS is incomplete — but building that UI waits for Alexander’s go.

---

*Compiled 2026-09-22 for agent consumption from product intent + UIRoot category survey + existing ddOS roadmap/agenda.*
