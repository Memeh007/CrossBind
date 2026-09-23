# ddOS Structure / Pose / Physics Research Memo (2023–2026)

**Audience:** Alexander Cecena / CrossBind (`crossbind`) engineering  
**Track:** Structure · Pose · Physics (library-first wraps)  
**Compiled:** 2026-09-22 PT  
**Method:** WebSearch + WebFetch of primary papers, GitHub READMEs, DOIs, licenses. No fabricated citations. Uncertainties flagged.

**Already shipped (do not reinvent):** PubChem/ChEMBL→targets→PDB/AF/upload; ligand-aware P2Rank + top-K dock; AutoDock Vina 1.2.x; GNINA path (often `gnina_ok=false` until binary); ProLIF table↔3D; ADMET; Open Targets; AF honesty banners; prefer holo PDB; scores ≠ Kd/IC50.

---

## Executive summary (≤10)

1. **Hybrid sample→validate remains the 2024–2026 consensus:** classical/hybrid docking (Vina/GNINA) or DiffDock-class pose AI → PoseBusters/strain/clash filters → ProLIF/PLIP contacts → optional MM/GBSA. Pure ML RMSD wins often fail physical validity (Buttenschoen et al., *Chem. Sci.* 2024).
2. **Highest-leverage wrap for ddOS:** finish **GNINA 1.3** install/docs (PyTorch CNNs, KD models, covalent) — path already exists; binary is the gap (*J. Cheminform.* 2025, DOI 10.1186/s13321-025-00973-x).
3. **Best open DiffDock-class option:** **DiffDock-L** (ICLR 2024; MIT; Docker/`pip`-hostile conda) for blind/apo poses + confidence; always rescore with Vina/GNINA — DiffDock FAQ explicitly says confidence ≠ affinity.
4. **Best open AF3-class option for commercial-safe local use:** **Boltz-1/2** (MIT; `pip install boltz[cuda]`; bioRxiv 2024.11.19.624167 / 2025.06.14.659707). Prefer over AF3 weights for product shipping. Chai-1 is also Apache-2.0 as of current README (verify before commercial claims).
5. **AF3 Server / AF3 weights are licensing landmines:** Server outputs **must not** feed docking/VS tools; weights are **non-commercial org only** and cannot train similar models (DeepMind terms, last modified 2024-11-09). Use only as optional academic side-path with hard banners.
6. **Pocket gap:** P2Rank is solid; 2024 LIGYSIS benchmark shows **fpocket + PRANK rescore** often beats standalone P2Rank on top-N+2 recall (DOI 10.1186/s13321-024-00923-z). Cryptic: **PocketMiner** (Nat Commun 2023); successor **AE-PocketMiner** is 2026 preprint territory — treat as research, not P0.
7. **Physics-lite missing entirely:** no OpenMM minimize/short MD, no Uni-GBSA / AmberTools MM/GBSA, no PoseBusters/PoseCheck gate, no ligand strain filter — these are the cheapest credibility upgrades after GNINA.
8. **Ensemble/apo–holo vision still thin:** ship multi-PDB + AF sample ensembles before co-folding; DynamicBind (Nat Commun 2024) helps apo→holo induced fit but is heavier than multi-structure Vina.
9. **Batch ligands + Uni-Dock (Apache 2.0, JCTC 2023)** unlock GPU ultralarge VS without leaving Vina-family scoring — natural extension of existing Meeko/Vina path.
10. **Honesty rule stays:** Boltz-2 `affinity_pred_value` / GNINA CNN / DiffDock confidence / MM/GBSA ΔG are **not** experimental Kd/IC50 — surface them as ranked evidence with method tags.

---

## Tool comparison table

