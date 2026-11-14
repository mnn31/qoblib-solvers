#!/usr/bin/env python3
"""Build the problem 05 submission rows only from the records of run_independent.py.

    python build_from_runs.py <runs dir> <submission dir> --date <submission date> \
        --hardware "..." --reference <url at a fixed commit> --table <05-sports/solutions/README.md>

One row per instance with at least one run that found a valid timetable. Every field
comes from the run records: # Runs is the number of runs, # Feasible Runs and
# Successful Runs the runs with a timetable that check.py accepts, Total Runtime the
mean wall clock time of all runs (a run without a timetable counts with its full
time), CPU Runtime the mean process CPU time of all runs (all CP-SAT worker threads
together), Time to Solution the mean wall clock time of the successful runs. The
solution is the one of the fastest successful run. The time series holds every run;
a run without a timetable is a null incumbent from start to end. The script stops if
a record is missing or comes from another commit, OR-Tools version or setting, if a
sweep part ran with another setting, or if a timetable fails the checker again.
Instances without any successful run are listed and get no row.
"""
import argparse, csv, glob, json, os, re, shutil, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from robinx import read_instance, read_solution_sol  # noqa: E402
from check import check  # noqa: E402

QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))
COLUMNS = ["Problem","Submitter","Affiliation","Date","Reference","Best Objective Value","Optimality Bound",
 "Modeling Approach","# Decision Variables","# Binary Variables","# Integer Variables","# Continuous Variables",
 "# Non-Zero Coefficients","Coefficients Type","Coefficients Range","Workflow","Algorithm Type","Paradigm","# Runs",
 "# Feasible Runs","# Successful Runs","Success Threshold","Hardware Specifications","Total Runtime","Time to Solution",
 "CPU Runtime","GPU Runtime","QPU Runtime","Other HW Runtime","Remarks"]
MODEL = ("Constraint programming model of the hard constraints on binary game, home and break indicator variables; "
         "no objective.")
