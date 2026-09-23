# AGENTS.md — ddOS execution bible (Hermes / MiniCPM / Cursor / Grok)

**ALWAYS read this file before writing or changing any code.**  
If a chat request conflicts with this file, **this file wins** unless Alexander explicitly overrides it in the current turn.

**Product:** ddOS (Drug Discovery Operating System)  
**Repo folder:** CrossBind · **Python package:** `crossbind/` (do not rename casually)  
**Owner:** Alexander Cecena · GitHub `Memeh007`  
**Runtime:** local FastAPI + Jinja · `run.bat` · `http://127.0.0.1:8787`  
**Target local agent stack:** Hermes Agent + **MiniCPM5-2B** (native **131,072**-token context; XML tool-calling; optional Think mode) — this file is the **offloaded architecture brain**; MiniCPM is the **fast executor**, not the architect  
**Deeper overflow:** `docs/DDOS_OS_SPEC.md` · `docs/agenda.md` · `docs/DESIGN.expanded.md` (UI) · `docs/ddos_pipeline_upgrade_queue_2026-09.md` (**build contract B1–B14**) · `docs/ddos_research_structure_2026.md` · `docs/ddos_research_biology_2026.md` · `docs/ddos_operating_system_roadmap_2026.md`

When prompting any agent, say: *Read AGENTS.md for pipeline rules, UI design system, and golden snippets before writing code.*

---

## 0. Prime Directives (unbreakable)

1. **Wrap first, invent last.** Never write custom algorithms for pocket finding, docking, cheminformatics parsing, IFPs, or free-energy. Use approved libraries/CLIs only (see section 4).
2. **Compose tools that help tools.** Prefer adapters where stage N validates or enriches stage N-1 (e.g. PoseBusters/strain after Vina/GNINA/DiffDock before ProLIF; GNINA CNN rescores Vina-family poses; OT/orthologs enrich dock hits; ADMET-AI triages before wet lab). Do not invent chemistry to replace a mature validator.
3. **Zero-cost / local-first compute.** Prefer local CLIs (`subprocess` for P2Rank/Vina/GNINA) and free public REST (PubChem, ChEMBL, RCSB, AlphaFold DB, Open Targets GraphQL). Do **not** call OpenAI/Anthropic/paid cloud LLMs for biology truth. Optional **local** Ollama narrate only if evidence-bound.
4. **Honesty over hype.** Never label Vina / GNINA CNN / DiffDock confidence as experimental **Kd / IC50**. AlphaFold structures require provenance warnings. Pockets are hypotheses. Ligand-aware winner = "best-ranked for this ligand under engine X," never "the true site."
5. **Evidence you can point at.** Every claim ties to residue/distance/atoms, score field name, PDB/UniProt/ChEMBL/Open Targets ID, or measured ADMET descriptor.
6. **UI is gated.** Do **not** redesign UI, "physics UI," or restyle chrome unless Alexander says **go** / "start UI" in the current turn. You MAY update this file / `docs/DESIGN.md` anytime.
7. **Visualization is science, not decoration.** When UI is authorized: motion and highlights must make binding / biological process legible (site -> pocket -> pose -> contacts). No purple-gradient AI-SaaS slop; no falling decorative molecules; no fake MD.
8. **Deepen the discovery spine, do not freestyle architecture.** ddOS is not "a docking form." Prefer proof/engines/biology/study-scale over cosmetics. **Architect / heavy models** may search the web and propose wraps. **MiniCPM5-2B** must only implement the **one named B-slice or single-file task** it was given (see §9) — never redesign the pipeline in one shot.
9. **Windows Desktop is primary.** Paths under `C:\Users\alexc\Desktop\CrossBind`. Keep `bin/p2rank/` gitignored. Cache-bust static JS when changing boot/viewer scripts.
10. **Brand:** UI product name **ddOS**. Boot logo = `crossbind/static/img/boot-logo.png` (text-free). Never reintroduce "Cross Affinity" wordmarks in chrome.
11. **Finished outputs.** No placeholder panels, lorem, skipped sections, or unfinished empty states in production paths (Taste Skill Output spirit).

---

## 1. What we are building (one paragraph)

