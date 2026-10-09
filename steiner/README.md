# QOBLIB problem 04, Steiner Tree Packing

Negotiated congestion routing for the Steiner tree packing instances, the
PathFinder style rip up and reroute method used in VLSI switchbox routing.

**Result: 147 previously open instances now have a verified feasible solution
on record, and one of the 14 best-known-only instances is improved.** See
[`results/`](results). Submitted upstream as
[ZIB-AOPT/QOBLIB#88](https://github.com/ZIB-AOPT/QOBLIB/pull/88).

## The idea

The reference formulation is a multicommodity flow MIP with millions of
variables, which is why most instances had no solution on record: exact solvers
only finished the small ones. The graphs themselves are small for a router.

Each net is routed as a greedy Steiner tree by multi source Dijkstra from the
partial tree to the nearest unconnected terminal. Node cost is base cost plus
present overuse times a pressure factor that grows each iteration, plus an
accumulated history penalty. Iterate until no node is shared. If a stall leaves
one or two contested nodes, one of the nets through such a node is forced to
detour around it. Then prune non terminal leaves and run cost polish passes
rerouting each net with the other nets' nodes forbidden.

On a solved instance it lands within about 2% of the proven optimum in 0.1 s.
Every instance here routes in seconds.

## Layout

| path | what it is |
| :--- | :--- |
| `route.py` | the router, stdlib only |
| `sweep_steiner.py` | sequential multi seed sweep, every solution checked |
| `build_submission.py` | assemble the QOBLIB submission directory |
| `open_instances.txt`, `bestknown_instances.txt` | instance lists from the published site data |
| `results/open`, `results/bestknown` | best solution and per seed record per instance |

## Use

```bash
git clone --depth 1 https://github.com/ZIB-AOPT/QOBLIB.git
cd QOBLIB/04-steiner/check && cargo build --release
CHECK_STEINER=$PWD/target/release/check_steiner python sweep_steiner.py open_instances.txt --seeds 10 --outdir results/open
```

## Verification

Every solution reported was verified with `04-steiner/check` as it was
produced, and the best solution per instance was verified again before
packaging. Runs that do not improve a published value are included so the
method stays comparable.
