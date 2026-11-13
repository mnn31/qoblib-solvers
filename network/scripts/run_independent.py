#!/usr/bin/env python3
"""Independent parallel tempering runs with full records.

    python scripts/run_independent.py --instances 12,20,22,23,24 --seeds 0,1,2,3,4 \
        --seconds 7200 --replicas 8 --workers 1 --outdir runs_2026-11

One run per (instance, seed), each starting from random topologies drawn from its
seed; no published solution is read. Each run searches for a fixed wall clock
budget, then recovers an exact integral routing of its best topology, writes the
solution and checks it with 08-network/check. The json of each run has the wall
clock and process CPU time of the search and of the routing, the incumbent series,
the integral objective, the checker output and the load average of the machine at
the start and end of the run. Series times are seconds from the start of the run.
While the search runs, an entry is the ceiling of the routing LP value of the best
topology so far; the last entry is the checked integral objective at the end of the
run, after the routing. Existing records are skipped, so a stopped sweep can resume.
Use --workers 1 to run strictly one run at a time.
"""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[v] = "1"
import argparse, json, math, platform, subprocess, sys, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))
DEMAND = f"{QOBLIB}/08-network/instances/demand.txt"
CHECKER = f"{QOBLIB}/08-network/check/target/release/check_network"


def commit():
    return subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


COMMIT = commit()


def one(job):
    n, seed, seconds, replicas, out = job
    import numpy as np
    from qoblib_net import CongestionOracle, parse_demand, parallel_tempering, write_solution
    from qoblib_net.topology import random_topology
    iid = f"network{n:02d}"
    stem = f"{out}/{iid}_seed{seed}"
    r = {"instance": iid, "n": n, "seed": seed, "seconds_budget": seconds, "replicas": replicas,
         "objective": None, "valid": False, "commit": COMMIT, "python": platform.python_version(),
         "machine": platform.platform()}
    import highspy
    r["highs"] = highspy.Highs().version()
    r["load_start"] = os.getloadavg()
    w0, c0 = time.perf_counter(), time.process_time()
    try:
        demand = parse_demand(DEMAND, n)
        rng = np.random.default_rng(seed)
        start = [random_topology(n, rng) for _ in range(replicas)]
        res = parallel_tempering(n, demand, seconds=seconds, replicas=replicas, seed=seed, start=start)
        r["search_wall"] = time.perf_counter() - w0
        r["search_cpu"] = time.process_time() - c0
        r.update(best_lp=res["energy"], evals=res["evals"], swaps=res["swaps"], arcs=res["arcs"])
        # shift the search trajectory to seconds from the start of the run (the
        # search clock starts after the starting energies are evaluated)
        off = r["search_wall"] - res["seconds"]
        r["search_offset"] = off
        series = [{"Time": round(e["Time"] + off, 6), "Incumbent": e["Incumbent"]} for e in res["trajectory"]]
        w1, c1 = time.perf_counter(), time.process_time()
        z, flows, col = CongestionOracle(n, demand).integral(res["arcs"], time_limit=600)
        r["routing_wall"] = time.perf_counter() - w1
        r["routing_cpu"] = time.process_time() - c1
        if flows is None:
            r["error"] = "integral routing failed"
        else:
            write_solution(stem + ".sol", n, res["arcs"], z, flows, col)
            p = subprocess.run([CHECKER, str(n), DEMAND, stem + ".sol"], capture_output=True, text=True)
            out_lines = (p.stdout + p.stderr).strip().splitlines()
            r["checker"] = out_lines[-3:]
            r["valid"] = p.returncode == 0
            if r["valid"]:
                # the objective declared in the solution file, as confirmed by the checker
                r["objective"] = next(int(l.split(":")[1]) for l in out_lines if l.startswith("Solution objective value:"))
                # the end of the run, with the checked integral objective
                series.append({"Time": round(time.perf_counter() - w0, 6), "Incumbent": r["objective"]})
        r["series"] = series
        # time from the start of the run until the best topology was first found
        r["tts_wall"] = next(e["Time"] for e in series if e["Incumbent"] == series[-1]["Incumbent"])
    except Exception as e:
        r["error"] = repr(e)
    r["wall_seconds"] = time.perf_counter() - w0
    r["cpu_seconds"] = time.process_time() - c0
    r["load_end"] = os.getloadavg()
    json.dump(r, open(stem + ".json", "w"))
    return iid, seed, r["objective"], r.get("best_lp"), r["wall_seconds"], r["cpu_seconds"], r.get("tts_wall")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default="12,20,22,23,24")
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--seconds", type=float, default=7200)
    ap.add_argument("--replicas", type=int, default=8)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--outdir", default="runs_2026-11")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    inst = [int(x) for x in a.instances.split(",")]
    # seed major order, so a stopped sweep leaves every instance with the same number of runs
    jobs = [(n, int(s), a.seconds, a.replicas, a.outdir) for s in a.seeds.split(",") for n in inst
            if not os.path.exists(f"{a.outdir}/network{n:02d}_seed{int(s)}.json")]
    meta = {"commit": COMMIT, "seconds": a.seconds, "replicas": a.replicas, "workers": a.workers,
            "seeds": a.seeds, "instances": a.instances, "started": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "runs_queued": len(jobs)}
    with open(f"{a.outdir}/sweep_meta.jsonl", "a") as fh:
        fh.write(json.dumps(meta) + "\n")
    print(f"{len(jobs)} runs on {a.workers} workers", flush=True)
    with Pool(a.workers) as pool:
        for k, (iid, seed, obj, lp, wall, cpu, tts) in enumerate(pool.imap_unordered(one, jobs), 1):
            print(f"[{k}/{len(jobs)}] {iid} seed {seed}: {obj} (LP {lp}) wall {wall:.0f} cpu {cpu:.0f} tts {tts}", flush=True)
    print("=== RUNS DONE ===", flush=True)


if __name__ == "__main__":
    main()
