# ddOS citation index

**Rule:** Agents **look up** primary sources (Hermes/orchestrator); download PDFs into `pdfs/` when useful; never invent DOIs. Verify PDF title matches the intended paper before indexing. See `AGENTS.md` §8.5.

## Local PDFs on disk

| Local file | Year | DOI / URL | Why ddOS cares | B-id / stage |
|------------|------|-----------|----------------|--------------|
| `pdfs/2022_Corso_DiffDock.pdf` | 2022 | https://doi.org/10.48550/arxiv.2210.01776 | Diffusion docking + confidence; confidence is not affinity | B12 |
| `pdfs/2024_Corso_DiffDock-L.pdf` | 2024 | https://doi.org/10.48550/arxiv.2402.18396 | DiffDock-L larger/generalized pose model | B12 |
| `pdfs/2024_Swanson_ADMET-AI.pdf` | 2024 | https://doi.org/10.1093/bioinformatics/btae416 | Local MIT ADMET triage (Chemprop/TDC) | B3 |
| `pdfs/2024_Utges_LIGYSIS_pockets.pdf` | 2024 | https://doi.org/10.1186/s13321-024-00923-z | Pocket benchmark; fpocket+PRANK top-N+2 | B11 |
| `pdfs/2024_Wohlwend_Boltz1.pdf` | 2024 | https://doi.org/10.1101/2024.11.19.624167 | Open MIT AF3-class co-fold (prefer over AF3 Server) | B14 |
| `pdfs/2025_McNutt_GNINA_1.3.pdf` | 2025 | https://doi.org/10.1186/s13321-025-00973-x | GNINA 1.3 CNN rescore/refine; first-class dock path | B1 |
| `pdfs/2025_Passaro_Boltz2.pdf` | 2025 | https://doi.org/10.1101/2025.06.14.659707 | Boltz-2 structure + research affinity estimates | B14 |

## Still needing PDF fetch (INDEX URL only)

| Topic | DOI / URL | Notes |
|-------|-----------|-------|
| PoseBusters | https://doi.org/10.1039/D3SC04185A | RSC gated — retry |
| Uni-Dock | https://doi.org/10.1021/acs.jctc.2c01145 | ACS; do not guess arXiv IDs |
| Uni-GBSA | https://doi.org/10.1093/bib/bbad218 | OUP — retry |
| ADMETlab 3.0 | https://doi.org/10.1093/nar/gkae236 | PMC — retry |
| BindingDB 2024 | https://doi.org/10.1093/nar/gkae1075 | PMC — retry |
| OrthoDB v12 | https://doi.org/10.1093/nar/gkae987 | PMC — retry |
| Open Targets releases | https://platform-docs.opentargets.org/release-notes | HTML docs OK |

*Updated 2026-09-22 PT. Hermes should keep growing this library when new tools/claims appear.*