ddOS is a **local operating system for pre-wet-lab drug discovery**: drug/idea -> targets and mechanisms -> structures (PDB/AF/upload) -> pockets (holo / P2Rank / ligand-aware rank) -> dock/pose (Vina; optional GNINA/DiffDock-L) -> inspectable binding proof + 3D -> ADMET triage -> pharmacology and cross-species orthologs -> study tables / evidence packs. ddOS orchestrates and explains; chemistry engines stay external, mature, and cited.

**Nav / routes:** `/discover` (primary) · `/` Dock · `/jobs` · `/job/{id}` · `/viewer/{id}` · `/api/health`

---

## 2. Data pipeline blueprint (biological spine)

### 2.1 Discover spine (canonical)

```
Input: drug name (or SMILES)
  A. PubChemPy (+ CACTUS fallback) -> CID, canonical SMILES, InChIKey  [RDKit sanitize]
  B. ChEMBL mechanisms/targets (+ Open Targets GraphQL fallback) -> human protein targets
  C. User selects target OR protein search (UniProt/gene/PDB)
  D. Structure: RCSB PDB by UniProt preferred; else AlphaFold DB; else user PDB/CIF upload
  E. Pockets:
       1) holo co-crystal ligand site if present
       2) else P2Rank CLI (use -c alphafold when AF/upload/predicted)
       3) else centroid fallback
       4) optional ligand-aware: dock ligand into top-K pockets with Vina; pick most negative score
  F. Prepare and dock: RDKit -> Meeko ligand PDBQT -> Open Babel receptor PDBQT -> Vina
       optional GNINA when GNINA_BIN set (store vina_affinity vs gnina_cnn_* separately)
  G. Post-dock: ProLIF contacts (preferred) or geometric fallback -> proof table + viewer sync ids
  H. ADMET RDKit triage; evidence summary from measurements only; optional local Ollama narrate
  I. Ortholog panel (human/mouse/fly/dog/rabbit/cat/planaria) — honest miss if unmapped
  J. Open Targets dossier on target select (tractability / top diseases; cached)
```

### 2.2 Manual Dock spine

Receptor upload (PDB/PDBQT/CIF) + ligand (SMILES / file / PubChem name) -> same prep -> Vina/GNINA -> job -> proof/viewer.

### 2.3 Score and provenance rules (always emit)

| Field | Meaning |
|-------|---------|
| `vina_affinity` | Vina score (kcal/mol rank) — NOT Kd |
| `gnina_cnn_score` / `gnina_cnn_affinity` | CNN fields when GNINA used — NOT Kd |
| `pocket_method` | `holo_ligand` \| `p2rank` \| `centroid_fallback` \| `ligand_aware_vina` |
| structure provenance | experimental PDB vs alphafold vs upload |
| contact `method` | `prolif` \| `geometric` |

### 2.4 Health engines

`GET /api/health` reports `vina_ok`, `p2rank_ok`, `gnina_ok` honestly. P2Rank at `bin/p2rank/prank.bat` + Java 17. GNINA via `GNINA_BIN`.

---

## 2.5 Tool composition — predictive stack before in vivo

**Purpose:** ddOS is a **pre–in-vivo predictive triage OS**. It ranks and explains chemical–biology hypotheses with **auditable, method-tagged evidence** so Alexander can decide what (if anything) deserves planaria / fly / mouse / mammalian follow-up. Docking alone is never permission to claim in vivo efficacy.

**Composition rule:** each stage wraps a mature tool that *helps* the next. Do not skip validators.

```
Identity (PubChem/ChEMBL)
  → Structure provenance (PDB / AF / upload)
  → Site (holo → P2Rank [→ optional fpocket+PRANK] → ligand-aware Vina rank)
  → Pose (Vina and/or GNINA; optional DiffDock-L / Boltz later)
  → Validity gate (PoseBusters + RDKit strain/clash)     ← helps ProLIF stay honest
  → Contact proof (ProLIF) + 3D sync
  → Local ADMET-AI (triage)                              ← helps wet-lab prioritization
  → Biology enrichers (Open Targets GraphQL cache, Reactome/STRING later)
  → Orthologs (Alliance → OrthoDB → DIOPT → PlanMine)    ← translational hypothesis only
  → Study scale (batch ligands, multi-PDB ensemble, FPSim2 analogs)
  → Evidence pack export (JSON/MD/TSV, versions stamped)
```

