# AGENTS.md — standing instructions for every coding run on ddOS

**Read this file before writing or changing any code in this repository.**  
If anything here conflicts with a casual chat request, follow this file unless Alexander explicitly overrides it in the current turn.

**Product:** **ddOS** (Drug Discovery Operating System)  
**Repo / Desktop folder:** `CrossBind`  
**Python package path (do not casually rename):** `crossbind/`  
**Owner:** Alexander Cecena (GitHub: Memeh007)  
**Deeper vision / backlog prose:** `docs/agenda.md` · evidence roadmap: `docs/ddos_operating_system_roadmap_2026.md`

---

## 0. Cold-start checklist (every session)

1. Read **this** `AGENTS.md`.
2. Skim `docs/agenda.md` if the task touches product direction, UI, viz, or new science modules.
3. Prefer **library wraps** over new chemistry/ML implementations.
4. Confirm whether the task is **UI** — if yes, see §3 (blocked without explicit go-ahead).
5. Keep scores honest (Vina/GNINA/DiffDock confidence ≠ Kd/IC50).

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

*If you are an automated coding agent: treating this file as optional is a bug.*
