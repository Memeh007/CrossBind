# Structure-Based Docking / VS Landscape (2025–2026) → Cross Affinity Backlog

Research compiled for Cross Affinity (local FastAPI: SMILES→RDKit→Meeko→AutoDock Vina 1.2 + optional GNINA, 3Dmol). Goal: credible pre-wet-lab simulation for LinkedIn-style biotech audiences. Sources fetched/searched; no fabricated papers.

---

## 1. Commercial platforms — what users highlight

### Schrödinger Glide (+ Maestro / LiveDesign / Active Learning / Generative Glide)
- **Positioning:** Industrial default for reliable ligand–receptor docking; hierarchical HTVS→SP, Glide WS (WaterMap explicit-water energetics), covalent CovDock, constraints, peptides/macrocycles.
- **2025–2026 product moves users talk about:**
  - Glide ~2× faster as default (Release 2025-3).
  - Docking Report for native redocking diagnostics (2026-1).
  - MacroDock ~2.5× faster, ~80% success; density-map docking (2026-3).
  - Active Learning Glide for >1B libraries; **Generative Glide** claims goal-directed navigation of up to ~50B compounds on a workstation in ~2 days (vs brute-force docking).
- **UX/workflow highlights:** Guided GUI + Ligand Designer interactive 3D design; prepared commercial libraries; AB-FEP+ rescoring path; Python APIs.
- **Sources:** https://www.schrodinger.com/platform/products/glide/ ; release notes 2025-3 / 2026-1 / 2026-3 ; Generative Glide webinar page.

### OpenEye OEDocking (Cadence / Orion)
- **Tools:** FRED (exhaustive VS), HYBRID (ligand-guided enrichment), POSIT (knowledge-guided pose + reliability index), Induced-Fit Posing; Gigadock / Gigadock Warp for tens of billions.
- **User highlights:** Speed (claimed 5–100× vs competitors), multi-crystal ensembles, crystallographic ligand as guide, Chemgauss4, cloud/toolkit options.
- **Source:** https://www.eyesopen.com/oedocking (fetched).

### Cresset Flare / Lead Finder
- **Highlights:** Dedicated VS scoring (DUD ROC AUC ~0.74 claimed historically); covalent + non-covalent; ensemble / template / constrained docking; “Flickering Waters”; Electrostatic Complementarity & field/pharmacophore design (Spark/Blaze) as differentiator beyond pure docking.
- **Sources:** https://cresset-group.com/software/lead-finder/ ; Flare docking method pages.

### BioSolveIT SeeSAR (+ Chemical Space Docking®, HPSee)
- **Strongest “steal this UX” commercial product for medchem audiences:** drag-drop protein prep, auto binding-site detection (DoGSiteScorer), one-click FlexX docking, **HYDE** per-atom color-coded ΔG / desolvation feedback, ADME (Optibrium), FastGrow fragment grow, ReCore scaffold hop, covalent warheads (36), Chemical Space Docking for trillion-scale synthons on modest hardware, Activity Spotter (SeeSAR 15 “Apollo”, 2026).
- **Privacy angle:** local GUI + optional remote HPSee; “keep data local.”
- **Sources:** https://www.biosolveit.de/products/seesar/ ; Chemical Space Docking pages; SeeSAR 15 Apollo announcements (2026).

### ICM-Pro (MolSoft)
- **Highlights:** Continuously flexible ligand docking with grid potentials; **4D / multi-receptor ensemble**; Pocket Finder (drug-likeness score); interactive 3D Ligand Editor (Novartis collab); OpenMM MD integration; PROTAC ternary modeling; historically strong CAPRI / physics reputation.
- **Source:** https://www.molsoft.com/icm_pro.html (fetched).

### MOE (CCG)
- **Highlights:** Site Finder (alpha-sphere), induced-fit / covalent docking, integrated SVL scripting, pharmacophore + SBDD suite — enterprise “one GUI for everything” rather than docking-only.
- **Sources:** https://www.chemcomp.com/en/Products.htm ; CCG product literature.

**Competitive takeaway for Cross Affinity:** Credibility in 2026 is less “has Vina” and more **prep → pocket → multi-engine/ensemble → interpretable score → ADMET triage → interactive design loop**, with optional ultra-large / generative screening.

---

## 2. Modern open / ML tools

