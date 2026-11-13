#!/usr/bin/env python3
"""Build the submission rows only from the records of run_independent.py.

    python scripts/build_from_runs.py <runs dir> <submission dir> --date <date of the last run> \
        --hardware "..." --reference <url at a fixed commit> --table <solutions/README.md>

Every field comes from a run record. Time to Solution is the mean over successful
runs of the time from the start of the run until the best topology was found, Total
Runtime the mean wall clock of all runs and CPU Runtime the mean process CPU time of
all runs, both including the integral routing at the end. A successful run is one
that reaches the reported value. The script stops if a record is missing, invalid,
from another commit or from another search setting, if runs were not one at a
time, or if a run's final incumbent differs from its checked integral objective.

The model fields describe the reference model d3ver0int.zpl for n nodes: n(n-1)
arc variables, n(n-1)(n-1) flow variables and the congestion variable, and
n(n-1)(5n-3) non-zeros in the constraints. These match
08-network/models/integer_lp/lp_files and the 20250102_MIP_Schicker rows.
"""
import argparse, csv, glob, json, os, re, shutil, statistics as st
ap = argparse.ArgumentParser()
ap.add_argument("runs"); ap.add_argument("sub")
ap.add_argument("--date", required=True); ap.add_argument("--hardware", required=True)
ap.add_argument("--reference", required=True); ap.add_argument("--table", required=True)
ap.add_argument("--min-runs", type=int, default=5)
a = ap.parse_args()
COLUMNS = ["Problem","Submitter","Affiliation","Date","Reference","Best Objective Value","Optimality Bound",
 "Modeling Approach","# Decision Variables","# Binary Variables","# Integer Variables","# Continuous Variables",
 "# Non-Zero Coefficients","Coefficients Type","Coefficients Range","Workflow","Algorithm Type","Paradigm","# Runs",
 "# Feasible Runs","# Successful Runs","Success Threshold","Hardware Specifications","Total Runtime","Time to Solution",
 "CPU Runtime","GPU Runtime","QPU Runtime","Other HW Runtime","Remarks"]
MODEL = ("Reference integer multicommodity flow model of d3ver0int.zpl, decomposed into a topology search over 2-in/2-out "
         "digraphs with an exact min-congestion flow solved for each candidate")
WORKFLOW = ("Parallel tempering over 2-in/2-out digraphs with {r} replicas. The temperatures form a geometric ladder from 6% down to 0.2% "
 "of the best energy among the starting topologies. A move is a 2-exchange (85% of proposals) or a 3-exchange (15%) of arc heads, "
 "which keeps every in and out degree at 2. A proposal is discarded if it would create a loop or a repeated arc, or if the digraph "
 "is no longer strongly connected. Adjacent replicas try to swap every 40 proposals. The energy of a topology is the min-congestion "
 "multicommodity flow LP for it, solved with HiGHS on one thread. Every replica starts from a random 2-in/2-out topology drawn from "
 "the run's seed, and no published solution is read. At the end the integral routing of the best topology is computed once by "
 "solving the same model with integer flows, and the solution is checked with 08-network/check.")
table = {}
for l in open(a.table):
    p = [x.strip() for x in l.split("|")]
    if len(p) > 5 and re.match(r"network\d\d$", p[1]) and re.match(r"-?\d+$", p[2]):
        table[p[1]] = (int(p[2]), p[3])
recs = {}
for f in glob.glob(f"{a.runs}/network*_seed*.json"):
    r = json.load(open(f)); recs.setdefault(r["instance"], []).append(r)
commits = {r["commit"] for rs in recs.values() for r in rs}
settings = {(r["seconds_budget"], r["replicas"]) for rs in recs.values() for r in rs}
if len(commits) != 1 or len(settings) != 1:
    raise SystemExit(f"runs differ in commit or setting: {commits} {settings}")
meta = [json.loads(l) for l in open(f"{a.runs}/sweep_meta.jsonl")]
if any(m["workers"] != 1 or m["commit"] not in commits for m in meta):
    raise SystemExit(f"a sweep part ran with more than one worker or another commit: {meta}")
