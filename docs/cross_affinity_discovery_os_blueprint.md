# Cross Affinity Discovery OS — Technical Blueprint

**Product:** grow CrossBind / Cross Affinity from a local docking app into a privacy-first local drug-discovery platform  
**Author context:** Alexander Cecena — metformin × planaria (*S. mediterranea*) research  
**Researched:** 2026-09-21 (PT) via live web search + HTTP probes  
**Companion doc:** `cross_affinity_sota_docking_landscape_2026.md` (docking engines)  
**Guiding constraint:** **library-first** — wrap mature PyPI / CLI tools; do **not** build custom parsers, scrapers, or H-bond detectors from scratch.

---

## Guiding principle: wrap, don’t reimplement

Cross Affinity’s value is **orchestration + UX + honesty**, not reinventing cheminformatics. Every discovery layer should be a thin FastAPI module over a maintained client. Custom HTTP is allowed only when no client exists (e.g. AlphaFold DB `/prediction/{accession}`, PlanMine InterMine). Prefer `httpx` + pydantic models over hand-rolled `urllib` when wrapping raw endpoints.

**Existing stack to keep (CrossBind today):** FastAPI, RDKit, Meeko, Open Babel / `obabel`, AutoDock Vina 1.2, optional GNINA, 3Dmol.js, localhost bind.

---

## A) Best OPEN APIs / databases + LIBRARY-FIRST wrappers

### A1. Drug identity & structures

| Source | Open for local/research? | Primary endpoints | Recommended library | License (lib) | How we call it | What we will NOT write |
|--------|--------------------------|-------------------|---------------------|---------------|----------------|------------------------|
| **PubChem** | Yes (public domain data; fair-use API) | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/...` | **`pubchempy`** | MIT | `pcp.get_compounds("metformin", "name")` → CID, SMILES, InChIKey | Custom PUG URL builders / HTML scrapers (replace CrossBind’s hand-rolled PUG GET) |
| **ChEMBL** | Yes — CC BY-SA 3.0 | `https://www.ebi.ac.uk/chembl/api/data/` | **`chembl-webresource-client`** | Apache-2.0 | `new_client.molecule.search("metformin")`; `.mechanism.filter(molecule_chembl_id=...)` | Manual pagination / JSON schema parsing |
| **UniChem** | Yes (EBI) | `https://www.ebi.ac.uk/unichem/rest/` (and newer UniChem 2) | **`bioservices`** (`UniChem`) or thin `httpx` | GPLv3 (bioservices) | Cross-map CID ↔ ChEMBL ↔ DrugBank IDs | Scraper for source websites |
| **RDKit (local)** | Yes | N/A (local) | **`rdkit`** (already) | BSD-3-Clause | `Chem.MolFromSmiles` → descriptors, SDF, 3D embed | Custom SMILES parsers |

**Live probe (2026-09-21):** PubChem name `metformin` → CID **4091**, formula `C4H11N5`. Throttle header present: `X-Throttling-Control` (Green). Documented soft limits ≈ **5 req/s**, **400 req/min** — respect `X-Throttling-Control` (PubChem PUG-REST update paper / docs: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest ).

**Fallback:** NIH CACTUS (already in CrossBind) only if PubChem fails — keep as tertiary.

**Optional thin aggregator:** `bioservices` also wraps PubChem/ChEMBL/UniProt in one dependency (GPLv3 — OK for local research app; note copyleft if redistributing as SaaS).

---

### A2. Drug → target links

