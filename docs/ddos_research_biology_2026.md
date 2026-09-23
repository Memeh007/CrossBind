# ddOS Research Memo — Biology / Pharm / ADMET / Study Desk (2023–2026)

**Product:** ddOS (CrossBind / `crossbind`) — local-first drug discovery OS  
**Track:** Biology / pharmacology / ADMET / study desk  
**Date:** 2026-09-22 (PT)  
**Audience:** Alexander Cecena + engineering  
**Method:** WebSearch + WebFetch of primary docs/papers; no fabricated citations  
**Honesty banner (applies to all ddOS evidence packs):** scores ≠ Kd; association scores ≠ causality; predicted ADMET ≠ measured PK; orthologs ≠ identical pharmacology.

---

## 1. Executive summary

ddOS already ships PubChem/ChEMBL resolve, Open Targets dossier hooks, basic ADMET, human-effects stubs, ortholog stubs, ProLIF, Vina+P2Rank, and a Discover→dock journey. The 2026-09 vision is a **vertical slice**: any drug → targets/structures → dock → human pharmacology/pathways → annotated proteomes/orthologs across **human, mouse, fly, planaria, dog, rabbit, cat**.

**What changed 2023–2026 that matters for that slice:**

1. **Open Targets Platform absorbed Open Targets Genetics (25.03)** and continues through **26.06** with GraphQL v4, ClickHouse-backed ~2× API speed, ChEMBL 37 in 26.06, and unified variant/study/credible-set entities. Prefer **parquet downloads / BigQuery / local cache** for batch; GraphQL for interactive entity pulls. Source: [Open Targets release notes](https://platform-docs.opentargets.org/release-notes), [GraphQL docs](https://platform-docs.opentargets.org/data-access/graphql-api).
2. **ChEMBL 34→37** (Mar 2024 → May 2026) remains the libre bioactivity backbone (CC BY-SA). **BindingDB 2024** adds patent-heavy affinity (CC BY 4.0 for BDB-curated; ChEMBL subset inherits BY-SA). **GtoPdb** remains gold-standard curated pharmacology. **DrugBank** and **DisGeNET** moved further into **license-gated** territory — treat as optional enrichment, not core local stack.
3. **Best local ADMET upgrade:** **ADMET-AI** (Swanson et al. 2024; v2 Chemprop in 2026) — MIT, pip-installable, offline. **ADMETlab 3.0** (Fu et al. 2024) is broader (119 endpoints + API) but **web/API-only**. SwissADME / pkCSM remain web-batch-limited.
4. **Ortholog stack for translational species:** **OrthoDB v12** (widest eukaryote sampling + REST/Python/R) + **Alliance of Genome Resources** (human/mouse/fly/worm/yeast/zebrafish/rat — *not* planaria) + **DIOPT** for fly ↔ vertebrate. **Planaria:** SmedGD retired; use **PlanMine** (+ SIMRbase for SmedSxl). Dog/rabbit/cat: UniProt + OrthoDB/Ensembl Compara; Alliance coverage is thinner.
5. **Study desk gap:** commercial LiveDesign/CDD Vault win on registration, assay ELN, SAR grids, collaborative MPO, and auditable export. Open stack approximates with **ChEMBL+BindingDB+FPSim2+RDKit+parquet evidence packs** — not a vault.

**Top recommendations (priority order):**
1. Pin **Open Targets GraphQL + parquet cache** (version-stamped) as the disease/target/drug evidence spine.
2. Ship **ADMET-AI local** behind honesty banners; keep ADMETlab as optional online enricher.
3. Build **ortholog resolver**: OrthoDB + Alliance + DIOPT + PlanMine template queries; species matrix H/M/Fly/Planaria first.
4. Local **FPSim2** on ChEMBL fps (+ optional SureChEMBL for patents) for analogs.
5. **Evidence-pack exporter** (JSON/TSV/Markdown) mimicking CDD “project snapshot” — no UI redesign.

---

## 2. Tool / API table

| Name | Access | Local? | License risk | ddOS fit | Priority |
|------|--------|--------|--------------|----------|----------|
| **Open Targets Platform GraphQL v4** | `https://api.platform.opentargets.org/api/v4/graphql` + parquet FTP/AWS | Cache parquet locally; live GraphQL for UI | Low (open platform data; cite OT) | **Primary** disease–target–drug–genetics spine; Genetics merged 25.03 | **P0** |
| **Open Targets Genetics (standalone)** | Deprecated post-25.03 | N/A | N/A | Do **not** build new clients; use Platform | — |
| **ChEMBL 34–37** | REST + SQLite/Postgres dumps + `chembl_webresource_client` | **Yes** (sqlite dump) | Low–med (CC BY-SA 3.0; share-alike on redistributed ChEMBL data) | Already shipped; pin release; use for MoA, indications, bioactivity | **P0** |
| **BindingDB** | REST + MySQL/Oracle dumps | **Yes** (dump) | Low for BDB-curated (CC BY 4.0); ChEMBL imports = BY-SA | Patent SAR + Kd/Ki/IC50; complements ChEMBL | **P1** |
| **IUPHAR/GtoPdb** | Web + downloads; REST | Partial (downloads) | Low (cite GtoPdb; check terms for redistribution) | Expert-curated targets/ligands/clinical use | **P1** |
| **DrugBank** | Academic license / commercial API | Dump only under license | **High** for product embedding | Useful labels/DDI narrative; **do not** ship in core OSS without license | **P3** |
| **Pharos / TCRD** | GraphQL `https://pharos-api.ncats.io/graphql` | TCRD dumps exist | Low (NIH IDG) | Understudied targets (Tdark/Tbio); TDL triage | **P2** |
| **DisGeNET / DISGENET** | REST under freemium plans (v25.x) | No free full dump | **High** (commercialized; free academic = partial) | Prefer Open Targets + literature for GDA; DisGeNET optional | **P3** |
| **Reactome** | Content Service + Analysis Service REST | Downloads + API | **Low** (data CC0; graphics CC BY 4.0) | Pathway mechanisms, drug→pathway overlays | **P1** |
| **WikiPathways** | SPARQL + API + downloads | **Yes** | Low (CC licenses per pathway) | Community pathways; good for niche biology | **P2** |
| **KEGG** | REST (rate-limited); FTP subscription | Academic FTP only | **High** commercial; academic bulk needs subscription | Avoid as dependency; use Reactome/WP; KEGG IDs as optional xref | **P3** |
| **STRING** | API + downloads | Network dumps local | Low–med (cite; check commercial) | PPI context for target neighborhoods | **P1** |
| **BioGRID** | Downloads + REST | **Yes** | Low | Genetic/physical interactions | **P2** |
| **OmniPath** | Web service + `omnipath`/`OmnipathR` | Cacheable | **Med** — filter `license=commercial` for for-profit; resource-specific | Unified signaling; license-aware filter critical | **P2** |
| **OrthoDB v12** | REST + Python/R packages + OrthoLoger/ODB-mapper | Downloads + local OrthoLoger | Low | **Best breadth** for planaria-adjacent + mammals | **P0** |
| **eggNOG 6** | Downloads + mapper | **Yes** (eggNOG-mapper) | Low | Functional OG annotation; complement OrthoDB | **P2** |
| **Ensembl Compara** | REST + biomart | Homology dumps | Low | Vertebrate orthologs (dog/rabbit/cat/human/mouse) | **P1** |
| **Alliance of Genome Resources** | REST `/api/gene/{id}/orthologs` | Open data files | Low | Curated model-org orthologs (FB, MGI, …); **no planaria** | **P0** (model orgs) |
| **DIOPT** | Web API (FlyRNAi) | No | Low (cite) | Fly ↔ human/mouse multi-method consensus | **P1** |
| **PlanMine** | InterMine templates + webservice | Query live; cache results | Low (academic resource) | **Planaria orthologs** across assemblies/species | **P0** (planaria) |
| **SmedGD** | **Retired** | N/A | N/A | Point users to PlanMine / SIMRbase | — |
| **FlyBase** | API + downloads | Partial | Low | Fly gene/chemical reports; Alliance partner | **P1** |
| **MGI** | Reports + Alliance | Partial | Low | Mouse phenotypes for translational inference | **P1** |
| **ADMET-AI** (v1 paper 2024; v2 pkg 2026) | pip / CLI / optional web | **Yes (offline)** | Low (MIT) | **Primary local ADMET**; TDC-trained Chemprop | **P0** |
| **ADMETlab 3.0** | Web + API | **No** (API-only models) | Unclear redistribution; free web use | Rich 119-endpoint enricher; rate-limit | **P2** |
| **SwissADME** | Web only | No | Free academic web | Physchem/druglikeness; batch ≤~200 | **P3** |
| **pkCSM** | Web | No | Free web | Classic graph-sig PK/tox; batch limited | **P3** |
| **Tox21 / ToxCast / EPA CTX** | CTX Bioactivity API + invitrodb dumps | **Yes** (invitrodb + tcpl) | Low (US gov) | Assay-grounded tox; DTXSID link | **P1** |
| **CypReact / CyProduct** | Java offline | **Yes** | Academic tool | CYP substrate/reactant local | **P2** |
| **DeepTox** | Historical | Models aging | — | Prefer ADMET-AI / ToxCast-trained models | — |
| **PubChem** | PUG-REST / PUG-View | Fingerprints via download | Low | Similarity + assay; already used | **P0** |
| **SureChEMBL** | Downloads / search | Fingerprint DBs local via FPSim2 | Low–med (EMBL-EBI) | Patent chemical space | **P2** |
| **FPSim2** | Python lib (ChEMBL) | **Yes** | Low (MIT-ish) | Local Tanimoto NN on ChEMBL/SureChEMBL fps | **P0** |
| **Molbloom** | pip (`whitead/molbloom`) | **Yes** | Low | **Membership** (in catalog?) not similarity — use for purchasability gates | **P2** |
| **Therapeutics Data Commons (TDC)** | pip datasets | **Yes** | Low | ADMET training/eval benchmarks | **P2** |

---

## 3. Papers / reviews (≥10) with takeaways

| # | Citation | Takeaway for ddOS |
|---|----------|-------------------|
| 1 | Swanson et al. (2024). *ADMET-AI…* **Bioinformatics** 40:btae416. [DOI 10.1093/bioinformatics/btae416](https://doi.org/10.1093/bioinformatics/btae416) · [PMC11226862](https://pmc.ncbi.nlm.nih.gov/articles/PMC11226862/) | Best **local** ADMET path: Chemprop-RDKit on 41 TDC sets; 1M mols ~3.1 h local GPU; DrugBank percentile context. Ship offline; banner: predicted ≠ measured. |
| 2 | Fu et al. (2024). *ADMETlab 3.0…* **NAR** 52:W422–W431. [DOI 10.1093/nar/gkae236](https://doi.org/10.1093/nar/gkae236) · [PMC11223840](https://pmc.ncbi.nlm.nih.gov/articles/PMC11223840/) | 119 endpoints, DMPNN-Des, **API + uncertainty**. Use as optional online enricher; not local-first. |
| 3 | Liu et al. (2025). *BindingDB in 2024…* **NAR**. [DOI 10.1093/nar/gkae1075](https://doi.org/10.1093/nar/gkae1075) · [PMC11701568](https://pmc.ncbi.nlm.nih.gov/articles/PMC11701568/) | ~2.9M affinities; patent curation unique vs ChEMBL; CC BY 4.0 (BDB) / BY-SA (ChEMBL subset). Ideal SAR pack source. |
| 4 | Zdrazil et al. (2024). *The ChEMBL Database in 2023…* **NAR** 52:D1180–D1192. [DOI 10.1093/nar/gkad1004](https://doi.org/10.1093/nar/gkad1004) | Multi-bioactivity types over time; releases 34+ continue (35 Dec 2024; 36 Jul 2025; 37 May 2026 — [FTP index](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/)). |
| 5 | Harding et al. (2024). *IUPHAR/BPS Guide to PHARMACOLOGY in 2024.* **NAR**. [DOI 10.1093/nar/gkad944](https://doi.org/10.1093/nar/gkad944) | Expert MoA, quantitative interactions, approved-drug curation — human pharmacology “truth set.” |
| 6 | Tegenfeldt et al. (2025). *OrthoDB and BUSCO update…* **NAR**. [DOI 10.1093/nar/gkae987](https://doi.org/10.1093/nar/gkae987) · [PMC11701741](https://pmc.ncbi.nlm.nih.gov/articles/PMC11701741/) | OrthoDB v12: 5827 eukaryotes; REST + OrthoLoger/ODB-mapper for new genomes (planaria-scale annotation). |
| 7 | Hernández-Plaza et al. (2023). *eggNOG 6.0…* **NAR** 51:D389–D394. [DOI 10.1093/nar/gkac1022](https://doi.org/10.1093/nar/gkac1022) | Functional OG annotation across 12k+ organisms; pair with OrthoDB for labels. |
| 8 | Szklarczyk et al. (2023). *STRING database in 2023…* **NAR** 51:D638–D646. [DOI 10.1093/nar/gkac1000](https://doi.org/10.1093/nar/gkac1000) | PPI + enrichment for any sequenced genome — target neighborhood after docking. |
| 9 | Kelleher et al. (2023). *Pharos 2023…* **NAR** 51:D1405–D1416. [DOI 10.1093/nar/gkac1033](https://doi.org/10.1093/nar/gkac1033) | IDG TCRD/Pharos GraphQL for understudied proteome & TDL. |
| 10 | Hasselgren & Oprea (2024). *AI for Drug Discovery: Are We There Yet?* **Annu Rev Pharmacol Toxicol** 64:527–550. [DOI 10.1146/annurev-pharmtox-040323-040828](https://doi.org/10.1146/annurev-pharmtox-040323-040828) | Skeptical practical review: lists real tools (TDC, ADMETlab, OCHEM, NCATS predictors) vs hype; “not there yet” on end-to-end AI discovery. |
| 11 | Zhang et al. (2025). *Artificial intelligence in drug development.* **Nature Medicine** 31:45–59. [DOI 10.1038/s41591-024-03434-4](https://doi.org/10.1038/s41591-024-03434-4) | End-to-end pharma process view; reinforces validation/clinical gaps — use for honesty framing. |
| 12 | Loeffler et al. (2024). *Reinvent 4…* **J Cheminform** 16:20. [DOI 10.1186/s13321-024-00812-5](https://doi.org/10.1186/s13321-024-00812-5) | Open generative design (Apache 2); optional later chemical-space expansion, not P0 for study desk. |
| 13 | White et al. (2023). *Bloom filters for molecules.* **J Cheminform**. [DOI 10.1186/s13321-023-00765-1](https://doi.org/10.1186/s13321-023-00765-1) · [molbloom](https://github.com/whitead/molbloom) | Fast **catalog membership**; not analog search — pair with FPSim2. |
| 14 | Öztürk-Çolak et al. (2024). *FlyBase: updates…* **Genetics**. [DOI 10.1093/genetics/iyad211](https://doi.org/10.1093/genetics/iyad211) | Fly chemical reports + orthology hooks via Alliance/DIOPT. |
| 15 | Open Targets Platform release notes 25.03–26.06 (2025–2026). [docs](https://platform-docs.opentargets.org/release-notes) | Genetics merged; GraphQL entities for variant/study/credible set; 26.06 adds ChEMBL 37, baseline expression revamp, Helm chart WIP. |

**Also useful (secondary):** Daina et al. SwissADME (2017) Sci Rep; Pires et al. pkCSM (2015) J Med Chem — still cited as baselines in 2024 ADMET papers but API/web-only.

---

## 4. Concrete gaps vs ddOS vision

### 4.1 Pharmacology / human effects
| Vision need | Gap today | Fill with |
|-------------|-----------|-----------|
| Drug → MoA → indications → safety | Partial (ChEMBL + OT stubs) | GtoPdb curated interactions + OT drug MoA/indications + ChEMBL drug warnings |
| Genetic support for target | OT Genetics separate/stale | **OT Platform 25.03+** credible sets / L2G via GraphQL |
| Disease evidence pack | Thin | OT associationByDatasource parquet + Reactome pathways |
| DDI / clinical PK narrative | Missing | Prefer open labels (DailyMed/openFDA) over DrugBank unless licensed; CypReact for metabolism hypotheses |

### 4.2 Orthologs / translational proteomes
| Species | Coverage | Gap |
|---------|----------|-----|
| Human / mouse | Strong (Alliance, MGI, Ensembl, OrthoDB) | Wire Alliance + MGI phenotypes into dossier |
| Fly | Strong (FlyBase + DIOPT + Alliance) | DIOPT API + FlyBase chemical report links |
| Planaria (*S. mediterranea*) | **Community-only** (PlanMine; SmedGD retired) | No Alliance; reciprocal-BLAST orthologs — **must banner confidence** |
| Dog / rabbit / cat | OrthoDB + Ensembl Compara / UniProt | Thin curated pharma; no Alliance-class curation |
| Cross-species pharmacology transfer | Stubs only | Need explicit **“ortholog ≠ drug target equivalence”** + sequence identity / OG phyletic profile |

### 4.3 Study desk (vs LiveDesign / CDD Vault)
Commercial patterns to approximate (not clone UI):

| Commercial pattern | Open approximation for ddOS |
|--------------------|-----------------------------|
| Compound registration + lot tracking | Local SQLite/Postgres registry of SMILES/InChIKey + provenance |
| Multi-ligand SAR table (pIC50 matrix) | ChEMBL/BindingDB query → tidy table; RDKit R-group / Murcko |
| Activity cliffs / MMP | RDKit mmpdb or ChEMBL MMP dumps |
| Multi-parameter optimization radar | ADMET-AI + docking score panel (honest units) |
| Collaborative ELN / assay import | Out of scope short-term; export CSV for CDD/ELN |
| Evidence pack / report export | **Versioned JSON + Markdown + TSV** with source DOIs, OT release, ChEMBL version |
| 3D design session | Already: Vina/P2Rank/ProLIF — attach to SAR row |

**Not worth building now:** full CDD-class permissions, inventory, or LiveDesign live-collab.

---

## 5. Next 5 engineering slices (API wraps / caching / honesty — no UI redesign)

1. **OT GraphQL client + parquet cache (P0)**  
   - Pin Platform release (e.g. 26.06).  
   - Entity fetch: `drug(chemblId)`, `target(ensemblId)`, `disease(efoId)`, associations, known drugs, pharmacogenetics.  
   - Disk cache keyed by `(release, entity_type, id)`.  
   - Banner: “Open Targets association score ≠ experimental validation.”

2. **ADMET-AI local service (P0)**  
   - `pip install admet-ai` (prefer v2 for Chemprop v2 compat; note prediction drift vs v1 paper).  
   - Batch CSV in Discover/library pipeline.  
   - Banner: “ML ADMET on TDC labels; not clinical PK. Scores ≠ Kd.”

3. **Ortholog resolver v1 (P0)**  
   - Inputs: UniProt / Ensembl / FlyBase / MGI / PlanMine contig.  
   - Backends: Alliance REST (model orgs) → OrthoDB `/orthologs` → DIOPT (fly) → PlanMine InterMine template.  
   - Output: species × ortholog table with method + stringency + sequence identity when available.  
   - Banner: “Orthologs support translational *hypothesis*, not dose or MoA transfer.”

4. **Evidence pack exporter (P1)**  
   - Bundle: drug identity, OT dossier summary, ChEMBL MoA/activities (top-N), BindingDB patent hits, Reactome pathways, dock summary, ADMET-AI vector, ortholog matrix.  
   - Formats: `evidence_pack.json`, `.tsv`, `.md`.  
   - Embed versions: ChEMBL N, OT YYYY.MM, OrthoDB v12, model hashes.

5. **FPSim2 analog neighbor service (P1)**  
   - Build HDF5 from ChEMBL `.fps` (release-matched).  
   - Query: Tanimoto ≥ 0.7 / top-k → SAR seed table.  
   - Optional: Molbloom purchasability gate; SureChEMBL fps later.  
   - Banner: “Chemical similarity ≠ bioisosterism or shared target.”

**Deferred (license / complexity):** DrugBank embed, DisGeNET full, KEGG pathways as dependency, OmniPath commercial filter UI, LiveDesign-like collab.

---

## 6. Planaria / fly translational notes (metformin / senescence background)

### 6.1 Resource reality
- **SmedGD is retired** (Stowers PLANOSPHERE). Current assemblies/transcriptomes: **PlanMine** (MPI) and SIMRbase for SmedSxl v3.1.  
  - PlanMine: [user guide](https://planmine.mpinat.mpg.de/planmine/user_guide.html); ortholog templates via reciprocal BLAST best hits across flatworm species/assemblies.  
- **Alliance / MGI / FlyBase do not include planaria** — ddOS must treat PlanMine as a first-class but lower-confidence ortholog source.
- **Fly** remains the best invertebrate bridge: FlyBase chemical reports + DIOPT multi-algorithm orthologs to human/mouse ([FlyBase 2024](https://doi.org/10.1093/genetics/iyad211); [DIOPT API](https://www.flyrnai.org/tools/diopt/web/api)).

### 6.2 Biology relevant to metformin / aging / regeneration
- Planarian aging/rejuvenation literature (2025) emphasizes **regeneration-driven systemic rejuvenation** in sexual *S. mediterranea*, not metformin per se: Dai et al., *Nature Aging* (2025) [DOI 10.1038/s43587-025-00847-9](https://doi.org/10.1038/s43587-025-00847-9).
- Metformin work in planarians is emerging mainly in ***Dugesia japonica*** regeneration (2025 *Genes* / *IJMS* papers on eyespot regeneration / miR-27b axes) — **not** a mature *S. mediterranea* senescence pharmacology atlas. Treat as hypothesis-generating.
- Conserved axes to prioritize in ortholog packs for metformin-class work: **AMPK (PRKAA), mTOR/Raptor, insulin/IGF, mitochondrial ETC Complex I**, DNA damage/senescence markers (where annotated). Map human → mouse (Alliance) → fly (DIOPT) → planaria (PlanMine BLAST/OG) with identity thresholds.
- Starvation / mTOR / telomere papers in immortal planarians exist historically; they support **nutrient-sensing conservation** framing, not automatic drug translation.

### 6.3 ddOS-specific honesty for this research line
1. Label planaria orthologs as **RBH/PlanMine**, not Alliance-curated.  
2. Never present docking to a human structure as evidence of planarian target engagement.  
3. Separate panels: **human clinical pharmacology (metformin)** vs **invertebrate phenotypic literature** vs **computed orthologs**.  
4. Evidence pack for “metformin translational” should cite OT/ChEMBL AMPK evidence *and* planaria papers as distinct layers.

---

## 7. Access patterns cheat-sheet (implementers)

```text
Open Targets GraphQL:
  POST https://api.platform.opentargets.org/api/v4/graphql
  Bulk: FTP/AWS parquet for release N (prefer over N× single-entity calls)

ChEMBL:
  https://www.ebi.ac.uk/chembl/api/data/ ... or local sqlite chembl_XX
  fps: chembl_XX.fps.gz → FPSim2 HDF5

BindingDB:
  REST + monthly dumps; CC BY 4.0 for BDB-curated rows

GtoPdb:
  https://www.guidetopharmacology.org/ (downloads + web services)

Pharos:
  https://pharos-api.ncats.io/graphql

Reactome:
  https://reactome.org/ContentService/  (data CC0)

STRING:
  https://string-db.org/api/ ... + species-specific protein network downloads

OrthoDB:
  https://www.orthodb.org/  REST /orthologs ; OrthoLoger conda

Alliance:
  https://www.alliancegenome.org/api/gene/{id}/orthologs

PlanMine:
  InterMine templates (Smed orthologous contigs) + webservice URLs

ADMET-AI:
  pip install admet-ai && admet_predict --data_path in.csv --save_path out.csv

ADMETlab 3.0:
  https://admetlab3.scbdd.com/ + documented API (online only)

EPA CTX / ToxCast:
  ctx-python / ctxR + invitrodb local

FPSim2:
  https://chembl.github.io/FPSim2/
```

---

## 8. License risk summary (product counsel view)

| Tier | Resources | Guidance |
|------|-----------|----------|
| **Ship freely (with attribution)** | Open Targets, PubChem, Reactome data (CC0), BindingDB BDB-curated (CC BY), OrthoDB, Alliance open data, ToxCast/CTX, ADMET-AI MIT, FPSim2, Molbloom | Core local stack |
| **Ship with share-alike care** | ChEMBL (CC BY-SA) | OK to query/cache; redistribution of derived DBs must respect BY-SA |
| **Optional / gated** | DrugBank, DisGeNET full, KEGG FTP/commercial, OmniPath non-commercial subsets | Feature-flag; never bundle dumps in OSS release without review |
| **Web enrichers only** | ADMETlab API, SwissADME, pkCSM | User-initiated; cache responses with TOS check |

---

## 9. Sources index (URLs fetched or searched 2026-09-22 PT)

- Open Targets GraphQL: https://platform-docs.opentargets.org/data-access/graphql-api  
- Open Targets releases: https://platform-docs.opentargets.org/release-notes  
- OT 26.03 blog: https://blog.opentargets.org/open-targets-platform-26-03-has-been-released/  
- ChEMBL downloads: https://chembl.gitbook.io/chembl-interface-documentation/downloads  
- ChEMBL 35 FTP: https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_35/  
- GtoPdb 2024.4 / 2025.1 blogs: https://blog.guidetopharmacology.org/  
- BindingDB 2024 NAR: https://pmc.ncbi.nlm.nih.gov/articles/PMC11701568/  
- ADMET-AI paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11226862/ · GitHub https://github.com/swansonk14/admet_ai  
- ADMETlab 3.0: https://admetlab3.scbdd.com/ · PMC https://pmc.ncbi.nlm.nih.gov/articles/PMC11223840/  
- OrthoDB v12: https://pmc.ncbi.nlm.nih.gov/articles/PMC11701741/ · https://www.orthodb.org  
- PlanMine: https://planmine.mpinat.mpg.de/ · SmedGD retirement: https://planosphere.stowers.org/smedgd  
- Reactome license: https://reactome.org/license  
- KEGG licensing: https://www.pathway.jp/en/licensing.html  
- DisGeNET plans: https://www.disgenet.com/plans  
- DrugBank academic: https://www.drugbank.com/academic_research  
- FPSim2: https://chembl.github.io/FPSim2/  
- Molbloom: https://github.com/whitead/molbloom  
- Hasselgren & Oprea 2024: https://doi.org/10.1146/annurev-pharmtox-040323-040828  
- Zhang et al. Nat Med 2025: https://doi.org/10.1038/s41591-024-03434-4  
- Nature Aging planaria 2025: https://doi.org/10.1038/s43587-025-00847-9  

---

*End of memo. Path: `/workspace/ddos_research_biology_2026.md`*