| Tool | Role | Notes & dates | URL |
|------|------|---------------|-----|
| **AutoDock Vina 1.2** | Physics sampling + score | Baseline everyone compares to; Python bindings, expanded FF | JCIM 2021; still core 2025–26 |
| **GNINA** | Hybrid: Vina-like search + CNN pose/affinity | Strong PoseBusters / hybrid workflows; v1.1–1.3 line (2024–2025) | https://github.com/gnina/gnina ; J Cheminform GNINA 1.3 (2025) |
| **Uni-Dock** | GPU Vina-family ultralarge VS | >1000–2000× vs single-core Vina; Apache 2.0 relicense Mar 2025 | https://github.com/dp-yuanyn/Uni-Dock ; JCTC 2023 |
| **Vina-GPU 2.x** | GPU Vina | ~20–50× speedups; Polaris ASAP challenge workflows used Vina-GPU + priors | Molecules 2022; Tang et al. updates |
| **DiffDock / DiffDock-L** | Blind diffusion pose generation + confidence | Confidence is **intra-ligand**; for VS needs external score (Vina/GNINA) — ChemRxiv 2025 hybrid study | Corso et al. ICLR 2023; DiffDock-L follow-ons |
| **KarmaDock** | Fast large-library DL docking | High redocking accuracy; physics plausibility weaker than classical (Nat Mach Intell Feb 2025 benchmark) | Nat Comput Sci 2023 |
| **SurfDock** | Surface-informed diffusion | Strong pose + VS claims; ALDH1B1 prospective hits; Nat Methods 2025 (online Nov 2024) | https://doi.org/10.1038/s41592-024-02516-y |
| **AlphaFold3** | Co-folding complexes | Outperforms classical docking on some held-out PoseBusters cuts; **not a drop-in VS engine**; limited access | Nature 2024 |
| **Chai-1** | Open-ish co-folding | Competitive in PoseBench / FoldBench; MSA-sensitive | Boitreaud et al. 2024 |
| **Boltz-1 / Boltz-2** | Open AF3-class; Boltz-2 adds affinity | MIT + Recursion, **MIT license**, Jun 6 2025; affinity ~FEP-ish Pearson 0.62 on held-out OpenFE bench, 1000× faster; CASP16 affinity lead (vendor claim) | https://boltz.bio/boltz2 ; Recursion IR |
| **PyRx** | Desktop VS GUI over AutoDock/Vina/SMINA | Teaching / small lab UX; licensing split free vs paid | https://pyrx.sourceforge.io/ |
| **DockThor** | Brazilian HPC web server | Free VS (limits ~5k ligands registered); good LinkedIn “I ran a screen” demo | https://dockthor.lncc.br/v2/ |
| **GalaxyDock / GalaxyDock-DL** | Academic docking + DL | Linux OSS; weights often non-commercial | variously published |

**2025–2026 consensus from benchmarks (not marketing):**
- **AI pose models** often win redocking RMSD but fail **physical validity** (PoseBusters); physics tools (Vina/GNINA/Glide/ICM) produce more rational geometries (Nat Mach Intell 13 Feb 2025: Gu et al.).
- **Co-folding** strong in-distribution, **collapses on novel systems** (~25–40% success OOD vs >60% physics) — Zenodo multi-paradigm benchmark 2025/26; eLife Mac1 co-folding eval; FoldBench Nat Commun.
- **Practical SOTA pattern:** physics or hybrid **sample** → CNN/ML **rescore** (GNINA, RTMScore, EquiScore) → optional co-fold refine / Boltz-2 affinity on shortlist → consensus.

---

## 3. End-to-end apps / startups — product angles

| Org | Angle (2025–2026 discourse) | Sources |
|-----|----------------------------|---------|
| **Isomorphic Labs** | IsoDDE beyond AF3: structure + affinity + pockets + antibody design; pharma partnerships; structure-first platform | https://www.isomorphiclabs.com/articles/the-isomorphic-labs-drug-design-engine-unlocks-a-new-frontier |
| **Recursion** | Recursion OS: phenomics + multi-omics + chemistry; Boltz-2 collab; clinical assets (REC-4881 etc.); “data layers not just models” | recursion.com news / pipeline; Boltz-2 IR Jun 2025 |
| **Insilico** | PandaOmics + Chemistry42 generative SBDD; rentosertib Phase 2a narrative; PLI/ADMET/FEP in design loops | Chemistry42 JCIM; company news 2025 |
| **Atomwise** | AtomNet structure-based DL bioactivity / novel chemotypes; PoseRanker; large multi-target published screens | BusinessWire Apr 2024; AtomNet papers |
| **deepmirror (elio)** | Medchem-first UI: generative + potency/ADMET models + structure/cofolding validation; privacy/ISO27001; hit-rate case studies | https://www.deepmirror.ai/ |
| **Polaris** | **Not a docking SaaS** — industry benchmarking hub (Recursion/AZ/Pfizer/…). ASAP blind-docking challenges; Vina-GPU+priors papers | https://polarishub.io/ ; JCIM Polaris Challenge 2025 |
| **Benchling computational** | ELN/LIMS + emerging compute; less docking-core, more workflow/data gravity (mention as integration target, not docking peer) | product ecosystem discourse |
| **BioSolveIT / Schrödinger** demos | Dominate LinkedIn “screen→inspect→design” video UX | SeeSAR / Generative Glide content |

