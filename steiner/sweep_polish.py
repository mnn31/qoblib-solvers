#!/usr/bin/env python3
"""Multistart negotiated congestion routing followed by exact polishing and
large neighbourhood search, for a list of Steiner packing instances.

    python sweep_polish.py open_instances.txt --seeds 8 --lns-seconds 300 \
        --workers 16 --outdir results/polished [--targets steiner_targets.tsv]

Every (instance, seed) pair is one job: route.py builds a feasible packing,
polish.py improves it, the official checker verifies it. Jobs run in a process
pool; the per instance record keeps every run so the submission can report
averages over independent runs. Output layout matches sweep_steiner.py.
"""
import argparse, csv, json, os, subprocess, sys, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
QOBLIB = os.environ.get("QOBLIB_ROOT", "/Users/manan/WORK/QOBLIB/repo")
INST = f"{QOBLIB}/04-steiner/instances"
CHK = os.environ.get("CHECK_STEINER", f"{QOBLIB}/04-steiner/check/target/release/check_steiner")


def valid(inst, sol):
    r = subprocess.run([CHK, "--arcs", f"{INST}/{inst}/arcs.dat", "--terms", f"{INST}/{inst}/terms.dat",
                        "--sol", sol], capture_output=True, text=True)
    return r.returncode == 0


def one(job):
    inst, seed, lns_seconds, tmp, init_dir = job
    import route, polish
    t0 = time.perf_counter()
    out = f"{tmp}/{inst}_seed{seed}.sol"
    log = open(f"{tmp}/{inst}_seed{seed}.log", "w")
    lg = lambda *a: print(*a, file=log, flush=True)
    try:
        init = f"{init_dir}/{inst}.sol" if init_dir else None
        if init and os.path.exists(init):
            trees = polish.read_solution(init)
            _, adj, _ = route.load_instance(f"{INST}/{inst}")
            lg(f"start from {init}")
        else:
            trees, adj = route.route(f"{INST}/{inst}", seed=seed, log=lg)
        if trees is None:
            return {"instance": inst, "seed": seed, "cost": None, "seconds": time.perf_counter() - t0,
                    "valid": False, "route_cost": None}
        route_cost = sum(adj[u][v] for k in trees for (u, v) in trees[k])
        trees, adj = polish.improve(f"{INST}/{inst}", trees, lns_seconds, seed, log=lg)
        c = route.write_solution(out, trees, adj)
        ok = valid(inst, out)
        return {"instance": inst, "seed": seed, "cost": c if ok else None, "seconds": time.perf_counter() - t0,
                "valid": ok, "route_cost": route_cost}
    except Exception as e:  # a crashed seed is an invalid run, not a dead sweep
        lg("EXC", repr(e))
        return {"instance": inst, "seed": seed, "cost": None, "seconds": time.perf_counter() - t0,
                "valid": False, "route_cost": None, "error": repr(e)}
    finally:
        log.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("listfile")
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--lns-seconds", type=float, default=300)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--outdir", default="results/polished")
    ap.add_argument("--targets", default=None, help="tsv with instance/ours/kaminski columns")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--init-dir", default=None, help="start every seed from <init-dir>/<inst>.sol if present")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    tmp = os.path.join(a.outdir, "tmp"); os.makedirs(tmp, exist_ok=True)
    targets = {}
    if a.targets:
        for r in csv.DictReader(open(a.targets), delimiter="\t"):
            targets[r["instance"]] = r
    insts = [l.strip() for l in open(a.listfile) if l.strip()]
    if a.skip_existing:
        insts = [i for i in insts if not os.path.exists(f"{a.outdir}/{i}.json")]
    # biggest instances first so the pool tail is short
    insts.sort(key=lambda i: -os.path.getsize(f"{INST}/{i}/arcs.dat"))
    jobs = [(i, s, a.lns_seconds, tmp, a.init_dir) for i in insts for s in range(a.seeds)]
    runs = {i: [] for i in insts}
    done = 0
    with Pool(a.workers) as pool:
        for rec in pool.imap_unordered(one, jobs):
            inst = rec["instance"]
            runs[inst].append(rec)
            done += 1
            if len(runs[inst]) == a.seeds:
                rs = sorted(runs[inst], key=lambda r: r["seed"])
                ok = [r for r in rs if r["valid"]]
                best = min(ok, key=lambda r: r["cost"]) if ok else None
                if best:
                    os.replace(f"{tmp}/{inst}_seed{best['seed']}.sol", f"{a.outdir}/{inst}.sol")
                for r in rs:
                    p = f"{tmp}/{inst}_seed{r['seed']}.sol"
                    if os.path.exists(p): os.remove(p)
                json.dump({"instance": inst, "best_cost": best["cost"] if best else None,
                           "runs": [{k: r[k] for k in ("seed", "cost", "seconds", "valid", "route_cost")} for r in rs]},
                          open(f"{a.outdir}/{inst}.json", "w"), indent=1)
                t = targets.get(inst)
                tag = ""
                if t:
                    his = t.get("kaminski") or "None"
                    ours = t.get("ours")
                    if best and his not in ("None", ""):
                        tag = "BEAT" if best["cost"] < int(his) else "tie" if best["cost"] == int(his) else "worse"
                    tag = f"  ours_before {ours} kaminski {his} -> {tag}"
                print(f"[{done}/{len(jobs)}] {inst}: best {best['cost'] if best else 'NONE'} "
                      f"(route {min((r['route_cost'] or 10**9) for r in rs)}) valid {len(ok)}/{len(rs)} "
                      f"{sum(r['seconds'] for r in rs):.0f}s{tag}", flush=True)
    print("=== SWEEP DONE ===", flush=True)


if __name__ == "__main__":
    main()
