#!/usr/bin/env python3
"""Assemble the QOBLIB submission directory for problem 06.

Layout produced (what misc/ci/check_submission.py expects):

    06-portfolio/submissions/<YYYYMMDD>_<tag>_<name>/
        README.md
        <instance>/
            <instance>_summary.csv
            <instance>_solution.sol
            README.md

    PYTHONPATH=. python scripts/build_submission.py --out /tmp/sub06
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from fractions import Fraction

from qoblib_portfolio.model import Coefficients, Instance

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
    "https://github.com/mnn31/qoblib-solvers/tree/main/portfolio")
DATE = os.environ.get("QOBLIB_DATE", "2026-08-18")
DATE_TAG = os.environ.get("QOBLIB_DATE_TAG", "20260817")
HARDWARE = os.environ.get(
    "QOBLIB_HARDWARE",
    "Apple M3 Pro (Mac15,6), 11 cores (5 performance + 6 efficiency), 18 GB "
    "unified memory, macOS 26.3, arm64. Runtimes are from a single-process rerun "
    "with no other load, so they are not inflated by contention.")

README = """# Exact chain dynamic programming for the portfolio instances

The reference model couples periods only through the rebalancing term between
consecutive periods, and charges no rebalancing into the final period. Every
other term, the risk quadratic, the return, the short-selling cost and the cash
interest on the slack register, depends on a single period's portfolio.

That makes the model a chain. Enumerating the feasible per-period portfolios
under the budget and capital slack registers and running a forward dynamic
program over them gives the exact optimum, with the last period detaching.

Contents, 160 instances:

* a003, a004 and a005, 96 instances, all previously listed open with no feasible
  solution on record. A period has between 84 and 991 feasible portfolios here,
  so each closes in well under a second.
* a010_t10 and a010_t15, 64 instances. These match the published values exactly,
  so nothing improves, but they are now proven optimal rather than best known.
  A period has 10,606 feasible portfolios, so these take a few minutes each.

All values are proven optima, not heuristic bounds, so the optimality bound
equals the objective throughout.

## Rounding

The objective is not evaluated in floating point anywhere. Prices and
covariances are parsed straight from the instance files into exact rationals,
and every quantity below is formed and rounded exactly, so the result is
bit-identical to the coefficients Zimpl writes into the shipped LP and QUBO
files.

Zimpl's `round` is half away from zero, which is not what IEEE or Python's
`round` does. On an exact rational x it is

    round(x) = trunc(x + 1/2)   if x >= 0
    round(x) = trunc(x - 1/2)   if x <  0

so 0.5 goes to 1 and -0.5 goes to -1, whereas banker's rounding would send both
to 0. Getting this wrong shifts individual coefficients by one unit and the
totals by more.

Unit prices are rebased exactly before anything is rounded: one unit of asset i
is `unit` of cash at t = 0, so `p[i,t] = raw_p[i,t] * unit / raw_p[i,0]` is kept
as a rational, never as a decimal.

Rounding is then applied once per model coefficient, exactly where the reference
model applies it, and never to a running total:

| coefficient | expression rounded |
| :--- | :--- |
| risk, per ordered group pair and period | `lambda * tau_i * tau_j * cov[i,j,t] * p[i,t] * p[j,t]` |
| return, per group and period | `tau * (p[i,t+1] - p[i,t])` |
| transaction and liquidation, per group and period | `delta * p[i,t]` |
| short selling, per short group and period | `rho * p[i,t]` |
| cash interest, per slack bit | `nu * unit * 2^k` |

Every rounded coefficient is an integer, so from that point on the whole
objective, and the dynamic program over it, is integer arithmetic with no
further rounding and no accumulation error.

This was validated against the shipped a010 reference solutions before any of
these results were produced: it reproduces their published objective values
exactly, including the ones marked proven optimal, which is what gives
confidence that the rounding matches the reference model term by term.

The method is exact and not anytime, so there is no objective time series: the
dynamic program produces no incumbent before it returns the optimum.

## Runtimes

The reported runtimes come from a rerun with a single process and nothing else
on the machine. An earlier version of this submission reported wall clock from
a run with eight concurrent workers on an 11-core machine, which inflated them:
the same 64 a010 instances take 238.5 minutes that way against 105.1 minutes
single-process, a factor of 2.27. All 160 objectives are identical between the
two runs, so only the timings changed.

Two separate effects are at work, measured on this machine with the same
instance and lambda:

| condition | median solve |
| :--- | ---: |
| performance cores, idle machine | 75.2 s |
| efficiency cores, idle machine | 118.2 s |

