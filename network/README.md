# QOBLIB problem 08, Network Design

Stochastic search for the Bienstock-Gunluk min-congestion network design
problem, [QOBLIB](https://zib-aopt.github.io/QOBLIB/) problem 08.

Build a digraph on `n` nodes where every node has in-degree and out-degree
exactly 2, route a fixed traffic matrix over it, and minimise the largest total
load on any arc. Instances `network05` to `network24`. Six are solved to proven
optimality; for the other fourteen only best-known upper bounds are known.

**Result: 11 new best-known values on `network13` to `network23`**, up to 5.0%.
Submitted upstream as [ZIB-AOPT/QOBLIB#45](https://github.com/ZIB-AOPT/QOBLIB/pull/45).
See [`results/`](results/README.md).

## The idea

The problem splits cleanly in two:

- **Outer**: which digraph? Combinatorial and enormous. The search computes no
  lower bound.
- **Inner**: given the digraph, how to route? A min-congestion multicommodity
  flow. Its LP relaxation is solved in milliseconds and used as the search energy.

So the search only ever moves over topologies, scoring each one with an exact LP
oracle. Two properties measured here make that work:

1. On all 20 published solutions, `ceil(LP)` equals the published objective
   exactly. The LP relaxation of the routing is tight, so the LP value is a
   sound search energy and integrality only has to be restored at the end.
2. A 2-in/2-out digraph is the union of two fixed-point-free permutations that
   disagree everywhere, and the 2-exchange `(a->b),(c->d) => (a->d),(c->b)`
   (and a 3-exchange of arc heads, 15% of moves) preserves every degree. A move
   that would create a loop or a repeated arc is skipped, and a result that is
   not strongly connected is rejected, so only strong connectivity needs a check.

That is exactly the setting simulated annealing and parallel tempering are for:
a rugged discrete landscape with a cheap exact energy and a natural
degree-preserving move set.

## Layout

| path | what it is |
| :--- | :--- |
| `qoblib_net/instance.py` | demand matrix, published best-known values, lower bounds |
| `qoblib_net/topology.py` | the 2-in/2-out digraph space and its degree-preserving moves |
| `qoblib_net/oracle.py` | exact min-congestion routing, LP for search and MIP for output |
| `qoblib_net/search.py` | simulated annealing and parallel tempering |
| `qoblib_net/solio.py` | solution-file I/O and an independent feasibility checker |
| `scripts/check_reference.py` | reproduce every published solution, run this first |
| `scripts/solve.py` | search one instance |
| `scripts/sweep.py` | multi-seed sweep, the unit of work that can be submitted |
| `scripts/build_submission.py` | assemble a QOBLIB submission directory (2026-08-18 submission) |
| `scripts/run_independent.py` | independent seeded runs with full records, one at a time with `--workers 1` |
| `scripts/build_from_runs.py` | build submission rows only from the records of `run_independent.py` |
| `runs_*/` | run records behind a submission: one json and solution per run, run log, settings |
| `results/` | solutions and the write-up |

## Use

```bash
pip install -r ../requirements.txt
git clone --depth 1 https://github.com/ZIB-AOPT/QOBLIB.git
export QOBLIB_ROOT=$PWD/QOBLIB

PYTHONPATH=. python scripts/check_reference.py
PYTHONPATH=. python scripts/sweep.py --instances 11-23 --seeds 5 --seconds 1800 --workers 1

# runs with full records, strictly one at a time, then rows from the records
python scripts/run_independent.py --instances 12,20 --seeds 0,1,2,3,4 --seconds 7200 \
    --replicas 8 --workers 1 --outdir runs
python scripts/build_from_runs.py runs <submission dir> --date <date> --hardware "..." \
    --reference <url at a fixed commit> --table $QOBLIB_ROOT/08-network/solutions/README.md
```

## Verification

`qoblib_net.solio.verify` is a from-scratch re-implementation of the official
Rust checker (`08-network/check/src/main.rs`). It reproduces the published
objective for all 20 instances. It is a development convenience, not a
substitute. The official Rust checker was run on everything reported here.