WORKFLOW = ("Constraint programming. The hard constraints of the instance (round robin structure, phases, CA1 to CA4, GA1, "
            "BR1, BR2) are posted directly on binary game variables x[home,away,slot] plus home and break indicators, with "
            "no objective. OR-Tools CP-SAT runs its default portfolio with {w} workers and a fixed seed until a feasible "
            "timetable is found or the time limit of {t:.0f} s expires. Soft constraints are ignored, as the benchmark "
            "specifies. Every timetable is checked by an independent checker before it is reported.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs"); ap.add_argument("sub")
    ap.add_argument("--date", required=True); ap.add_argument("--hardware", required=True)
    ap.add_argument("--reference", required=True); ap.add_argument("--table", required=True)
    ap.add_argument("--list", default=os.path.join(HERE, "rerun_2026-11.txt"))
    ap.add_argument("--seeds", default="0,1,2,3,4")
    a = ap.parse_args()
    files = {os.path.basename(p)[:-7]: p for p in glob.glob(f"{QOBLIB}/05-sports/instances/*/*.xml.gz")}
    names = [l.split()[0] for l in open(a.list) if l.strip() and not l.startswith("#")]
    seeds = [int(s) for s in a.seeds.split(",")]
    table = {}
    for l in open(a.table):
        p = [x.strip() for x in l.split("|")]
        if len(p) > 5 and re.match(r"-?\d+$", p[2]):
            table[p[1]] = (int(p[2]), p[3])
    meta = [json.loads(l) for l in open(f"{a.runs}/sweep_meta.jsonl")]
    recs, keys = {}, set()
    for n in names:
        for s in seeds:
            f = f"{a.runs}/{n}_seed{s}.json"
            if not os.path.exists(f):
                raise SystemExit(f"missing record {f}")
            r = json.load(open(f)); recs.setdefault(n, []).append(r)
            keys.add((r["commit"], r["ortools"], r["workers"], r["seconds_limit"]))
    if len(keys) != 1:
        raise SystemExit(f"runs differ in commit, OR-Tools version or setting: {keys}")
    commit, ortools, workers, limit = keys.pop()
    if any((m["commit"], m["workers"], m["seconds"]) != (commit, workers, limit) for m in meta):
        raise SystemExit(f"a sweep part ran with another setting: {meta}")
    unsolved, rows = [], 0
    for n in names:
        rs = recs[n]
        ok = [r for r in rs if r["valid"]]
        if any(r["feasible"] and not r["valid"] for r in rs):
            raise SystemExit(f"{n}: a timetable was rejected by the checker")
        if not ok:
            unsolved.append(n); continue
        inst = read_instance(files[n])
        for r in ok:  # check every reported timetable again from its file
            if check(inst, read_solution_sol(f"{a.runs}/{n}_seed{r['seed']}.sol")):
                raise SystemExit(f"{n} seed {r['seed']}: solution file fails the checker")
        fast = min(ok, key=lambda r: r["wall_seconds"])
        d = f"{a.sub}/{n}"; os.makedirs(d, exist_ok=True)
        shutil.copyfile(f"{a.runs}/{n}_seed{fast['seed']}.sol", f"{d}/{n}_solution.sol")
        series = []
        for r in rs:
            sr = list(r["series"])
            if not r["valid"]:
                sr.append({"Time": round(r["wall_seconds"], 3), "Incumbent": None})
            series.append(sr)
        json.dump(series, open(f"{d}/{n}_objective_time_series.json", "w"))
        nt, S = inst.n, inst.S
        breaks = any(c.tag in ("BR1", "BR2") for c in inst.hard())
        nvars = nt * (nt - 1) * S + nt * S + (2 * nt * (S - 1) if breaks else 0)
        t = table.get(n)
        note = ("This instance has no entry in the best known table." if t is None else
                f"Reaches the table value {t[0]} ({t[1]}).")
        walls = ", ".join(f"{r['wall_seconds']:.1f} s" if r["valid"] else f"no timetable in {r['wall_seconds']:.0f} s"
                          for r in rs)
        low = ("Runs of a fraction of a second are partly idle (for example while the worker threads start and "
               "stop), so CPU time can come out below wall clock time. ") if any(r["cpu_seconds"] < r["wall_seconds"] for r in rs) else ""
        rem = (f"{note} Pure feasibility problem: the objective is 0 for any timetable that satisfies all hard "
               f"constraints, so 0 is also the bound. {nt} teams, {S} slots, {'phased' if inst.phased else 'not phased'}, "
               f"{len(inst.hard())} hard constraints. {len(rs)} independent runs, CP-SAT seeds "
               f"{', '.join(str(r['seed']) for r in rs)}, {workers} workers and a {limit:.0f} s limit each, strictly one "
               f"run at a time; {len(ok)} of {len(rs)} found a timetable. Wall clock per run, model build included: {walls}. "
               "Time to Solution is the mean wall clock time of the runs that found a timetable. Total Runtime is the mean "
               "wall clock time and CPU Runtime the mean process CPU time over all runs; CPU time adds up all CP-SAT "
               f"worker threads, so with {workers} workers it is up to about {workers} times the wall clock time. "
               f"{low}Runtimes are rounded to 0.01 s here and to 0.1 s in the list above (runs without a timetable to 1 s). "
               "The solution file is the timetable of the fastest run. Checked with an independent checker that accepts "
               f"all 249 reference solutions in 05-sports/solutions.")
        row = dict.fromkeys(COLUMNS, "N/A")
        row.update({"Problem": n, "Submitter": "Manan Gupta", "Affiliation": "The Harker School", "Date": a.date,
                    "Reference": a.reference, "Best Objective Value": 0, "Optimality Bound": 0, "Modeling Approach": MODEL,
                    "# Decision Variables": nvars, "# Binary Variables": nvars, "# Integer Variables": 0,
                    "# Continuous Variables": 0, "Workflow": WORKFLOW.format(w=workers, t=limit),
                    "Algorithm Type": "Stochastic", "Paradigm": "Classical", "# Runs": len(rs), "# Feasible Runs": len(ok),
                    "# Successful Runs": len(ok), "Success Threshold": 0, "Hardware Specifications": a.hardware,
                    "Total Runtime": round(st.mean(r["wall_seconds"] for r in rs), 2),
                    "Time to Solution": round(st.mean(r["wall_seconds"] for r in ok), 2),
                    "CPU Runtime": round(st.mean(r["cpu_seconds"] for r in rs), 2), "Remarks": rem})
        with open(f"{d}/{n}_summary.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerow(row)
        rows += 1
    print(f"{rows} rows from commit {commit[:7]}, OR-Tools {ortools}, {workers} workers, {limit:.0f} s")
    print(f"{len(unsolved)} instances without a timetable in any run: {', '.join(unsolved)}")


if __name__ == "__main__":
    main()
