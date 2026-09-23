"""Runtime settings for CrossBind."""

from __future__ import annotations

import os
from pathlib import Path

# Project root: CrossBind/
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("CROSSBIND_DATA", ROOT / "data")).resolve()
JOBS_DIR = DATA_DIR / "jobs"
CACHE_DIR = DATA_DIR / "cache"
UPLOAD_MAX_BYTES = int(os.environ.get("CROSSBIND_UPLOAD_MAX", 50 * 1024 * 1024))

HOST = os.environ.get("CROSSBIND_HOST", "127.0.0.1")
PORT = int(os.environ.get("CROSSBIND_PORT", "8787"))

VINA_BIN = os.environ.get("VINA_BIN", "").strip() or None
GNINA_BIN = os.environ.get("GNINA_BIN", "").strip() or None

# Common Windows fallbacks (checked only if VINA_BIN unset)
_VINA_CANDIDATES = [
    ROOT / "bin" / "vina",
    ROOT / "bin" / "vina.exe",
    ROOT / "bin" / "vina_1.2.7_win.exe",
    Path("C:/Program Files/AutoDock Vina/vina.exe"),
]

ALLOWED_RECEPTOR_EXT = {".pdb", ".pdbqt", ".cif", ".mmcif"}
ALLOWED_LIGAND_EXT = {".pdb", ".pdbqt", ".mol", ".mol2", ".sdf", ".smi", ".smiles"}


def resolve_vina_bin() -> str | None:
    if VINA_BIN and Path(VINA_BIN).is_file():
        return VINA_BIN
    if VINA_BIN:
        # User set path but missing — still return so error message is clear
        return VINA_BIN
    for p in _VINA_CANDIDATES:
        if p.is_file():
            return str(p)
    # PATH lookup
    import shutil

    for name in ("vina", "vina.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def resolve_gnina_bin() -> str | None:
    """Locate optional GNINA binary (CNN docking / rescoring).

    Windows tip: set ``GNINA_BIN`` to the full path of ``gnina.exe`` (WSL builds
    are common — point at the Windows-visible path or run under WSL). Example::

        set GNINA_BIN=C:/Users/you/bin/gnina.exe

    Scores are **not** experimental Kd — ``vina_affinity`` and CNN fields are stored separately.
    """
    import shutil

    if GNINA_BIN and Path(GNINA_BIN).is_file():
        return GNINA_BIN
    if GNINA_BIN:
        # Explicit override even if missing — caller surfaces a clear error
        return GNINA_BIN

    candidates = [
        ROOT / "bin" / "gnina",
        ROOT / "bin" / "gnina.exe",
        ROOT / "bin" / "gnina_1.3" / "gnina",
        ROOT / "bin" / "gnina_1.3" / "gnina.exe",
        Path("C:/Program Files/gnina/gnina.exe"),
        Path.home() / "bin" / "gnina.exe",
        Path.home() / "bin" / "gnina",
        Path.home() / "AppData" / "Local" / "gnina" / "gnina.exe",
    ]
    for pth in candidates:
        try:
            if pth.is_file():
                return str(pth)
        except OSError:
            continue

    for name in ("gnina", "gnina.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "structures").mkdir(parents=True, exist_ok=True)


# Optional local LLM (Ollama). Never used for cloud calls by default.
# Bundling weights in-repo is intentionally unsupported — LLMs can invent biology.
OLLAMA_HOST = (os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = (os.environ.get("OLLAMA_MODEL") or "llama3.2").strip() or "llama3.2"

P2RANK_BIN = os.environ.get("P2RANK_BIN", "").strip() or None
P2RANK_HOME = os.environ.get("P2RANK_HOME", "").strip() or None

_P2RANK_CANDIDATES = [
    ROOT / "bin" / "p2rank" / "prank",
    ROOT / "bin" / "p2rank" / "prank.bat",
    ROOT / "bin" / "prank",
    ROOT / "bin" / "prank.bat",
    ROOT / "bin" / "p2rank.bat",
]


def resolve_p2rank_bin() -> str | None:
    """Locate P2Rank CLI (prank / prank.bat). Optional — Discover falls back without it."""
    import shutil

    if P2RANK_BIN:
        p = Path(P2RANK_BIN)
        if p.is_file() or shutil.which(P2RANK_BIN):
            return str(P2RANK_BIN)
        return P2RANK_BIN  # set but missing — caller surfaces a clear error
    if P2RANK_HOME:
        home = Path(P2RANK_HOME)
        for name in ("prank.bat", "prank", "prank.sh"):
            cand = home / name
            if cand.is_file():
                return str(cand)
    for p in _P2RANK_CANDIDATES:
        if p.is_file():
            return str(p)
    for name in ("prank", "prank.bat"):
        found = shutil.which(name)
        if found:
            return found
    return None