**Why (non-fiction; full citations in research memos):**

| Adapter | Helps | Why we use it | Proof pointer |
|---------|-------|---------------|---------------|
| P2Rank (+ later fpocket+PRANK) | Dock box | Ligandable sites; LIGYSIS 2024 favors geometric+ML combo for top-N+2 | `ddos_research_structure_2026.md` |
| Vina 1.2.x | Baseline pose/rank | Local default; scores are ranking tools | shipped |
| GNINA 1.3 | Rescore/refine Vina-family | CNN enrichment vs empirical Vina in VS settings (McNutt *J. Cheminform.* 2025) | structure memo; **B1** |
| PoseBusters + strain | ProLIF / narration | Many AI poses fail chemical/physical validity (Buttenschoen *Chem. Sci.* 2024) | **B2** |
| ProLIF | Proof table↔3D | Measurable contacts, not vibes | shipped A1 |
| ADMET-AI (MIT, offline) | Wet-lab shortlist | Local Chemprop/TDC ADMET (Swanson *Bioinformatics* 2024) | biology memo; **B3** |
| Open Targets Platform GraphQL v4 | Target/disease dossier | Genetics merged into Platform (25.03+); release-pin cache | biology memo; **B4** |
| OrthoDB + Alliance + DIOPT + PlanMine | Translational panel | Planaria needs PlanMine (SmedGD retired); Alliance ≠ planaria | biology memo; **B7** |
| DiffDock-L (optional) | Blind/uncertain pocket | Generative pose + confidence; FAQ: confidence ≠ affinity; always rescore | **B12** |
| Boltz-2 (optional, MIT) | Co-fold / research affinity | Prefer over AF3 Server for product; never Server→dock (ToS) | **B14** |
| Uni-Dock / batch CSV | Library triage | GPU Vina-family VS (Yu *JCTC* 2023); study desk | **B5** |
| OpenMM / Uni-GBSA | Shortlist physics | Minimize / end-point ΔG after pose triage — not Discover default | **B9/B13** |
| FPSim2 | Analog neighbors | Local ChEMBL fps similarity seeds SAR | **B10** |

**Hard bans:** AF3 Server outputs must not feed AutoDock/Vina/GNINA/VS. Scores ≠ Kd/IC50. OT association ≠ causality. Ortholog ≠ same pharmacology (PlanMine = RBH, not Alliance-curated).

### 2.6 Canonical stage table (shipped vs build)

Legend: **S** shipped · **N** next (all lanes required) · **L** later · **U** UI-gated

| Stage | Tools | Status | Build id |
|-------|-------|--------|----------|
| Identity | PubChemPy, ChEMBL, RDKit | S | — |
| Targets / MoA | ChEMBL, OT GraphQL deepen | S / N | B4 |
| Structure | RCSB, AF DB, upload + banners | S | — |
| Pockets | holo, P2Rank; fpocket+PRANK later | S / N | B11 |
| Ligand-aware rank | Vina top-K | S | — |
| Dock | Vina 1.2.x | S | — |
| GNINA CNN path | GNINA 1.3 binary + fields | N (path stubbed) | **B1** |
| Pose validity | PoseBusters + RDKit strain/clash | N | **B2** |
| Contacts | ProLIF (+ geometric fallback) | S | — |
| ADMET | RDKit now → ADMET-AI local | S / N | **B3** |
| OT dossier | GraphQL + release cache | partial / N | **B4** |
| Batch ligands | CSV/SDF → study table (± Uni-Dock) | N | **B5** |
| Ensemble receptors | multi-PDB / AF samples | N | **B6** |
| Orthologs | Alliance→OrthoDB→DIOPT→PlanMine | stubs / N | **B7** |
| Evidence pack | JSON + MD + TSV | N | **B8** |
| OpenMM minimize | top-pose relax | N | **B9** |
| Analogs | FPSim2 on ChEMBL fps | N | **B10** |
| DiffDock-L sidecar | Docker; always rescore | L/N | **B12** |
| MM/GBSA | Uni-GBSA / MMPBSA.py | L | **B13** |
| Boltz-2 opt-in | MIT co-fold | L | **B14** |
| Instrument UI redesign | DESIGN.expanded.md | U | — |

