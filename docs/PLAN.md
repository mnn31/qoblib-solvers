# Plan

Three tracks, ordered by how certain the payoff is. They are independent, so a
failure on one costs nothing on the others.

## Track A: verification harness (done)

`network/scripts/check_reference.py` reproduces the published objective for all
20 network-design instances and confirms the LP oracle agrees with every one of
them. This is the foundation: without it, no search result can be trusted, and
with it, any claimed improvement can be self-checked before it goes anywhere.

Status: passing on all 20.

## Track B: the network-design search (done)

Target was `network11` to `network23`, deliberately not `network24`, whose
continuous-flow twin is MIPLIB 2017's `dano3mip`. That record was set in 2022
with Gurobi's NoRel heuristic warm-started from the previous record, which came
from ParaSCIP in 2014, so it is defended by the people who write the solvers.

`network11` to `network23` are QOBLIB-specific truncations of the same demand
matrix. They are not in MIPLIB and have nothing like that history.

Status: an early version claimed 10 to 11 new best-known values, but it seeded
replicas from the published solutions, which is not allowed; it was withdrawn.
From random starts, run one at a time at 1800 s, the method improves
`network13` to `network23` and reaches the proven optimum on `network05` to
`network10`. See `network/results/README.md`.

## Track C: open instances (done for problem 06)

333 of QOBLIB's 1,264 instances have no feasible solution on record at all. On
those, the first valid submission takes the record outright.

Status: the `a003`, `a004` and `a005` portfolio families, 96 instances, are
closed to proven optimality. The `a010` families, 64 more, are also proven
optimal. See `portfolio/results/README.md`.

Still open, ranked by effort:

- **`06-portfolio`, `a200`/`a400` (16 bases times 8 lambda)**: done. A restricted
  state version of the chain DP puts all 128 on record; weak at the highest
  lambda. See `portfolio/qoblib_portfolio/heuristic.py`.
- **`05-sports` (102 open)**: read the warning first, those instances were
  selected because existing solvers could not find any feasible solution in
  reasonable time.
- **`04-steiner` (147 open)**: done. The millions of variables belong to the MIP
  formulation, not the graphs; a rip-up-and-reroute router closes all 147 in
  seconds each and improves one best-known value. See `steiner/`.

Do not touch `02-labs` (records held by a decade of dedicated tabu search) or
`10-topology` (Graph Golf, its own long-running competition, integer objective).

## Submission mechanics

Read `CONTRIBUTING.md` in the benchmark repo before the first PR. The parts that
bite:

- Every PR needs approval from two committee members, so expect a wait.
- `Optimality Bound` must stay `N/A` for heuristic runs. Setting it equal to the
  objective asserts a proven optimum and triggers a hard check.
- At least 5 independent runs for a stochastic method, 10+ recommended, seeds
  documented.
- Run the checker with `--generate-readme` so each instance directory carries a
  rendered README. Reviewers ask for this.
- The objective time series is optional but expected. It is CI-enforced
  monotone, so a minimisation run whose incumbent ever increases blocks the
  merge.
- The official Rust checkers need `cargo`. Install Rust before the first PR.
