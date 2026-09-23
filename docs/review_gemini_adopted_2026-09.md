# Review adoption — Gemini feedback (2026-09-22 PT)

Accepted into `AGENTS.md` §2.7 / §9.3 and this build pass.

| Feedback | Action |
|----------|--------|
| MiniCPM attention ~20–30K | §9.3 hard pack + ~25K soft cap; only §§0–5 + one file + one B-slice |
| Receptor prep fragility | `crossbind/docking/receptor.py` optional **pdbfixer** repair before Open Babel |
| PlanMine fragility | B7 must use RBH SQLite cache (queued; not live-only) |
| PoseBusters Windows deps | `scripts/smoke_posebusters.py` — pass before FastAPI wiring |
| Execute B1→B2→B3 | Queue unchanged; B1 code path exists — needs `GNINA_BIN` binary |

## B1 remaining (binary)

Code already isolates `vina_affinity` vs `gnina_cnn_*`. Hard-enable = place `gnina.exe` (or WSL binary) at `bin/gnina.exe` or set `GNINA_BIN`, then `/api/health` shows `gnina_ok: true`. Optional: `GNINA_CNN`, `GNINA_CNN_SCORING` env vars.