secs, reps = settings.pop()
for inst, rs in sorted(recs.items()):
    rs.sort(key=lambda r: r["seed"])
    ok = [r for r in rs if r["valid"]]
    if len(rs) < a.min_runs:
        raise SystemExit(f"{inst}: only {len(rs)} runs")
    if len(ok) != len(rs):
        raise SystemExit(f"{inst}: {len(rs) - len(ok)} invalid runs")
    for r in ok:
        if r["series"][-1]["Incumbent"] != r["objective"]:
            raise SystemExit(f"{inst} seed {r['seed']}: series ends at {r['series'][-1]['Incumbent']}, objective {r['objective']}")
    best = min(r["objective"] for r in ok); top = [r for r in ok if r["objective"] == best]
    n = rs[0]["n"]
    d = f"{a.sub}/{inst}"; os.makedirs(d, exist_ok=True)
    shutil.copyfile(f"{a.runs}/{inst}_seed{top[0]['seed']}.sol", f"{d}/{inst}_solution.sol")
    json.dump([r["series"] for r in ok], open(f"{d}/{inst}_objective_time_series.json", "w"))
    t = table.get(inst)
    note = "This instance has no entry in the best known table." if t is None else (
        f"Improves the table value {t[0]} ({t[1]})." if best < t[0] else
        f"Reaches the table value {t[0]} ({t[1]})." if best == t[0] else
        f"Does not reach the table value {t[0]} ({t[1]}); included so the method stays comparable.")
    seeds = [r["seed"] for r in rs]
    runs_word = "run" if len(top) == 1 else "runs"
    rem = (f"{note} Heuristic, so the optimality bound is N/A. {len(rs)} independent runs from scratch, seeds "
           f"{', '.join(map(str, seeds))}, each with {reps} replicas and {secs:.0f} s of search followed by the integral routing, "
           f"strictly one run at a time. Run values: {', '.join(str(r['objective']) for r in rs)}. Time to Solution is the mean time from "
           f"the start of the run until the best topology was found, over the {len(top)} successful {runs_word} (runs "
           "reaching the reported value); its integral routing is computed at the end of the run and takes under a second. Total Runtime "
           "is the mean wall clock time and CPU Runtime the mean process CPU time over all runs, both including the integral routing. Each "
           "run is single threaded, so CPU time stays just under wall time. The declared objective is recomputed from the flows rather "
           "than taken from the solver's z variable, which the model only bounds from below. Verified with 08-network/check.")
    row = dict.fromkeys(COLUMNS, "N/A")
    row.update({"Problem": inst, "Submitter": "Manan Gupta", "Affiliation": "The Harker School", "Date": a.date,
                "Reference": a.reference, "Best Objective Value": best, "Modeling Approach": MODEL,
                "# Decision Variables": n * (n - 1) * n + 1, "# Binary Variables": n * (n - 1),
                "# Integer Variables": n * (n - 1) ** 2 + 1, "# Continuous Variables": 0,
                "# Non-Zero Coefficients": n * (n - 1) * (5 * n - 3), "Coefficients Type": "Integer",
                "Coefficients Range": "1 - 1000000", "Workflow": WORKFLOW.format(r=reps), "Algorithm Type": "Stochastic",
                "Paradigm": "Classical", "# Runs": len(rs), "# Feasible Runs": len(ok), "# Successful Runs": len(top),
                "Success Threshold": 0, "Hardware Specifications": a.hardware,
                "Total Runtime": round(st.mean(r["wall_seconds"] for r in rs), 1),
                "Time to Solution": round(st.mean(r["tts_wall"] for r in top), 1),
                "CPU Runtime": round(st.mean(r["cpu_seconds"] for r in rs), 1), "Remarks": rem})
    with open(f"{d}/{inst}_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerow(row)
print(len(recs), "rows from commit", commits.pop())