| Source | Open? | Endpoints | Recommended library | License | Call pattern | Do NOT write |
|--------|-------|-----------|---------------------|---------|--------------|--------------|
| **ChEMBL** mechanisms + activities | Yes CC BY-SA 3.0 | `/mechanism`, `/activity`, `/target`, `/drug_indication` | **`chembl-webresource-client`** | Apache-2.0 | Prefer `max_phase` drugs + curated `mechanism`; activities as secondary evidence with pChEMBL filters | Custom HTML scrape of ChEMBL UI |
| **Open Targets Platform** | Yes (open data; cite OT) | GraphQL `https://api.platform.opentargets.org/api/v4/graphql` (data release **26.06** / API **26.6.3** as of probe) | **`httpx` + curated GraphQL strings** (no mature first-party PyPI client; avoid inventing one) | N/A (client is ours; data CC0-ish OT terms) | `drug(chemblId:)` → `mechanismsOfAction`, `linkedDiseases`; `target(ensemblId:)` → `associatedDiseases` | Scraping platform.opentargets.org HTML |
| **BindingDB** | Yes (free web services) | `https://bindingdb.org/rest/getLigandsByUniprot?...` | **`httpx`** (no strong PyPI client) | Free for research; cite BindingDB | Affinity rows by UniProt; live probe: UniProt `P54646` returned hits | Parsing BindingDB download dumps unless batch needed |
| **IUPHAR/BPS Guide to Pharmacology (GtoPdb)** | Yes — ODbL / CC BY-SA 4.0 data | `https://www.guidetopharmacology.org/services/` | **`httpx`** | Free; **API key may be required ~late Aug/Sep 2026** (check current ToS) | Ligand → interactions → targets | Scrape GtoPdb pages |
| **DrugBank** | **Not fully open** | Clinical API (key) | Avoid for core path | Proprietary / academic license | Optional future *user-supplied* key module | Bundling DrugBank dumps or claiming “DrugBank-powered” without license |

**Live probe (2026-09-21):** Open Targets `drug(chemblId:"CHEMBL1431")` → name `METFORMIN`; mechanisms include **Mitochondrial complex I (NADH dehydrogenase) inhibitor** with MT-ND* / NDUF* targets (partial response truncated). ChEMBL `/molecule/CHEMBL1431` intermittently **HTTP 500** during research window — client must retry/backoff.

**Ranking rule for UI:** curated mechanism (ChEMBL / Open Targets / GtoPdb) ≫ single assay activity ≫ text-mined association.

---

### A3. Protein identity

| Source | Library | License | Call | Do NOT write |
|--------|---------|---------|------|--------------|
| **UniProt REST** | **`unipressed`** (preferred) or `bioservices.UniProt` | MIT / GPLv3 | Accession lookup, gene→accession, proteome filters | Custom XML parsers for UniProt |
| ID mapping / gene symbols | **`mygene`** | BSD | `mygene.MyGeneInfo().querymany(symbols, species="human", fields="uniprot,ensembl")` | Homegrown synonym tables |

**Live UniProt release header:** `2026_03` (2026-09-02 deployment). Human Swiss-Prot ≈ **20,431** reviewed.

---

### A4. Structures (PDB / mmCIF / AlphaFold) → docking inputs

| Source | When to prefer | Formats | Library / client | License | Call | Do NOT write |
|--------|----------------|---------|------------------|---------|------|--------------|
| **RCSB PDB** | Experimental structure exists for human (or close ortholog) target; ligand-bound preferred for redock validation | **mmCIF** source of truth; **PDB** for legacy tools; **PDBQT** only after prep | **`rcsbsearchapi`** (search) + **`pypdb`** / **`biotite`** / **`biopython`** (fetch+parse) | BSD / MIT / Biopython | Search by UniProt accession → rank by resolution, method, ligand identity → download via `https://files.rcsb.org/download/{pdb_id}.cif` | BeautifulSoup on rcsb.org pages; custom mmCIF tokenizers (`biotite.structure.io.pdbx` / Biopython MMCIFParser) |
| **PDBe** | Same archive, EU mirror / PDBe-KB annotations | cif/pdb | `httpx` to PDBe REST if needed | Open | Prefer RCSB for Cross Affinity unless PDBe-KB ligands needed | Duplicate archive downloaders |
| **AlphaFold DB (AFDB)** | No usable experimental structure; or domains missing in PDB | Prefer **mmCIF** from API; PDB also offered; confidence in B-factors / JSON | **`httpx`** → `GET https://alphafold.ebi.ac.uk/api/prediction/{UNIPROT}` then download `cifUrl` / `pdbUrl` | AF models CC-BY-4.0 | Live probe: `P54619` → `latestVersion` **6**, mean pLDDT **86.56**, model date **2025-08-01** | Hardcoding `...model_v4...` URLs; ignoring pLDDT/PAE |

