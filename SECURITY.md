# Security Policy — CrossBind

CrossBind is a **local-first, researchers-only** molecular docking UI. It is **not** a hardened multi-tenant SaaS.

## Default posture

- Binds to **`127.0.0.1`** via `run.bat` / `run.sh` / documented uvicorn commands.
- Do **not** expose the port to the public internet.
- Docking engines are invoked with an **argv list only** (`subprocess` without `shell=True`) to avoid shell injection.

## Uploads & paths

- Upload filenames are sanitized; directory components are stripped.
- Job files live only under `data/jobs/<job_id>/`.
- API file downloads are allow-listed and resolved with a path-escape check.
- Default upload size cap: ~50 MB (`CROSSBIND_UPLOAD_MAX`).

## Secrets & data

- Gitignore covers `data/jobs/*`, `venv/`, `.env`, and local docking binaries under `bin/`.
- Do not commit proprietary structures, unpublished compounds, or API tokens.
- PubChem / CACTUS lookups send compound **names** to public HTTP APIs — use only for non-sensitive queries.

## Engine binaries

- `VINA_BIN` / `GNINA_BIN` must point to trusted binaries you installed.
- CrossBind does not download docking engines automatically.

## Reporting

Portfolio / research software. Report issues on your GitHub fork. Do not include confidential structures or credentials in tickets.


## Local LLM narration (optional)

- CrossBind does **not** ship multi-GB model weights and does **not** call cloud LLMs by default.
- Optional `POST /api/job/{id}/narrate` talks only to a local Ollama HTTP endpoint (`OLLAMA_HOST`, default `http://127.0.0.1:11434`) with model `OLLAMA_MODEL` (default `llama3.2`).
- System prompt requires evidence-bound output; unconstrained LLMs still can hallucinate biology — treat narration as a research hypothesis, never as experimental proof or medical advice.
- If Ollama is unreachable, the API returns the deterministic evidence summary plus an honest unavailable message.
