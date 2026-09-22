"""P2Rank CLI wrapper — detect binary, run predict, parse pocket hypotheses.

Library-first: never reimplement pocket ML. P2Rank is optional; callers must
fall back when the binary is missing.
"""

from __future__ import annotations

import csv
import io
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from crossbind.config import resolve_p2rank_bin

# Default cubic box size (Å) around a P2Rank center for Vina.
DEFAULT_POCKET_BOX = 22.0


def p2rank_available() -> bool:
    bin_path = resolve_p2rank_bin()
    if not bin_path:
        return False
    p = Path(bin_path)
    return p.is_file() or bool(shutil.which(bin_path))


def is_alphafold_provenance(structure: dict | None) -> bool:
    """True when structure should use P2Rank ``-c alphafold``."""
    st = structure or {}
    label = (st.get("label") or "").lower()
    provenance = (st.get("provenance") or "").lower()
    method = (st.get("method") or "").lower()
    if label in {"predicted", "uploaded"} or provenance in {
        "alphafold_db",
        "user_upload",
        "predicted",
    }:
        return True
    if "alphafold" in method or "predicted" in method:
        return True
    sid = str(st.get("pdb_id") or st.get("filename") or "")
    if sid.upper().startswith("AF-"):
        return True
    return False


def parse_predictions_csv(text: str) -> list[dict[str, Any]]:
    """Parse P2Rank ``*_predictions.csv`` into pocket dicts.

    Tolerates padded headers/values (P2Rank right/left-justifies columns).
    """
    # Drop comment / blank lines; keep header + data
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(line)
    if not lines:
        return []

    reader = csv.DictReader(io.StringIO("\n".join(lines)), skipinitialspace=True)
    pockets: list[dict[str, Any]] = []
    for i, row in enumerate(reader):
        if not row:
            continue
        # Normalize keys (strip spaces from header names)
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items() if k is not None}
        name = norm.get("name") or f"pocket{i + 1}"
        try:
            cx = float(norm.get("center_x") or "nan")
            cy = float(norm.get("center_y") or "nan")
            cz = float(norm.get("center_z") or "nan")
        except ValueError:
            continue
        if cx != cx or cy != cy or cz != cz:  # NaN check
            continue
        score = _maybe_float(norm.get("score"))
        prob = _maybe_float(norm.get("probability"))
        rank = _maybe_int(norm.get("rank")) or (i + 1)
        residues_raw = norm.get("residue_ids") or ""
        residues = [r for r in residues_raw.split() if r]
        size = [DEFAULT_POCKET_BOX, DEFAULT_POCKET_BOX, DEFAULT_POCKET_BOX]
        pockets.append(
            {
                "id": name.strip(),
                "rank": rank,
                "score": score,
                "probability": prob,
                "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
                "size": size,
                "residues": residues,
                "method": "p2rank",
                "source": "p2rank",
            }
        )
    pockets.sort(key=lambda p: (p.get("rank") is None, p.get("rank") or 999, -(p.get("score") or 0)))
    return pockets


def parse_predictions_file(path: str | Path) -> list[dict[str, Any]]:
    return parse_predictions_csv(Path(path).read_text(encoding="utf-8", errors="replace"))


def run_p2rank(
    structure_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    alphafold: bool = False,
    visualizations: bool = False,
    threads: int = 1,
    log: Callable[[str], None] | None = None,
    timeout_s: int = 600,
) -> list[dict[str, Any]]:
    """Run ``prank predict -f <structure>`` and return parsed pockets.

    Raises FileNotFoundError if the binary is missing; RuntimeError on CLI failure.
    """
    bin_path = resolve_p2rank_bin()
    if not bin_path or not (Path(bin_path).is_file() or shutil.which(bin_path)):
        raise FileNotFoundError(
            "P2Rank (prank) not found. Install from https://github.com/rdk/p2rank "
            "(needs Java 17+) and set P2RANK_BIN / P2RANK_HOME, or place under CrossBind/bin/p2rank/."
        )

    structure_path = Path(structure_path).resolve()
    if not structure_path.is_file():
        raise FileNotFoundError(structure_path)

    own_tmp = out_dir is None
    work = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="ddos_p2rank_"))
    work.mkdir(parents=True, exist_ok=True)

    cmd = [
        bin_path,
        "predict",
        "-f",
        str(structure_path),
        "-o",
        str(work),
        "-visualizations",
        "1" if visualizations else "0",
        "-threads",
        str(max(1, int(threads))),
    ]
    if alphafold:
        cmd.extend(["-c", "alphafold"])

    if log:
        log(f"Running P2Rank: {' '.join(cmd[:4])} …")

    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        proc = subprocess.run(cmd, timeout=timeout_s, check=False, **kwargs)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"P2Rank timed out after {timeout_s}s") from exc

    stdout = proc.stdout or ""
    if log and stdout:
        for line in stdout.strip().splitlines()[-20:]:
            log(f"p2rank: {line}")

    pred = _find_predictions_csv(work, structure_path)
    if proc.returncode != 0 and not pred:
        raise RuntimeError(
            f"P2Rank failed (exit {proc.returncode}). "
            f"Last output: {stdout[-500:] if stdout else '(empty)'}"
        )
    if not pred:
        raise RuntimeError(f"P2Rank produced no *_predictions.csv under {work}")

    pockets = parse_predictions_file(pred)
    for p in pockets:
        p["p2rank_config"] = "alphafold" if alphafold else "default"
        p["predictions_csv"] = str(pred)

    if own_tmp:
        # Keep CSV next to structure cache is nicer, but tmp is fine for parse-only;
        # callers who need artifacts should pass out_dir.
        pass

    return pockets


def _find_predictions_csv(work: Path, structure_path: Path) -> Path | None:
    stem = structure_path.name  # e.g. 1fbl.pdb → 1fbl.pdb_predictions.csv
    direct = work / f"{stem}_predictions.csv"
    if direct.is_file():
        return direct
    # Nested output dirs used by some P2Rank versions
    matches = sorted(work.rglob("*_predictions.csv"))
    return matches[0] if matches else None


def _maybe_float(v: str | None) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _maybe_int(v: str | None) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None