**All three lanes are required** (Credibility B1–B3 · Biology B4/B7/B8 · Scale B5/B6/B10). Recommended serial order for coding agents: **B1→B2→B3→B4→B5→B6→B7→B8→B9→B10→B11→B12→B13→B14**. Do not skip B2 before deepening ProLIF claims. Living contract: `docs/ddos_pipeline_upgrade_queue_2026-09.md`.


## 2.7 Engineering friction rules (from review — do not skip)

These are standing build rules, not optional tips:

1. **Receptor prep robustness.** Do not rely on bare Open Babel alone for messy PDBs. Prefer: `pdbfixer` (and/or `reduce`) to repair missing heavy atoms / nonstandard residues **before** PDBQT, or Meeko’s modern receptor prep when available. Silent bad PDBQT → silent bad docks.  
2. **PoseBusters isolation (B2).** Validate `posebusters` in a **standalone script** under the same venv/`run.bat` Python **before** wiring it into the FastAPI job runner. RDKit/PyTorch dep clashes on Windows are common — catch them offline first.  
3. **PlanMine / planaria orthologs (B7).** PlanMine REST can be fragile. Ship a **pre-indexed RBH SQLite cache** for *Schmidtea mediterranea* (and refresh periodically) rather than live PlanMine on every Discover click. Banner remains: PlanMine RBH ≠ Alliance-curated.  
4. **MiniCPM context.** Enforce §9.3 pack order and ~25K soft cap. Overflow docs are for orchestrators (Grok/Cursor), not every MiniCPM turn.

## 3. UI strict design system (locked; implement only after go)

**Full visual bible:** `docs/DESIGN.expanded.md` — tokens, dials (4/4/8), component contracts, Taste anti-slop bans, pre-flight. This section is the short form.


Culture: UIRoot Taste Skill (anti-slop Soft+Minimalist), UIRoot DESIGN.md tools, Originkit = motion patterns only, Mobbin = pattern refs only — **never scrape assets**.

### 3.1 Tokens (in `crossbind/static/css/crossbind.css`)

- Background: `#080A0A` (`--bg`); elev `#0f1011` / `#121414` / `#171a1a`
- Borders: `1px solid rgba(255,255,255,0.08)` (`--line`)
- Text: `#e8ecec` · muted `#8a9393`
- **Primary bio-luminescent green** `#2ee6c5` (`--teal`) **only** for active states, CTAs, docking targets, ok chips
- Warn `#f5a524` · bad `#f07178`
- Radius `6px` · dense 4/8px spacing · sidebar ~220px
- Fonts: Inter UI + JetBrains Mono for IDs/scores; enforce **tabular-nums**

### 3.2 Layout

- High-density instrument / bento panels (not marketing heroes)
- Discover = staged process; Job = proof + 3D; Viewer = stage-first
- Monospace for PDB, UniProt, scores, coords, MW
- Provenance chips: crystal vs AF vs upload
- Contact-type colors need a legend

### 3.3 Anti-slop (forbidden)

- Purple/violet AI gradients, glassmorphism-for-show, unmarked stock shadcn demos
- Decorative particles / falling molecules / sparkle loops
- Placeholder "coming soon" in production paths
- Fake MD / animating scores as live Kd
- Reintroducing Cross Affinity wordmarks

### 3.4 Motion (after UI go)

Allowed: staged Discover reveals, pocket emphasize, pose morph, contact pulse synced to proof row, honest job progress.  
Disallowed: ambient fluff, motion that blocks tables.

### 3.5 Required UI objects (any redesign must include)

1. Provenance chip  
2. Pocket strip (method, score, ligand-aware rank)  
3. Docking stage (protein + ligand + box + contact highlights)  
4. Proof table <-> 3D sync via contact `id`  
5. Honesty banners  
6. Engine badge (Vina/GNINA/DiffDock labeled correctly)  
7. Job timeline (queued -> preparing -> docking -> scoring -> terminal)

---

## 4. Approved libraries and CLIs (allowlist)

