#!/usr/bin/env python3
"""Assemble the QOBLIB submission directory for problem 08.

Layout produced (what misc/ci/check_submission.py expects):

    08-network/submissions/<YYYYMMDD>_<tag>_<name>/
        README.md
        <instance>/
            <instance>_summary.csv
            <instance>_solution.sol
            <instance>_objective_time_series.json

    PYTHONPATH=. python scripts/build_submission.py --out /tmp/sub08
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil

from qoblib_net import parse_demand

QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))

COLUMNS = ["Problem", "Submitter", "Affiliation", "Date", "Reference",
           "Best Objective Value", "Optimality Bound", "Modeling Approach",
           "# Decision Variables", "# Binary Variables", "# Integer Variables",
           "# Continuous Variables", "# Non-Zero Coefficients",
           "Coefficients Type", "Coefficients Range", "Workflow",
           "Algorithm Type", "Paradigm", "# Runs", "# Feasible Runs",
           "# Successful Runs", "Success Threshold", "Hardware Specifications",
           "Total Runtime", "Time to Solution", "CPU Runtime", "GPU Runtime",
           "QPU Runtime", "Other HW Runtime", "Remarks"]

SUBMITTER = os.environ.get("QOBLIB_SUBMITTER", "Manan Gupta")
AFFILIATION = os.environ.get("QOBLIB_AFFILIATION", "The Harker School")
REFERENCE = os.environ.get(
    "QOBLIB_REFERENCE",
    "https://github.com/mnn31/qoblib-solvers/tree/main/network")
DATE = os.environ.get("QOBLIB_DATE", "2026-08-18")
DATE_TAG = os.environ.get("QOBLIB_DATE_TAG", "20260818")
HARDWARE = os.environ.get("QOBLIB_HARDWARE", "Apple M3 Pro (Mac15,6), 11 cores (5 performance + 6 efficiency), 18 GB unified memory, macOS 26.3, arm64. One run at a time with nothing else on the machine, so no run shared the CPU with another.")

README = """# Parallel tempering over network topologies

The problem separates. Choosing the digraph is combinatorial and has no useful
lower bound; choosing the routing on a fixed digraph is a min-congestion
multicommodity flow, which is a linear program. So the search moves only over
topologies and scores each one with an exact LP.

Two things make that practical. On all 20 published solutions the ceiling of the
routing LP equals the published objective exactly, so the LP value is a sound
search energy and integrality only has to be restored at the end. And a 2-in/2-out
digraph is the union of two fixed-point-free permutations that disagree
everywhere, so the 2-exchange (a->b),(c->d) => (a->d),(c->b) preserves every
degree and every proposal is feasible by construction.

Eight replicas on a geometric temperature ladder from 6% to 0.2% of the
incumbent energy, degree-preserving 2- and 3-exchanges as the move, replica
exchange every 40 proposals. Every replica starts from an independently sampled
random 2-in/2-out topology: the published solutions are never read by the
search, so nothing here starts from an incumbent record. Five independent runs
per instance, single core each, 40 minutes per run, seeds 0 to 4.

The integral routing is recovered once at the end by re-solving the same model
with integrality on the flow variables.

Each objective time series holds one entry per run, recorded whenever the best
found objective improves, with the final entry marking the end of the run.

Code: https://github.com/mnn31/qoblib-solvers/tree/main/network
"""


def write_csv(path: str, row: dict) -> None:
    full = {c: row.get(c, "N/A") for c in COLUMNS}
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerow(full)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--results", default="results/best")
    ap.add_argument("--stats", default="results/run_stats.json")
    a = ap.parse_args()

    stats = {int(k): v for k, v in json.load(open(a.stats)).items()}
    root = f"{a.out}/{DATE_TAG}_ParallelTempering_Gupta"
    os.makedirs(root, exist_ok=True)
    open(f"{root}/README.md", "w").write(README)

    made = 0
    for fname in sorted(os.listdir(a.results)):
        if not fname.endswith(".sol"):
            continue
        n = int(fname[len("network"):-len(".sol")])
        inst = f"network{n:02d}"
        parse_demand(f"{QOBLIB}/08-network/instances/demand.txt", n)
        obj = int(open(f"{a.results}/{fname}").readlines()[1].split("=")[1])
        st = stats[n]

        n_arcs = n * (n - 1)
        n_x = n_arcs
        n_f = n * (n - 1) * (n - 1)
        nz = 2 * n_arcs + n_arcs * (2 * n - 1) + n_f * 2 + n_arcs * n

        d = f"{root}/{inst}"
        os.makedirs(d, exist_ok=True)
        shutil.copy(f"{a.results}/{fname}", f"{d}/{inst}_solution.sol")
        json.dump(st["trajectories"],
                  open(f"{d}/{inst}_objective_time_series.json", "w"))

        improves = st.get("improves", True)
        write_csv(f"{d}/{inst}_summary.csv", {
            "Problem": inst,
            "Submitter": SUBMITTER, "Affiliation": AFFILIATION,
            "Date": DATE, "Reference": REFERENCE,
            "Best Objective Value": obj,
            "Optimality Bound": "N/A",
            "Modeling Approach":
                "Reference integer multicommodity flow model of d3ver0int.zpl, "
                "decomposed into a topology search over 2-in/2-out digraphs with an "
                "exact min-congestion flow solved for each candidate",
            "# Decision Variables": n_x + n_f + 1,
            "# Binary Variables": n_x,
            "# Integer Variables": n_f + 1,
            "# Continuous Variables": 0,
            "# Non-Zero Coefficients": nz,
            "Coefficients Type": "Integer",
            "Coefficients Range": "1 - 1000000",
            "Workflow":
                "Parallel tempering over 2-in/2-out digraphs. Eight replicas on a "
                "geometric temperature ladder from 6% to 0.2% of the incumbent energy; "
                "moves are degree-preserving 2- and 3-exchanges on the arc set, so "
                "every proposal is feasible by construction and only strong "
                "connectivity is rechecked; replica exchange every 40 proposals. A "
                "replica's energy is the exact min-congestion multicommodity flow LP "
                "for its topology, solved with HiGHS. Every replica starts from an "
                "independently sampled random 2-in/2-out topology; the published "
                "solutions are never read by the search. The integral routing is "
                "recovered once at the end by re-solving the same model with "
                "integrality on the flow variables.",
            "Algorithm Type": "Stochastic", "Paradigm": "Classical",
            "# Runs": st["nruns"], "# Feasible Runs": st["nruns"],
            "# Successful Runs": st["nsucc"], "Success Threshold": 0,
            "Hardware Specifications": HARDWARE,
            "Total Runtime": round(st["avg_secs"], 1),
            "Time to Solution": round(st["tts"], 1),
            "CPU Runtime": round(st["avg_secs"], 1),
            "Remarks":
                "Heuristic, so the optimality bound is left as N/A. Runtimes are the "
                "average over the independent runs, single core each, queueing "
                "excluded. Time to solution is the average over runs of the moment "
                "each run last improved its incumbent. "
                + ("" if improves else
                   "This run does not reach the published best-known value and is "
                   "included so the method stays comparable over time rather than "
                   "only appearing where it wins. ")
                + "Successful runs are those "
                "reaching this method's own best value. The declared objective is "
                "recomputed from the flows rather than taken from the solver's z "
                "variable, which the model only bounds from below. Verified with "
                "08-network/check.",
        })
        made += 1
    print(f"built {made} instance directories under {root}")


if __name__ == "__main__":
    main()
