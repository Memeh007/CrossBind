#!/usr/bin/env python3
"""Build / refresh the local PlanMine (S. mediterranea) RBH-style ortholog cache (B7).

Examples (from the repo root, same Python as run.bat):

  # Full build: every S. mediterranea contig with a Homo sapiens BLAST hit (~72k rows) + gene links
  python scripts/build_planmine_rbh_cache.py --all

  # Targeted refresh for specific human symbols (4 small PlanMine queries per symbol)
  python scripts/build_planmine_rbh_cache.py --genes PRKAA1,PRKAG1,MTOR --refresh

  # Regenerate the committed seed (metformin-axis genes) from a fresh live pull
  python scripts/build_planmine_rbh_cache.py --seed-genes --db /tmp/pm.sqlite \
      --export-seed crossbind/discovery/data/planmine_smed_seed.json

The default DB is data/cache/planmine_smed_rbh.sqlite (gitignored; override with
CROSSBIND_PLANMINE_DB or --db). PlanMine base URL: CROSSBIND_PLANMINE_URL.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crossbind.discovery import planmine  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=None, help="SQLite path (default: data/cache/planmine_smed_rbh.sqlite)")
    ap.add_argument("--all", action="store_true", help="bulk-download the full Homo sapiens BLAST slice")
    ap.add_argument("--genes", default="", help="comma-separated human symbols to fetch")
    ap.add_argument("--seed-genes", action="store_true", help="fetch the metformin-axis seed symbol list")
    ap.add_argument("--refresh", action="store_true", help="re-fetch symbols already in the cache")
    ap.add_argument("--export-seed", type=Path, default=None, help="write a seed JSON for the fetched symbols")
    ap.add_argument("--no-seed", action="store_true", help="do not initialise a new DB from the committed seed")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.genes.split(",") if s.strip()]
    if args.seed_genes:
        symbols += [s for s in planmine.SEED_SYMBOLS if s not in symbols]
    if not args.all and not symbols:
        ap.error("give --all, --genes, or --seed-genes")

    db = args.db or planmine.db_path()
    con = planmine.connect(db, seed=not (args.no_seed or args.export_seed))
    try:
        versions = planmine.planmine_versions()
        if not versions:
            print(f"PlanMine not reachable at {planmine.PLANMINE_URL}", file=sys.stderr)
            return 2
        planmine.set_meta(con, planmine_url=planmine.PLANMINE_URL, **versions)
        print(f"PlanMine {planmine.PLANMINE_URL} api={versions.get('planmine_api')} "
              f"release={versions.get('planmine_release')} -> {db}")

        if args.all:
            t = time.time()
            counts = planmine.fetch_all(con)
            print(f"full build: {counts} in {time.time() - t:.0f}s")

        failed = []
        for sym in symbols:
            if planmine.is_covered(con, sym) and not args.refresh and not args.all:
                print(f"  {sym}: cached (use --refresh to re-fetch)")
                continue
            try:
                n = planmine.fetch_symbol(con, sym)
            except planmine.PlanMineError as exc:
                failed.append(sym)
                print(f"  {sym}: FAILED {exc}", file=sys.stderr)
                continue
            hit = planmine.resolve_symbol(con, sym)
            if hit:
                tag = "reciprocal" if hit["reciprocal"] else f"forward-only (reverse best {','.join(hit['reverse_best_symbols'])})"
                print(f"  {sym}: {n} hits -> {hit['gene'] or hit['contig']} e={hit['evalue']:.0e} {tag}")
            else:
                print(f"  {sym}: {n} hits -> no mapping at e<={planmine.EVALUE_MAX:.0e}")

        if args.export_seed:
            stats = planmine.export_seed(con, symbols, args.export_seed)
            print(f"seed written: {args.export_seed} {stats}")
        print("cache:", {k: v for k, v in planmine.cache_meta(con).items() if k != "planmine_url"})
        return 1 if failed else 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
