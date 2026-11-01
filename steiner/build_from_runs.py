#!/usr/bin/env python3
"""Build the submission rows only from the records of run_independent.py.

    python build_from_runs.py results/runs_nov <submission_dir> --date 2026-11-02 \
        --hardware "..." --reference <url at a fixed commit> --table <solutions/README.md>

Every field comes from a run record. Time to Solution is the mean over successful
runs of the wall clock time to the best value, Total Runtime the mean wall clock of
all runs, CPU Runtime the mean process CPU time of all runs. A successful run is one
that reaches the reported value. The script stops if a record is missing or invalid.
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
WORKFLOW = ("Negotiated congestion routing (PathFinder style rip up and reroute) builds a feasible packing: each net is routed as a greedy "
 "Steiner tree by multi source Dijkstra on node costs that grow with present and historical overuse, until no node is shared. Every net is "
 "then replaced in turn by a minimum Steiner tree of the grid with the other nets' nodes removed (Dreyfus Wagner recursion driven by Dijkstra, "
 "exact since nets have at most six terminals), repeated until no net improves. A large neighbourhood search then rips up two to four adjacent "
 "nets and re-inserts them exactly in every order, with small random node costs on the earlier nets and occasional random kicks, for a fixed "
 "time budget. The best packing seen is kept. No published solution is used at any point.")
table = {}
for l in open(a.table):
    p = [x.strip() for x in l.split("|")]
    if len(p) > 5 and p[1].startswith("stp_"):
        table[p[1]] = (int(p[2]), p[3])
recs = {}
for f in glob.glob(f"{a.runs}/stp_*_seed*.json"):
    r = json.load(open(f)); recs.setdefault(r["instance"], []).append(r)
commits = {r["commit"] for rs in recs.values() for r in rs}
if len(commits) != 1:
    raise SystemExit(f"runs come from several commits: {commits}")
for inst, rs in sorted(recs.items()):
    rs.sort(key=lambda r: r["seed"])
    ok = [r for r in rs if r["valid"]]
    if len(rs) < a.min_runs:
        raise SystemExit(f"{inst}: only {len(rs)} runs")
    if not ok:
        raise SystemExit(f"{inst}: no valid run")
    best = min(r["cost"] for r in ok); top = [r for r in ok if r["cost"] == best]
    d = f"{a.sub}/{inst}"; os.makedirs(d, exist_ok=True)
    shutil.copyfile(f"{a.runs}/{inst}_seed{top[0]['seed']}.sol", f"{d}/{inst}_solution.sol")
    json.dump([r["series"] for r in ok], open(f"{d}/{inst}_objective_time_series.json", "w"))
    t = table.get(inst)
    note = "This instance has no entry in the best known table." if t is None else (
        f"Improves the table value {t[0]}." if best < t[0] else
        f"Reaches the table value {t[0]} ({t[1]})." if best == t[0] else f"Does not reach the table value {t[0]} ({t[1]}).")
    rem = (f"{note} {len(rs)} independent runs from scratch, seeds {', '.join(str(r['seed']) for r in rs)}, with {rs[0]['lns_seconds']:.0f} s of neighbourhood search "
           f"after routing and exact polish. Run values: {', '.join(str(r['cost']) for r in rs)}. Time to Solution is the mean wall clock time to the best value over the {len(top)} "
           "successful runs, which are the runs reaching the reported value. Total Runtime is the mean wall clock time and CPU Runtime the mean process CPU time over all runs. "
           "The objective is the total arc cost of the routing. Verified with 04-steiner/check.")
    row = dict.fromkeys(COLUMNS, "N/A")
    row.update({"Problem": inst, "Submitter": "Manan Gupta", "Affiliation": "The Harker School", "Date": a.date, "Reference": a.reference,
                "Best Objective Value": best, "Modeling Approach": "No optimisation model is built, the method works directly on the routing graph",
                "Workflow": WORKFLOW, "Algorithm Type": "Stochastic", "Paradigm": "Classical", "# Runs": len(rs), "# Feasible Runs": len(ok),
                "# Successful Runs": len(top), "Success Threshold": 0, "Hardware Specifications": a.hardware,
                "Total Runtime": round(st.mean(r["wall_seconds"] for r in rs), 1), "Time to Solution": round(st.mean(r["tts_wall"] for r in top), 1),
                "CPU Runtime": round(st.mean(r["cpu_seconds"] for r in rs), 1), "Remarks": rem})
    with open(f"{d}/{inst}_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerow(row)
print(len(recs), "rows from commit", commits.pop())