**PDB vs AF decision tree (encode in `structures.py`):**
1. Search PDB/PDBe for UniProt accession (polymer entity).
2. If ≥1 entry: rank (resolution ≤3.5 Å preferred; X-ray/EM over NMR for docking; prefer holo with druglike ligand).
3. Else: AFDB monomer; **refuse silent docking** if mean pLDDT < ~70 or binding-site residues <70 — surface warning.
4. AF3 / Boltz co-folding is **out of Slice 1–2** (see SOTA docking doc); do not claim AFDB monomers are co-folded complexes.

**To Vina/GNINA:**
- Receptor: mmCIF/PDB → **`pdbfixer`** (MIT) missing residues/atoms → Open Babel / Meeko receptor path → **PDBQT** (already CrossBind).
- Ligand: SMILES → RDKit → **`meeko`** → PDBQT (already).
- Do **not** feed raw AF CIF straight into Vina without fixer + protonation.

**Pocket detection (optional Slice 2):** **P2Rank** CLI (MIT, not PyPI — vendor binary under `bin/`) and/or **fpocket** CLI; wrap subprocess like Vina. Do not reimplement LIGSITE.

---

### A5. Pathways / human effects / disease

| Source | Open? | Library | Notes | Do NOT write |
|--------|-------|---------|-------|--------------|
| **Open Targets** | Yes | `httpx` GraphQL | Best single graph for drug→target→disease + tractability | Scrapers |
| **Reactome** | Yes — content **CC0** | **`httpx`** Content Service; optional `bioservices.Reactome` | `GET .../data/mapping/UniProt/{acc}/pathways?species=9606` — live probe OK for `P54646` | Custom pathway layout engines |
| **WikiPathways** | Yes — CC0 | `httpx` / JSON API | Enrichment / links | SVG scrapers |
| **Monarch Initiative** | Yes | `httpx` → `https://api-v3.monarchinitiative.org` | Phenotypes / model organisms | — |
| **DisGeNET** | **License trap** | Skip by default | Free academic ≠ redistribute in a product; commercial needs paid license ([support article](https://support.disgenet.com/support/solutions/articles/202000087487-do-i-need-a-commercial-license-can-i-use-disgenet-data-in-my-product-)) | Shipping DisGeNET dumps inside Cross Affinity |
| **GTEx** | Open API for expression | `httpx` optional | Tissue expression of target — nice-to-have Slice 3 | Claiming “patient-level” data |

**UI copy source of truth:** Open Targets mechanisms + Reactome pathway names + ChEMBL `mechanism_of_action` strings — always show **citations and evidence type**.

---

### A6. Orthologs / comparative proteomes

Target organisms for Alexander’s translational workflow:

| Organism | Taxon | UniProt all / reviewed (live 2026-09-21) | Ortholog quality |
|----------|-------|------------------------------------------|------------------|
| Human | 9606 | 210,706 / 20,431 | Reference |
| Mouse | 10090 | 87,756 / 17,283 | Excellent (Ensembl Compara, OMA, OrthoDB) |
| Fruit fly | 7227 | 42,881 / 3,904 | Excellent — live Ensembl: `PRKAA1` → fly orthologs (many2many; ~25% id) |
| Dog | 9615 | 46,473 / 857 | Good via Ensembl/OMA |
| Rabbit | 9986 | 42,933 / 979 | Moderate |
| Cat | 9685 | 60,377 / 234 | Moderate (few Swiss-Prot) |
| **Planaria *S. mediterranea*** | **79327** | **1,588 / 4** | **Sparse in UniProt; see §E** |

| Source | Library | License | Call | Do NOT write |
|--------|---------|---------|------|--------------|
| **Ensembl Compara** | **`httpx`** REST (`/homology/symbol/:species/:symbol`) | Open | `target_taxon` filters for 10090, 7227, 9615, … Rate limit headers observed: ~55k/hour | Scraping Ensembl HTML |
| **OMA** | **`httpx`** `https://omabrowser.org/api/` | Open | Genome **`SCHMD`** exists: **29,850** entries for *S. mediterranea* (live); protein ortholog endpoints | Reimplement HOGs |
| **OrthoDB** | **`httpx`** `https://data.orthodb.org/` | Open | Ortholog groups by gene/UniProt | — |
| **EggNOG** | Mapper CLI / downloads | Open | Batch annotation offline | Web scraping |
| **UniProt** ortholog xrefs | **`unipressed`** | MIT | Follow DR lines / Proteomes | — |
| **DIOPT** (fly-centric) | `httpx` | Academic tool | https://www.flyrnai.org/tools/diopt/web/api — great for human↔fly | Treating DIOPT scores as experimental proof |
| **g:Profiler** | **`gprofiler-official`** | BSD | Orthology + enrichment helper | Custom GO enrichment |

**Planaria-specific:**
| Resource | Status (2026-09) | Access | Notes |
|----------|------------------|--------|-------|
| **PlanMine** | Active InterMine warehouse (MPI) | Web + InterMine clients (Python/Perl/Ruby/Java); templates e.g. `Smed_Orthologous` | https://planmine.mpinat.mpg.de/planmine/ — BLAST homology, GO, assembly orthologs; SSL may need careful CA handling in clients |
| **SmedGD** | **Retired** | Redirects to Planosphere / PlanMine | Do not depend on SmedGD URLs ([Planosphere note](https://planosphere.stowers.org/smedgd)) |
| **PLANA** (Planarian Anatomy Ontology) | Active OBO | GitHub `obophenotype/planaria-ontology`; OLS | Anatomy/phenotype terms — **not** gene orthologs |
| **WormBase ParaSite** | Has *S. mediterranea* genomes | REST / FTP | Useful nucleotide/protein downloads |
| **OMA SCHMD** | Present | REST | Best *global* ortholog API hook for planaria proteins **if** sequences map into OMA |

---

### A7. Post-dock interaction fingerprints (already needed for credibility)

| Tool | PyPI | License | Role | Do NOT write |
|------|------|---------|------|--------------|
| **ProLIF** | `prolif` | Apache-2.0 | Preferred IFP for docked poses (MDAnalysis/RDKit) | Custom H-bond / π-stack code |
| **PLIP** | `plip` | **GPL-2.0** | Strong visual reports; GPL copyleft — prefer ProLIF inside MIT app, or call PLIP as **optional external CLI** | Vendoring PLIP into core MIT tree without license review |

---

## B) Recommended architecture (local FastAPI, privacy-first)

### B1. Package layout (extend CrossBind → `crossbind/discovery/` or rename product to Cross Affinity)

```
crossbind/
  app.py                 # routes only — thin
  docking/               # existing Vina/GNINA pipeline (keep)
  discovery/
    drug.py              # pubchempy + chembl client + RDKit normalize
    targets.py           # chembl mechanisms + Open Targets GraphQL
    structures.py        # rcsbsearchapi + pypdb/biotite + AFDB httpx + pdbfixer
    pharmacology.py      # Reactome + OT diseases + pathway cards
    orthologs.py         # Ensembl REST + OMA + optional PlanMine
    interactions.py      # prolif wrap over docked pose
    cache.py             # SQLite helpers
  data/
    cache.sqlite         # HTTP/API response cache
    structures/          # cif/pdb/pdbqt blobs
    jobs/                # existing
```

Each module exports **pure functions** + pydantic models; FastAPI routers call them. No scraping modules.

### B2. Caching strategy

- **SQLite** at `data/cache.sqlite` (or `CROSSBIND_DATA/cache.sqlite`).
- Tables: `http_cache(key TEXT PK, url, fetched_at, expires_at, body BLOB, content_type)` and `entity_cache(kind, id, json, fetched_at)`.
- Keys: e.g. `pubchem:name:metformin`, `chembl:mech:CHEMBL1431`, `afdb:P54619:v6`, `ensembl:homology:PRKAA1:7227`.
- TTLs (starting points): PubChem/ChEMBL/OT **7–30 d**; PDB/AF files **forever** (content-addressed by ID+version); UniProt **30 d**.
- Respect privacy: **no cloud sync**; optional “offline mode” uses cache only.
- Rate-limit locally with token bucket per host (PubChem especially).

### B3. Rate limits / ToS notes (summary)

| API | Practical limit / ToS | Cache? |
|-----|----------------------|--------|
| PubChem | ~5 r/s, 400/min; watch `X-Throttling-Control` | Yes |
| ChEMBL | Be polite; EBI ToS; CC BY-SA attribution | Yes |
| Open Targets | No auth; discourage bulk entity loops — use downloads for proteome-scale | Yes + FTP for bulk |
| UniProt | Generous; provide contact User-Agent | Yes |
| RCSB | Fair use; prefer file CDN for binaries | Cache files on disk |
| AFDB | Pace metadata calls; bulk via GCS for proteomes | Cache cif |
| Ensembl | ~55k/hour class limits (header) | Yes |
| BindingDB | Research use; cite | Yes |
| GtoPdb | Watch 2026 API-key policy | Yes |
| DrugBank | **Do not embed** without license | N/A |
| DisGeNET | **Do not redistribute** in product | Link-out only |
| PlanMine | Cite; InterMine fair use | Cache template results |

Always send a clear User-Agent: `CrossAffinity/0.x (local; Alexander Cecena; contact…)`.

### B4. Minimal viable vertical slice (one UI flow)

**Demo drug: metformin** (aligned with Alexander’s planaria work).

1. User types `metformin` (or SMILES / CID).
2. `drug.py` → PubChem CID + SMILES (`pubchempy`) + ChEMBL ID (`chembl-webresource-client`).
3. `targets.py` → ranked targets (Open Targets mechanisms + ChEMBL); pick top human UniProt (e.g. AMPK / complex I subunits — show **evidence**, don’t over-claim “the” target).
4. `structures.py` → best PDB or AF model; prepare PDBQT via existing pipeline + `pdbfixer`.
5. Existing **dock** job → Vina/GNINA.
6. `pharmacology.py` → Reactome pathways + OT disease links for those targets.
7. `orthologs.py` → table: human → mouse / fly / dog / rabbit / cat / **planaria (OMA or BLAST-to-PlanMine with confidence banner)**.
8. `interactions.py` → ProLIF fingerprint on top pose.

One page: **Resolve → Targets → Structure → Dock → Effects → Orthologs**.

---

## C) What NOT to claim (regulatory / medical honesty)

Cross Affinity / CrossBind must **not** claim:

1. **Clinical efficacy, dosing, or safety** for any drug–disease pair (“treats diabetes”, “safe in humans”).
2. **Regulatory readiness** (FDA/EMA IND/NDA support) or GLP/GCP compliance.
3. **Equivalence** of Vina/GNINA scores to ICM, Glide, FEP, or experimental ΔG / Kd / IC50.
4. That **docking poses are experimentally validated** without crystal redock / wet-lab confirmation.
5. That **AlphaFold models are experimental structures** or that AF monomer pockets are confirmed binding sites.
6. That **orthologs imply identical pharmacology** across species (especially planaria — huge evolutionary distance).
7. **Diagnosis, treatment, or personalized medicine** features.
8. Bundled **DrugBank / DisGeNET** knowledge as if openly licensed for redistribution.
9. “AI discovered a drug” marketing from a local docking run.
10. Silent failure: if planaria ortholog mapping is BLAST-only or missing, the UI must say so.

Safe framing: *research hypothesis generation; pre-wet-lab triage; educational / translational exploration.*

Keep / extend CrossBind’s existing disclaimer language.

---

## D) Ordered implementation plan (library wraps only)

### Slice 1 — This week (vertical metformin demo)

**Goal:** one localhost flow without new docking engines.

| Step | Module | Exact calls (via libraries) |
|------|--------|-----------------------------|
| 1.1 | `discovery/drug.py` | `pubchempy.get_compounds(name,"name")`; RDKit canonicalize; `chembl_webresource_client.new_client.molecule.filter(molecule_synonyms__synonym__iexact=name)` or search → ChEMBL ID |
| 1.2 | `discovery/targets.py` | `new_client.mechanism.filter(molecule_chembl_id=CHEMBL…)`; Open Targets POST GraphQL `drug(chemblId:)` → `mechanismsOfAction { rows { mechanismOfAction targets { id approvedSymbol } } }` |
| 1.3 | Map gene → UniProt | `mygene` or `unipressed` mapping Ensembl/symbol → Swiss-Prot accession |
| 1.4 | `discovery/structures.py` | `rcsbsearchapi` text/UniProt search → top PDB ID; download CIF via biotite/Biopython; else `httpx.get(https://alphafold.ebi.ac.uk/api/prediction/{acc})` → `cifUrl` |
| 1.5 | Prep | `pdbfixer` → existing Open Babel/Meeko receptor path; ligand via existing Meeko |
| 1.6 | Dock | Existing `docking/pipeline.py` Vina (optional GNINA) |
| 1.7 | `discovery/pharmacology.py` | Reactome `GET https://reactome.org/ContentService/data/mapping/UniProt/{acc}/pathways?species=9606`; OT `associatedDiseases` for target |
| 1.8 | Cache + UI | SQLite cache; single Jinja/HTMX results panel with citations |

**Do not build in Slice 1:** custom IFP, pocket ML, PlanMine deep integration, DrugBank, DisGeNET, AF3.

**Exact endpoint cheat-sheet (Slice 1):**
```
PubChem:   https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/IsomericSMILES,CanonicalSMILES,MolecularFormula/JSON
           (prefer pubchempy)
ChEMBL:    https://www.ebi.ac.uk/chembl/api/data/mechanism.json?molecule_chembl_id=CHEMBL1431
           (prefer chembl-webresource-client)
Open Targets POST https://api.platform.opentargets.org/api/v4/graphql
UniProt:   https://rest.uniprot.org/uniprotkb/{acc}.json  (prefer unipressed)
RCSB search: via rcsbsearchapi → files https://files.rcsb.org/download/{PDB}.cif
AFDB:      https://alphafold.ebi.ac.uk/api/prediction/{acc}
Reactome:  https://reactome.org/ContentService/data/mapping/UniProt/{acc}/pathways?species=9606
```

### Slice 2 — Orthologs + pockets + IFP

| Step | Libraries | Endpoints / tools |
|------|-----------|-------------------|
| 2.1 | `httpx` Ensembl | `GET https://rest.ensembl.org/homology/symbol/human/{SYMBOL}?type=orthologues;target_taxon={tax}` for 10090,7227,9615,9986,9685 |
| 2.2 | `httpx` OMA | `https://omabrowser.org/api/protein/{id}/orthologs/` ; map planaria via OMA SCHMD when possible |
| 2.3 | PlanMine | InterMine Python client / template `Smed_Orthologous` + BLAST homology for human protein sequence — **label confidence** |
| 2.4 | P2Rank or fpocket | CLI wrap → auto docking box (replacing manual box for demo) |
| 2.5 | `prolif` | Interaction fingerprint table under pose viewer |
| 2.6 | BindingDB | Optional potency context `getLigandsByUniprot` |

### Slice 3 — Comparative proteome cards + hardening

| Step | Work |
|------|------|
| 3.1 | Pre-cache ortholog tables for AMPK / complex I / metformin-relevant genes across the 7 species |
| 3.2 | WikiPathways + Monarch phenotype links; GTEx expression sparklines |
| 3.3 | GtoPdb client (with API key if required) |
| 3.4 | Offline “research pack” export (JSON+CIF+poses) for micropub supplements |
| 3.5 | Attribution page auto-generated from cache provenance |
| 3.6 | Only then consider Boltz-2 / Uni-Dock from the SOTA docking backlog |

---

## E) Planaria realism check (*S. mediterranea*)

**Be honest: planaria ortholog mapping is sparse compared to fly/mouse.**

| Evidence (2026-09-21 live) | Implication |
|----------------------------|-------------|
| UniProt taxon 79327: **1,588** total sequences, **4** Swiss-Prot reviewed | Cannot rely on UniProt ortholog xrefs alone |
| OMA genome **SCHMD**: **29,850** entries | Best programmatic proteome-scale hook, but assembly-era / not identical to newest PlanMine transcripts |
| Ensembl Compara | Standard vertebrate/fly pipelines; **planaria not a first-class Compara species** like mouse/fly — don’t expect `/homology/.../target_taxon=79327` to match fly quality |
| PlanMine | Gold community resource for Smed transcripts, BLAST hits, GO — InterMine API; assembly IDs (`dd_Smed`, `ox_Smed`, SMESG/SMEST) need mapping discipline |
| SmedGD | Retired — do not call |
| PLANA | Anatomy ontology only |
| Evolutionary distance | Lophotrochozoan vs human — even reciprocal-best-hit “orthologs” are **hypothesis generators** for metformin/AMPK-like pathways, not proof of conserved binding sites |

**Recommended Cross Affinity behavior for planaria:**
1. Always show human (and mouse/fly) orthologs first with Ensembl/OMA confidence.
2. For planaria: try OMA SCHMD → if miss, sequence search via PlanMine BLAST / local diamond against PlanMine peptides.
3. UI banner: *“Planaria mappings are sequence-similarity based and may be incomplete; validate with PlanMine and experiment.”*
4. Never auto-dock a planaria “ortholog structure” unless an AF/UniProt accession exists and passes pLDDT gates — most will not.

This still supports Alexander’s metformin×planaria narrative: **human target hypothesis → docking on human structures → tentative planaria gene IDs for RNAi/qPCR follow-up**, which matches how planarian pharmacology papers actually work.

---

## Library manifest (install targets)

```text
# Already in CrossBind spirit
rdkit
meeko
fastapi
httpx
# Slice 1 adds
pubchempy
chembl-webresource-client
unipressed
mygene
rcsbsearchapi
pypdb
biotite
biopython
pdbfixer          # or pdbfixer-wheel if packaging needs wheels
# Slice 2
prolif
MDAnalysis        # prolif dependency stack
gprofiler-official
# Optional / license-aware
bioservices       # GPLv3 aggregator — optional
plip              # GPL-2 — optional CLI, not core import
openbabel-wheel   # if pip obabel bindings preferred over system obabel
```

CLIs (not pip-first): `vina`, `gnina` (optional), `prank` (P2Rank), `fpocket`, system `obabel`.

---

## Sources & live probes (cite)

| Resource | URL | Accessed |
|----------|-----|----------|
| PubChem PUG-REST docs | https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest | 2026-09-21 |
| ChEMBL web services | https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services | 2026-09-21 |
| Open Targets GraphQL | https://platform-docs.opentargets.org/data-access/graphql-api | 2026-09-21 |
| Open Targets API meta | https://api.platform.opentargets.org/ (data 26.06) | 2026-09-21 |
| RCSB Web APIs | https://www.rcsb.org/docs/programmatic-access/web-apis-overview | 2026-09-21 |
| AlphaFold DB API example | https://alphafold.ebi.ac.uk/api/prediction/P54619 | 2026-09-21 |
| Reactome Content Service | https://reactome.org/ContentService/ | 2026-09-21 |
| BindingDB REST | https://www.bindingdb.org/rwd/bind/BindingDBRESTfulAPI.jsp | 2026-09-21 |
| OMA API / SCHMD | https://omabrowser.org/api/genome/SCHMD/ | 2026-09-21 |
| OrthoDB | https://data.orthodb.org/ | 2026-09-21 |
| Ensembl REST homology | https://rest.ensembl.org/documentation/info/homology_symbol | 2026-09-21 |
| PlanMine | https://planmine.mpinat.mpg.de/planmine/ ; user guide | 2026-09-21 |
| SmedGD retired | https://planosphere.stowers.org/smedgd | 2026-09-21 |
| PLANA | https://planosphere.stowers.org/anatomyontology | 2026-09-21 |
| DIOPT API | https://www.flyrnai.org/tools/diopt/web/api | 2026-09-21 |
| DisGeNET commercial vs academic | https://support.disgenet.com/.../do-i-need-a-commercial-license... | 2026-09-21 |
| DrugBank terms | https://trust.drugbank.com/drugbank-trust-center/terms-of-use | 2026-09-21 |
| UniProt REST live counts | https://rest.uniprot.org/ (release 2026_03) | 2026-09-21 |
| PyPI metadata | pubchempy, chembl-webresource-client, unipressed, prolif, pdbfixer, … | 2026-09-21 |
| CrossBind baseline | `/workspace/CrossBind/README.md` | local |

---

## Bottom line

Ship Cross Affinity as a **library-orchestrated local OS**: PubChemPy + ChEMBL client + Open Targets GraphQL + UniPressed/MyGene + RCSB search/fetch + AFDB HTTP + Reactome + Ensembl/OMA orthologs + existing Vina/Meeko/RDKit, with ProLIF and P2Rank next. **Do not scrape; do not reimplement IFPs; do not pretend planaria orthology is solved.** Slice 1 proves the vision with metformin in one UI path this week.
