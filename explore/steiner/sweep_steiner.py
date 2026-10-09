#!/usr/bin/env python3
"""Route every listed Steiner instance with several seeds, keep the best
checker-valid solution per instance, and record per-seed costs and times.

    python sweep_steiner.py open_instances.txt --seeds 10 --outdir results/open

Strictly sequential, one route at a time, so the timings mean something. Every
kept solution is verified with the official checker before it is written down.
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
INST = "/Users/manan/WORK/QOBLIB/repo/04-steiner/instances"
CHK = os.path.join(HERE, "target/release/check_steiner")

def cost_of(path):
    for line in open(path):
        if line.startswith("# Cost:"):
            return int(line.split(":")[1])
    raise ValueError(f"no cost line in {path}")

def valid(inst, sol):
    r = subprocess.run([CHK, "--arcs", f"{INST}/{inst}/arcs.dat",
                        "--terms", f"{INST}/{inst}/terms.dat", "--sol", sol],
                       capture_output=True, text=True)
    return r.returncode == 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("listfile")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--outdir", default="results/open")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    tmp = os.path.join(a.outdir, "tmp"); os.makedirs(tmp, exist_ok=True)
    for inst in [l.strip() for l in open(a.listfile) if l.strip()]:
        rec_path = f"{a.outdir}/{inst}.json"
        if a.skip_existing and os.path.exists(rec_path):
            continue
        runs, best = [], None
        for seed in range(a.seeds):
            out = f"{tmp}/{inst}_seed{seed}.sol"
            t0 = time.perf_counter()
            subprocess.run([sys.executable, os.path.join(HERE, "route.py"),
                            f"{INST}/{inst}", out, "--seed", str(seed)],
                           check=True, capture_output=True)
            dt = time.perf_counter() - t0
            ok = valid(inst, out)
            c = cost_of(out) if ok else None
            runs.append({"seed": seed, "cost": c, "seconds": dt, "valid": ok})
            if ok and (best is None or c < best[0]):
                best = (c, out)
        if best:
            os.replace(best[1], f"{a.outdir}/{inst}.sol")
        for r in runs:  # clean the rest
            p = f"{tmp}/{inst}_seed{r['seed']}.sol"
            if os.path.exists(p): os.remove(p)
        json.dump({"instance": inst, "best_cost": best[0] if best else None,
                   "runs": runs}, open(rec_path, "w"), indent=1)
        print(f"{inst}: best {best[0] if best else 'NONE'}  "
              f"valid {sum(r['valid'] for r in runs)}/{len(runs)}  "
              f"{sum(r['seconds'] for r in runs):.1f}s", flush=True)

if __name__ == "__main__":
    main()
