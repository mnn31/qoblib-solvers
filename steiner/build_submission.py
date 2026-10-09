#!/usr/bin/env python3
"""Assemble the QOBLIB submission directory for problem 04 from sweep results.

    python build_submission.py --results results/open results/bestknown --out /tmp/sub04

Each instance directory gets <inst>_summary.csv and <inst>_solution.sol. The
method builds no optimisation model, so the variable fields describe the emitted
routing (one integer per routed arc per net) and the coefficient fields are N/A,
following the convention agreed on the Birkhoff submission.
"""
import argparse, csv, json, os, shutil

COLUMNS = ["Problem","Submitter","Affiliation","Date","Reference","Best Objective Value",
 "Optimality Bound","Modeling Approach","# Decision Variables","# Binary Variables",
 "# Integer Variables","# Continuous Variables","# Non-Zero Coefficients","Coefficients Type",
 "Coefficients Range","Workflow","Algorithm Type","Paradigm","# Runs","# Feasible Runs",
 "# Successful Runs","Success Threshold","Hardware Specifications","Total Runtime",
 "Time to Solution","CPU Runtime","GPU Runtime","QPU Runtime","Other HW Runtime","Remarks"]

SUBMITTER = "Manan Gupta"; AFFILIATION = "The Harker School"
REFERENCE = "https://github.com/mnn31/qoblib-solvers/tree/main/steiner"
DATE = "2026-10-09"; DATE_TAG = "20261009"
HARDWARE = ("Apple M3 Pro (Mac15,6), 11 cores (5 performance + 6 efficiency), 18 GB unified "
            "memory, macOS 26.3, arm64. Runs executed strictly one at a time on an otherwise "
            "idle machine.")
WORKFLOW = ("Negotiated congestion routing (PathFinder style rip up and reroute). Each net is "
            "routed as a greedy Steiner tree by multi source Dijkstra from the partial tree to "
            "the nearest unconnected terminal. Node cost is base cost plus present overuse times "
            "a pressure factor that grows by 1.5 each iteration, plus an accumulated history "
            "penalty; iterate until no node is shared by two nets. Then prune non terminal leaves "
            "and run three cost polish passes rerouting each net with the other nets' nodes "
            "forbidden. Routing order is shuffled by the seed.")
README = """# Negotiated congestion routing for the Steiner tree packing instances

A PathFinder style rip up and reroute router, the standard method for switchbox
and channel routing in VLSI. Each net is routed as a greedy Steiner tree; nodes
used by more than one net accumulate a congestion penalty that grows every
iteration until the nets separate. Three cost polish passes follow.

No optimisation model is built. The reference formulation for this class is a
multicommodity flow MIP with millions of variables, which is why most instances
had no solution on record; the graphs themselves are small for a router, and
every instance here routes in seconds.

Every reported solution was verified with 04-steiner/check. Runs that do not
improve on a published value are included so the method stays comparable.

Code: https://github.com/mnn31/qoblib-solvers/tree/main/steiner
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--published", default="/Users/manan/WORK/QOBLIB/repo/04-steiner/solutions/README.md")
    a = ap.parse_args()
    pub = {}
    for line in open(a.published):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) > 3 and parts[1].startswith("stp_"):
            try: pub[parts[1]] = (int(parts[2]), parts[3])
            except ValueError: pass
    root = f"{a.out}/{DATE_TAG}_NegotiatedCongestion_Gupta"; os.makedirs(root, exist_ok=True)
    open(f"{root}/README.md", "w").write(README)
    made = 0
    for rd in a.results:
        for f in sorted(os.listdir(rd)):
            if not f.endswith(".json"): continue
            rec = json.load(open(f"{rd}/{f}")); inst = rec["instance"]
            if rec["best_cost"] is None: continue
            sol = f"{rd}/{inst}.sol"
            runs = rec["runs"]; valid = [r for r in runs if r["valid"]]
            best = rec["best_cost"]; nsucc = sum(1 for r in valid if r["cost"] == best)
            arcs_used = sum(1 for l in open(sol) if l.strip() and not l.startswith("#"))
            p = pub.get(inst)
            if p is None: status = "open"
            elif best < p[0]: status = "improves"
            elif best == p[0]: status = "matches"
            else: status = "worse"
            note = {"open": "No feasible solution was on record for this instance before this submission. ",
                    "improves": f"Improves the published value {p[0] if p else ''}. ",
                    "matches": f"Reaches the published value exactly without improving it. ",
                    "worse": f"Does not reach the published value {p[0] if p else ''}; included so the method stays comparable. "}[status]
            d = f"{root}/{inst}"; os.makedirs(d, exist_ok=True)
            shutil.copy(sol, f"{d}/{inst}_solution.sol")
            row = {c: "N/A" for c in COLUMNS}
            row.update({"Problem": inst, "Submitter": SUBMITTER, "Affiliation": AFFILIATION,
                "Date": DATE, "Reference": REFERENCE, "Best Objective Value": best,
                "Optimality Bound": "N/A",
                "Modeling Approach": "No optimisation model is built. Routing heuristic on the arc graph; variable counts describe the emitted routing.",
                "# Decision Variables": arcs_used, "# Binary Variables": 0,
                "# Integer Variables": arcs_used, "# Continuous Variables": 0,
                "Workflow": WORKFLOW, "Algorithm Type": "Stochastic", "Paradigm": "Classical",
                "# Runs": len(runs), "# Feasible Runs": len(valid), "# Successful Runs": nsucc,
                "Success Threshold": 0, "Hardware Specifications": HARDWARE,
                "Total Runtime": round(sum(r["seconds"] for r in runs)/len(runs), 3),
                "Time to Solution": round(sum(r["seconds"] for r in runs)/len(runs), 3),
                "CPU Runtime": round(sum(r["seconds"] for r in runs)/len(runs), 3),
                "Remarks": note + "Runtimes are the average over the independent runs. Successful runs are those reaching this method's own best value. The objective is the total arc cost of the routing. Verified with 04-steiner/check."})
            with open(f"{d}/{inst}_summary.csv", "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerow(row)
            made += 1
    print(f"built {made} instance directories under {root}")

if __name__ == "__main__":
    main()
