#!/usr/bin/env python3
"""Restricted-state chain heuristic for the open large QOBLIB problem 06 instances.

    python scripts/portfolio_heuristic.py --bases a003,a004,a005 --lambdas 0,0.0001
    python scripts/portfolio_heuristic.py --bases a200_t10_s01 --lambdas 0.0001 --check

Values are heuristic (no optimality proof), but exact for the reference model:
every schedule is re-evaluated with the integer objective and can be verified
with the official checker (--check).  Reference values are looked up in the
exact-solver summaries (--exact-summaries) and in the published best-known
table (--published) so the output prints the gap directly.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import time
from fractions import Fraction

from qoblib_portfolio.model import Coefficients, Instance
from qoblib_portfolio.heuristic import solve_heuristic
from qoblib_portfolio.solver import LAMBDA_GRID, LAMBDA_TAG, objective, write_canonical

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))
BUDGET_BY_ASSETS = {3: 3, 4: 4, 5: 4, 10: 4, 50: 20, 200: 50, 400: 100}
CHECKER = f"{QOBLIB}/06-portfolio/check/target/release/check_portfolio"


def bases_for(prefixes: list[str]) -> list[str]:
    root = f"{QOBLIB}/06-portfolio/instances"
    out = []
    for d in sorted(os.listdir(root)):
        if d.startswith("po_") and any(d.startswith(f"po_{p}") for p in prefixes):
            out.append(d)
    return out


def load_references(exact_globs: list[str], published: str | None) -> dict[str, tuple[int, str]]:
    """instance id -> (value, kind) with kind 'optimal' or 'published'."""
    ref = {}
    if published and os.path.exists(published):
        row = re.compile(r"^\|\s*(\S+)\s*\|\s*(-?\d+)\s*\|\s*(best known|optimal)")
        for line in open(published):
            m = row.match(line)
            if m:
                ref[m.group(1)] = (int(m.group(2)), "published " + m.group(3))
    for pattern in exact_globs:
        for path in glob.glob(pattern):
            for r in json.load(open(path)):
                if r.get("proven_optimal"):
                    ref[r["instance"]] = (int(r["objective"]), "optimal")
    return ref


def run_checker(instance_dir: str, sol_path: str) -> str:
    if not os.path.exists(CHECKER):
        return "checker missing"
    p = subprocess.run([CHECKER, instance_dir, sol_path], capture_output=True, text=True)
    tail = (p.stdout + p.stderr).strip().splitlines()
    return f"exit {p.returncode}: {tail[-1] if tail else ''}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bases", default="a003,a004,a005",
                    help="comma-separated instance-name prefixes, e.g. a200_t10_s01")
    ap.add_argument("--lambdas", default=",".join(LAMBDA_GRID))
    ap.add_argument("--outdir", default="results/heuristic")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--kicks", type=int, default=3)
    ap.add_argument("--chain-kicks", type=int, default=4)
    ap.add_argument("--loo", type=int, default=8)
    ap.add_argument("--lns-iters", type=int, default=30)
    ap.add_argument("--lns-k", type=int, default=7)
    ap.add_argument("--cd-lns-iters", type=int, default=10)
    ap.add_argument("--seed-width", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--time-limit", type=float, default=None,
                    help="soft wall-clock limit per instance in seconds (search phase)")
    ap.add_argument("--check", action="store_true", help="run the official checker on each .sol")
    ap.add_argument("--exact-summaries", default=f"{PKG}/results/small/summary.json,{PKG}/results/a010/*/summary.json")
    ap.add_argument("--published", default=f"{QOBLIB}/06-portfolio/solutions/README.md")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    ref = load_references(a.exact_summaries.split(","), a.published)
    lams = a.lambdas.split(",")
    records = []
    print(f"{'instance':<30} {'heuristic':>10} {'reference':>10} {'gap%':>7} {'secs':>6}  note")

    for base in bases_for(a.bases.split(",")):
        inst_dir = f"{QOBLIB}/06-portfolio/instances/{base}"
        t0 = time.time()
        inst = Instance(inst_dir)
        budget = BUDGET_BY_ASSETS[inst.n]
        short = base[3:]
        parse_s = time.time() - t0
        for lam_text in lams:
            iid = f"{short}_b{budget:03d}_{LAMBDA_TAG[lam_text]}"
            t1 = time.time()
            coef = Coefficients(inst, budget, Fraction(lam_text))
            coef_s = time.time() - t1
            value, U, info = solve_heuristic(coef, rounds=a.rounds, kicks=a.kicks,
                                             loo=a.loo, seed_width=a.seed_width, chain_kicks=a.chain_kicks,
                                             lns_iters=a.lns_iters, lns_k=a.lns_k, cd_lns_iters=a.cd_lns_iters, seed=a.seed,
                                             time_limit=a.time_limit, verbose=a.verbose)
            assert objective(coef, U) == value
            total_s = time.time() - t1 + (parse_s if lam_text == lams[0] else 0)
            path = f"{a.outdir}/{iid}.sol"
            write_canonical(path, coef, U, base, lam_text, value,
                            comment="heuristic: restricted-state chain DP over per-period "
                                    "local optima, no optimality proof")
            note = ""
            if a.check:
                note = run_checker(inst_dir, path)
            r = ref.get(iid)
            if r is None:
                ref_txt, gap_txt = "n/a", ""
            else:
                rv, kind = r
                ref_txt = str(rv)
                gap = 0.0 if rv == value else (value - rv) / abs(rv) * 100 if rv else float("nan")
                gap_txt = f"{gap:+.3f}"
                tag = "match" if value == rv else ("better" if value < rv else "worse")
                note = f"{tag} vs {kind}  " + note
            print(f"{iid:<30} {value:>10} {ref_txt:>10} {gap_txt:>7} {total_s:>6.1f}  {note}")
            records.append({"instance": iid, "base": base, "budget": budget, "lambda": lam_text,
                            "objective": value, "proven_optimal": False,
                            "reference": None if r is None else r[0],
                            "reference_kind": None if r is None else r[1],
                            "seconds": total_s, "coef_seconds": coef_s,
                            "search_seconds": info["seconds"], "pool_states": info["pool_states"],
                            "rounds": info["rounds"], "solution": os.path.basename(path)})

    json.dump(records, open(f"{a.outdir}/summary.json", "w"), indent=1)
    print(f"\n{len(records)} instances written to {a.outdir}")


if __name__ == "__main__":
    main()