| Tool | Year | Role | Open? | Install difficulty | Fit for ddOS wrap | Priority | Why |
|------|------|------|-------|--------------------|-------------------|----------|-----|
| **GNINA 1.3** | 2024–25 | Hybrid dock + CNN rescore/refine; covalent | Yes (Apache-2.0 lineage / open binary) | Med (CUDA binary ~1.2 GB; path already in CrossBind) | Excellent | **P0** | Already stubbed; closes `gnina_ok`; KD models for HTVS |
| **PoseBusters** | 2024 | Chemical/stereo/clash pose validity gate | Yes (BSD-3) | Easy (`pip`) | Excellent | **P0** | Filters ML/classical junk before ProLIF; Chem Sci DOI 10.1039/D3SC04185A |
| **RDKit strain + clash** (PoseCheck pattern) | 2023– | Ligand strain / clash filters | Yes (BSD) | Easy | Excellent | **P0** | Library-first; no new UI; Gu et al./PoseCheck workflows |
| **DiffDock-L** | 2024 | Blind diffusion pose + confidence | Yes (MIT) | Hard (conda/Docker + GPU) | High (optional engine) | **P1** | Best maintained DiffDock; Docker Hub `rbgcsail/diffdock` |
| **Uni-Dock** | 2023–25 | GPU Vina-family ultralarge VS | Yes (Apache 2.0 as of 2025-03) | Med (CUDA build) | High | **P1** | Batch-ligand natural fit; same score family as Vina |
| **Boltz-2** (also Boltz-1) | 2024–25 | Co-fold + optional affinity | Yes (MIT) | Med–Hard (GPU, MSA server) | High (opt-in module) | **P1** | Commercial-safe AF3-class; affinity needs honesty banners |
| **fpocket + P2Rank rescore** | ongoing / 2024 eval | Geometric pockets + ML rank | Yes (MIT / MIT) | Easy–Med | High | **P1** | LIGYSIS 2024: best top-N+2 when combined |
| **Uni-GBSA** | 2023 | MM/GB(PB)SA pipeline (Gromacs/acpype) | Yes (open; conda heavy) | Hard | Med–High | **P1** | Batch end-point ΔG; DOI 10.1093/bib/bbad218. *Note: no package literally named `gbsa-py` found — Uni-GBSA / MMPBSA.py are the real options* |
| **OpenMM minimize ± short MD** | ongoing | Clash removal / pose relax | Yes (MIT/X11) | Med | High | **P1** | Physics-lite before GBSA; already common in ICM/HADDOCK3 |
| **PLIP** (local) | ongoing | Rich interaction typology | Yes (GPL-2.0) | Easy | Med | **P2** | Complements ProLIF; web UX ideas; GPL copyleft caution |
| **DynamicBind** | 2024 | Ligand-specific induced-fit from apo | Yes (MIT) | Hard (GPU) | Med | **P2** | Nat Commun DOI 10.1038/s41467-024-45461-2; ensemble story |
| **DiffDock-Pocket** | 2023 | Pocket-conditioned flexible side chains | Yes (MIT) | Hard | Med | **P2** | Fits ligand-aware P2Rank boxes; NeurIPS MLSB |
| **Uni-Mol Docking V2** | 2024 | Pocket-conditioned ML pose | Yes (MIT) | Hard | Med | **P2** | Strong PoseBusters claims (77.6% <2 Å); arXiv 2405.11769 |
| **Chai-1** | 2024 | AF3-class co-fold + restraints | Yes (Apache 2.0 code+weights per README) | Hard (A100-class preferred) | Med | **P2** | Restraints useful; GPU hungry; bioRxiv 10.1101/2024.10.10.615955 |
| **PocketMiner** | 2023 | Cryptic pocket GNN from single struct | Yes (code on GitHub) | Med | Med | **P2** | Nat Commun DOI 10.1038/s41467-023-36699-3 |
| **DeepPocket / GrASP / VN-EGNN** | 2022–24 | DL pocket rank/segment | Yes | Med–Hard | Low–Med | **P3** | Benchmarked in LIGYSIS; secondary to fpocket+PRANK |
| **FlowDock** | 2024–25 | Flow-matching dock + affinity | Yes | Hard | Low–Med | **P3** | Bioinformatics / arXiv 2412.10966; younger than DiffDock-L |
| **NeuralPLexer / NP3** | 2024–25 | Sequence+ligand co-fold | Partial (code Clear BSD; weights NC on Zenodo) | Hard | Low | **P3** | Nat Mach Intell 2024; commercial weight risk |
| **RoseTTAFold-All-Atom / RFdiffusionAA** | 2024– | Design / all-atom complex | Academic open (check license) | Very hard | Low for dock core | **P3** | Better for binder *design* than pose triage |
| **EquiBind / TankBind** | 2022 | Keypoint/regression docking | Yes (MIT) | Med | **Avoid as primary** | **P3** | Superseded by DiffDock; keep only as historical baseline |
| **AlphaFold 3 (local weights)** | 2024 | Co-fold | Code Apache; **weights non-commercial** | Hard + access request | Academic-only path | **P3** | Nature DOI 10.1038/s41586-024-07487-w; no product default |
| **AlphaFold Server** | 2024– | Hosted co-fold | Free non-commercial UI | N/A (hosted) | **Do not automate into dock** | — | ToS: outputs must not feed AutoDock/Glide/etc. |
| **OpenFE ABFE** | ongoing | Alchemical FEP | Yes | Very hard | Later | **P3** | Gold-standard physics; not “lite” |
| **arpeggio (PDBe)** | ongoing | Atom-level contacts | Yes | Med | Low | **P3** | Overlaps ProLIF; useful for PDB mmCIF fidelity |
| **AE-PocketMiner** | 2026 preprint | Cryptic + allosteric coupling | Research code | Uncertain | Research | **P3** | Too new; watch Bowman lab |
| **SiteMap** | commercial | Pocket/druggability | Paywall | — | No as primary | — | Compare only; use open alternatives |
| **Schrödinger free tiers** | — | Demo/education | Restricted | — | Reference UX only | — | Not a wrap target |

