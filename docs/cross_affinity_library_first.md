# Cross Affinity: library-first dependency catalog

**Research date:** 2026-09-21 (PT)  
**Scope:** mature PyPI/CLI wrappers and engines to call from a local FastAPI drug-discovery OS; prefer wrapping an upstream API/CLI over reimplementing chemistry or structural bioinformatics.

## Executive recommendation

Use a thin adapter layer in FastAPI (`adapters/pubchem.py`, `adapters/chembl.py`, etc.) that normalizes IDs, records the source/version/query, caches responses, and exposes stable Cross Affinity schemas. Keep network calls and heavy CPU jobs out of the request thread: use a task queue/background worker for downloads, P2Rank/fpocket, PLIP, and ADMET-AI inference. Pin versions after a small compatibility test matrix.

**Top 12 for Slice 1–2:**

1. `rdkit` — molecule parsing, canonical SMILES, descriptors, fingerprints (BSD-3-Clause).
2. `pubchempy` — name/CAS/SMILES ↔ PubChem CID and PubChem properties (MIT).
3. `chembl_webresource_client` — ChEMBL molecules, targets, assays, activities (Apache-2.0).
4. `rcsb-api` — supported RCSB PDB search/metadata client (MIT).
5. `biopython` — PDB/mmCIF parsing plus AlphaFold DB lookup/download helpers (Biopython License Agreement; permissive, with some BSD-3-Clause files).
6. `pdbfixer` — missing residues/atoms, alternate locations, heterogens, hydrogens, standardization (MIT).
7. `openmm` — structure/system representation and later minimization or simulation (`openmm.app`; MIT API, platform components have additional terms).
8. `p2rank` — strong pocket-prediction baseline, wrapped as a pinned subprocess (MIT; JDK 17+).
9. `prolif` — Python-native protein–ligand interaction fingerprints (Apache-2.0).
10. `mygene` — gene symbol/Entrez/Ensembl/UniProt annotation and batch queries (BSD).
11. `ensembl-rest` — orthology/homology calls against Ensembl REST (MIT).
12. `admet-ai` — free local ML ADMET predictions for triage (MIT; Python 3.11+).

`bioservices`, `openbabel`, and `plip` are useful but should be optional/isolation-bound in a product whose own distribution cannot accept GPL code. `fpocket`, OrthoDB, OMA, and `useful-rdkit-utils` are optional add-ons rather than Slice 1–2 hard dependencies.

---

## Catalog

### 1. Drug name → CID / SMILES

