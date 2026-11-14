# Sports timetabling (QOBLIB problem 05)

The benchmark version of problem 05 is a pure feasibility problem: find a time
constrained double round robin timetable that satisfies every hard constraint of
the instance (capacity CA1 to CA4, game GA1, break BR1 and BR2, plus the phased
structure where present). Soft constraints are ignored. 102 of the 249 instances
had no solution on the best known table.

## Method

`solve.py` posts the hard constraints directly as a constraint programming model
on binary game variables `x[home, away, slot]`, with home indicators
`home[t, s]` and, when break constraints are present, home and away break
indicators. There is no objective. OR-Tools CP-SAT searches for a feasible point
with its default portfolio: 16 workers in the first cloud runs (`results/`),
8 workers in the five-run sweep of 2026-11 (`runs_2026-11/`).

## Verification

Every timetable is checked before it is reported:

- `check.py`, an independent checker written from the ITC2021 problem
  description and cross checked against `05-sports/misc/itc2mip.py`. It accepts
  all 249 reference solutions in the benchmark repository and rejects perturbed
  copies of them.
- For the first cloud runs only, also the official RobinX validator
  (https://github.com/Robin-X/RobinX), run by `validate_robinx.py`, which also
  records the soft constraint penalty of each timetable in the RobinX XML copy.
  The runs of 2026-11 were checked with `check.py` alone.

## Files

| file | purpose |
| :--- | :--- |
| `robinx.py` | read RobinX instances, read and write timetables (`.sol` and RobinX XML) |
| `check.py` | independent hard constraint checker |
| `solve.py` | CP-SAT model and single instance driver |
| `sweep.py` | run a list of instances one at a time, resumable |
| `validate_robinx.py` | run the official validator over a results directory |
| `build_submission.py` | assemble the QOBLIB submission directory |
| `run_independent.py` | seeded independent runs, one at a time, with wall and CPU time per run |
| `build_from_runs.py` | build the submission rows from the run records |
| `rerun_2026-11.txt` | the 173 instances of the 2026-11 runs |
| `runs_2026-11/` | records of the 865 runs of 2026-11-12 and 2026-11-13 |
| `open_instances.txt` | the 102 instances with no solution on record when this started |
| `results/` | per instance JSON logs, timetables and validator reports |

## Results

`results/README.md` covers the first cloud runs, `runs_2026-11/README.md` the
five-run sweep of 2026-11 behind the current submission rows.
