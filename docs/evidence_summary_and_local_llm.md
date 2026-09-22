# Evidence summary & optional local LLM

## Deterministic evidence summary

`crossbind.analysis.explain.build_explanation(result)` builds plain-English paragraphs **only** from structured `result.json` fields (title, vina affinity, engine, pocket method, ADMET Lipinski/QED, top contacts with residue/type/distance). Caveats are always appended: docking score ≠ Kd; contacts are pose hypotheses; not medical advice.

Stored as `result.explanation`. Rebuild via:

```http
POST /api/job/{id}/explain
```

## Residue binding proof (UI)

Job page table for the selected pose: Residue | Chain/res | Interaction type | Distance (Å) | Atom detail | Method, plus cutoffs (hbond 3.5 Å, etc.) and an honesty banner stating contacts are computational geometry — not crystallographic density or assay proof.

## Optional local Ollama narration

```http
POST /api/job/{id}/narrate
```

- Calls `OLLAMA_HOST` (default `http://127.0.0.1:11434`) `/api/chat` with `OLLAMA_MODEL` (default `llama3.2`).
- System prompt: use only provided JSON evidence; do not invent residues/distances/pathways/clinical claims; label output as research hypothesis.
- On failure: returns deterministic explanation + “Local LLM not available…”.
- **Does not** embed multi-GB weights in the repo. Bundling an LLM does not guarantee non-fiction.
