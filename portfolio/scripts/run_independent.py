#!/usr/bin/env python3
"""Independent runs of the restricted chain heuristic with full records.

    python scripts/run_independent.py --bases a050,a200,a400 --seeds 0,1,2,3,4,5,6,7,8,9 \
        --workers 5 --outdir results/runs_nov

One run per (instance, lambda, seed), each in a fresh process state: read the
instance, build the exact integer coefficients, then search with the parameters
in SEARCH until the search stops on its own (no time limit, no target). No run
reads a published solution or the output of another run. Each run writes one json
with the wall clock and process CPU time, the time to its best value and every
incumbent, plus its solution and the checker output. Existing records are skipped,
so a stopped sweep can resume.
"""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[v] = "1"
import argparse, json, platform, subprocess, sys, time
from fractions import Fraction
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, PKG)
QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))
CHECKER = f"{QOBLIB}/06-portfolio/check/target/release/check_portfolio"
BUDGET_BY_ASSETS = {3: 3, 4: 4, 5: 4, 10: 4, 50: 20, 200: 50, 400: 100}
# the larger search setting of the 2026-10-25 re-run, now used for every row
SEARCH = dict(rounds=8, kicks=6, chain_kicks=8, loo=16, lns_iters=96, lns_k=7, cd_lns_iters=8, seed_width=12)


def commit():
    return subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


COMMIT = commit()


def one(job):
    base, lam, seed, out = job
    from qoblib_portfolio.model import Coefficients, Instance
    from qoblib_portfolio.heuristic import solve_heuristic
    from qoblib_portfolio.solver import LAMBDA_TAG, objective, write_canonical
    inst_dir = f"{QOBLIB}/06-portfolio/instances/{base}"
    w0, c0 = time.perf_counter(), time.process_time()
    series = [{"Time": 0.0, "Incumbent": None}]
    cpu_at_best = [None]

    def rec(value):
        last = series[-1]["Incumbent"]
        if last is None or value < last:
            series.append({"Time": round(time.perf_counter() - w0, 3), "Incumbent": int(value)})
            cpu_at_best[0] = time.process_time() - c0

    inst = Instance(inst_dir)
    budget = BUDGET_BY_ASSETS[inst.n]
    iid = f"{base[3:]}_b{budget:03d}_{LAMBDA_TAG[lam]}"
    stem = f"{out}/{iid}_seed{seed}"
    r = {"instance": iid, "base": base, "lambda": lam, "budget": budget, "seed": seed, "objective": None,
         "valid": False, "search": SEARCH, "commit": COMMIT, "python": platform.python_version(), "machine": platform.platform()}
    try:
        coef = Coefficients(inst, budget, Fraction(lam))
        value, U, info = solve_heuristic(coef, seed=seed, on_change=rec, **SEARCH)
        assert objective(coef, U) == value
        r["wall_seconds"] = time.perf_counter() - w0
        r["cpu_seconds"] = time.process_time() - c0
        write_canonical(stem + ".sol", coef, U, base, lam, value,
                        comment="heuristic: restricted-state chain DP over per-period local optima, no optimality proof")
        p = subprocess.run([CHECKER, inst_dir, stem + ".sol"], capture_output=True, text=True)
        r["checker"] = (p.stdout + p.stderr).strip().splitlines()[-1:]
        r["valid"] = p.returncode == 0
        r["objective"] = int(value) if r["valid"] else None
        r["rounds"] = info["rounds"]
        r["pool_states"] = info["pool_states"]
    except Exception as e:
        r["error"] = repr(e)
        r["wall_seconds"] = time.perf_counter() - w0
        r["cpu_seconds"] = time.process_time() - c0
    best = [e for e in series if e["Incumbent"] is not None]
    r["tts_wall"] = best[-1]["Time"] if best else None
    r["tts_cpu"] = cpu_at_best[0]
    if best:
        series.append({"Time": round(r["wall_seconds"], 3), "Incumbent": best[-1]["Incumbent"]})
    r["series"] = series
    json.dump(r, open(stem + ".json", "w"))
    return iid, seed, r["objective"], r["wall_seconds"], r["cpu_seconds"], r["tts_wall"]


def main():
    from qoblib_portfolio.solver import LAMBDA_GRID, LAMBDA_TAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--bases", default="a050,a200,a400")
    ap.add_argument("--lambdas", default=",".join(LAMBDA_GRID))
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--outdir", default="results/runs_nov")
    ap.add_argument("--cells", help="file with one instance id per line; only these are run")
    a = ap.parse_args()
    cells = None if not a.cells else {l.split()[0] for l in open(a.cells) if l.strip() and l.startswith(("a0", "a2", "a4"))}
    os.makedirs(a.outdir, exist_ok=True)
    root = f"{QOBLIB}/06-portfolio/instances"
    bases = [d for d in sorted(os.listdir(root))
             if d.startswith("po_") and any(d.startswith(f"po_{p}") for p in a.bases.split(","))]
    jobs = []
    # cheapest families first, so a stopped sweep leaves whole families done
    for b in sorted(bases, key=lambda d: int(d.split("_")[1][1:])):
        n = int(b.split("_")[1][1:])
        for lam in a.lambdas.split(","):
            iid = f"{b[3:]}_b{BUDGET_BY_ASSETS[n]:03d}_{LAMBDA_TAG[lam]}"
            if cells is not None and iid not in cells:
                continue
            for s in a.seeds.split(","):
                if not os.path.exists(f"{a.outdir}/{iid}_seed{int(s)}.json"):
                    jobs.append((b, lam, int(s), a.outdir))
    meta = {"commit": COMMIT, "search": SEARCH, "workers": a.workers, "seeds": a.seeds, "bases": a.bases,
            "started": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "runs_queued": len(jobs)}
    with open(f"{a.outdir}/sweep_meta.jsonl", "a") as fh:
        fh.write(json.dumps(meta) + "\n")
    print(f"{len(jobs)} runs on {a.workers} workers", flush=True)
    with Pool(a.workers) as pool:
        for n, (iid, seed, val, wall, cpu, tts) in enumerate(pool.imap_unordered(one, jobs), 1):
            print(f"[{n}/{len(jobs)}] {iid} seed {seed}: {val} wall {wall:.0f} cpu {cpu:.0f} tts {tts}", flush=True)
    print("=== RUNS DONE ===", flush=True)


if __name__ == "__main__":
    main()
