#!/usr/bin/env python3
"""Independent seeded NuMVC runs on MIS instances, each solution checked with the official checker.
    mis_batch.py <outdir> <workers> <seconds> <seeds a,b,c> <inst1,inst2,...>"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
OUT, W, SEC, SEEDS, INSTS = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4].split(","), sys.argv[5].split(",")
R = "/Users/manan/WORK/QOBLIB/repo/07-independentset"; HERE = os.path.dirname(os.path.abspath(__file__))
CHK = f"{R}/check/target/release/check_stableset"
os.makedirs(OUT, exist_ok=True)
def run(job):
    inst, seed = job
    sol = f"{OUT}/{inst}_seed{seed}.sol"; t0 = time.time()
    p = subprocess.run([f"{HERE}/numvc", f"{R}/instances/{inst}.gph", sol, SEC, seed], capture_output=True, text=True)
    traj = [l.split() for l in p.stdout.splitlines() if l.strip()]
    c = subprocess.run([CHK, f"{R}/instances/{inst}.gph", sol], capture_output=True, text=True)
    size = int(traj[-1][1]) if traj else None
    rec = {"instance": inst, "seed": int(seed), "size": size, "tts": float(traj[-1][0]) if traj else None, "seconds": time.time() - t0,
           "checker_rc": c.returncode, "checker": (c.stdout + c.stderr).strip().splitlines()[-1:], "trajectory": traj}
    json.dump(rec, open(f"{OUT}/{inst}_seed{seed}.json", "w"))
    print(f"{inst} seed{seed}: {size} tts {rec['tts']} rc {c.returncode}", flush=True)
with ThreadPoolExecutor(W) as ex:
    list(ex.map(run, [(i, s) for i in INSTS for s in SEEDS]))
print("=== MIS BATCH DONE ===", flush=True)
