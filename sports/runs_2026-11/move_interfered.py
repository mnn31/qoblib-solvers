#!/usr/bin/env python3
"""Move sports run records whose run overlapped other work on the laptop into a side folder,
so run_independent.py runs them again. Windows are local times of 2026-11-12."""
import json, glob, os, shutil, datetime as dt
D = "/Users/manan/WORK/QOBLIB/work/sports_runs_nov"
SIDE = f"{D}/interfered_2026-11-12"
wins = [(dt.datetime(2026, 11, 12, 17, 15), dt.datetime(2026, 11, 12, 18, 15)),
        (dt.datetime(2026, 11, 12, 20, 15), dt.datetime(2026, 11, 12, 20, 50))]
os.makedirs(SIDE, exist_ok=True)
moved = []
for f in glob.glob(f"{D}/*_seed*.json"):
    r = json.load(open(f))
    end = dt.datetime.fromtimestamp(os.path.getmtime(f))
    start = end - dt.timedelta(seconds=r["wall_seconds"])
    if any(start < hi and end > lo for lo, hi in wins):
        stem = f[:-5]
        for ext in (".json", ".sol", ".xml"):
            if os.path.exists(stem + ext):
                shutil.move(stem + ext, SIDE)
        moved.append(f"{r['instance']} seed {r['seed']} {start:%H:%M:%S}-{end:%H:%M:%S}")
open(f"{SIDE}/moved.txt", "a").write("\n".join(sorted(moved)) + "\n")
print(len(moved), "runs moved for a clean rerun")
