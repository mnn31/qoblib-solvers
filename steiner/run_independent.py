#!/usr/bin/env python3
"""Independent runs of the Steiner packing pipeline with full records.

    python run_independent.py instances.txt --seeds 0,1,2,3,4 --lns-seconds 600 \
        --small-seconds 120 --workers 5 --outdir results/runs_nov

Every run starts from nothing: routing, exact polish, then neighbourhood search
for a fixed budget. No run reads a published solution or the output of another
run. Each (instance, seed) writes one json with the wall clock and process CPU
time of the run, the time to its best value, and every incumbent, plus its
solution and log. Existing records are skipped, so a stopped sweep can resume.
"""
import argparse, json, os, platform, subprocess, sys, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
QOBLIB = os.environ.get("QOBLIB_ROOT", "/Users/manan/WORK/QOBLIB/repo")
INST = f"{QOBLIB}/04-steiner/instances"
CHK = os.environ.get("CHECK_STEINER", f"{QOBLIB}/04-steiner/check/target/release/check_steiner")
SMALL_ARCS_BYTES = 157000      # the 29 smallest instances by arc file size get the short budget


def commit():
    return subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def valid(inst, sol):
    return subprocess.run([CHK, "--arcs", f"{INST}/{inst}/arcs.dat", "--terms", f"{INST}/{inst}/terms.dat",
                           "--sol", sol], capture_output=True, text=True).returncode == 0


def one(job):
    inst, seed, budget, out = job
    import route, polish
    base = f"{out}/{inst}_seed{seed}"
    log = open(base + ".log", "w")
    lg = lambda *a: print(*a, file=log, flush=True)
    w0, c0 = time.perf_counter(), time.process_time()
    series = [{"Time": 0.0, "Incumbent": None}]
    cpu_at_best = [None]

    def rec(cost):
        last = series[-1]["Incumbent"]
        if last is None or cost < last:
            series.append({"Time": round(time.perf_counter() - w0, 3), "Incumbent": cost})
            cpu_at_best[0] = time.process_time() - c0

    r = {"instance": inst, "seed": seed, "lns_seconds": budget, "cost": None, "valid": False,
         "commit": COMMIT, "python": platform.python_version(), "machine": platform.platform()}
    try:
        trees, adj = route.route(f"{INST}/{inst}", seed=seed, log=lg)
        if trees is not None:
            r["route_cost"] = sum(adj[u][v] for k in trees for (u, v) in trees[k])
            rec(r["route_cost"])
            trees, adj = polish.improve(f"{INST}/{inst}", trees, budget, seed, log=lg, on_change=rec)
            c = route.write_solution(base + ".sol", trees, adj)
            r["valid"] = valid(inst, base + ".sol")
            r["cost"] = c if r["valid"] else None
    except Exception as e:
        lg("EXC", repr(e))
        r["error"] = repr(e)
    log.close()
    r["wall_seconds"] = time.perf_counter() - w0
    r["cpu_seconds"] = time.process_time() - c0
    best = [e for e in series if e["Incumbent"] is not None]
    r["tts_wall"] = best[-1]["Time"] if best else None
    r["tts_cpu"] = cpu_at_best[0]
    if best:
        series.append({"Time": round(r["wall_seconds"], 3), "Incumbent": best[-1]["Incumbent"]})
    r["series"] = series
    json.dump(r, open(base + ".json", "w"))
    return inst, seed, r["cost"], r["wall_seconds"], r["cpu_seconds"], r["tts_wall"]


COMMIT = commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("listfile")
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--lns-seconds", type=float, default=600)
    ap.add_argument("--small-seconds", type=float, default=120)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--outdir", default="results/runs_nov")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    insts = [l.strip() for l in open(a.listfile) if l.strip()]
    insts.sort(key=lambda i: os.path.getsize(f"{INST}/{i}/arcs.dat"))
    jobs = []
    for i in insts:
        small = os.path.getsize(f"{INST}/{i}/arcs.dat") < SMALL_ARCS_BYTES
        for s in a.seeds.split(","):
            if not os.path.exists(f"{a.outdir}/{i}_seed{int(s)}.json"):
                jobs.append((i, int(s), a.small_seconds if small else a.lns_seconds, a.outdir))
    json.dump({"commit": COMMIT, "workers": a.workers, "seeds": a.seeds, "lns_seconds": a.lns_seconds,
               "small_seconds": a.small_seconds, "started": time.strftime("%Y-%m-%d %H:%M:%S %Z")},
              open(f"{a.outdir}/sweep_meta.json", "w"), indent=1)
    print(f"{len(jobs)} runs on {a.workers} workers", flush=True)
    with Pool(a.workers) as pool:
        for n, (inst, seed, cost, wall, cpu, tts) in enumerate(pool.imap_unordered(one, jobs), 1):
            print(f"[{n}/{len(jobs)}] {inst} seed {seed}: {cost} wall {wall:.0f} cpu {cpu:.0f} tts {tts}", flush=True)
    print("=== RUNS DONE ===", flush=True)


if __name__ == "__main__":
    main()
