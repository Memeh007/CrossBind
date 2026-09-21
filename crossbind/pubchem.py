"""Name → SMILES via PubChem (with retries) and optional CACTUS fallback."""

from __future__ import annotations

import time
from urllib.parse import quote

import requests

_UA = {"User-Agent": "CrossBind/1.0 (local research; Alexander Cecena)"}


def name_to_smiles(name: str, *, retries: int = 3) -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError("Empty compound name")

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            return _pubchem_smiles(name)
        except Exception as exc:
            last_err = exc
            time.sleep(0.6 * (attempt + 1))

    try:
        return _cactus_smiles(name)
    except Exception as cactus_err:
        raise RuntimeError(
            f"Could not resolve SMILES for {name!r}. "
            f"PubChem: {last_err}; CACTUS: {cactus_err}"
        ) from cactus_err


def _pubchem_smiles(name: str) -> str:
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{quote(name)}/property/CanonicalSMILES,IsomericSMILES/JSON"
    )
    r = requests.get(url, headers=_UA, timeout=20)
    if r.status_code == 404:
        raise ValueError(f"PubChem: no compound named {name!r}")
    r.raise_for_status()
    props = r.json()["PropertyTable"]["Properties"][0]
    smi = props.get("IsomericSMILES") or props.get("CanonicalSMILES")
    if not smi:
        raise ValueError("PubChem returned empty SMILES")
    return smi


def _cactus_smiles(name: str) -> str:
    url = f"https://cactus.nci.nih.gov/chemical/structure/{quote(name)}/smiles"
    r = requests.get(url, headers=_UA, timeout=20)
    r.raise_for_status()
    smi = r.text.strip()
    if not smi or "<" in smi:
        raise ValueError("CACTUS returned no SMILES")
    return smi
