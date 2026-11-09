#!/usr/bin/env python3
"""Build the submission rows only from the records of run_independent.py.

    python scripts/build_from_runs.py <runs dir> <submission dir> --date 2026-11-09 \
        --hardware "..." --reference <url at a fixed commit> --table <solutions/README.md>

Every field comes from a run record. Time to Solution is the mean over successful
runs of the wall clock time to the best value, Total Runtime the mean wall clock of
all runs, CPU Runtime the mean process CPU time of all runs. A successful run is one
that reaches the reported value. The script stops if a record is missing, invalid or
from another commit.
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
MODEL = "Reference binary quadratic model of bqp_u3_c10.zpl, searched as a chain over per period unit count portfolios"
WORKFLOW = ("Restricted state chain dynamic program. For each period, build a pool of good portfolios by exact integer local search "
 "(add, remove, swap and pair moves with exact incremental gains), exact subset enumeration over small groups of assets, and roundings "
 "of a Frank Wolfe relaxation, with neighbouring periods entering as separable rebalancing anchors. Run the exact chain dynamic program "
 "over the pools, then coordinate descent over periods with kicks and repeat. All coefficients are the exact integer coefficients of the "
 "reference model, so the checker agrees bit for bit. No published solution is used at any point.")
table = {}
for l in open(a.table):
    p = [x.strip() for x in l.split("|")]
    if len(p) > 5 and re.match(r"a\d{3}_", p[1]) and re.match(r"-?\d+$", p[2]):
        table[p[1]] = (int(p[2]), p[3])
recs = {}
for f in glob.glob(f"{a.runs}/a*_seed*.json"):
    r = json.load(open(f)); recs.setdefault(r["instance"], []).append(r)
commits = {r["commit"] for rs in recs.values() for r in rs}
if len(commits) != 1:
    raise SystemExit(f"runs come from several commits: {commits}")
for inst, rs in sorted(recs.items()):
    rs.sort(key=lambda r: r["seed"])
    ok = [r for r in rs if r["valid"]]
    if len(rs) < a.min_runs:
        raise SystemExit(f"{inst}: only {len(rs)} runs")
    if len(ok) != len(rs):
        raise SystemExit(f"{inst}: {len(rs) - len(ok)} invalid runs")
    best = min(r["objective"] for r in ok); top = [r for r in ok if r["objective"] == best]
    d = f"{a.sub}/{inst}"; os.makedirs(d, exist_ok=True)
    shutil.copyfile(f"{a.runs}/{inst}_seed{top[0]['seed']}.sol", f"{d}/{inst}_solution.sol")
    json.dump([r["series"] for r in ok], open(f"{d}/{inst}_objective_time_series.json", "w"))
    t = table.get(inst)
    note = "This instance has no entry in the best known table." if t is None else (
        f"Improves the table value {t[0]} ({t[1]})." if best < t[0] else
        f"Reaches the table value {t[0]} ({t[1]})." if best == t[0] else f"Does not reach the table value {t[0]} ({t[1]}); included so the gap is on record.")
    seeds = [r["seed"] for r in rs]
    seed_txt = f"seeds {seeds[0]} to {seeds[-1]}" if seeds == list(range(seeds[0], seeds[-1] + 1)) else "seeds " + ", ".join(map(str, seeds))
    rem = (f"{note} {len(rs)} independent runs from scratch, {seed_txt}, each run searching until it stops on its own (no time limit, no target). "
           f"Run values: {', '.join(str(r['objective']) for r in rs)}. Time to Solution is the mean wall clock time to the best value over the {len(top)} "
           "successful runs, which are the runs reaching the reported value. Total Runtime is the mean wall clock time and CPU Runtime the mean process "
           "CPU time over all runs, both including building the exact integer coefficients. Heuristic, so the optimality bound is N/A. Verified with 06-portfolio/check.")
    row = dict.fromkeys(COLUMNS, "N/A")
    row.update({"Problem": inst, "Submitter": "Manan Gupta", "Affiliation": "The Harker School", "Date": a.date, "Reference": a.reference,
                "Best Objective Value": best, "Modeling Approach": MODEL, "Workflow": WORKFLOW, "Algorithm Type": "Stochastic",
                "Paradigm": "Classical", "# Runs": len(rs), "# Feasible Runs": len(ok), "# Successful Runs": len(top), "Success Threshold": 0,
                "Hardware Specifications": a.hardware, "Total Runtime": round(st.mean(r["wall_seconds"] for r in rs), 1),
                "Time to Solution": round(st.mean(r["tts_wall"] for r in top), 1),
                "CPU Runtime": round(st.mean(r["cpu_seconds"] for r in rs), 1), "Remarks": rem})
    with open(f"{d}/{inst}_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerow(row)
print(len(recs), "rows from commit", commits.pop())