**Implication:** Cross Affinity should market as **local, transparent, hybrid physics+ML docking workbench**, not as Recursion-scale OS. Compete on **honesty, privacy, pose quality, and medchem-readable UX**.

---

## 4. Must-have capabilities for a credible 2026 docking app

| Capability | Why (landscape) |
|------------|-----------------|
| **Pocket detection + auto-box** | SeeSAR/MOE/ICM all auto-site; DiffDock blind mode exists but VS still needs focused boxes |
| **Ensemble docking** | OpenEye multi-crystal, ICM 4D, Cresset ensemble; single rigid receptor = known failure mode |
| **Consensus / multi-score** | Gu et al. 2025 hierarchical VS; DiffDock-L+GNINA ChemRxiv 2025; classical consensus literature |
| **RMSD-to-crystal / redock report** | Schrödinger Docking Report 2026-1 — validation story LinkedIn loves |
| **ADMET / drug-likeness filters** | SeeSAR+Optibrium; deepmirror ADMET-first; Polaris ADME datasets |
| **Batch CSV / SDF in–out** | Non-negotiable for VS demos |
| **Pose viz + interaction fingerprints** | 3Dmol already; need HYDE-like or PLIP/ProLIF style annotations |
| **MD refine (optional, P2)** | ICM OpenMM; SeeSAR YASARA — nice, not day-1 |
| **Active learning / shortlist affinity** | AL-Glide, Generative Glide, Boltzina (Vina→Boltz-2), Boltz-2 affinity |
| **Uncertainty / confidence** | DiffDock confidence; GNINA CNN; POSIT reliability — display explicitly |
| **Local privacy** | deepmirror Trust Center; SeeSAR local+HPSee; Cross Affinity’s FastAPI-local is a **real differentiator** |

---

## 5. Honest limits: Vina alone vs ICM / Glide / GNINA / DiffDock

**Vina alone can claim:**
- Fast flexible-ligand docking in a defined box
- Reasonable redocking / enrichment **when receptor & protonation are good**
- Open, reproducible, privacy-friendly baseline

**Vina alone cannot honestly claim:**
- Best-in-class enrichment vs **Glide** on many TrueDecoy-style VS sets (Gu et al., Nat Mach Intell Feb 2025 — Glide-based methods highest EFs among docking tools on TrueDecoy)
- Explicit water / desolvation physics like **Glide WS / WaterMap** or **HYDE**
- Continuous side-chain / induced-fit sampling like **ICM** (or Glide IFD-MD)
- Blind docking without a box like **DiffDock-L / AF3 / Boltz**
- Learned affinity approaching FEP like **Boltz-2** (vendor benchmarks) or Schrödinger FEP+
- Guaranteed physical pose validity *or* best RMSD — **GNINA** often improves ranking; **KarmaDock/SurfDock** may win RMSD but AI poses can be less physically plausible (PoseBusters / Gu 2025)
- Ultra-large (10⁸–10¹⁰) library throughput without **Uni-Dock / Vina-GPU / AL / Chemical Space Docking / Gigadock**

**Positioning line for Cross Affinity:**  
“Vina (+ optional GNINA) for transparent physics sampling; ML rescoring and optional co-fold/affinity on shortlists — not a Glide/FEP replacement.”

---

## Prioritized feature backlog for Cross Affinity

### P0 — Credibility floor (ship before loud LinkedIn demos)
1. **Auto pocket + docking box** (fpocket / P2Rank / DoGSite-like, or ligand-centroid from co-crystal) with manual override — matches SeeSAR/MOE expectations.
2. **Batch CSV/SDF** ligands → ranked table (score, CNNaffinity if GNINA, LE, MW, LogP, TPSA, Ro5 flags) + download poses SDF.
3. **Crystal redock + RMSD report** when reference ligand present (Schrödinger Docking Report parity at OSS level).
4. **GNINA path as first-class** (not buried): Vina pose → CNN rescore / `--cnn_scoring` modes; show both scores.
5. **Pose viz upgrades:** H-bonds, clashes, pocket surface, score overlay in 3Dmol; traffic-light torsion sanity (SeeSAR Visual Torsions inspiration).
6. **Local-by-default privacy copy + no-cloud toggle** — own the deepmirror/SeeSAR trust narrative.

