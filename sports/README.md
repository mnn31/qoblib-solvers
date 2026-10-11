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
with its default 16 worker portfolio.

## Verification

Every timetable is checked twice before it is reported:

- `check.py`, an independent checker written from the ITC2021 problem
  description and cross checked against `05-sports/misc/itc2mip.py`. It accepts
  all 249 reference solutions in the benchmark repository and rejects perturbed
  copies of them.
- The official RobinX validator (https://github.com/Robin-X/RobinX), run by
  `validate_robinx.py`, which also records the soft constraint penalty of each
  timetable in the RobinX XML copy.

## Files

| file | purpose |
| :--- | :--- |
| `robinx.py` | read RobinX instances, read and write timetables (`.sol` and RobinX XML) |
| `check.py` | independent hard constraint checker |
| `solve.py` | CP-SAT model and single instance driver |
| `sweep.py` | run a list of instances one at a time, resumable |
| `validate_robinx.py` | run the official validator over a results directory |
| `build_submission.py` | assemble the QOBLIB submission directory |
| `open_instances.txt` | the 102 instances with no solution on record when this started |
| `results/` | per instance JSON logs, timetables and validator reports |

## Results

See `results/README.md`.
