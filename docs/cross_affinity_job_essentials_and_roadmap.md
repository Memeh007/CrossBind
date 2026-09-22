# Cross Affinity — Per-Job Essentials, Competitor Patterns & Roadmap

**Researched:** 2026-09-21 (PT) via live web search + page fetches  
**Product context:** Cross Affinity / CrossBind — local FastAPI docking + Discover (drug→targets→PDB/AF→auto-box→Vina), 3D viewer, ortholog stubs  
**Goal:** What a SOTA *local / pre-wet-lab* drug-discovery web app **must** capture and display on every docking/study job, plus a concrete `result.json` / `discovery.json` schema to implement now  
**Constraint:** Evidence-based only; no fabricated product claims. Cross Affinity is **not** Munroe Lab software and does **not** claim ICM/Glide/FEP equivalence (existing CrossBind README disclaimer).

**Companion docs:** `cross_affinity_discovery_os_blueprint.md`, `cross_affinity_sota_docking_landscape_2026.md`, `cross_affinity_library_first.md`

---

## Executive takeaway

Every job card must answer, at a glance:

1. **What ligand?** (preferred name + CID/ChEMBL + SMILES/InChIKey)  
2. **What protein?** (gene + UniProt + organism + short name)  
3. **What structure?** (PDB vs AlphaFold vs upload; resolution / pLDDT; path)  
4. **How docked?** (engine, box, exhaustiveness, seed if available)  
5. **What scored?** (top affinity + pose table; optional RMSD / CNN / IFP)  
6. **How honest?** (disclaimer flags: not clinical, score ≠ experimental ΔG, AF ≠ crystal)

Industry tools converge on a **named session/hitlist row** with ligand identity, receptor identity, sortable numeric scores, pose/model toggle, and exportable provenance — not anonymous UUIDs alone.

---

## A) Per-job identity fields (must-have metadata schema)

### A1. Job / session identity (card header)

