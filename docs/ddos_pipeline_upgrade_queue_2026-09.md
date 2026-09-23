# ddOS Pipeline Upgrade Queue — merged research (2026-09-22 PT)

**Product:** ddOS / CrossBind (`crossbind`) v1.3.2  
**Living stack:** Vina ✅ · P2Rank ✅ · GNINA path stubbed ❌ binary · ProLIF ✅ · RDKit ADMET ✅ · OT dossier hooks ✅  
**Rule:** library-first · scores ≠ Kd · **no UI redesign** until Alexander says go  
**Sources:** `docs/ddos_research_structure_2026.md` · `docs/ddos_research_biology_2026.md` · prior `docs/ddos_operating_system_roadmap_2026.md`

This file is the **action queue** MiniCPM / other agents should follow. Prefer it over improvising features.

---

## What we inferred (product, not tools)

ddOS is already a credible **Discover → pocket → dock → contact proof** instrument. The next credibility cliff is not prettier chrome — it is:

1. **Pose quality gates** (many 2024 ML poses fail chemical/physical validity — PoseBusters).
2. **Second scoring engine** (GNINA 1.3 CNN) so ranking is not Vina-only.
3. **Study-scale surfaces** (batch ligands, multi-PDB, evidence packs) so demos look like discovery, not one-off docks.
4. **Biology that matches Alexander’s vision** (OT genetics spine, local ADMET-AI, orthologs including PlanMine for planaria).
5. **Hard license walls** (never AF3 Server → dock; prefer Boltz MIT over AF3 weights for product).

---

## Unified build order (pipeline only)

| Order | Slice | Track | Why now | Effort |
|------:|-------|-------|---------|--------|
| **B1** | **GNINA 1.3 hard enable** | Structure | Path exists; only binary/CUDA gap; enrichment vs Vina well cited (McNutt 2025) | Med (install + healthcheck + CNN fields) |
| **B2** | **PoseBusters + RDKit strain/clash gate** before ProLIF | Structure | Cheap credibility; Chem Sci 2024 | Easy–Med |
| **B3** | **ADMET-AI local** (MIT offline) replace/extend RDKit-only triage | Biology | Best local ADMET (Swanson 2024); honesty banners | Easy–Med |
| **B4** | **Open Targets GraphQL v4 + release-pinned cache** deepen dossier | Biology | Genetics merged 25.03; Platform through 26.06 | Med |
| **B5** | **Batch ligands (CSV/SDF)** → study table (Vina multiprocess; Uni-Dock later) | Structure | Unlocks VS demos without co-folding | Med |
| **B6** | **Multi-PDB / AF-sample ensemble dock** + provenance rollup | Structure | Already prefer-holo; need multi-structure | Med |
| **B7** | **Ortholog resolver v1** Alliance → OrthoDB → DIOPT → PlanMine | Biology | Vertical slice for H/M/fly/planaria (+ dog/rabbit/cat later) | Med–Hard |
| **B8** | **Evidence pack export** JSON + MD + TSV (versions stamped) | Biology | Study desk without UI redesign | Easy–Med |
| **B9** | **OpenMM minimize** (± short restrained MD) on top poses | Structure | Physics-lite before GBSA | Med |
| **B10** | **FPSim2** on ChEMBL fps for analog neighbors | Biology | SAR seed table | Med |
| **B11** | **fpocket + P2Rank rescore** second opinion | Structure | LIGYSIS 2024 top-N+2 | Med |
| **B12** | **DiffDock-L Docker sidecar** (blind) → always Vina/GNINA rescore | Structure | Confidence ≠ affinity | Hard (GPU) |
| **B13** | **Uni-GBSA / MMPBSA.py** end-point column | Structure | Shortlist only; not Discover default | Hard |
| **B14** | **Boltz-2 opt-in** co-fold + research affinity | Structure | MIT AF3-class; never AF3 Server automation | Hard (GPU) |

**Defer:** DynamicBind, Uni-Mol Docking V2, PocketMiner cryptic lane, Chai (re-verify Apache at pin), PLIP dual (GPL caution), DrugBank/DisGeNET/KEGG embeds, LiveDesign-class collab, UI redesign.

---

## Recommended next coding sprint (pick one lane)

**Lane A — Credibility (fastest scientific trust):** B1 → B2 → B3  
**Lane B — Discovery OS vertical:** B4 → B7 → B8 (pharmacology + orthologs + export)  
**Lane C — Scale:** B5 → B6 → B10 (batch + ensemble + analogs)

Default recommendation if Alexander does not choose: **Lane A**, then B5.

---

## Honesty checklist (bake into every slice)

- Vina / GNINA CNN / DiffDock confidence / Boltz affinity / MM/GBSA / ADMET-AI ≠ experimental Kd/IC50/PK  
- OT association ≠ causal validation  
- Ortholog ≠ same pharmacology (PlanMine = RBH, not Alliance-curated)  
- AF3 Server outputs must **not** enter dock/VS pipelines  
- Method-tag every numeric column (`vina`, `gnina_cnn`, `posebusters_pass`, `admet_ai`, `ot_assoc`, …)

---

## Companion memos

| File | Contents |
|------|----------|
| `docs/ddos_research_structure_2026.md` | Pose/dock/physics tools, papers, install notes |
| `docs/ddos_research_biology_2026.md` | OT/ChEMBL/ADMET/orthologs/study desk + planaria notes |
| `docs/ddos_operating_system_roadmap_2026.md` | Earlier P0–P2 roadmap (still valid; this queue supersedes ordering) |

---

*Compiled 2026-09-22 PT from dual-track research. Update when a slice ships.*
