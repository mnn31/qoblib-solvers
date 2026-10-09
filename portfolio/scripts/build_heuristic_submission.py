#!/usr/bin/env python3
"""Assemble the QOBLIB submission for the heuristic (restricted state chain DP)
runs on the large portfolio families. Picks the best of the seeds per instance.

    python build_heuristic_submission.py --results results/heuristic_open_seed0 \
        results/heuristic_open_seed1 results/heuristic_open_seed2 results/heuristic_a050 --out /tmp/sub06h
"""
import argparse, csv, glob, json, os, re, shutil
from collections import defaultdict

COLUMNS = ["Problem","Submitter","Affiliation","Date","Reference","Best Objective Value",
 "Optimality Bound","Modeling Approach","# Decision Variables","# Binary Variables",
 "# Integer Variables","# Continuous Variables","# Non-Zero Coefficients","Coefficients Type",
 "Coefficients Range","Workflow","Algorithm Type","Paradigm","# Runs","# Feasible Runs",
 "# Successful Runs","Success Threshold","Hardware Specifications","Total Runtime",
 "Time to Solution","CPU Runtime","GPU Runtime","QPU Runtime","Other HW Runtime","Remarks"]
SUBMITTER = "Manan Gupta"; AFFILIATION = "The Harker School"
REFERENCE = "https://github.com/mnn31/qoblib-solvers/tree/main/portfolio"
DATE = "2026-10-09"; DATE_TAG = "20261009"
HARDWARE = ("Cloud CPU instance: 16 vCPU slice of an AMD EPYC 9655 host, 755 GB RAM visible, "
            "Ubuntu 24.04, Python 3.12, no GPU. Runs executed one at a time within the instance, "
            "but the host is shared with other tenants and showed high load, so wall clock "
            "times are indicative only.")
WORKFLOW = ("Restricted state chain dynamic program. For each period, build a pool of good "
            "portfolios by exact integer local search (add, remove, swap and pair moves with "
            "exact incremental gains), exact subset enumeration over small groups of assets, and "
            "roundings of a Frank Wolfe relaxation, with neighbouring periods entering as separable "
            "rebalancing anchors. Run the exact chain dynamic program over the pools, then "
            "coordinate descent over periods with kicks and repeat. All coefficients are the exact "
            "integer coefficients of the reference model, so the checker agrees bit for bit.")
README = """# Restricted state chain dynamic program for the large portfolio families

The exact chain dynamic program in the ChainDP submission enumerates every
feasible per period portfolio, which is impossible for a050 and above. This
submission keeps the chain structure but restricts each period to a pool of good
portfolios found by exact integer local search, exact subset enumeration and
relaxation roundings, runs the exact chain dynamic program over the pools, and
polishes by coordinate descent. The method is a heuristic and claims no
optimality.

Validation before any of this was produced: it matches the proven optimum on all
160 instances of the a003 to a010 families, and on a050 it is within a few
hundredths of a percent of the published values at low lambda and clearly worse
at the two highest lambdas, where the published values come from a MIP solver.
Those a050 runs are included here so the gap is on record.

The a200 and a400 families had no feasible solution on record. Every solution
here was verified with 06-portfolio/check as it was produced.

Code: https://github.com/mnn31/qoblib-solvers/tree/main/portfolio
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--published", default=os.path.expanduser("~/WORK/QOBLIB/repo/06-portfolio/solutions/README.md"))
    a = ap.parse_args()
    pub = {}
    for line in open(a.published):
        m = re.match(r"^\|\s*(a\d+_t\d+_\S+)\s*\|\s*(-?\d+)\s*\|", line)
        if m: pub[m.group(1)] = int(m.group(2))
    runs = defaultdict(list)
    for rd in a.results:
        for rec in json.load(open(f"{rd}/summary.json")):
            rec["_dir"] = rd; runs[rec["instance"]].append(rec)
    root = f"{a.out}/{DATE_TAG}_RestrictedChainDP_Gupta"; os.makedirs(root, exist_ok=True)
    open(f"{root}/README.md", "w").write(README)
    made = 0
    for iid, rs in sorted(runs.items()):
        best = min(rs, key=lambda r: r["objective"]); b = best["objective"]
        p = pub.get(iid)
        status = "open" if p is None else ("improves" if b < p else ("matches" if b == p else "worse"))
        note = {"open": "No feasible solution was on record for this instance before this submission. ",
                "improves": f"Improves the published value {p}. ",
                "matches": "Reaches the published value exactly without improving it. ",
                "worse": f"Does not reach the published value {p}; included so the gap is on record. "}[status]
        d = f"{root}/{iid}"; os.makedirs(d, exist_ok=True)
        shutil.copy(f"{best['_dir']}/{best['solution']}", f"{d}/{iid}_solution.sol")
        secs = sum(r["seconds"] for r in rs) / len(rs)
        row = {c: "N/A" for c in COLUMNS}
        row.update({"Problem": iid, "Submitter": SUBMITTER, "Affiliation": AFFILIATION, "Date": DATE,
            "Reference": REFERENCE, "Best Objective Value": b, "Optimality Bound": "N/A",
            "Modeling Approach": "Reference binary quadratic model of bqp_u3_c10.zpl, searched as a chain over per period unit count portfolios",
            "Workflow": WORKFLOW, "Algorithm Type": "Stochastic", "Paradigm": "Classical",
            "# Runs": len(rs), "# Feasible Runs": len(rs),
            "# Successful Runs": sum(1 for r in rs if r["objective"] == b), "Success Threshold": 0,
            "Hardware Specifications": HARDWARE, "Total Runtime": round(secs, 1),
            "Time to Solution": round(secs, 1), "CPU Runtime": round(secs, 1),
            "Remarks": note + "Heuristic, so the optimality bound is N/A. Runtimes are the average over the seeds and include building the exact integer coefficients. Successful runs are those reaching this method's own best value. Verified with 06-portfolio/check."})
        with open(f"{d}/{iid}_summary.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerow(row)
        made += 1
    print(f"built {made} instance directories under {root}")

if __name__ == "__main__":
    main()
