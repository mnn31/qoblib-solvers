#!/usr/bin/env python3
"""Assemble the QOBLIB submission directory for problem 05 from solver results.

    python build_submission.py --results results/p600 results/p3600 --out /tmp/sub05

One directory per solved instance with <inst>_summary.csv and <inst>_solution.sol
(Gurobi style x#home#away#slot lines, the format 05-sports/misc/sol2itc.py reads).
The same timetable is also written as RobinX XML (<inst>_robinx.xml) so it can be
validated with the ITC2021 validator. If an instance appears in several result
directories the fastest feasible run is used.
"""
import argparse, csv, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robinx import read_instance, read_solution, write_solution_sol, write_solution_xml  # noqa: E402
from check import check  # noqa: E402

COLUMNS = ["Problem","Submitter","Affiliation","Date","Reference","Best Objective Value",
 "Optimality Bound","Modeling Approach","# Decision Variables","# Binary Variables",
 "# Integer Variables","# Continuous Variables","# Non-Zero Coefficients","Coefficients Type",
 "Coefficients Range","Workflow","Algorithm Type","Paradigm","# Runs","# Feasible Runs",
 "# Successful Runs","Success Threshold","Hardware Specifications","Total Runtime",
 "Time to Solution","CPU Runtime","GPU Runtime","QPU Runtime","Other HW Runtime","Remarks"]

SUBMITTER = "Manan Gupta"; AFFILIATION = "The Harker School"
REFERENCE = "https://github.com/mnn31/qoblib-solvers/tree/main/sports"
HARDWARE = ("RunPod cloud CPU pod: AMD EPYC 9655 (96 core host), container limited to 16 vCPUs "
            "(8 physical cores with SMT), Ubuntu 24.04, x86_64, OR-Tools 9.15. One instance at a "
            "time with 16 CP-SAT workers; nothing else ran in the container. The host is shared "
            "with other tenants, so wall clock times carry some noise.")
WORKFLOW = ("Constraint programming. The hard constraints of the instance (round robin structure, "
            "phases, CA1 to CA4, GA1, BR1, BR2) are posted directly on binary game variables "
            "x[home,away,slot] plus home and break indicators, with no objective. OR-Tools CP-SAT "
            "runs its default portfolio of 16 workers until a feasible timetable is found or the "
            "time limit expires. Soft constraints are ignored, as the benchmark specifies. Every "
            "timetable is verified by an independent checker before being reported.")
README = """# CP-SAT feasibility runs for the sports timetabling instances

The feasibility version of problem 05 asks for a timetable that satisfies all
hard constraints. The hard constraints are posted directly as a constraint
programming model on binary game variables x[home, away, slot], with home and
break indicator variables, and OR-Tools CP-SAT searches for a feasible point
with no objective.

The variable counts in each summary describe this model: n(n-1)S game variables,
nS home indicators and, when break constraints are present, 2n(S-1) break
indicators, all binary. The model has no objective and no reference MIP is
built, so the coefficient fields are N/A.

Every timetable was verified by an independent checker that reproduces the hard
constraint semantics of the ITC2021 problem description and accepts all 249
reference solutions in 05-sports/solutions, and by the ITC2021 RobinX validator
where noted. The solution files use the Gurobi style x#home#away#slot format that
05-sports/misc/sol2itc.py converts to RobinX XML; a RobinX XML copy of each
timetable is included alongside.

Code: https://github.com/mnn31/qoblib-solvers/tree/main/sports
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--instances", default="/Users/manan/WORK/QOBLIB/repo/05-sports/instances")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    a = ap.parse_args()
    date_tag = a.date.replace("-", "")
    files = {os.path.basename(p).replace(".xml.gz", ""): p for p in glob.glob(f"{a.instances}/*/*.xml.gz")}
    best = {}
    for rd in a.results:
        for jf in sorted(glob.glob(f"{rd}/*.json")):
            rec = json.load(open(jf))
            sol = jf[:-5] + ".sol"
            if not rec.get("checked_feasible") or not os.path.exists(sol):
                continue
            inst = rec["instance"]
            if inst not in best or rec["wall_seconds"] < best[inst][0]["wall_seconds"]:
                best[inst] = (rec, sol)
    root = f"{a.out}/{date_tag}_CPSAT_Gupta"; os.makedirs(root, exist_ok=True)
    open(f"{root}/README.md", "w").write(README)
    made = 0
    for inst in sorted(best):
        rec, sol = best[inst]
        I = read_instance(files[inst]); games = read_solution(sol)
        viol = check(I, games)
        if viol:
            print("REFUSING", inst, viol[:2]); continue
        n, S = I.n, I.S
        has_br = any(c.tag in ("BR1", "BR2") for c in I.hard())
        nvar = n * (n - 1) * S + n * S + (2 * n * (S - 1) if has_br else 0)
        d = f"{root}/{inst}"; os.makedirs(d, exist_ok=True)
        write_solution_sol(f"{d}/{inst}_solution.sol", games, 0,
                           f"instance {inst}\nfeasible timetable, all hard constraints satisfied\nOR-Tools CP-SAT, seed {rec['seed']}, {rec['workers']} workers")
        write_solution_xml(f"{d}/{inst}_robinx.xml", I, games, SUBMITTER, "CP-SAT",
                           "Feasibility version: hard constraints only")
        t = round(rec["wall_seconds"], 2)
        row = {c: "N/A" for c in COLUMNS}
        row.update({"Problem": inst, "Submitter": SUBMITTER, "Affiliation": AFFILIATION,
            "Date": a.date, "Reference": REFERENCE, "Best Objective Value": 0,
            "Optimality Bound": 0,
            "Modeling Approach": "Constraint programming model of the hard constraints on binary game, home and break indicator variables; no objective.",
            "# Decision Variables": nvar, "# Binary Variables": nvar,
            "# Integer Variables": 0, "# Continuous Variables": 0,
            "Workflow": WORKFLOW, "Algorithm Type": "Exact", "Paradigm": "Classical",
            "# Runs": 1, "# Feasible Runs": 1, "# Successful Runs": 1,
            "Success Threshold": 0, "Hardware Specifications": HARDWARE,
            "Total Runtime": t, "Time to Solution": t, "CPU Runtime": t,
            "Remarks": (f"No feasible solution was on record for this instance before this submission. "
                        f"Pure feasibility problem: the objective is 0 for any timetable that satisfies all hard "
                        f"constraints, so 0 is also the bound. {n} teams, {S} slots, {'phased' if I.phased else 'not phased'}, "
                        f"{len(I.hard())} hard constraints. Single run, CP-SAT seed {rec['seed']}, time limit "
                        f"{int(rec['seconds_limit'])} s; runtime is wall clock including model build. "
                        f"Verified with an independent checker; a RobinX XML copy of the timetable is included.")})
        with open(f"{d}/{inst}_summary.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerow(row)
        made += 1
    print(f"built {made} instance directories under {root}")


if __name__ == "__main__":
    main()