| Tool | License / install | What it replaces | Fit for local FastAPI |
|---|---|---|---|
| **PubChemPy 1.0.5** (`pubchempy`) | MIT; `python -m pip install pubchempy` (Python >=3.10). Docs: [pubchempy.org](https://docs.pubchempy.org/). | Hand-written PUG REST URL construction, pagination, JSON parsing, name-to-CID resolution, synonym/property retrieval, and SMILES normalization plumbing. | **Excellent Slice 1.** Simple synchronous wrapper; call in a worker or adapter, cache by normalized input, preserve CID and returned canonical/isomeric SMILES. No API key. Treat PubChem rate limits/timeouts as first-class errors. |
| **BioServices** (`bioservices`) | GPLv3; `python -m pip install bioservices`. Docs: [bioservices.readthedocs.io](https://bioservices.readthedocs.io/). | A broad collection of REST/SOAP adapters, including PubChem, UniProt, ChEMBL, PDB/PDBe, Ensembl and many others. | Useful for exploratory breadth, but **not a default core dependency** because GPLv3 and a wide, heterogeneous API surface complicate a commercial/proprietary FastAPI service. Use in an isolated optional worker or choose the focused clients below. |

**Recommended flow:** accept name/CAS/SMILES → PubChemPy resolution → RDKit parse/sanitize → persist `input`, CID, canonical SMILES, isomeric SMILES, InChIKey, source URL, timestamp, and ambiguity candidates. Never silently select among multiple name matches.

### 2. Drug → targets

| Tool | License / install | What it replaces | Fit |
|---|---|---|---|
| **ChEMBL Webresource Client 0.9.13** (`chembl_webresource_client`) | Apache Software License / Apache-2.0; `python -m pip install chembl_webresource_client`. Official client: [github.com/chembl/chembl_webresource_client](https://github.com/chembl/chembl_webresource_client). | ChEMBL REST URL building, filters, field selection, pagination, lazy evaluation, local response caching, and molecule/target/activity joins. | **Excellent Slice 1.** Official ChEMBL client, no local ChEMBL database required. Use `molecule`, `target`, `activity`, and `mechanism` resources; cache and retain ChEMBL release/version. Build a normalized target evidence table rather than presenting every assay row as a target claim. |

### 3. UniProt / gene annotation

| Tool | License / install | What it replaces | Fit |
|---|---|---|---|
| **MyGene 3.2.2** (`mygene`) | BSD (PyPI classifier); `python -m pip install mygene`. Docs: [docs.mygene.info](https://docs.mygene.info/projects/mygene-py/en/latest/). | MyGene.info HTTP calls, query syntax, batching, identifier fields, and optional DataFrame conversion for Entrez/Ensembl symbols and cross-references. | **Excellent Slice 1–2.** Use `MyGeneInfo().query`, `getgene`, and `querymany`; cache by query/species and record returned build/source. Great for gene-centric UX, not a replacement for full UniProt evidence. |
| **BioServices UniProt** (`bioservices.UniProt`) | GPLv3 through `bioservices`; same install as above. | UniProt search, TSV/FASTA retrieval, identifier mapping and endpoint details. | Good breadth and convenient FASTA/mapping helpers, but keep optional for license reasons. For a permissive core, use direct UniProt REST via a small `httpx` adapter or a focused permissive client and keep the same normalized schema. |

### 4. PDB fetch/search and structure parsing

| Tool | License / install | What it replaces | Fit |
|---|---|---|---|
| **rcsb-api 1.7.3** (`rcsb-api`) | MIT; `python -m pip install rcsb-api`. Docs: [rcsbapi.readthedocs.io](https://rcsbapi.readthedocs.io/). | RCSB Search API JSON query construction, HTTP handling, result decoding, and REST endpoint selection. | **Preferred PDB search client.** Current package is the successor direction to `rcsbsearchapi`; use text, attribute, sequence/structure searches and RCSB data APIs. Pin and test because API packages evolve. |
| **rcsbsearchapi 2.0.1** | BSD-3-Clause; `python -m pip install rcsbsearchapi`. | Same search API work as above. | **Compatibility fallback only.** Search results indicate migration toward `rcsb-api`; use it for an existing codebase, not new Cross Affinity code. |
| **PyPDB 2.11** (`pypdb`) | MIT; `python -m pip install pypdb`. | Older RCSB search/PDB-file retrieval wrappers and common BLAST/PFAM/chemical/sequence queries. | Good small wrapper and fallback, but prefer `rcsb-api` for a new integration. Use its current client modules rather than deprecated `get_pdb_file` helpers. |
| **Biopython 1.88** (`biopython`, `Bio.PDB`) | Biopython License Agreement; `python -m pip install biopython`. | PDB/mmCIF parsing, residue/chain/entity traversal, structure writing, and local structural inspection. | **Excellent Slice 1–2.** Use `PDBParser`, `MMCIFParser`, `PDBIO`/`MMCIFIO`, and strict/quiet parsing policy. This is a local parser, not a database search service. |

**Recommended split:** `rcsb-api` for search/metadata/download URLs; Biopython for parsing and canonical internal structure records. Store the original file and a checksum, not only parsed atoms.

### 5. AlphaFold DB download

| Tool / data | License / install | What it replaces | Fit |
|---|---|---|---|
| **Biopython `Bio.PDB.alphafold_db`** | Included in Biopython; `python -m pip install biopython`. AlphaFold DB data is CC-BY-4.0 (check current data-use terms). | Constructing AlphaFold DB URLs/API calls, checking prediction metadata, downloading CIFs, and coupling downloads to a structure parser. | **Best Slice 1 path.** `get_predictions(accession)` retrieves model metadata; `download_cif_for(...)` downloads a prediction; `get_structural_models_for(...)` can retrieve/parse models. Cache by UniProt accession/model version and persist pLDDT/PAE metadata where available. |
| **Direct AlphaFold DB API/files** | No extra library; API endpoint and downloadable files. | — | Use direct HTTP only behind the same adapter if Biopython’s helper lacks a needed field. Validate accession, enforce size/time limits, and label predicted structures separately from experimental PDB structures. |

### 6. Pocket detection

| Tool | License / install | What it replaces | Fit |
|---|---|---|---|
| **P2Rank** | MIT; standalone release from [github.com/rdk/p2rank](https://github.com/rdk/p2rank), requires JDK 17+; typical runtime install is a pinned release archive, then `prank predict -f protein.pdb`. | Implementing geometric/feature-based pocket detection, training/packaging a pocket predictor, ranking pockets, and writing pocket-score output. | **Preferred Slice 2 baseline.** Wrap with `subprocess` in a worker, use an allow-listed executable path (never interpolate user input into a shell string), parse JSON/CSV output, and save the exact model/release. No official PyPI/Python wrapper found. |
| **fpocket / dpocket / mdpocket** | MIT; no first-party PyPI package found. Conda: `conda install -c conda-forge fpocket`; source build: clone repo, `make`, `make install`. CLI example: `fpocket -f structure.pdb`. | Implementing Voronoi tessellation, pocket descriptors, trajectory pocket analysis, and CLI output parsing. | Valuable **optional alternative/ensemble method**. Wrap as a separately installed CLI container/worker. Validate input/output and record fpocket version; do not make it a Python wheel dependency. |
| **Python wrappers** | No mature official wrapper found in the search. Third-party projects such as PredictBind/wtfdtb exist but need independent maintenance/security review. | — | Prefer a small Cross Affinity subprocess adapter over adopting an unverified wrapper. |

**Pocket policy:** report pockets as hypotheses, not binding truth. Keep P2Rank/fpocket scores, coordinates, residues, source structure, and method/version so results can be compared.

### 7. Structure preparation

| Tool | License / install | What it replaces | Fit |
|---|---|---|---|
| **PDBFixer 1.12.0** (`pdbfixer`) | MIT; `python -m pip install pdbfixer` (or `conda install -c conda-forge pdbfixer`). | Missing-residue/atom detection and repair, alternate-location handling, nonstandard residue replacement, heterogen removal, hydrogen addition, and solvent/ion setup boilerplate. | **Excellent Slice 1–2.** Use its Python API in a worker; retain the input/output file and a change log. Avoid automatic choices without recording pH, force-field assumptions, removed ligands, and added atoms. |
| **OpenMM 8.x** (`openmm`, `openmm.app`) | MIT for the public API; `python -m pip install openmm` (CUDA extras/platforms have additional licensing/runtime terms). | Low-level topology/trajectory handling, force-field system construction, minimization, and simulation orchestration. | **Excellent companion**, especially if Slice 2 includes restrained minimization or local relaxation. `openmm.app` is also useful for reading/writing prepared structures. Do not claim PDBFixer alone provides a validated docking-ready receptor. |
| **Open Babel 3.2.1** (`openbabel`) | GPL-2.0-only; official wheels: `python -m pip install openbabel`; CLI is `obabel`. | Format conversion, protonation/charge helpers, hydrogenation, ligand 3-D conversion, and cheminformatics file interoperability. | Technically very useful but **license-sensitive**. Keep as an optional CLI worker/container if GPL-2.0 is incompatible with Cross Affinity distribution. `openbabel-wheel` is an older unofficial alternative; prefer official wheels/current docs. |

### 8. Interactions

| Tool | License / install | What it replaces | Fit |
|---|---|---|---|
| **ProLIF 2.2.2** (`prolif`) | Apache-2.0; `python -m pip install rdkit prolif` (or `conda install -c conda-forge prolif`). Docs: [prolif.readthedocs.io](https://prolif.readthedocs.io/). | Writing atom/residue geometric interaction rules, trajectory iteration, fingerprints, and interaction DataFrame/visualization plumbing. | **Preferred Slice 2 interaction engine.** Python-native and supports H-bonds, hydrophobic, ionic, pi-stacking, cation-pi, metal, halogen and van der Waals contacts. Feed prepared receptor/ligand structures and retain fingerprint parameters. |
| **PLIP 3.x** (`plip`) | GPL-2.0-only; `python -m pip install plip`; requires Open Babel >=3 and bindings; CLI examples `plip -f structure.pdb` or `plip -i 1vsn`. | Rule-based protein–ligand interaction detection, report generation, XML/JSON-like output, and visualization helpers. | Mature and useful as an **optional corroborating engine**, but GPL-2.0 and Open Babel make it a poor hard dependency for a proprietary service. Isolate as a container/worker and normalize its output beside ProLIF; do not combine scores without method provenance. |

### 9. Orthologs

| Tool | License / install | What it replaces | Fit |
|---|---|---|---|
| **ensembl-rest 0.3.4** (`ensembl-rest`) | MIT; `python -m pip install ensembl-rest`. | Ensembl REST URL/headers, homology endpoint calls, parameter encoding, and response parsing. | **Preferred Slice 2 orthology client** for species supported by Ensembl. Use `/homology/symbol/:species/:symbol` or `/homology/id/:species/:id` with `type=orthologues`, target species/taxon, and explicit release/build metadata. |
| **OrthoDB Python package / OrthoDB-py** (`orthodb`) | Current PyPI `orthodb` search result reports MIT; install `python -m pip install orthodb` (or `pipx install orthodb`; verify package identity/version before pinning). OrthoDB REST supports `/search`, `/genesearch`, `/orthologs`, `/fasta`, `/species`. | OrthoDB version selection, search, ortholog/fasta requests, pagination, and response decoding. | Good optional source when Ensembl coverage or orthology definitions differ. **Confirm the package is the official OrthoDB-py project**, not the older similarly named `orthodb-cli`; pin the exact release and record OrthoDB version (for example v12). |
| **PyOMADB 2.2.x** (`omadb`) | LGPLv3; `python -m pip install omadb`. Docs: [pyomadb](https://dessimozlab.github.io/pyomadb/build/html/). | OMA Browser REST calls, batching/cache options, protein/HOG information and OMA orthology access. | Useful alternative/validation source; LGPLv3 requires legal review but is generally easier to isolate than GPL. The client is not a substitute for harmonizing species IDs and orthology confidence across databases. |
| **pyensembl** | Apache-2.0; `python -m pip install pyensembl`. | Local Ensembl GTF/FASTA indexing and gene/transcript coordinate lookups. | Helpful for local gene context, **not an ortholog REST client**. Use only if Cross Affinity needs pinned local reference releases. |

### 10. ADMET

| Tool | License / install | What it replaces | Fit |
|---|---|---|---|
| **RDKit descriptors** (`rdkit.Chem.Descriptors`) | BSD-3-Clause; `python -m pip install rdkit`. | Implementing molecular-weight, logP-related/basic counts, H-bond counts, rotatable-bond, ring, charge, and fingerprint/descriptors from scratch. | **Mandatory Slice 1.** Use `Descriptors.CalcMolDescriptors` plus explicit descriptor allow-lists; store RDKit version and sanitization outcome. These are calculated descriptors, not ADMET predictions. |
| **useful-rdkit-utils 2.x** (`useful_rdkit_utils`) | MIT; `python -m pip install useful_rdkit_utils` (optional extras: `useful_rdkit_utils[all]`). | Reusable descriptor/fingerprint/property utilities, Rule-of-Five calculations, dataset comparisons and convenience CLI/Jupyter routines. | Good ergonomic add-on after RDKit. Do not make it a hard dependency until the exact API and descriptor definitions are pinned; core product logic should call RDKit directly. |
| **ADMET-AI 2.0.1** (`admet-ai`) | MIT, free/open source; `python -m pip install admet-ai` (Python >=3.11; optional web extra: `python -m pip install 'admet-ai[web]'`). CLI: `admet_predict`. | Packaging/training/inference plumbing for a multi-endpoint ADMET ML model and local batch prediction. | **Good Slice 2 triage service** if the deployment can accept its model/dependency footprint. Run in a worker, batch SMILES, cache model/version and output uncertainty/endpoint names. Clearly label as computational prioritization—not clinical, regulatory, or experimental evidence. |

---

## License and deployment notes

- **Permissive core:** RDKit (BSD-3), PubChemPy (MIT), ChEMBL client (Apache-2.0), `rcsb-api` (MIT), Biopython (permissive Biopython license), PDBFixer (MIT), OpenMM API (MIT), ProLIF (Apache-2.0), MyGene (BSD), `ensembl-rest` (MIT), and ADMET-AI (MIT).
- **Legal-review/optional boundary:** BioServices and PLIP are GPL; Open Babel is GPL-2.0-only; OMA client is LGPLv3. A subprocess/container boundary does not automatically settle all licensing questions—have counsel review the intended distribution and linking model.
- Upstream **data licenses and terms are separate from package licenses**: PubChem, ChEMBL, UniProt, RCSB PDB, AlphaFold DB, Ensembl, OrthoDB and OMA each have attribution, rate-limit, redistribution, and/or data-use rules. Store source, release, query, timestamp, and attribution metadata.
- Do not expose arbitrary shell execution through FastAPI. For CLI tools, pass an argument array, allow-list binaries, use a temporary job directory, impose CPU/RAM/time/output limits, and inspect output before persistence.

## Slice plan

### Slice 1: identity, annotation, and reproducible structure intake

- RDKit; PubChemPy; ChEMBL client; MyGene.
- `rcsb-api` + Biopython for search/download/parse.
- Biopython AlphaFold DB helper for UniProt accession → predicted CIF.
- PDBFixer for a logged, reversible preparation step.
- Use direct UniProt/Ensembl REST adapters where the focused package is more permissive than BioServices.

### Slice 2: structural hypotheses and triage

- OpenMM for topology/minimization where needed.
- P2Rank subprocess for pocket ranking; add fpocket as a second method if benchmarking justifies it.
- ProLIF for normalized interaction fingerprints; optionally compare with isolated PLIP.
- `ensembl-rest` first; add OrthoDB/OMA when cross-database orthology evidence is needed.
- ADMET-AI for local batch triage plus RDKit descriptors; present uncertainty and model/version provenance.

## Sources checked

- [PubChemPy PyPI/docs](https://pypi.org/project/pubchempy/) · [BioServices PyPI/docs](https://pypi.org/project/bioservices/) · [ChEMBL client PyPI/GitHub](https://pypi.org/project/chembl_webresource_client/)
- [MyGene PyPI/docs](https://pypi.org/project/mygene/) · [RCSB API docs/PyPI](https://rcsbapi.readthedocs.io/) · [PyPDB PyPI](https://pypi.org/project/pypdb/) · [Biopython PyPI/Bio.PDB](https://www.pypi.org/project/biopython)
- [AlphaFold DB](https://www.alphafold.ebi.ac.uk/) · [fpocket](https://github.com/Discngine/fpocket) · [P2Rank](https://github.com/rdk/p2rank)
- [PDBFixer PyPI](https://pypi.org/project/pdbfixer/) · [OpenMM docs](https://docs.openmm.org/latest/) · [Open Babel docs/PyPI](https://openbabel.org/docs/)
- [ProLIF PyPI/docs](https://prolif.readthedocs.io/) · [PLIP PyPI/GitHub](https://pypi.org/project/plip/)
- [OrthoDB user guide](https://www.ezlab.org/orthodb_userguide) · [PyOMADB docs/PyPI](https://dessimozlab.github.io/pyomadb/build/html/) · [Ensembl REST](https://rest.ensembl.org/documentation/)
- [RDKit PyPI/docs](https://www.rdkit.org/docs/) · [useful-rdkit-utils](https://useful-rdkit-utils.readthedocs.io/) · [ADMET-AI PyPI/GitHub](https://pypi.org/project/admet-ai/)