### P1 — Competitive parity for “serious” VS
7. **Consensus docking:** Vina + GNINA (+ optional Uni-Dock or second score e.g. Vinardo); rank-by-rank / Z-score fusion.
8. **Ensemble receptors:** multi-PDB / MD-frame upload; best-pose-per-ligand across ensemble (OpenEye/ICM pattern).
9. **ADMET / PAINS / Brenk filters** pre- and post-dock (RDKit + public models); MPO-style radar.
10. **Active-learning lite:** dock cheap → train surrogate on scores → prioritize next batch (AL-Glide story without billion-compound claims).
11. **DiffDock-L optional blind mode** for pocket-unknown cases + **always** physics/GNINA rescore (ChemRxiv 2025 hybrid lesson).
12. **Uncertainty UI:** DiffDock confidence / GNINA CNN variance / ensemble score spread as first-class columns.

### P2 — SOTA-adjacent differentiators
13. **Uni-Dock or Vina-GPU** backend for 10⁵–10⁶ library screens.
14. **Boltz-2 affinity / Boltzina-style** rescoring on top-N only (cost control); MIT license is strategic.
15. **Short MD minimize / OpenFF or OpenMM refine** of top poses (ICM/SeeSAR pattern) — optional GPU.
16. **Co-fold panel** (Boltz-1/2 or Chai-1) for “is this pose consistent with sequence-conditioned complex?” with OOD warning banners.
17. **Fragment grow / inspirator** (lightweight FastGrow-like) — high LinkedIn engagement, lower scientific risk than claiming FEP.
18. **Polaris / PoseBusters validation suite** packaged so users can reproduce benchmarks (community trust).

---

## 5 “Steal this UX” ideas (from real products)

1. **SeeSAR Analyzer “HYDE traffic lights”** — per-atom favorable/unfavorable contributions + one-click ADME filters (https://www.biosolveit.de/products/seesar/).
2. **SeeSAR Binding Site Mode** — auto-detect site, expand by residue click, empty-pocket finder before dock.
3. **Schrödinger Docking Report** — redocking diagnostics to “maximize docking performance” before library screen (Release 2026-1 notes).
4. **OpenEye POSIT reliability index** — show pose confidence from similarity to known binders (https://www.eyesopen.com/oedocking).
5. **deepmirror elio loop** — generate/prioritize for ADMET+potency → structure/cofold validate → chemist stays in one medchem UI with privacy badges (https://www.deepmirror.ai/).

Honorable mentions: BioSolveIT Chemical Space Docking “synthon not product” storytelling; Glide Generative Glide “50B on a workstation” narrative (aspirational, don’t overclaim); Boltz-2 “affinity without FEP wait” shortlist panel.

---

## Suggested Cross Affinity 2026 narrative (honest)

> Local FastAPI docking workbench: RDKit prep → auto-pocket → Vina 1.2 sampling → optional GNINA CNN / consensus → ADMET triage → 3Dmol inspection, with crystal RMSD validation and privacy-first defaults. Roadmap: ensemble + Uni-Dock scale + Boltz-2 shortlist affinity — not a replacement for Glide WS / FEP+, and not co-folding-as-VS without caveats.

---

## Key citations (verify before marketing claims)

- Schrödinger Glide product & Generative Glide: schrodinger.com (product + webinar pages); Release Notes 2025-3, 2026-1, 2026-3.
- OpenEye OEDocking: https://www.eyesopen.com/oedocking
- SeeSAR: https://www.biosolveit.de/products/seesar/
- ICM-Pro: https://www.molsoft.com/icm_pro.html
- Gu et al., Nat Mach Intell, **13 Feb 2025**, AI vs physics docking for VS: https://www.nature.com/articles/s42256-025-00993-0
- SurfDock, Nat Methods **2025** (27 Nov 2024 online): https://doi.org/10.1038/s41592-024-02516-y
- Boltz-2 announcement **6 Jun 2025**: https://boltz.bio/boltz2
- Uni-Dock: JCTC doi:10.1021/acs.jctc.2c01145 ; GitHub Apache 2.0 Mar 2025
- PoseBusters: Chem Sci 2024 (Buttenschoen et al.) — AI pose validity critique
- DiffDock-L + Vina/GNINA VS hybrid: ChemRxiv 2025 (doi 10.26434/chemrxiv-2025-96kzg-v2)
- Polaris Hub: https://polarishub.io/
- deepmirror: https://www.deepmirror.ai/
- Isomorphic IsoDDE: isomorphiclabs.com article above
- AF3: Nature 2024 doi:10.1038/s41586-024-07487-w
- eLife Mac1 co-folding prospective eval: doi:10.7554/elife.110475

