# qoblib-solvers

Solvers and results for two problem classes of the
[Quantum Optimization Benchmarking Library](https://zib-aopt.github.io/QOBLIB/).

The two are independent. Each lives in its own directory with its own code,
its own results and its own write-up.

| directory | problem | result |
| :--- | :--- | :--- |
| [`network/`](network) | 08, Network Design | 11 new best-known values on `network13` to `network23`, up to 5.0% |
| [`portfolio/`](portfolio) | 06, Portfolio Optimization | 160 instances solved to proven optimality, 96 of them previously open; a heuristic puts the 128 previously open a200 and a400 instances on record |

Nothing here is reported before it has been checked with QOBLIB's own checkers.
Each directory documents exactly which checks were run.

## Also here

- [`docs/RESEARCH_NOTES.md`](docs/RESEARCH_NOTES.md) surveys where headroom is
  left across all ten QOBLIB problem classes.
- [`scripts/survey_qoblib.py`](scripts/survey_qoblib.py) regenerates that survey
  from the published site data.

## Licence

Apache 2.0, matching the benchmark's code licence. QOBLIB instance data is
CC BY 4.0 and is not vendored here.
