# Ligand-aware pocket ranking (ddOS P0)

**Product:** ddOS · **Package:** `crossbind` · **Slice:** P0 credibility foundations

## What it does

Two-stage pocket selection for a **specific query ligand**:

1. **Propose** pocket hypotheses  
   - Prefer a **holo crystal ligand** site when a co-crystallized HETATM ligand exists in the PDB.  
   - Otherwise run **P2Rank** (`prank predict`). Use **`-c alphafold`** when structure provenance is AlphaFold / predicted / uploaded.  
   - If P2Rank is not installed → graceful **centroid / crystal-ligand auto-box** fallback (same as pre-1.3.1 Discover).

2. **Rank for this ligand** (optional / auto when multiple pockets)  
   - Dock the query ligand into the **top-K** pockets (default **K=3**) with the existing **AutoDock Vina** pipeline.  
   - Pick the pocket with the **most negative** Vina affinity.  
   - Persist `p2rank_score` (or prior score) + `docked_score` per pocket on the job result.

## Honesty (non-negotiable)

- Never call a pocket **“the true site.”**  
- After ligand-aware ranking, label: **best-ranked pocket for this ligand under Vina.**  
- **Vina ≠ Kd / IC50.**  
- AlphaFold banners remain: AF pocket look ≠ pose success.  
- No bundled LLM biology claims.

## Result fields

| Field | Meaning |
|-------|---------|
| `pockets[]` | Proposed (and possibly Vina-scored) pocket list |
| `selected_pocket` | Winner used for the final dock box |
| `pocket_method` | `p2rank` \| `holo_ligand` \| `centroid_fallback` \| `ligand_aware_vina` |

## Discover UI

- Pocket table with method / score / center / residues.  
- AF banner + holo-preferred note.  
- **Pocket ranking:** Auto (ligand-aware when multiple) · Force ligand-aware · Selected only.  
- **Top-K** control (default 3).

## Install P2Rank on Windows (for this app)

P2Rank is **optional**. Without it, ddOS still docks using holo/centroid boxes.

1. Install **Java 17+** (Temurin / Oracle / Microsoft Build of OpenJDK). Confirm: `java -version`.
2. Download a release zip from [rdk/p2rank releases](https://github.com/rdk/p2rank/releases).
3. Extract, e.g. to `C:\Users\<you>\Desktop\CrossBind\bin\p2rank\`.
4. Either:
   - Ensure `prank.bat` is reachable as `CrossBind\bin\p2rank\prank.bat`, **or**
   - Set environment variables before `run.bat`:
     ```bat
     set P2RANK_HOME=C:\path\to\p2rank
     rem or:
     set P2RANK_BIN=C:\path\to\p2rank\prank.bat
     ```
5. Restart ddOS (`run.bat`). Check `GET /api/health` → `"p2rank_ok": true`.

Docs upstream: [github.com/rdk/p2rank](https://github.com/rdk/p2rank). For AF models: `prank predict -c alphafold -f model.pdb`.

## Library-first note

ddOS wraps the P2Rank CLI; it does **not** reimplement pocket ML. Vina remains the docking engine for ligand-aware ranking in this slice (DiffDock / MM/GBSA / FEP are out of scope).