---

## Papers (1-line takeaway each; ≥12)

1. **Corso et al., ICLR 2023 — DiffDock** (arXiv 2210.01776): Diffusion over ligand pose degrees of freedom with a confidence model; established the modern generative docking paradigm.  
2. **Corso et al., ICLR 2024 — DiffDock-L / “Deep Confident Steps…”** (arXiv 2402.18396): Larger model + training strategies improve pocket generalization; default in `gcorso/DiffDock` since Feb 2024.  
3. **Plainer et al., NeurIPS MLSB 2023 — DiffDock-Pocket**: Pocket-conditioned all-atom diffusion with side-chain flexibility; strong when bound structure unavailable.  
4. **Buttenschoen, Morris & Deane, *Chem. Sci.* 2024 — PoseBusters** (DOI 10.1039/D3SC04185A): Many AI dockers fail chemical/physical validity and OOD sequences; validity gates are mandatory.  
5. **McNutt et al., *J. Cheminform.* 2025 — GNINA 1.3** (DOI 10.1186/s13321-025-00973-x): PyTorch rewrite, CrossDocked2020 v1.3 CNNs, knowledge-distilled fast scorers, covalent docking.  
6. **Yu et al., *JCTC* 2023 — Uni-Dock** (DOI 10.1021/acs.jctc.2c01145): GPU batch docking with Vina/Vinardo/AD4 scores; orders-of-magnitude VS speedup.  
7. **Alcaide et al., arXiv 2024 — Uni-Mol Docking V2** (arXiv 2405.11769): Reports 77.6% <2 Å on PoseBusters with improved chemical validity; optional Uni-Dock refine.  
8. **Abramson et al., *Nature* 2024 — AlphaFold 3** (DOI 10.1038/s41586-024-07487-w): Joint biomolecular complex prediction including ligands; accuracy ≠ free commercial product license.  
9. **Wohlwend et al., bioRxiv 2024 — Boltz-1** (DOI 10.1101/2024.11.19.624167): Open MIT AF3-level complex model; code+weights+data released.  
10. **Passaro et al., bioRxiv 2025 — Boltz-2** (DOI 10.1101/2025.06.14.659707): Joint structure + binding affinity; claims FEP-approaching correlation at ~1000× speed — still not experimental IC50.  
11. **Chai Discovery, bioRxiv 2024 — Chai-1** (DOI 10.1101/2024.10.10.615955): Competitive co-folding; experimental restraints boost hard complexes; Apache 2.0 per current GitHub README.  
12. **Qiao et al., *Nat. Mach. Intell.* 2024 — NeuralPLexer** (DOI 10.1038/s42256-024-00792-z): Sequence+ligand generative complex prediction with apo/holo sampling; weight redistribution restricted (Zenodo NC).  
13. **Lu et al., *Nat. Commun.* 2024 — DynamicBind** (DOI 10.1038/s41467-024-45461-2): Equivariant generative model predicts ligand-specific protein conformation from apo inputs.  
14. **Meller et al., *Nat. Commun.* 2023 — PocketMiner** (DOI 10.1038/s41467-023-36699-3): GNN predicts cryptic pocket sites from a single structure ~1000× faster than MD.  
15. **Utgés et al., *J. Cheminform.* 2024 — LIGYSIS pocket comparison** (DOI 10.1186/s13321-024-00923-z): fpocket+PRANK / DeepPocket top ranking; argue top-N+2 recall as standard metric.  
16. **Yang et al., *Brief. Bioinform.* 2023 — Uni-GBSA** (DOI 10.1093/bib/bbad218): Automated MM/GB(PB)SA workflow for batch VS end-point energies.  
17. **Krivák & Hoksza, *J. Cheminform.* 2018 — P2Rank** (historical core; still maintained): ML ligandable-point ranking; ddOS already wraps — do not replace, extend.  
18. **Stein et al., *JCIM* 2021 — Ligand strain in large-library docking** (DOI 10.1021/acs.jcim.1c00368): Strain filters remove many false poses; calibrate thresholds per target.  
19. *(Uncertainty / early)* **NeuralPLexer3, NeurIPS 2025 proceedings PDF**: Flow-model successor claiming ~78.4% PoseBusters-combined success — verify published DOI/weights before engineering commitment.  
20. *(Uncertainty / early)* **AE-PocketMiner bioRxiv/NSF PAR 2026**: Attention extension for cryptic pockets + allosteric coupling — watch, do not ship yet.

