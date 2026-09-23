# AGENTS.md — ddOS execution bible (Hermes / MiniCPM / Cursor / Grok)

**ALWAYS read this file before writing or changing any code.**  
If a chat request conflicts with this file, **this file wins** unless Alexander explicitly overrides it in the current turn.

**Product:** ddOS (Drug Discovery Operating System)  
**Repo folder:** CrossBind · **Python package:** `crossbind/` (do not rename casually)  
**Owner:** Alexander Cecena · GitHub `Memeh007`  
**Runtime:** local FastAPI + Jinja · `run.bat` · `http://127.0.0.1:8787`  
**Target local agent stack:** Hermes Agent + MiniCPM5-2B (native ~128K context) — this file is the offloaded architecture brain  
**Deeper overflow:** `docs/DDOS_OS_SPEC.md` · `docs/agenda.md` · `docs/DESIGN.md` · `docs/ddos_operating_system_roadmap_2026.md`

When prompting any agent, say: *Read AGENTS.md for pipeline rules, UI design system, and golden snippets before writing code.*

---

## 0. Prime Directives (unbreakable)

1. **Wrap first, invent last.** Never write custom algorithms for pocket finding, docking, cheminformatics parsing, IFPs, or free-energy. Use approved libraries/CLIs only (see section 4).
2. **Zero-cost / local-first compute.** Prefer local CLIs (`subprocess` for P2Rank/Vina/GNINA) and free public REST (PubChem, ChEMBL, RCSB, AlphaFold DB, Open Targets GraphQL). Do **not** call OpenAI/Anthropic/paid cloud LLMs for biology truth. Optional **local** Ollama narrate only if evidence-bound.
3. **Honesty over hype.** Never label Vina / GNINA CNN / DiffDock confidence as experimental **Kd / IC50**. AlphaFold structures require provenance warnings. Pockets are hypotheses. Ligand-aware winner = "best-ranked for this ligand under engine X," never "the true site."
4. **Evidence you can point at.** Every claim ties to residue/distance/atoms, score field name, PDB/UniProt/ChEMBL/Open Targets ID, or measured ADMET descriptor.
5. **UI is gated.** Do **not** redesign UI, "physics UI," or restyle chrome unless Alexander says **go** / "start UI" in the current turn. You MAY update this file / `docs/DESIGN.md` anytime.
6. **Visualization is science, not decoration.** When UI is authorized: motion and highlights must make binding / biological process legible (site -> pocket -> pose -> contacts). No purple-gradient AI-SaaS slop; no falling decorative molecules; no fake MD.
7. **Infer toward the full OS.** ddOS is not "a docking form." Prefer features that deepen the discovery spine (proof, engines, biology, study scale) over cosmetic changes. Search the web for better libraries; propose wraps that fit the allowlist.
8. **Windows Desktop is primary.** Paths under `C:\Users\alexc\Desktop\CrossBind`. Keep `bin/p2rank/` gitignored. Cache-bust static JS when changing boot/viewer scripts.
9. **Brand:** UI product name **ddOS**. Boot logo = `crossbind/static/img/boot-logo.png` (text-free). Never reintroduce "Cross Affinity" wordmarks in chrome.
10. **Finished outputs.** No placeholder panels, lorem, skipped sections, or unfinished empty states in production paths (Taste Skill Output spirit).

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

## 3. UI strict design system (locked; implement only after go)

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
| ADMET | RDKit now; ADMET-AI / SwissADME link-outs later |
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
| `docs/DESIGN.md` | visual contract |
| `tests/` | pytest |

---

## 7. Priority when inferring next work

1. Truth and proof  
2. Engine wraps (GNINA, DiffDock-L)  
3. Biology context (Open Targets depth, orthologs)  
4. Study-scale (multi-PDB, batch ligands)  
5. UI / living viz — only after explicit go  

Agents with web search: find better libraries, then wrap — do not invent chemistry.

---

## 8. Definition of done

A skeptical computational chemist can: trace drug->target IDs; see structure provenance; see why a pocket was chosen; click proof residues that match 3D; know scores are not Kd; export enough for wet-lab planning.

---

## 9. Hermes / MiniCPM5-2B note

This file is the offloaded architecture so a ~2B model with long context becomes a **translation engine** (rules -> Python/Jinja), not an architecture guesser. Keep sections 0-5 intact under any truncation. Hermes also loads `.hermes.md` (points here).

---

*ddOS AGENTS.md — Hermes/MiniCPM edition. UI redesign gated until Alexander says go.*
