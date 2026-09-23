# AGENTS.md — standing instructions for every coding run on ddOS

**Read this file before writing or changing any code in this repository.**  
If anything here conflicts with a casual chat request, follow this file unless Alexander explicitly overrides it in the current turn.

**Product:** **ddOS** (Drug Discovery Operating System)  
**Repo / Desktop folder:** `CrossBind`  
**Python package path (do not casually rename):** `crossbind/`  
**Owner:** Alexander Cecena (GitHub: Memeh007)  
**Deeper vision / backlog prose:** `docs/agenda.md` · evidence roadmap: `docs/ddos_operating_system_roadmap_2026.md`
**Whole-product agent bible (features, libraries, UIRoot map, journeys):** `docs/DDOS_OS_SPEC.md`

---

## 0. Cold-start checklist (every session)

1. Read **this** `AGENTS.md`.
2. Read `docs/DDOS_OS_SPEC.md` for whole-app context (journeys, feature matrix, library stack, UIRoot map).
3. Skim `docs/agenda.md` if the task touches product direction, UI, viz, or new science modules.
4. Skim `docs/DESIGN.md` if the task is (or will become) UI — still gated by §3 / §7.5.
5. Prefer **library wraps** over new chemistry/ML implementations.
6. Confirm whether the task is **UI** — if yes, see §3 (blocked without explicit go-ahead).
7. Keep scores honest (Vina/GNINA/DiffDock confidence ≠ Kd/IC50).

---

## 1. What we are building (never forget)

ddOS is a **local-first drug discovery operating system**, not “a dark-themed Vina form.”

End-to-end intent:

**drug / idea → targets & mechanisms → structures (PDB/AF/upload) → pockets (holo / P2Rank / ligand-aware rank) → dock / pose → living, inspectable binding viz + residue proof → ADMET triage → pharmacology & cross-species orthologs → study tables / evidence packs**

You must **infer** depth: biology process legibility, physics-aware visualization, and best-in-class scientific tools — not shallow chrome.

Layers: Identity · Structure · Site · Dock/Pose · Physics & proof · Biology context · ADMET · Study desk · Evidence-bound optional local AI.

---

## 2. Hard rules

### Library-first
Wrap mature tools. Do **not** reinvent: pocket ML, force fields, cheminformatics cores, interaction fingerprint engines.

Prefer / plan around: **RDKit**, **Meeko**, **Open Babel**, **AutoDock Vina**, **GNINA**, **P2Rank**, **ProLIF** / PLIP, **Biopython**, **Open Targets**, **ChEMBL**, **PubChem**, optional **DiffDock-L**, later OpenMM/OpenFE — cite and wrap.

### Scientific honesty
- Never label docking / CNN / DiffDock-confidence as experimental **Kd / IC50**.
- AlphaFold structures: show provenance warnings (pose success ≠ crystal).
- Pockets are **hypotheses**. Ligand-aware winner = “best-ranked for this ligand under engine X,” never “the true site.”
- Optional LLM (Ollama): **evidence-bound only**. No bundled cloud LLM as biology truth.

### Local-first
Default bind `127.0.0.1`. No secret exfiltration. Don’t add cloud dependencies without asking.

### Package / brand
- UI product name: **ddOS**
- Import package folder stays **`crossbind`** until an explicit rename project.
- Boot logo: text-free brand mark (`static/img/boot-logo.png`); do not reintroduce “Cross Affinity” wordmarks in UI chrome.

---

## 3. UI / visualization gate (critical)

**Do not start UI redesign, “physics UI,” living-docking animation work, or visual restyles unless Alexander explicitly says to begin UI in the current conversation.**

When UI *is* authorized:
- Goal = make docking and biology **understandable and alive** (site lighting, contact proof in 3D, staged process), not generic SaaS polish.
- Design inspiration (e.g. Mobbin) = **patterns only** — never scrape or copy copyrighted screen assets into the repo.
- Prefer instrument / scientific OS aesthetics over marketing landing pages.

Until then: deepen science, proof objects, APIs, docs, tests, engine wraps.

---

## 4. How to implement

- **Orchestration + UX + honesty** in `crossbind/`; engines as CLI/PyPI deps.
- Match existing FastAPI + Jinja + static JS style unless migrating with a clear plan.
- Windows Desktop path is primary for Alexander: `C:\Users\alexc\Desktop\CrossBind`, `run.bat`, port **8787**.
- After behavior changes: restart server if needed; verify `/api/health` when engines matter (`vina_ok`, `p2rank_ok`, …).
- Cache-bust static assets when changing boot/JS that browsers sticky-cache.
- Commit clearly; push only with approval when required.
- Keep `bin/p2rank/` and large binaries **gitignored**.