---

## Gaps vs current ddOS pipeline

Mapped to shipped CrossBind modules (`crossbind/docking/*`, `discovery/p2rank.py`, `discovery/ligand_aware.py`, `analysis/interactions.py`):

| Gap | Current state | Impact |
|-----|---------------|--------|
| **GNINA binary reliability** | Path/docs exist; `gnina_ok` often false | Leaves only Vina score; misses CNN rescore/refine and covalent |
| **Pose physical validity gate** | ProLIF after dock; no PoseBusters/strain | Bad ML/classical poses still enter contact proof |
| **Batch ligands / library VS** | Top-K single-ligand oriented | Cannot demo credible library triage |
| **Multi-PDB / ensemble receptors** | Prefer holo when present; no multi-structure dock aggregation | Apo/AF single-frame failure mode |
| **Blind / apo DiffDock-class path** | Pockets → box dock only | Misses cryptic/mis-pocketed cases |
| **Co-folding (Boltz/Chai)** | AF honesty banners for monomers; no ligand co-fold | No sequence+SMILES complex path |
| **Cryptic / allosteric sites** | Orthosteric P2Rank | Misses PocketMiner-class opportunities |
| **fpocket second opinion** | P2Rank only | LIGYSIS 2024 says combined geometric+ML wins |
| **Physics-lite (OpenMM / MM/GBSA)** | Absent | No energy minimize, strain, or end-point ΔG column |
| **Score provenance UI/data model** | Honesty slogan exists | Need per-pose method tags: `vina` / `gnina_cnn` / `diffdock_conf` / `gbsa` / `boltz_aff` |
| **PLIP-style interaction richness** | ProLIF shipped | Optional second fingerprint + publication-ready diagrams |
| **AF3 Server automation** | Must remain blocked | Licensing: cannot pipe Server CIF into Vina |

**What serious open tools do that ddOS still lacks (non-paywall):**