so core type alone accounts for 1.57x. The remainder of the 2.27x is memory and
cache pressure from running eight solves at once. With 5 performance and 6
efficiency cores, eight concurrent workers cannot all sit on performance cores,
which is why the original numbers mixed the two.

Code: https://github.com/mnn31/qoblib-solvers/tree/main/portfolio
"""


def write_csv(path: str, row: dict) -> None:
    full = {c: row.get(c, "N/A") for c in COLUMNS}
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerow(full)


def load_records(results: str) -> list[dict]:
    """`results` is a directory of results, or a parent holding several."""
    dirs = []
    for root, _, files in os.walk(results):
        if "summary.json" in files:
            dirs.append(root)
    dirs.sort()
    out = []
    for d in dirs:
        for rec in json.load(open(f"{d}/summary.json")):
            rec["_dir"] = d
            out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--results", default="results")
    a = ap.parse_args()

    records = load_records(a.results)
    root = f"{a.out}/{DATE_TAG}_ChainDP_Gupta"
    os.makedirs(root, exist_ok=True)
    open(f"{root}/README.md", "w").write(README)

    cache: dict[str, Instance] = {}
    for rec in records:
        iid, base = rec["instance"], rec["base"]
        if base not in cache:
            cache[base] = Instance(f"{QOBLIB}/06-portfolio/instances/{base}")
        inst = cache[base]
        coef = Coefficients(inst, rec["budget"], Fraction(rec["lambda"]))

        n, T, ub = inst.n, inst.periods, coef.ub
        n_bin = n * ub * 2 * T + coef.cs1 * T + coef.cs2 * T
        nz_cons = T * ((n * ub * 2 + coef.cs1) + (n * ub * 2 + coef.cs2))
        nz_quad = int(sum((coef.risk[t] != 0).sum() for t in range(T))) * ub * ub
        nz_lin = int((coef.delta != 0).sum() + (coef.short != 0).sum()
                     + (coef.ret != 0).sum()) * ub + coef.cs1 * T
        lo = min(int(coef.risk.min()), int(coef.ret.min()), 0)
        hi = max(int(coef.risk.max()), int(coef.delta.max()), int(coef.cash.max()))

        d = f"{root}/{iid}"
        os.makedirs(d, exist_ok=True)
        shutil.copy(f"{rec['_dir']}/{rec['solution']}", f"{d}/{iid}_solution.sol")

        # No objective time series: the dynamic program is exact and not anytime,
        # so it produces no incumbent before it finishes.  A one-point series
        # carries no information the Remarks field does not already state, and
        # the maintainers asked for it to be left out.

        write_csv(f"{d}/{iid}_summary.csv", {
            "Problem": iid,
            "Submitter": SUBMITTER, "Affiliation": AFFILIATION,
            "Date": DATE, "Reference": REFERENCE,
            "Best Objective Value": rec["objective"],
            "Optimality Bound": rec["objective"],
            "Modeling Approach":
                "Reference binary quadratic model of bqp_u3_c10.zpl, reformulated "
                "as a chain over per-period unit-count portfolios",
            "# Decision Variables": n_bin, "# Binary Variables": n_bin,
            "# Integer Variables": 0, "# Continuous Variables": 0,
            "# Non-Zero Coefficients": nz_cons + nz_quad + nz_lin,
            "Coefficients Type": "Integer",
            "Coefficients Range": f"{lo} - {hi}",
            "Workflow":
                "Parse prices and covariances in exact rational arithmetic; round every "
                "objective coefficient exactly as Zimpl does; enumerate all feasible "
                "per-period portfolios under the budget and capital slack registers; "
                "solve the resulting chain by forward dynamic programming, the last "
                "period detaching because the reference model charges no rebalancing "
                "into it; recover the schedule by backpointers.",
            "Algorithm Type": "Deterministic", "Paradigm": "Classical",
            "# Runs": 1, "# Feasible Runs": 1, "# Successful Runs": 1,
            "Success Threshold": 0,
            "Hardware Specifications": HARDWARE,
            "Total Runtime": round(rec["seconds"], 3),
            "Time to Solution": round(rec["seconds"], 3),
            "CPU Runtime": round(rec["seconds"], 3),
            "Remarks":
                "Exact method, so the reported value is a proven optimum and the "
                "optimality bound equals the objective. The algorithm is not anytime and "
                "produces no incumbent before it returns, so no objective time series "
                "is provided. Variable and coefficient counts are for "
                "the reference binary model before presolve; the non-zero count expands "
                "each group-pair risk coefficient over the ub^2 copy-slot pairs. "
                "Verified with 06-portfolio/check.",
        })
    print(f"built {len(records)} instance directories under {root}")


if __name__ == "__main__":
    main()