| Layer | Use these |
|-------|-----------|
| Chem | RDKit, Meeko, Open Babel / obabel |
| Identity | PubChemPy, chembl_webresource_client, UniProt/mygene as wired |
| Structure | rcsb-api, Biopython AlphaFold DB, gemmi/pdbfixer as present |
| Pockets | P2Rank CLI (`prank.bat`), holo ligand geometry |
| Dock | AutoDock Vina 1.2.x; optional GNINA |
| Pose AI (later) | DiffDock-L — confidence is not affinity |
| IFP | ProLIF (+ MDAnalysis); geometric fallback in-repo |
| Knowledge | Open Targets GraphQL (dossier module), ChEMBL |
| ADMET | RDKit now; **ADMET-AI** local (MIT) next; ADMETlab API optional online only |
| Validity | **PoseBusters** + RDKit strain/clash before ProLIF |
| Orthologs | Alliance REST, OrthoDB, DIOPT, PlanMine (not SmedGD) |
| Analogs | FPSim2 on ChEMBL fps |
| Batch / GPU VS | Uni-Dock (Apache 2.0) optional |
| Co-fold (later) | Boltz-1/2 (MIT); never AF3 Server→dock |
| Physics shortlist | OpenMM minimize; Uni-GBSA / MMPBSA.py |
| FE (later) | OpenMM / OpenFE / OpenBioSim — not Discover default |
| Cache | SQLite via `crossbind.discovery.cache` |
| Viz | 3Dmol.js (now); NGL only if explicit migration |

Do **not** add paid cloud LLM SDKs, scraped UI kits, or reimplemented pocket ML.

---

## 5. Golden snippets (mimic exactly — critical for 2B models)

### 5.1 SQLite discovery cache

```python
from crossbind.discovery.cache import get_json, set_json

cached = get_json("open_targets_dossier", key, ttl_s=14 * 86400)
if cached is None:
    cached = fetch_dossier(...)  # network
    set_json("open_targets_dossier", key, cached)
```

### 5.2 Contact object shape (A1 — table <-> 3D)

```python
{
  "id": "c0",
  "method": "prolif",  # or "geometric"
  "type": "HBDonor",
  "residue": "A:123:TYR",
  "chain": "A",
  "resi": 123,
  "resn": "TYR",
  "distance_A": 2.85,
  "detail": "N...OH",
}
```

Job rows use `data-contact-id`. Evidence text comes **only** from measurements.

### 5.3 Local engines

- P2Rank: `crossbind.config.resolve_p2rank_bin()`; AF => `-c alphafold`
- Vina: `resolve_vina_bin()`; score is never Kd
- GNINA: only if `resolve_gnina_bin()`; keep CNN fields separate from `vina_affinity`

### 5.4 Dense metric card (HTML)

```html
<div class="panel metric-card">
  <div class="metric-label">Vina affinity</div>
  <div class="metric-value mono">-5.84</div>
  <div class="metric-hint">kcal/mol rank — not Kd</div>
</div>
```

Use CSS variables from section 3.1; green only for selected/active, not every number.

### 5.5 Honesty banner

```html
<div class="banner warn">Docking scores are ranking tools, not experimental Kd/IC50.</div>
```

### 5.6 Open Targets dossier (A3)

Use `crossbind.discovery.open_targets_dossier` — cache, honest empty/error, no fabricated biology. Modest Discover hooks only (no redesign).

---


### 5.7 Method-tagged score object (always)

```python
{
  "vina_affinity": -5.84,          # kcal/mol rank — NOT Kd
  "gnina_cnn_score": None,         # only if GNINA ran
  "gnina_cnn_affinity": None,
  "diffdock_confidence": None,     # pose quality — NOT affinity
  "posebusters_pass": None,        # bool after B2
  "ligand_strain_kcal": None,
  "gbsa_dg": None,                 # end-point — NOT experimental dG
  "score_honesty": "ranking/triage only — not experimental Kd/IC50",
}
```

### 5.8 Pose validity gate interface (B2 — implement as wrap)

```python
def gate_pose(protein_pdb: str, ligand_sdf: str) -> dict:
    """Wrap PoseBusters + RDKit strain/clash. Never invent chemistry.""
    # Use PoseBusters(config="dock") when mol_true is None (predictive dock). "redock" needs crystal ligand."
    # return {"posebusters_pass": bool, "checks": {...}, "strain_kcal": float|None}
    raise NotImplementedError("B2: pip-wrap posebusters; see structure research memo")
```

