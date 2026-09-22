#!/usr/bin/env python3
"""Smoke script: Discover vertical slice for metformin."""

from __future__ import annotations

import json
import sys

from crossbind.discovery import run_discovery


def main() -> int:
    result = run_discovery("metformin")
    drug = result["drug"]
    print("CID", drug.get("cid"))
    print("SMILES", drug.get("smiles"))
    print("InChIKey", drug.get("inchikey"))
    print("ChEMBL", drug.get("chembl_id"))
    print("targets", len(result.get("targets") or []))
    for t in (result.get("targets") or [])[:5]:
        print(" -", t.get("gene"), t.get("uniprot"), t.get("mechanism"), t.get("source"))
    st = result.get("structure") or {}
    print("structure", st.get("provenance"), st.get("pdb_id"), st.get("path"))
    pk = result.get("pocket") or {}
    print(
        "pocket",
        pk.get("method"),
        "center",
        pk.get("center"),
        "size",
        pk.get("size"),
        "nonzero",
        pk.get("nonzero"),
    )
    ortho = result.get("orthologs") or {}
    print("orthologs gene", ortho.get("gene"))
    for s in ortho.get("species") or []:
        print(" -", s["label"], s["status"], s.get("id"), s.get("identity"))

    center = pk.get("center") or [0, 0, 0]
    ok = (
        drug.get("cid") == 4091
        and bool(drug.get("smiles"))
        and bool(center)
        and (abs(center[0]) + abs(center[1]) + abs(center[2]) > 1e-6 or pk.get("method") == "ligand_centroid")
        and len(ortho.get("species") or []) >= 7
    )
    out = {
        "ok": ok,
        "cid": drug.get("cid"),
        "smiles": drug.get("smiles"),
        "pocket": pk,
        "structure": {"provenance": st.get("provenance"), "pdb_id": st.get("pdb_id")},
    }
    print(json.dumps(out, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
