#!/usr/bin/env python3
"""Run parallel tempering across many instances and seeds, one process each.

QOBLIB requires at least 5 independent runs for a stochastic method (10+
recommended) with seeds documented, so a sweep, not a single run, is the unit
of work that can actually be submitted.

    python scripts/sweep.py --instances 11-23 --seeds 5 --seconds 1800 --workers 10

Writes one JSON per (instance, seed) into --outdir and prints a summary table
of the best result per instance against the published best-known value.
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import time

import numpy as np

from qoblib_net import (BKV, CongestionOracle, parse_demand, parallel_tempering,
                        verify, write_solution)
from qoblib_net.topology import random_topology

QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))


def parse_range(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def one_run(job):
    n, seed, seconds, replicas, outdir = job
    demand = parse_demand(f"{QOBLIB}/08-network/instances/demand.txt", n)
    rng = np.random.default_rng(seed)
    # Every replica starts from an independently sampled random topology.  The
    # published reference solutions are never read: seeding a replica with the
    # incumbent record would let any method reproduce it and would make the
    # resulting numbers meaningless as a measure of the search.
    start = [random_topology(n, rng) for _ in range(replicas)]
    res = parallel_tempering(n, demand, seconds=seconds, replicas=replicas,
                             seed=seed, start=start)
    rec = {"instance": f"network{n:02d}", "n": n, "seed": seed,
           "best_lp": res["energy"], "published_bkv": BKV[n],
           "evals": res["evals"], "swaps": res["swaps"],
           "seconds": res["seconds"], "arcs": res["arcs"],
           "trajectory": res["trajectory"]}
    os.makedirs(outdir, exist_ok=True)
    json.dump(rec, open(f"{outdir}/network{n:02d}_seed{seed}.json", "w"), indent=1)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default="11-23")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--seconds", type=float, default=1800)
    ap.add_argument("--replicas", type=int, default=8)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--outdir", default="results/sweep")
    ap.add_argument("--skip-existing", action="store_true",
                    help="skip (instance, seed) pairs whose result file already "
                         "exists, so an interrupted sweep can be resumed")
    a = ap.parse_args()

    jobs = [(n, s, a.seconds, a.replicas, a.outdir)
            for n in parse_range(a.instances) for s in range(a.seeds)]
    if a.skip_existing:
        jobs = [j for j in jobs
                if not os.path.exists(f"{a.outdir}/network{j[0]:02d}_seed{j[1]}.json")]
    print(f"{len(jobs)} runs on {a.workers} workers, {a.seconds:.0f}s each "
          f"(~{len(jobs) * a.seconds / a.workers / 60:.0f} min wall clock)")

    t0 = time.time()
    with mp.Pool(a.workers) as pool:
        results = pool.map(one_run, jobs)
    print(f"sweep finished in {(time.time() - t0)/60:.1f} min")

    best = {}
    for r in results:
        if r["n"] not in best or r["best_lp"] < best[r["n"]]["best_lp"]:
            best[r["n"]] = r

    # The routing must be integral, so the achievable objective for a topology is
    # ceil(LP), not the LP value itself.  Comparing the raw LP against the
    # published integer value reports fractions of a unit as improvements.
    print(f"\n{'instance':<11}{'ceil(LP)':>12}{'published':>11}{'delta':>11}{'':>3}")
    print("-" * 48)
    wins = []
    for n in sorted(best):
        r = best[n]
        achievable = math.ceil(r["best_lp"] - 1e-6)
        delta = achievable - BKV[n]
        flag = "  <-- candidate improvement" if delta < 0 else ""
        if delta < 0:
            wins.append(n)
        print(f"network{n:02d}{achievable:>12d}{BKV[n]:>11}{delta:>+11d}{flag}")

    for n in wins:
        demand = parse_demand(f"{QOBLIB}/08-network/instances/demand.txt", n)
        orc = CongestionOracle(n, demand)
        z, flows, col = orc.integral(best[n]["arcs"], time_limit=600)
        if flows is None:
            print(f"network{n:02d}: integral routing failed, not submittable")
            continue
        path = f"{a.outdir}/network{n:02d}.sol"
        write_solution(path, n, best[n]["arcs"], z, flows, col)
        ok, obj, msg = verify(path, n, demand)
        verdict = ("IMPROVEMENT CONFIRMED" if ok and obj < BKV[n]
                   else f"not an improvement after integralisation ({msg})")
        print(f"network{n:02d}: integral objective {obj} vs {BKV[n]} -> {verdict}")


if __name__ == "__main__":
    main()