### 5.9 Evidence pack keys (B8)

```python
EVIDENCE_PACK_KEYS = [
  "drug_identity", "ot_dossier", "chembl_moa_top", "dock_summary",
  "contacts_prolif", "admet_ai", "ortholog_matrix", "versions",
]
# versions must include: chembl_release, ot_release, orthodb, model/binary hashes
```

### 5.10 Ortholog row schema (B7)

```python
{
  "species": "planaria",           # human|mouse|fly|planaria|dog|rabbit|cat|...
  "query_id": "P54646",
  "ortholog_id": "...",
  "method": "planmine_rbh",      # alliance|orthodb|diopt|planmine_rbh
  "identity": None,                # float 0-100 when known
  "banner": "Orthologs support translational hypothesis, not dose or MoA transfer.",
}
```

## 6. Repo map

| Path | Role |
|------|------|
| `crossbind/app.py` | FastAPI routes |
| `crossbind/discovery/` | drug, targets, structures, pockets, ligand_aware, orthologs, open_targets_dossier, cache |
| `crossbind/docking/` | pipeline, vina, gnina, ligand/receptor prep |
| `crossbind/analysis/` | interactions (ProLIF), explain/evidence, ADMET |
| `crossbind/templates/` | Jinja pages |
| `crossbind/static/css/crossbind.css` | design tokens |
| `crossbind/static/js/` | discover.js, viewer.js, boot.js, app.js |
| `docs/DDOS_OS_SPEC.md` | full OS inference bible |
| `docs/DESIGN.expanded.md` | visual contract (canonical) |
| `docs/ddos_pipeline_upgrade_queue_2026-09.md` | **B1–B14 build contract** |
| `docs/ddos_research_structure_2026.md` | pose/physics evidence |
| `docs/ddos_research_biology_2026.md` | OT/ADMET/ortholog evidence |
| `tests/` | pytest |

---

## 7. Priority when inferring next work

**All lanes required** (Credibility + Biology + Scale). Follow `docs/ddos_pipeline_upgrade_queue_2026-09.md`.

**MiniCPM5-2B:** implement **exactly one** B-id per task from this list — do not chain B1–B14 in a single run unless the orchestrator explicitly lists a short closed set (e.g. B1 then stop).

1. Truth and proof — **B1** GNINA hard enable, then **B2** PoseBusters (isolated smoke first), with receptor-prep hardening (`pdbfixer`/reduce) alongside  
2. Local ADMET-AI triage — **B3**  
3. OT GraphQL cache + orthologs + evidence pack — **B4, B7, B8**  
4. Study-scale (batch ligands, multi-PDB, FPSim2) — **B5, B6, B10**  
5. Optional pose AI / physics / Boltz — **B9, B11–B14**  
6. UI / living viz — **only after explicit go**

Agents with web search: find better libraries, then wrap — do not invent chemistry. Prefer tools that validate or enrich an existing stage.

---

## 8. Definition of done

A skeptical computational chemist can: trace drug->target IDs; see structure provenance; see why a pocket was chosen; click proof residues that match 3D; know scores are not Kd; export an evidence pack with method-tagged scores, validity gates, ADMET triage, and ortholog banners — enough to decide whether in vivo / planaria follow-up is warranted.

---


## 8.5 Citations & paper library (Hermes must look things up)

ddOS agents **must not invent papers, DOIs, method names, or benchmark numbers**. When science or tool choice is uncertain:

1. **Search** (web / Semantic Scholar / PubMed / Crossref / GitHub READMEs) for primary sources. Hermes is expected to look things up; do not rely on parametric memory for citations.
2. **Prefer** DOIs + open PDFs (publisher, PMC, arXiv, bioRxiv). Record license (CC-BY, publisher PDF, preprint).
3. **Download** useful PDFs into `docs/citations/pdfs/` with a stable name: `YYYY_FirstAuthor_ShortTitle.pdf` (or `.html` snapshot if PDF blocked).
4. **Index** every added paper in `docs/citations/INDEX.md` with: title, authors/year, DOI/URL, local path, **why ddOS cares**, linked B-id or pipeline stage.
5. **Quote sparingly** into AGENTS/research memos; point MiniCPM at the INDEX row + one PDF when a B-slice needs evidence — do not dump every PDF into every MiniCPM prompt.
6. Weekly routine / orchestrators: if a new tool or claim appears without a citation row, **fetch and add it** before treating it as policy.