| Field | Why it is must-have | Evidence |
|-------|---------------------|----------|
| `job_id` | Stable local handle under `data/jobs/<id>/` | CrossBind already uses this layout (`SECURITY.md`, `pipeline.py`) |
| `job_title` | Human title: `ligand × GENE (UniProt) · PDB\|AF id` | CrossBind `job_identity.build_job_title`; DockThor requires a user **Job name** plus auto id ([DockThor Tutorial 1](https://dockthor.lncc.br/v2/tutorials/Tutorial1_1HPV.pdf)); Benchling sessions require immutable user-facing `name` ([App Status docs](https://docs.benchling.com/docs/introduction-to-app-status)) |
| `status` | `queued` / `running` / `completed` / `failed` (+ optional `completed_with_warnings`) | Benchling session statuses: RUNNING, SUCCEEDED, FAILED, TIMEOUT, COMPLETED_WITH_WARNINGS; CrossBind today: queued/running/completed/failed |
| `source` | `discover` \| `manual` \| `batch` | Distinguishes Discover vs upload path (already started in CrossBind `api_discover_dock`) |
| `started_at` / `finished_at` | ISO-8601 timestamps | Benchling `createdAt` / `modifiedAt`; CrossBind `pipeline.py` |
| `messages` / log pointer | Latest user-facing step + full `job.log` | Benchling messages (INFO/SUCCESS/WARNING/ERROR); SeeSAR Message Center for remote runs ([SeeSAR changelog](https://www.biosolveit.de/products/seesar/changelog/)) |

### A2. Ligand identity

| Field | Must? | Notes / sources |
|-------|-------|-----------------|
| `compound_name` (preferred / input name) | **Yes** | SeeSAR editable Name column ([First Aid](https://www.biosolveit.de/products/seesar/help/)); DockThor `bestranking.csv` keeps original filename + molecule name ([Tutorial 1](https://dockthor.lncc.br/v2/tutorials/Tutorial1_1HPV.pdf)); SwissADME requires name or auto-tags ([Help](https://www.swissadme.ch/help.php)) |
| `smiles` (canonical) | **Yes** | Prep + reproducibility; Meeko PDBQT embeds SMILES for safe SDF export ([Vina basic docking](https://autodock-vina.readthedocs.io/en/latest/docking_basic.html)) |
| `inchikey` | Strongly recommended | Dedup / cross-DB |
| `cid` (PubChem) | Strongly recommended | Discover path already resolves via PubChem |
| `chembl_id` | Strongly recommended | Mechanisms / Open Targets linkage |
| `molecular_formula`, `iupac_name` | Nice | Already in CrossBind `ligand_block` |
| `charge` / prep notes (pH, tautomer) | Recommended | Vina docs warn protonation can decide success ([basic docking](https://autodock-vina.readthedocs.io/en/latest/docking_basic.html)); DockThor Add H @ pH 7.4 |

### A3. Protein identity

| Field | Must? | Notes / sources |
|-------|-------|-----------------|
| `gene` (approved symbol) | **Yes** | Card title; Open Targets `approvedSymbol` ([OT GraphQL](https://platform-docs.opentargets.org/data-access/graphql-api)) |
| `uniprot` (accession) | **Yes** | Structure + ortholog key; Munroe-style LIMS protein library stores `accession`, `name`, `organism`, `source` (`custom-lab-lims-web/db.py`) |
| `protein_name` (recommended UniProt name) | **Yes** | Hitlist readability (ICM hitlist is chemical spreadsheet of named ligands against a named project receptor — [ICM hitlist guide](https://molsoft.com/gui/view-dock-results.html)) |
| `organism` / `taxon_id` | **Yes** | Ortholog honesty; Cross Affinity planaria/fly/mouse workflow |
| `ensembl_id` | Recommended | Open Targets target key |
| `function` (short UniProt blurb) | Recommended for dossier | UniProt `cc_function` / REST fields ([UniProt API help](https://www.uniprot.org/help/api_queries)) |
| `mechanism` (curated MoA string for this drug×target) | Recommended | From ChEMBL / Open Targets — label as curated association, not proof of binding |

### A4. Structure provenance

| Field | Must? | Notes / sources |
|-------|-------|-----------------|
| `provenance` | **Yes** | Enum: `experimental_pdb` \| `alphafold_db` \| `user_upload` \| `ensemble` — CrossBind already uses this |
| `label` | **Yes** | UI badge: `experimental` / `predicted` / `uploaded` |
| `pdb_id` **or** `alphafold_id` / `structure_id` | **Yes** | Never leave blank when a structure was used |
| `method` (X-ray / EM / NMR / AF) | Recommended | RCSB entry `experimental_method` ([RCSB Data API](https://data.rcsb.org/)) |
| `resolution_A` | Recommended for PDB | Ranking / honesty |
| `plddt_mean` (+ optional site pLDDT) | **Yes if AF** | Refuse silent docking on low confidence (blueprint decision tree) |
| `path` (local file) | **Yes** | Job-local copy preferred |
| `holo_ligand` (HET / name) if present | Recommended | Enables redock RMSD & auto-box from crystal ligand (DockThor redock workflow; CrossBind RMSD helper exists) |
| `warning` | **Yes when applicable** | AF pocket uncertainty, blind box, missing side chains, etc. |

### A5. Docking parameters (reproducibility block)

Mirror what Vina prints and what DockThor stores in `parameters.txt`:

| Field | Source |
|-------|--------|
| `engine` (`vina` / `gnina` / future) | CrossBind |
| `scoring` (`vina` / `vinardo` / `ad4` / `cnn`) | [Vina docs](https://autodock-vina.readthedocs.io/en/latest/docking_basic.html) |
| `center` `[x,y,z]`, `size` `[sx,sy,sz]` (Å) | Vina config; Meeko `--box_*` |
| `exhaustiveness`, `num_modes`, `energy_range` | [Vina manual](https://vina.scripps.edu/manual/) |
| `cpu`, `random_seed` (if captured) | Vina stdout |
| `pocket_method` | e.g. `crystal_ligand_centroid`, `protein_centroid`, `user`, `p2rank` |
| `receptor_prep`, `ligand_prep` tool versions | Meeko / Open Babel / pdbfixer strings |

### A6. Scores & poses

Minimum pose row (Vina / PyRx / ChimeraX ViewDockX):

| Field | Notes |
|-------|-------|
| `mode` | 1-based rank |
| `affinity` (kcal/mol) | More negative ≈ better rank **within same scoring function** |
| `rmsd_lb`, `rmsd_ub` | Distance from best mode ([Vina output table](https://autodock-vina.readthedocs.io/en/latest/docking_basic.html); PyRx Analyze Results) |
| Optional GNINA | `gnina_cnn_score`, `gnina_cnn_affinity` as **separate** fields (CrossBind README) |
| Optional redock | `rmsd_to_reference` (Å) when holo ref ligand provided (DockThor; CrossBind `rmsd.py`) |
| Optional physics terms | ICM exposes Hbond, Hphob, VwInt, Eintl, RTCNN, RecConf ([ICM hitlist](https://molsoft.com/gui/view-dock-results.html)) — **do not invent** these for Vina |

**Honesty rule (must display near scores):** Vina/GNINA scores are **not** comparable to ICM Score, Glide `r_i_docking_score`, or experimental ΔG/Kd (CrossBind README; ICM FAQ notes score units/thresholds are receptor-dependent — [ICM FAQ-Docking](https://molsoft.com/gui/faq-docking.html)).

### A7. Species / ortholog context

| Field | Purpose |
|-------|---------|
| `query_species` | Usually human (9606) for primary dock |
| `orthologs[]` | gene, uniprot, taxon, identity%, source (Ensembl/OMA/PlanMine), `confidence` |
| `docked_species` | If this job docked mouse/fly/planaria structure |
| `mapping_method` | `ensembl_compara` \| `oma` \| `blast_planmine` \| `diopt` — UI must say when planaria is BLAST-only |

### A8. Honesty / disclaimer flags (required on every card)

Align with blueprint §C and Discover payload `honesty` object:

```json
"honesty": {
  "not_medical_advice": true,
  "computational_hypotheses": true,
  "score_not_experimental_affinity": true,
  "structure_is_predicted": false,
  "ortholog_not_identical_pharmacology": true,
  "message": "Research triage only — not clinical advice. Docking scores are engine-specific ranks, not measured Kd/IC50."
}
```

Set `structure_is_predicted: true` whenever `provenance == alphafold_db`.

---

## B) What commercial / academic tools show on a session or pose card

Patterns to **steal** (documented behavior only).

### B1. SeeSAR (BioSolveIT)

- **Pose / molecule table:** estimated affinities (HYDE range), user SDF property columns, sortable headers, editable molecule **Name**, export SDF/XLSX ([Beginner’s Guide](https://www.biosolveit.de/wp-content/uploads/2021/05/BeginnersGuide_SeeSAR_11.pdf); [First Aid](https://www.biosolveit.de/products/seesar/help/)).
- **3D meaning:** per-atom HYDE spheres, torsion labels, interaction highlighting ([Visualization academy](https://www.biosolveit.de/application-academy/visualization-and-3d-export/)).
- **Session:** Save Project As…; remote docking progress + Message Center ([changelog](https://www.biosolveit.de/products/seesar/changelog/)).
- **2026 SeeSAR 15 Apollo:** multi-template docking; **originating template** shown in Template/Reference panel and 2D title — template **traceability** on each pose ([Apollo page](https://www.biosolveit.de/products/seesar/seesar-15-apollo/); changelog).
- **Steal:** named rows, affinity + ADME columns, template/structure provenance on the pose, project persistence.

### B2. Schrödinger Maestro / LiveDesign

- LiveReport outputs include **docked poses** (with optional surface) and **docking scores** as columns ([KNIME “Docking and protein surface”](https://nodepit.com/workflow/com.knime.hub/Users/schroedinger/LiveDesign_models/Docking/Docking%20and%20protein%20surface)).
- **Ensemble docking** reports which binding-site conformation scored best + corresponding pose ([Ensemble docking workflow](https://nodepit.com/workflow/com.knime.hub/Users/schroedinger/LiveDesign_models/Docking/Ensemble%20docking)).
- API helpers: `write_result_row(...)` builds a result dict with ligand/protein files, status, optional **strain**, reference-ligand flag; `create_lid` builds a **LID** image per pose; mapping UI supports **pose names** ([ld_glide_utils 2026-2](https://learn.schrodinger.com/public/python_api/2026-2/api/schrodinger.application.livedesign.ld_glide_utils.html); [mapping_widgets](https://learn.schrodinger.com/public/python_api/2026-2/api/schrodinger.application.livedesign.mapping_widgets.html)).
- Glide PV recognition in ChimeraX requires `r_i_docking_score` descriptor ([ViewDockX](https://www.cgl.ucsf.edu/chimerax/docs/user/tools/viewdockx.html)).
- **Steal:** corporate/ligand ID + pose name + score column + 2D LID thumbnail + receptor file pairing + ensemble “which receptor won”.

### B3. ICM (Molsoft)

- Project files: `PROJECTNAME_LIGANDNAME.ob`, stacks `.cnf`, VLS `PROJECTNAME_answers*.ob` ([Display & Analyze](https://molsoft.com/gui/view-dock-results.html)).
- **Hitlist columns (VLS):** IX, **Score**, Natom, Nflex, Hbond, Hphob, VwInt, Eintl, Dsolv, SolEl, mfScore, **RTCNN**, **RecConf** (receptor conformation index for 4D/ensemble).
- UI: checkbox to display pose, double-click load, Pretty View, pocket skin, atom energies, clash volumes; Convert To Standalone Hitlist / Save Project `.icb`.
- **Steal:** dense score breakdown *when the engine provides it*; ensemble receptor index; standalone shareable hitlist; never claim Vina equals ICM Score ≈ −32 heuristic.

### B4. PyRx + AutoDock Vina

- Analyze Results table: **binding affinity (kcal/mol)**, **RMSD lower/upper** vs best mode; sort by column header ([PyRx tutorial](https://stemskillslab.com/pyrx-tutorial-molecular-docking/); [PyRx FAQ](https://pyrx.sourceforge.io/faq/); [Vina basic docking](https://autodock-vina.readthedocs.io/en/latest/docking_basic.html)).
- PyRx 0.9.5 added **RMSD from reference structure** for AutoDock results ([release note](https://pyrx.sourceforge.io/pyrx-095-release-announcement/)).
- **Steal:** compact pose table identical to Vina stdout; redock RMSD column when ref exists.

### B5. DockThor (LNCC web server)

- Explicit **protein / ligand / cofactor** lists with filenames; **Job name** + email; grid + GA params persisted to `parameters.txt`.
- Results table: GA run, cluster model, **Score** (DockTScore), **Total Energy**, **RMSD vs reference** *or* Intermolecular Energy ([Tutorial 1 PDF](https://dockthor.lncc.br/v2/tutorials/Tutorial1_1HPV.pdf)).
- Downloads: `bestranking.csv` with original filenames + molecule names; mapfile.csv maps random server IDs → originals.
- **Steal:** never lose ligand/protein **display names** behind random IDs; parameters artifact; optional redock RMSD analysis step.

### B6. ChimeraX ViewDockX (+ sessions)

- Table: show checkboxes, **RATING** (stars), **ID**, plus all descriptors from input (names, scores); search; Graph/Plot; **Add HBonds** / **Add Clashes** columns; Save Mol2 with ratings ([ViewDockX docs](https://www.cgl.ucsf.edu/chimerax/docs/user/tools/viewdockx.html)).
- Session (`.cxs`) saves ViewDockX table status including checked rows.
- Supports Vina PDBQT, Glide MAE (needs docking score descriptor), GOLD, MOE, SwissDock, DOCK mol2.
- **Steal:** star rating / triage tags; H-bond & clash counts as computed columns; session restore of which pose was inspected.

### B7. Benchling compute / App Status (workflow UX, not a docking engine)

- **Session** = named unit of work with timeout, status enum, immutable message log; canvas shows status + latest message ([App Status](https://docs.benchling.com/docs/introduction-to-app-status)).
- Async tasks: poll task id until not RUNNING; result metadata available temporarily ([SDK TaskService](https://benchling.com/sdk-docs/1.24.0/benchling_sdk.services.v2.stable.task_service.html)).
- **Steal:** user-visible **job name**, terminal status including “completed with warnings”, chronological messages — map 1:1 onto Cross Affinity job cards.

### B8. Munroe Lab LIMS (local reference UX — protein chooser)

Observed in workspace Munroe / Custom Lab LIMS (not a published docking SaaS paper):

- **Proteins module:** UniProt search/fetch + RCSB download into a library with `accession`, `name`, `organism`, `source`, `local_path` (`custom-lab-lims-web/db.py`, `/proteins` routes).
- **Docking UI:** combo **Target Receptor (PDB)** from protein library; PubChem name→SMILES; interactive coordinate picker / auto-detect pocket from native ligand; log shows compound name + affinity (`custom-lab-lims-ref/lab_tools.py`, `USAGE.txt`).
- CrossBind README explicitly: product is **not** Munroe Lab software — reuse the **chooser pattern** (library + UniProt/PDB resolve + named receptor), not branding.

**Steal for “Munroe-Lab-like universal target selection”:**

1. Search UniProt by gene/name/accession → preview organism + function.  
2. Optionally pin PDB id or accept recommended structure.  
3. Persist selection into job as full protein + structure blocks (not filename alone).  
4. Same chooser works for Discover targets, manual dock, and (later) ortholog species switch.

---

## C) Prioritized UX — next 2–3 slices after protein picker + named jobs

Assume **Slice N** already shipping: protein chooser + `job_title` / ligand×protein identity on cards (CrossBind `job_identity.py` + Discover `selected_protein`).

### Slice N+1 — Target dossier + multi-structure picker (highest leverage)

| Item | Priority | Why | Implementation sketch |
|------|----------|-----|------------------------|
| **Target dossier** | P0 | Users need “what is this protein?” without leaving the job | UniProt function + GO via REST/`unipressed`; diseases + tractability via Open Targets GraphQL `target(ensemblId:)` ([OT docs](https://platform-docs.opentargets.org/data-access/graphql-api)); Reactome pathways (blueprint A5). Cache 7–30 d. |
| **Multi-PDB / ensemble picker** | P0 | Single auto-pick hides bad structures; commercial tools expose ensembles (SeeSAR multi-template; LiveDesign ensemble; ICM RecConf) | List PDB hits for UniProt (resolution, method, HET ligands); user picks 1…k; store `structures[]` + `selected_structure_id`; optional later: dock all, keep best score + `winning_structure_id` (LiveDesign pattern). |
| Named job card polish | P0 | Already partial | Ensure `api_discover_dock` merges `identity_from_discovery` into `result.json` (today meta is thinner than `job_identity` can provide). |

### Slice N+2 — Batch ligands + redock RMSD + IFP

| Item | Priority | Why | Implementation sketch |
|------|----------|-----|------------------------|
| **Batch ligands vs one target** | P1 | PyRx / DockThor / LiveDesign VS is the default medchem expectation | One `study_id` parent; N child jobs sharing protein/structure/box; study table sorted by top affinity; DockThor-style `bestranking` export. |
| **Redock RMSD when holo PDB** | P1 | Credibility control; DockThor & PyRx teach this | If structure has reference ligand, auto-compute `rmsd_to_reference` for pose 1 (CrossBind `rmsd.py` already); badge pass/fail vs 2.0 Å literature heuristic (cite as *common benchmark*, not guarantee). |
| **Interaction fingerprints (ProLIF)** | P1 | Interpretable pose card beyond a single number | Wrap `prolif` (Apache-2.0): default interactions Hydrophobic, HBDonor, HBAcceptor, PiStacking, Anionic, Cationic, CationPi, PiCation, VdWContact; store compact IFP matrix + top residue hits; optional lignetwork/3D later ([ProLIF docking tutorial](https://prolif.readthedocs.io/en/latest/notebooks/docking.html)). Prefer Meeko SDF export over naive PDBQT→SDF. |

### Slice N+3 — ADMET triage + species docking

| Item | Priority | Why | Implementation sketch |
|------|----------|-----|------------------------|
| **ADMET triage** | P2 | SeeSAR adds ADME columns; SwissADME one-panel-per-molecule is the open reference UX | Start with **local RDKit** drug-likeness (Lipinski/Veber-style counts) + optional SwissADME-like radar fields computed locally; link-out or optional API to ADMETlab 3.0 (119 endpoints: physchem, medchem, ADME, toxicity — [NAR 2024 ADMETlab 3.0](https://doi.org/10.1093/nar/gkae236)) with clear “prediction” labels. Do not block docking on Lipinski fails ([SwissADME Help](https://www.swissadme.ch/help.php) frames rules as estimates). |
| **Species / ortholog docking** | P2 | Planaria/fly/mouse translational story | From ortholog panel: “Dock ortholog…” creates job with `docked_species`, mapped UniProt/structure, same ligand; show identity% + mapping_method banner. Planaria: OMA SCHMD / PlanMine with low-confidence flag (blueprint A6). |

### Explicit non-goals for these slices

- Claiming Glide/ICM/FEP-level affinity.  
- Shipping DrugBank/DisGeNET dumps.  
- Silent AF docking without pLDDT warnings.  
- Building custom H-bond detectors (use ProLIF/PLIP).

---

## D) Concrete JSON schema to implement now

Two files per Discover→dock job (already written by CrossBind):

- `data/jobs/<job_id>/discovery.json` — full Discover payload (inputs + dossier stubs)  
- `data/jobs/<job_id>/result.json` — docking run state + scores + **identity**  

Below is a **forward-compatible** schema. Fields marked ★ are required for the next UI cut; others may be `null` / omitted until their slice ships.

### D1. `result.json` (docking job card source of truth)

```json
{
  "$schema_comment": "Cross Affinity result.json v1 — implement now",
  "id": "20260921_205400_ab12cd34",
  "job_title": "metformin × GPD2 (P43304) · PDB 5Z62",
  "status": "completed",
  "source": "discover",
  "started_at": "2026-09-22T03:54:00+00:00",
  "finished_at": "2026-09-22T03:54:42+00:00",

  "ligand": {
    "compound_name": "metformin",
    "cid": 4091,
    "chembl_id": "CHEMBL1431",
    "smiles": "CN(C)C(=N)NC(=N)N",
    "inchikey": "XZWYZXLIPXDALR-UHFFFAOYSA-N",
    "molecular_formula": "C4H11N5",
    "iupac_name": null
  },

  "protein": {
    "gene": "GPD2",
    "uniprot": "P43304",
    "protein_name": "Glycerol-3-phosphate dehydrogenase, mitochondrial",
    "organism": "Homo sapiens",
    "taxon_id": 9606,
    "ensembl_id": null,
    "function": "Short UniProt function blurb…",
    "pdb_id": "5Z62",
    "alphafold_id": null,
    "structure_id": "5Z62",
    "provenance": "experimental_pdb",
    "label": "experimental",
    "method": "X-RAY DIFFRACTION",
    "resolution_A": 1.85,
    "plddt_mean": null,
    "path": "upload_receptor.pdb",
    "holo_ligand": null,
    "warning": null
  },

  "mechanism": "…curated MoA string or null…",

  "docking": {
    "engine": "vina",
    "scoring": "vina",
    "center": [12.0, 8.0, 5.0],
    "size": [22.0, 22.0, 22.0],
    "exhaustiveness": 8,
    "num_modes": 9,
    "energy_range": 3,
    "cpu": 0,
    "random_seed": null,
    "pocket_method": "crystal_ligand_centroid",
    "receptor_prep": "meeko|obabel|pdbfixer",
    "ligand_prep": "meeko"
  },

  "scores": {
    "vina_affinity": -7.2,
    "gnina_cnn_score": null,
    "gnina_cnn_affinity": null,
    "rmsd_to_reference": null,
    "units_note": "kcal/mol for vina_affinity; not comparable to ICM/Glide/experimental ΔG"
  },

  "poses": [
    {
      "mode": 1,
      "affinity": -7.2,
      "rmsd_lb": 0.0,
      "rmsd_ub": 0.0
    },
    {
      "mode": 2,
      "affinity": -6.8,
      "rmsd_lb": 1.2,
      "rmsd_ub": 2.4
    }
  ],

  "interactions": null,

  "ortholog_context": {
    "query_species": "human",
    "docked_species": "human",
    "orthologs_ref": "see discovery.json orthologs"
  },

  "study": {
    "study_id": null,
    "batch_index": null,
    "batch_total": null
  },

  "ensemble": {
    "members": null,
    "winning_structure_id": null
  },

  "admet": null,

  "honesty": {
    "not_medical_advice": true,
    "computational_hypotheses": true,
    "score_not_experimental_affinity": true,
    "structure_is_predicted": false,
    "ortholog_not_identical_pharmacology": true,
    "message": "Research triage only — not clinical advice. Docking scores are engine-specific ranks, not measured Kd/IC50."
  },

  "files": {
    "receptor_pdbqt": "receptor.pdbqt",
    "ligand_pdbqt": "ligand.pdbqt",
    "poses": "poses.pdbqt",
    "poses_sdf": null,
    "log": "job.log",
    "discovery": "discovery.json"
  },

  "error": null,

  "compound_name": "metformin"
}
```

**Compatibility notes for implementers:**

- Keep top-level `compound_name`, `engine`, `center`, `size`, `vina_affinity`, `poses` temporarily if existing templates read them — but **UI should prefer** `ligand` / `protein` / `scores` / `job_title`.  
- On Discover dock create, call `identity_from_discovery(payload)` and merge into meta **before** queue (gap in current `api_discover_dock`).  
- Pose objects should always include `rmsd_lb` / `rmsd_ub` when Vina provides them (`vina.py` parse path).

### D2. `interactions` object (when ProLIF slice lands)

```json
"interactions": {
  "tool": "prolif",
  "tool_version": "x.y.z",
  "vicinity_cutoff_A": 6.0,
  "types": ["Hydrophobic", "HBDonor", "HBAcceptor", "PiStacking", "Anionic", "Cationic", "CationPi", "PiCation", "VdWContact"],
  "by_pose": {
    "1": [
      {"residue": "ASP129.A", "type": "HBDonor", "distance_A": 3.02},
      {"residue": "PHE330.B", "type": "Hydrophobic", "distance_A": null}
    ]
  },
  "tanimoto_to_pose1": [1.0, 0.30]
}
```

(Structure mirrors ProLIF `fp.ifp` / dataframe export — [tutorial](https://prolif.readthedocs.io/en/latest/notebooks/docking.html).)

### D3. `discovery.json` (extend current Discover payload)

```json
{
  "$schema_comment": "Cross Affinity discovery.json v1",
  "drug": {
    "input": "metformin",
    "name": "metformin",
    "cid": 4091,
    "chembl_id": "CHEMBL1431",
    "smiles": "…",
    "inchikey": "…",
    "molecular_formula": "C4H11N5",
    "iupac_name": null
  },
  "targets": [
    {
      "gene": "GPD2",
      "uniprot": "P43304",
      "ensembl_id": null,
      "mechanism": "…",
      "evidence_source": "chembl|open_targets|gtopdb",
      "rank": 1
    }
  ],
  "selected_uniprot": "P43304",
  "selected_protein": {
    "gene": "GPD2",
    "uniprot": "P43304",
    "protein_name": "…",
    "organism": "Homo sapiens",
    "function": "…",
    "mechanism": "…",
    "structure_label": "experimental",
    "structure_id": "5Z62",
    "provenance": "experimental_pdb",
    "method": "X-RAY DIFFRACTION",
    "resolution_A": 1.85,
    "plddt_mean": null,
    "warning": null
  },
  "structure": {
    "ok": true,
    "uniprot": "P43304",
    "pdb_id": "5Z62",
    "provenance": "experimental_pdb",
    "label": "experimental",
    "method": "X-RAY DIFFRACTION",
    "resolution_A": 1.85,
    "plddt_mean": null,
    "path": "/…/structures/5Z62.cif",
    "warning": null
  },
  "structure_candidates": [
    {
      "pdb_id": "5Z62",
      "method": "X-RAY DIFFRACTION",
      "resolution_A": 1.85,
      "has_ligand": true,
      "ligand_hets": ["CLR"]
    }
  ],
  "pocket": {
    "method": "crystal_ligand_centroid",
    "center": [12.0, 8.0, 5.0],
    "size": [22.0, 22.0, 22.0],
    "warning": null
  },
  "pharmacology": {},
  "dossier": {
    "go": [],
    "diseases": [],
    "tractability": [],
    "pathways": [],
    "sources": ["uniprot", "open_targets", "reactome"]
  },
  "orthologs": {
    "gene": "GPD2",
    "rows": [
      {
        "taxon_id": 10090,
        "organism": "Mus musculus",
        "gene": "Gpd2",
        "uniprot": null,
        "identity_pct": null,
        "source": "ensembl_compara",
        "confidence": "high"
      },
      {
        "taxon_id": 79327,
        "organism": "Schmidtea mediterranea",
        "gene": null,
        "uniprot": null,
        "identity_pct": null,
        "source": "oma_or_planmine",
        "confidence": "low"
      }
    ]
  },
  "job_title_preview": "metformin × GPD2 (P43304) · PDB 5Z62",
  "honesty": {
    "not_medical_advice": true,
    "computational_hypotheses": true,
    "message": "Not medical advice. Targets, mechanisms, and docking boxes are computational hypotheses for research triage — not clinical claims."
  }
}
```

`structure_candidates` + `dossier` may be empty arrays until Slice N+1; keep keys stable.

### D4. Minimal code merge checklist (now)

1. **`api_discover_dock`:** `meta.update(identity_from_discovery(payload))` + copy `honesty` + `docking` param block.  
2. **`run_docking_job`:** preserve ligand/protein/job_title/honesty when rewriting `result.json` (today rebuilds a thinner dict).  
3. **Jobs list / job page templates:** display `job_title` or `ligand.compound_name × protein.gene`; badge `protein.label`; show `scores.vina_affinity`.  
4. **Protein chooser API:** already have `refresh_for_target` / `resolve_protein_query` — persist `selected_protein` + `structure_candidates` into `discovery.json`.  
5. **Pose parse:** always emit `rmsd_lb`/`rmsd_ub` from Vina stdout.

---

## Sources (fetched or searched 2026-09-21 PT)

| Topic | URL |
|-------|-----|
| SeeSAR Beginner’s Guide v11 | https://www.biosolveit.de/wp-content/uploads/2021/05/BeginnersGuide_SeeSAR_11.pdf |
| SeeSAR First Aid | https://www.biosolveit.de/products/seesar/help/ |
| SeeSAR visualization | https://www.biosolveit.de/application-academy/visualization-and-3d-export/ |
| SeeSAR changelog / Apollo | https://www.biosolveit.de/products/seesar/changelog/ ; https://www.biosolveit.de/products/seesar/seesar-15-apollo/ |
| LiveDesign Glide utils (2026-2) | https://learn.schrodinger.com/public/python_api/2026-2/api/schrodinger.application.livedesign.ld_glide_utils.html |
| LiveDesign mapping / pose names | https://learn.schrodinger.com/public/python_api/2026-2/api/schrodinger.application.livedesign.mapping_widgets.html |
| KNIME LiveDesign docking workflows | https://nodepit.com/workflow/com.knime.hub/Users/schroedinger/LiveDesign_models/Docking/Docking%20and%20protein%20surface ; Ensemble docking sibling |
| ICM docking results / hitlist | https://molsoft.com/gui/view-dock-results.html |
| ICM FAQ docking scores | https://molsoft.com/gui/faq-docking.html |
| ChimeraX ViewDockX | https://www.cgl.ucsf.edu/chimerax/docs/user/tools/viewdockx.html |
| DockThor Tutorial 1 (1HPV) | https://dockthor.lncc.br/v2/tutorials/Tutorial1_1HPV.pdf |
| DockThor portal | https://dockthor.lncc.br/v2/ |
| AutoDock Vina basic docking | https://autodock-vina.readthedocs.io/en/latest/docking_basic.html |
| Vina manual | https://vina.scripps.edu/manual/ |
| PyRx FAQ / tutorial / 0.9.5 RMSD column | https://pyrx.sourceforge.io/faq/ ; https://stemskillslab.com/pyrx-tutorial-molecular-docking/ ; https://pyrx.sourceforge.io/pyrx-095-release-announcement/ |
| Benchling App Status | https://docs.benchling.com/docs/introduction-to-app-status |
| Open Targets GraphQL | https://platform-docs.opentargets.org/data-access/graphql-api |
| UniProt programmatic access | https://www.uniprot.org/help/api_queries |
| RCSB Data API | https://data.rcsb.org/ |
| ProLIF docking IFP tutorial | https://prolif.readthedocs.io/en/latest/notebooks/docking.html |
| SwissADME Help | https://www.swissadme.ch/help.php |
| ADMETlab 3.0 (NAR) | https://doi.org/10.1093/nar/gkae236 |
| CrossBind identity + pipeline (local) | `/workspace/CrossBind/crossbind/job_identity.py`, `pipeline.py`, `discovery/__init__.py` |
| Munroe / Custom Lab LIMS protein chooser (local UX ref) | `/workspace/custom-lab-lims-web/db.py`, `app.py` `/proteins*`; `/workspace/custom-lab-lims-ref/lab_tools.py`, `USAGE.txt` |

---

## One-line product principle

**If a LinkedIn biotech reader cannot tell which ligand, which gene/UniProt, which PDB/AF model, which engine, and which disclaimer apply to a job card in under five seconds, the metadata schema is not done.**


---

## 2026-09-22 competitive scan (PocketDock / DockSuiteX / NatDock / ProteinIQ)

**Peers researched:** PocketDock-style local docking UIs, DockSuiteX, NatDock / screening tool patterns, ProteinIQ DiffDock+GNINA stacks.

### Feature parity notes (what peers ship that we lacked)

| Layer | Peer pattern | Cross Affinity before this cut |
|-------|--------------|--------------------------------|
| Post-dock ADMET | PocketDock: RDKit MW/LogP/TPSA/HBD/HBA/rotB/QED + Lipinski/Veber on every job | Missing from `result.json` / job page |
| Pose–protein IFP | PocketDock / ProLIF-style H-bonds, hydrophobic, salt/π | Missing (schema placeholder only) |
| Pocket ranking | P2Rank binary in heavier installs | Deferred (centroid / crystal ligand today) |
| Batch screening | NatDock / suite hitlists | Later (`study_id` schema reserved) |
| Blind / physics | DiffDock + MM-GBSA / GNINA-first-class | Later; Vina primary, GNINA optional |

### What we shipped (2026-09-22)

1. **`crossbind/analysis/admet.py`** — RDKit descriptors + Lipinski / Veber / optional Ghose with units, pass/fail, honesty disclaimer. Hooked into `run_docking_job` → `result.admet`.
2. **`crossbind/analysis/interactions.py`** — ProLIF+MDAnalysis when installed; else solid RDKit/geometry fallback (H-bond, hydrophobic, salt, π cutoffs). Stores `result.interactions` (per-pose summary + top-pose detail + `contact_residues`). Analysis failures are **non-fatal**.
3. **Job page UI** — dense ADMET metric grid (tabular-nums, instrument theme) + interactions table + honesty banner.
4. **3D viewer polish** — ligand ball-and-stick / licorice+sphere with Jmol/CPK element colors; thicker than protein; H hidden; sidechains default off / thin; subtler dashed docking box; zoom-to-ligand; `viewer.js?v=…` cache-bust. Residue click + viewport height lock preserved.

### Next

- P2Rank pocket ranking (binary optional).
- Batch ligands vs one target (`study_id`).
- GNINA first-class install path + CNN columns always surfaced.
- ProLIF 2D/3D interaction viz (lignetwork) on the job / viewer page.
- DiffDock blind docking / MM-GBSA (heavy; later).

