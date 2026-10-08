# Results

## New best-known values, problem 08 (Network Design)

On the shared-CPU runs, eight instances improved over the values published in
`08-network/solutions/0-info.txt`. Every solution is verified by the official
Rust checker (`08-network/check`, exit code 0) and independently by
`qoblib_net.solio.verify`.

| instance | published best-known | this work | improvement | relative |
| :--- | ---: | ---: | ---: | ---: |
| network13 | 304,116 | **300,620** | 3,496 | 1.15% |
| network14 | 350,173 | **343,091** | 7,082 | 2.02% |
| network15 | 383,000 | **370,870** | 12,130 | 3.17% |
| network16 | 409,067 | **400,072** | 8,995 | 2.20% |
| network17 | 460,182 | **437,000** | 23,182 | 5.04% |
| network18 | 481,950 | **476,758** | 5,192 | 1.08% |
| network19 | 514,625 | **497,473** | 17,152 | 3.33% |
| network20 | 548,536 | **528,528** | 20,008 | 3.65% |

Solution files are in `results/best_random/`.

## An earlier version of this was wrong

The first run of this experiment seeded half the replicas from the published
reference topology. That means every run started sitting on the incumbent record
and could only ever report something at least as good, so the numbers measured
the seed rather than the search. A QOBLIB maintainer caught it on review, and he
was right.

The seeding is now removed from the code, not just from the run: `sweep.py`
never reads the `solutions/` directory, and the warm-start modes are gone from
`solve.py`. `check_reference.py` still reads the published solutions, because
verifying them is its entire purpose.

Re-running cold changed the result substantially, which is the point:

| instance | published | warm-started claim | cold-start truth | verdict |
| :--- | ---: | ---: | ---: | :--- |
| network13 | 304,116 | 299,715 | 300,620 | holds |
| network14 | 350,173 | 342,455 | 343,091 | holds |
| network15 | 383,000 | 370,967 | 370,870 | holds |
| network16 | 409,067 | 401,000 | 400,072 | holds |
| network17 | 460,182 | 434,429 | 437,000 | holds |
| network18 | 481,950 | 474,643 | 476,758 | holds |
| network19 | 514,625 | 497,000 | 497,473 | holds |
| network20 | 548,536 | 526,653 | 528,528 | holds |
| network21 | 593,000 | 570,022 | 627,462 | **withdrawn** |
| network22 | 647,594 | 621,810 | 686,514 | **withdrawn** |
| network23 | 686,453 | 660,000 | 720,834 | **withdrawn** |
| network12 | 276,474 | 276,474 | 277,527 | no claim |

The pattern is worth reading. Up to about 20 nodes the method finds these
improvements on its own from random starts, and the cold-start values are within
a few tenths of a percent of the warm-started ones, sometimes better. From 21
nodes up the search cannot get near the published values at all: warm-started
they looked like 4% improvements, cold they are 5 to 6% worse. All of that
apparent gain was the seed.

## Method

Parallel tempering over 2-in/2-out digraphs. Eight replicas on a geometric
temperature ladder from 6% to 0.2% of the incumbent energy, degree-preserving 2-
and 3-exchanges as the move, replica exchange every 40 proposals. Every replica
starts from an independently sampled random topology. A replica's energy is the
exact min-congestion multicommodity flow LP for its topology.

Five independent runs per instance, seeds 0 to 4, 40 minutes each, on an Apple
M3 Pro. These ran eight at a time, so each run shared the CPU with seven others.
Measured on network17, that costs about a third of the throughput: 104 LP
evaluations per second shared against 158 when running alone.

These numbers are being replaced. At the maintainer's request the whole set,
network05 to network24, is being rerun at 1800 s per run with strictly one run
on the machine at a time, so that every runtime is comparable. This page will be
updated when that finishes. The integral routing is recovered once at the end by
re-solving the same model with integrality on the flow variables.

The declared objective is recomputed from the flows rather than taken from the
solver's `z`, which the model only bounds from below; an untight `z` otherwise
disagrees with the checker's own recomputed maximum arc load.

## Not improved

`network11` matched its published value in all five runs without beating it.
`network12`, `network21`, `network22` and `network23` came out worse than
published and are not claimed.

`network24` was deliberately not targeted. Its continuous-flow twin is MIPLIB
2017's `dano3mip`, whose record was set in 2022 with Gurobi's NoRel heuristic
warm-started from the previous record.

## Reproducing

```bash
python scripts/sweep.py --instances 11-23 --seeds 5 --seconds 2400 --workers 8
python scripts/aggregate.py --sweep results/sweep_random --outdir results/best_random
```

Submitted upstream as https://github.com/ZIB-AOPT/QOBLIB/pull/45.
