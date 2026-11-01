#!/usr/bin/env python3
"""Fixed budget runs for the LABS rows, with the whole incumbent history.
    python run_runs.py <outdir> <workers> <seconds> <seeds a,b,c> <length:mode ...>
No run is told the best known energy: the target passed to lss is 0, which no
sequence reaches, so every run uses its full budget."""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
out, wk, secs, seeds = sys.argv[1], int(sys.argv[2]), sys.argv[3], [int(s) for s in sys.argv[4].split(",")]
os.makedirs(out, exist_ok=True)
commit = subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
def run(job):
    n, mode, seed = job
    sol = f"{out}/labs{n:03d}_seed{seed}.sol"
    p = subprocess.run([f"{HERE}/lss", str(n), mode, sol, secs, str(seed), "0", "8", "40"], capture_output=True, text=True)
    series, end = [], None
    for l in p.stdout.splitlines():
        f = l.split()
        if f[0] == "END":
            end = dict(wall=float(f[1]), best=int(f[2]), cpu=float(f[4]))
        else:
            series.append(dict(Time=float(f[0]), Incumbent=int(f[1]), cpu=float(f[5])))
    best = series[-1]
    rec = dict(n=n, mode=mode, seed=seed, budget=float(secs), energy=end["best"], wall=end["wall"], cpu=end["cpu"], tts=best["Time"], tts_cpu=best["cpu"],
               series=[dict(Time=e["Time"], Incumbent=e["Incumbent"]) for e in series] + [dict(Time=end["wall"], Incumbent=end["best"])], commit=commit)
    json.dump(rec, open(sol.replace(".sol", ".json"), "w"))
    print(f"labs{n:03d} seed{seed}: {rec['energy']} tts {rec['tts']:.1f}", flush=True)
jobs = [(int(s.split(":")[0]), s.split(":")[1], seed) for s in sys.argv[5:] for seed in seeds]
with ThreadPoolExecutor(wk) as ex:
    list(ex.map(run, jobs))
print("=== LABS RUNS DONE ===", flush=True)