---

## 5. Priorities when inferring “what next”

1. Truth & proof (contacts, provenance, pocket method on results)  
2. Engine wraps (GNINA, DiffDock-L, richer ProLIF)  
3. Biology context (Open Targets, orthologs)  
4. Study-scale (ensemble PDB, batch ligands)  
5. **UI / living viz** — only after explicit go-ahead  

Non-goals: fake MD, Kd theater, rewriting Vina/P2Rank, unsolicited UI passes.

---

## 6. Communication with Alexander

- Be direct; lead with outcomes.
- Ask before UI; ask before destructive git/data ops; ask before outbound messages/purchases.
- Update `docs/agenda.md` when he corrects long-term vision; update **this** file when standing engineering rules change.

---

---

## 7. UIRoot taste lock (read before ANY authorized UI work)

**Source of truth for anti-generic UI culture:** [UIRoot](https://uiroot.com/) — especially:
- [Taste Skill](https://uiroot.com/tools/158) — stop AI slop / boring frontends
- [Originkit](https://uiroot.com/tools/203) — free animated components (Framer/React/MCP); use for **motion patterns**, not as the scientific stack
- [UI Component catalog](https://uiroot.com/category/ui-component) — component libraries & motion/3D/sound kits to evaluate
- [DESIGN.md catalog](https://uiroot.com/category/design-md) — agent-readable design contracts (`DESIGN.md`, getdesign.md, DesignMD, Open Design, TypeUI, Impeccable, …)

**Our project design contract file:** `docs/DESIGN.md` (keep in sync when taste rules change).

### 7.1 Anti-slop (Taste Skill spirit) — mandatory when UI is authorized
Do **not** ship generic AI frontend defaults:
- Inter / purple-gradient / glassmorphism-for-its-own-sake / “AI SaaS” card grids
- Placeholder sections, lorem, unfinished empty states, fake charts
- Motion that is decorative only (sparkles, falling fluff) with no scientific meaning
- Copying marketing landing aesthetics onto a research instrument

Do ship **intentional taste**:
- Clear visual hierarchy, disciplined spacing, restrained palette
- Layout variance with purpose (instrument panels, not brochure sections)
- Motion that explains process (pocket appear → dock → contact proof), calm and complete
- Full, finished surfaces — Output Skill spirit: no skipped sections

### 7.2 Preferred taste modes for ddOS (when UI starts)
Default toward a hybrid of Taste Skill modes:
- **Soft + Minimalist** — calm, sophisticated, tight hierarchy, restrained color (scientific OS, not loud startup)
- Optional **Brutalist/Swiss** accents only for data density / monospace instrument chrome — never raw shock for its own sake
- Use **Redesign / Image-to-code** skills only when Alexander supplies references; prefer fidelity to those refs over improvising “pretty”

### 7.3 Originkit & component catalog — how to use
- Originkit / Magic UI / Aceternity / SmoothUI / Rare UI / etc. = **inspiration and optional motion primitives**
- Prefer **accessible, unstyled or headless bases** (e.g. Base UI / Radix patterns) under a ddOS-specific skin
- **3D / WebGL** kits (ThreeUI, Canvas UI, Shaders) only where they serve molecular/scene viz — do not turn the whole OS into a Three.js marketing site
- Sound kits (Cuelume, Sensory UI, …) are optional later; never required for science correctness
- **Never scrape UIRoot or vendor sites into the repo.** No copyrighted screenshots or copied proprietary CSS dumps. Link + pattern notes only; implement originals under MIT/our code

### 7.4 DESIGN.md workflow (UIRoot “DESIGN.md” category)
Before a large UI pass:
1. Update `docs/DESIGN.md` with tokens, type, spacing, motion, density, and ddOS-specific patterns (viewer, pocket strip, evidence proof).
2. Agents implement against `DESIGN.md` + this section — not against vibes.
3. Tools like getdesign.md / DesignMD / Open Design / TypeUI may be used to **analyze** references Alexander provides; output belongs in `docs/DESIGN.md`, not as opaque agent memory.

### 7.5 Still gated
Section 7 does **not** authorize UI work. It only locks taste for when Alexander says **go**.

---

*If you are an automated coding agent: treating this file as optional is a bug.*


