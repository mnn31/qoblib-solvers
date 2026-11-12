#!/usr/bin/env python3
"""Independent seeded CP-SAT runs with full records, strictly one run at a time.

    python run_independent.py --list instances.txt --seeds 0,1,2,3,4 --seconds 600 \
        --workers 8 --outdir runs_2026-11

Each run builds the model from the instance alone, solves it with the given CP-SAT
seed, worker count and time limit, checks any timetable with check.py and writes one
json with the wall clock and process CPU time (all CP-SAT threads together, so CPU
time is above wall time when several workers run), the time to the first feasible
timetable and the objective time series. The objective is 0 for every feasible
timetable, so the series has one entry at the start and one when a timetable is
found. Existing records are skipped, so a stopped sweep can resume.
"""
import argparse, glob, json, os, platform, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))
COMMIT = subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def one(path, seed, seconds, workers, out):
    import ortools
    from robinx import read_instance, write_solution_sol, write_solution_xml
    from check import check
    from solve import solve
    w0, c0 = time.perf_counter(), time.process_time()
    inst = read_instance(path)
    info, games = solve(inst, seconds, workers, seed)
    wall, cpu = time.perf_counter() - w0, time.process_time() - c0
    r = {"instance": inst.name, "group": os.path.basename(os.path.dirname(path)), "seed": seed, "workers": workers,
         "seconds_limit": seconds, "status": info["status"], "feasible": games is not None, "valid": False,
         "objective": None, "wall_seconds": wall, "cpu_seconds": cpu, "build_seconds": info["build_seconds"],
         "solve_seconds": info["solve_seconds"], "teams": inst.n, "slots": inst.S, "phased": inst.phased,
         "hard_constraints": len(inst.hard()), "commit": COMMIT, "ortools": ortools.__version__,
         "python": platform.python_version(), "machine": platform.platform()}
    series = [{"Time": 0.0, "Incumbent": None}]
    if games is not None:
        viol = check(inst, games)
        r["valid"] = not viol
        if viol:
            r["violations"] = viol[:20]
        else:
            r["objective"] = 0
            series.append({"Time": round(wall, 3), "Incumbent": 0})
            stem = f"{out}/{inst.name}_seed{seed}"
            write_solution_sol(stem + ".sol", games, 0, f"instance {inst.name}\nCP-SAT feasibility, seed {seed}, {workers} workers")
            write_solution_xml(stem + ".xml", inst, games, "Manan Gupta")
    r["tts_wall"] = series[-1]["Time"] if r["valid"] else None
    r["series"] = series
    json.dump(r, open(f"{out}/{inst.name}_seed{seed}.json", "w"))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True, help="one instance name per line")
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--outdir", default="runs_2026-11")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    files = {os.path.basename(p)[:-7]: p for p in glob.glob(f"{QOBLIB}/05-sports/instances/*/*.xml.gz")}
    names = [l.split()[0] for l in open(a.list) if l.strip() and not l.startswith("#")]
    missing = [n for n in names if n not in files]
    if missing:
        raise SystemExit(f"unknown instances: {missing[:5]}")
    # seed major, smallest files first, so a stopped sweep leaves every instance with the same number of runs
    names.sort(key=lambda n: (os.path.getsize(files[n]), n))
    jobs = [(n, int(s)) for s in a.seeds.split(",") for n in names
            if not os.path.exists(f"{a.outdir}/{n}_seed{int(s)}.json")]
    meta = {"commit": COMMIT, "seconds": a.seconds, "workers": a.workers, "seeds": a.seeds, "list": a.list,
            "started": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "runs_queued": len(jobs)}
    with open(f"{a.outdir}/sweep_meta.jsonl", "a") as fh:
        fh.write(json.dumps(meta) + "\n")
    print(f"{len(jobs)} runs, one at a time, {a.workers} workers, {a.seconds:.0f} s limit", flush=True)
    for k, (n, s) in enumerate(jobs, 1):
        r = one(files[n], s, a.seconds, a.workers, a.outdir)
        print(f"[{k}/{len(jobs)}] {n} seed {s}: {r['status']} valid {r['valid']} wall {r['wall_seconds']:.1f} cpu {r['cpu_seconds']:.1f}", flush=True)
    print("=== RUNS DONE ===", flush=True)


if __name__ == "__main__":
    main()