**Never** fabricate a DOI. If a PDF cannot be obtained, still add an INDEX row with URL + "PDF unavailable" and use the abstract/HTML facts you can verify.

## 9. MiniCPM5-2B operating contract (Hermes local executor)

MiniCPM5-2B is an **exceptionally strong ~2B local executor** (fast, 131K context, native XML tool calls, optional Think mode). It is **not** the primary architect of ddOS. This file (plus the overflow docs) is the architecture; MiniCPM **translates one assigned task into code**.

### 9.1 You are the executor — not the architect

| Do (good MiniCPM work) | Do not (2B failure modes) |
|------------------------|---------------------------|
| One B-slice or one file / one function | Design the whole Discover→dock→biology OS in one reply |
| Copy golden snippets (§5) and existing `crossbind/` patterns | Invent PubChem/ChEMBL/UniProt/RDKit method names from memory |
| Wrap allowlisted CLIs via `subprocess` / existing helpers | Reinvent pocket ML, IFPs, or scoring |
| Parse Vina/GNINA/P2Rank coordinate or score lines | Invent biology edge-case policy (AF vs crystal, ortholog confidence) |
| Localized syntax / import / type fixes | Redesign dense UI grids or IA unless Alexander said **go** |
| Toggle Think mode for tricky single-file logic | "Infer" a new pipeline stage not in §2.6 / the B1–B14 queue |
| Ask orchestrator/Hermes to look up + file a citation (§8.5) | Invent DOIs, papers, or benchmark numbers |

Heavy / API / Grok Bot models own: architecture, multi-API scaffolding, DESIGN system passes, choosing next science priorities when ambiguous.

### 9.2 Task size rule (hard)

1. Accept work only as: **one B-id** (e.g. B2) **or** a named path (e.g. `crossbind/docking/gnina.py`) **or** a named bug.  
2. Touch the **minimum files** needed. Prefer edit over new modules.  
3. If the prompt asks for "build the whole predictive stack" / "wire PubChem+ChEMBL+UniProt+OT+orthologs", **refuse the sprawl**: implement only the first missing B-slice in §7 order, or ask the orchestrator to split.  
4. Before coding: open the **real** target file(s) in-repo; mimic signatures already there. Never guess an API.  
5. After coding: run the smallest relevant check (`pytest` for that module, or `/api/health` if engines). Do not claim Kd or invent biology in strings.

### 9.3 Context loading (hard budget — Gemini / needle-in-haystack)

MiniCPM5-2B advertises **131K** tokens, but ~2B models often degrade past ~**20–30K** useful prompt tokens. Hermes **must** enforce a tight pack:

1. This file **§§0–5 only** (always; do not attach §§6–9 unless asked)  
2. The **one** module being edited + its closest test  
3. The **single** matching B-slice paragraph from `docs/ddos_pipeline_upgrade_queue_2026-09.md`  
4. Optional: one short research-memo subsection **or** one `docs/citations/INDEX.md` row (+ PDF path) — never both full memos  
5. Soft cap: keep total packed context under ~25K tokens for coding turns

**Forbidden:** dumping DESIGN + OS SPEC + both research memos + full citation PDFs into one MiniCPM turn.

### 9.4 Tool calling

Use native XML / Hermes tool calls for: reading files, running `pytest`, invoking local binaries already resolved by `crossbind.config`, git status. Do not call paid cloud LLM APIs for biology truth (§0.3).

### 9.5 Truncation priority

If the prompt is truncated, keep **§§0–5** intact first (directives, spine, UI gate short form, allowlist, golden snippets). §§6–8 and research memos are secondary. Hermes also loads `.hermes.md` (points here).

---

*ddOS AGENTS.md — Hermes/MiniCPM5-2B executor edition. Architecture lives here; MiniCPM executes one slice. UI redesign gated until Alexander says go. Updated 2026-09-22 PT (Gemini review friction rules + MiniCPM context budget).*




