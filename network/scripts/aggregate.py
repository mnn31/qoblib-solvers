#!/usr/bin/env python3
"""Pool the runs of a sweep, pick the best topology per instance, and write the
solution files and run statistics a submission needs.

    PYTHONPATH=. python scripts/aggregate.py --sweep results/sweep --outdir results/best

Produces:
    <outdir>/networkNN.sol          integral, checker-format, verified
    results/run_stats.json          per instance: runs, successes, runtimes,
                                    and the incumbent trajectory of every run
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import os

from qoblib_net import (BKV, CongestionOracle, parse_demand, verify,
                        write_solution)

QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))
DEMAND = f"{QOBLIB}/08-network/instances/demand.txt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="results/sweep")
    ap.add_argument("--outdir", default="results/best")
    ap.add_argument("--stats", default="results/run_stats.json")
    ap.add_argument("--keep-all", action="store_true",
                    help="also emit runs that do not beat the published value; "
                         "QOBLIB wants these on record so methods stay comparable")
    a = ap.parse_args()
    keep_all = a.keep_all

    runs = collections.defaultdict(list)
    for f in sorted(glob.glob(f"{a.sweep}/network*.json")):
        try:
            d = json.load(open(f))
        except json.JSONDecodeError as exc:
            print(f"  skipping unreadable {f}: {exc}")
            continue
        runs[d["n"]].append(d)

    os.makedirs(a.outdir, exist_ok=True)
    stats = {}
    print(f"{'instance':<11}{'runs':>5}{'best':>10}{'published':>11}{'delta':>10}")
    for n in sorted(runs):
        rs = runs[n]
        vals = [math.ceil(r["best_lp"] - 1e-6) for r in rs]
        best = min(vals)
        delta = best - BKV[n]
        print(f"network{n:02d}{len(rs):>5}{best:>10}{BKV[n]:>11}{delta:>+10}"
              f"{'  improves' if delta < 0 else ''}")
        if delta >= 0 and not keep_all:
            continue

        winner = rs[vals.index(best)]
        arcs = [tuple(int(x) for x in arc) for arc in winner["arcs"]]
        demand = parse_demand(DEMAND, n)
        orc = CongestionOracle(n, demand)
        z, flows, col = orc.integral(arcs, time_limit=900)
        if flows is None:
            print(f"  network{n:02d}: integral routing failed, skipped")
            continue
        path = f"{a.outdir}/network{n}.sol"
        write_solution(path, n, arcs, z, flows, col)
        ok, obj, msg = verify(path, n, demand)
        if not ok:
            print(f"  network{n:02d}: rejected after integralisation ({msg})")
            os.remove(path)
            continue
        if obj >= BKV[n] and not keep_all:
            print(f"  network{n:02d}: {obj} does not beat {BKV[n]}, not submitted")
            os.remove(path)
            continue

        # time to solution: when each run last improved its incumbent
        tts = [r["trajectory"][-2]["Time"] if len(r["trajectory"]) > 1
               else r["trajectory"][-1]["Time"] for r in rs]
        status = "improves" if obj < BKV[n] else ("matches" if obj == BKV[n] else "worse")
        stats[n] = {
            "objective": obj,
            "improves": bool(obj < BKV[n]),
            "status": status,
            "published": BKV[n],
            "nruns": len(rs),
            "nsucc": sum(1 for v in vals if v <= best),
            "avg_secs": sum(r["seconds"] for r in rs) / len(rs),
            "tts": sum(tts) / len(tts),
            "seeds": sorted(r["seed"] for r in rs),
            "trajectories": [r["trajectory"] for r in rs],
        }

    json.dump(stats, open(a.stats, "w"))
    from collections import Counter
    c = Counter(v["status"] for v in stats.values())
    print(f"\n{len(stats)} instances emitted: {c['improves']} improve, "
          f"{c['matches']} match, {c['worse']} worse; statistics written to {a.stats}")


if __name__ == "__main__":
    main()
