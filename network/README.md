# QOBLIB problem 08, Network Design

Stochastic search for the Bienstock-Gunluk min-congestion network design
problem, [QOBLIB](https://zib-aopt.github.io/QOBLIB/) problem 08.

Build a digraph on `n` nodes where every node has in-degree and out-degree
exactly 2, route a fixed traffic matrix over it, and minimise the largest total
load on any arc. Instances `network05` to `network24`. Six are solved to proven
optimality; the other fourteen have stood as best-known upper bounds, and the
24-node case has resisted proof of optimality since 1995.

**Result: 11 new best-known values on `network13` to `network23`**, up to 5.0%.
Submitted upstream as [ZIB-AOPT/QOBLIB#45](https://github.com/ZIB-AOPT/QOBLIB/pull/45).
See [`results/`](results/README.md).

## The idea

The problem splits cleanly in two:

- **Outer**: which digraph? Combinatorial, enormous, no useful lower bound.
- **Inner**: given the digraph, how to route? A min-congestion multicommodity
  flow, which is a linear program and therefore exactly solvable in milliseconds.

So the search only ever moves over topologies, scoring each one with an exact LP
oracle. Two properties measured here make that work:

1. On all 20 published solutions, `ceil(LP)` equals the published objective
   exactly. The LP relaxation of the routing is tight, so the LP value is a
   sound search energy and integrality only has to be restored at the end.
2. A 2-in/2-out digraph is the union of two fixed-point-free permutations that
   disagree everywhere, and the 2-exchange `(a->b),(c->d) => (a->d),(c->b)`
   preserves every degree. Every proposal is feasible by construction.

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
| `scripts/build_submission.py` | assemble a QOBLIB submission directory |
| `results/` | solutions and the write-up |

## Use

```bash
pip install -r ../requirements.txt
git clone --depth 1 https://github.com/ZIB-AOPT/QOBLIB.git
export QOBLIB_ROOT=$PWD/QOBLIB

PYTHONPATH=. python scripts/check_reference.py
PYTHONPATH=. python scripts/sweep.py --instances 11-23 --seeds 5 --seconds 1800 --workers 1
```

## Verification

`qoblib_net.solio.verify` is a from-scratch re-implementation of the official
Rust checker (`08-network/check/src/main.rs`). It reproduces the published
objective for all 20 instances. It is a development convenience, not a
substitute. The official Rust checker was run on everything reported here.