- **PLIP web:** one-click interaction typology diagrams, downloadable reports, PDB-ID fetch — ddOS has ProLIF sync but thinner “publication figure” export.  
- **DiffDock HF Space / Docker:** blind dock without pocket — ddOS requires pocket/box.  
- **Boltz CLI:** YAML batch co-fold + affinity fields — no equivalent.  
- **Uni-Dock / Uni-GBSA:** GPU library dock + automatic GBSA CSV — no equivalent.  
- **PoseBusters CLI:** pass/fail table for every pose — no equivalent.  
- **SeeSAR/Glide UX (reference only):** per-atom energy coloring, ensemble receptors, docking validation reports — steal *patterns*, not code.

---

## Recommended next 5 engineering slices (library-first, no UI redesign)

### Slice 1 — **GNINA 1.3 hard enablement (P0)**
- Pin docs to [gnina/gnina v1.3+](https://github.com/gnina/gnina); default CNN ensemble per README (`dense_1_3`, KD variants, `--cnn=fast`).  
- Healthcheck: detect binary + CUDA; surface `gnina_ok` clearly; optional CPU fallback message.  
- Pipeline: Vina or GNINA search → CNN rescore → keep existing ProLIF.  
- **Honesty:** CNN score ≠ Kd.

### Slice 2 — **Pose validity gate: PoseBusters + RDKit strain/clash (P0)**
- `pip`-wrap [maabuu/posebusters](https://github.com/maabuu/posebusters) and RDKit MMFF/UFF strain (PoseCheck-style).  
- Persist boolean columns on pose table; filter or flag before contact proof.  
- Cite Buttenschoen 2024 in method footer.

### Slice 3 — **Batch ligands + Uni-Dock optional accelerator (P1)**
- CSV/SDF multi-ligand job path reusing Meeko prep.  
- If CUDA: Uni-Dock (Apache 2.0) for Vina-family scores; else Vina multiprocess.  
- Top-K per ligand → existing ProLIF on shortlist only.

### Slice 4 — **Physics-lite: OpenMM minimize → Uni-GBSA optional (P1)**
- OpenMM local minimize (and optional ≤1 ns restrained MD) on top poses.  
- Uni-GBSA or AmberTools `MMPBSA.py` for end-point ΔG CSV (`unigbsa-pipeline`-style).  
- Banner: MM/GBSA correlates imperfectly; not FEP; not IC50.  
- *Note:* Could not locate a maintained package literally named `gbsa-py`; treat Uni-GBSA / gmx_MMPBSA / MMPBSA.py as the concrete targets.

### Slice 5 — **Ensemble receptors + optional DiffDock-L sidecar (P1)**
- Multi-PDB (and optional AF sample) dock; aggregate best-per-ensemble with provenance.  
- Optional DiffDock-L Docker worker when pockets uncertain / blind mode requested; always GNINA/Vina-rescore.  
- Defer Boltz-2 to slice 5b once GPU story is stable; never auto-call AF3 Server into dock.

**Defer (P2–P3):** DynamicBind, DiffDock-Pocket, Uni-Mol Docking V2, PocketMiner cryptic lane, Chai restraints, PLIP dual-fingerprint, OpenFE ABFE.

---

## Risks / honesty

| Risk | Detail | Mitigation |
|------|--------|------------|
| **AF3 licensing** | Weights: non-commercial organizations only; no training similar models; Server outputs **cannot** be used with docking/VS tools (Server Additional ToS / FAQ). | Prefer Boltz/Chai MIT–Apache; AF3 only behind academic flag + lawyer-readable banner; never Server→Vina. |
| **GPU / disk** | GNINA ~1.2 GB binary; DiffDock/Boltz/Chai want modern NVIDIA; MSA servers are shared resources. | Feature flags; CPU Vina always works; document min GPU (e.g. 8–24 GB). |
| **Score ≠ affinity** | DiffDock confidence, GNINA CNN, Boltz-2 `affinity_pred_value` / `affinity_probability_binary`, MM/GBSA ΔG all ≠ experimental Kd/IC50. | Method-tagged columns; existing honesty copy; separate “binder vs decoy” vs “rank analogs” semantics (Boltz-2 README). |
| **Physical validity** | ML poses can look right by RMSD and be chemically wrong. | PoseBusters + strain before biology narration / LLM. |
| **GPL PLIP** | GPL-2.0 may constrain distribution if linked tightly. | Prefer ProLIF (already in); call PLIP as optional subprocess with license note. |
| **NeuralPLexer weights** | Zenodo archive CC BY-NC-SA — commercial redistribution risk. | Skip for product default. |
| **Chai license history** | Early preprint said non-commercial download; current README claims Apache 2.0 for code+weights — **re-verify LICENSE file at pin time**. | Pin version + record license hash in repo. |
| **Overclaiming Boltz-2** | Vendor/bioRxiv affinity claims vs FEP are strong; independent reproduction still maturing as of 2025–26. | “Research affinity estimate” label; cite DOI; allow disable. |
| **Cryptic pocket false positives** | PocketMiner is fast/qualitative vs MD (2026 critiques exist). | Show as hypothesis sites, not confirmed pockets. |

---

## Install quick-reference (for eng)

| Tool | Install sketch | License (as documented) |
|------|----------------|-------------------------|
| GNINA 1.3 | Download release binary / Singularity; CUDA | Open (see repo) |
| PoseBusters | `pip install posebusters` | BSD-3 |
| DiffDock-L | `docker pull rbgcsail/diffdock` or conda env from `environment.yml` | MIT |
| Boltz | `pip install boltz[cuda] -U` | MIT |
| Chai-1 | `pip install chai_lab==0.6.1` (pin!) | Apache 2.0 (README) |
| Uni-Dock | Build from [dptech-corp/Uni-Dock](https://github.com/dptech-corp/Uni-Dock) | Apache 2.0 (relicensed 2025-03) |
| Uni-GBSA | conda: acpype, gromacs, gmx_MMPBSA; `pip install unigbsa lickit` | Open academic tooling |
| fpocket | `conda install -c conda-forge fpocket` | MIT |
| P2Rank | Already wrapped; JDK release tarball | MIT |
| OpenMM | `conda install -c conda-forge openmm` | MIT/X11 |
| PLIP | `pip install plip` | GPL-2.0 |
| DynamicBind | Clone + conda; GPU | MIT |
| PocketMiner | Bowman lab GitHub / web | See repo |

---

## Sources (primary)

- https://github.com/gcorso/DiffDock (+ ICLR 2023/2024 citations in README)  
- https://github.com/plainerman/DiffDock-Pocket  
- https://github.com/gnina/gnina ; DOI 10.1186/s13321-025-00973-x  
- https://github.com/jwohlwend/boltz ; DOI 10.1101/2024.11.19.624167 ; DOI 10.1101/2025.06.14.659707  
- https://github.com/chaidiscovery/chai-lab ; DOI 10.1101/2024.10.10.615955  
- https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md  
- https://alphafoldserver.com/ (ToS / FAQ: no docking use of outputs)  
- DOI 10.1039/D3SC04185A (PoseBusters)  
- DOI 10.1021/acs.jctc.2c01145 (Uni-Dock)  
- https://github.com/deepmodeling/Uni-Mol/tree/main/unimol_docking_v2 ; arXiv 2405.11769  
- DOI 10.1038/s41467-024-45461-2 (DynamicBind)  
- DOI 10.1038/s41467-023-36699-3 (PocketMiner)  
- DOI 10.1186/s13321-024-00923-z (LIGYSIS pocket comparison)  
- DOI 10.1093/bib/bbad218 (Uni-GBSA)  
- DOI 10.1038/s41586-024-07487-w (AF3)  
- DOI 10.1038/s42256-024-00792-z (NeuralPLexer)  
- https://github.com/pharmai/plip ; https://github.com/PDBeurope/arpeggio  
- https://github.com/Discngine/fpocket ; https://github.com/rdk/p2rank  
- https://github.com/cch1999/posecheck (strain/clash patterns)

---

*End of memo. Companion landscape notes also exist at `CrossBind/docs/cross_affinity_sota_docking_landscape_2026.md` (broader commercial/UX); this memo is the structure/pose/physics engineering brief.*
