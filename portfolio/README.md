# QOBLIB problem 06, Portfolio Optimization

Exact solver for the multi-period portfolio model of
[QOBLIB](https://zib-aopt.github.io/QOBLIB/) problem 06.

**Result: 160 instances solved to proven optimality.** 96 of them were listed as
open, with no feasible solution on record. See [`results/`](results/README.md).

Submitted upstream as [ZIB-AOPT/QOBLIB#44](https://github.com/ZIB-AOPT/QOBLIB/pull/44).

**Large families:** `qoblib_portfolio/heuristic.py` is a restricted state version
of the same chain dynamic program for a050 and above, where the per period
portfolios cannot be enumerated. It reproduces the proven optimum on all 160
small instances, is within a few hundredths of a percent of the published a050
values at low lambda and clearly worse at the highest lambda, and puts all 128
previously open a200 and a400 instances on record. Submitted as
[ZIB-AOPT/QOBLIB#87](https://github.com/ZIB-AOPT/QOBLIB/pull/87).

## The idea

The reference model couples periods in exactly one place, the rebalancing term
between consecutive periods, and it charges no rebalancing into the final
period. Everything else, the risk quadratic, the return, the short-selling cost
and the cash interest on the slack register, is a function of a single period's
portfolio.

So the model is a chain, and the optimum follows from one forward dynamic
program over per-period portfolios:

```
f_0(s)  = cost_0(s)
f_t(s)  = cost_t(s) + min_s' [ f_{t-1}(s') + rebalance_t(s', s) ]    0 < t < T-1
optimum = min_s f_{T-2}(s) + min_s cost_{T-1}(s)
```

A per-period portfolio is a vector of unit counts over the 2n (asset, direction)
groups, subject to the budget and capital slack registers. That structure is
invisible to a MIP or QUBO solver working on the flat binary model, which is why
instances a general solver has to branch on close exactly here.

## Layout

| path | what it is |
| :--- | :--- |
| `qoblib_portfolio/model.py` | instance parsing and the exact objective, in rational arithmetic with Zimpl rounding |
| `qoblib_portfolio/solver.py` | the chain dynamic program, canonical solution I/O |
| `scripts/portfolio_solve.py` | solve a family of instances |
| `scripts/build_submission.py` | assemble a QOBLIB submission directory |
| `results/` | solutions and the write-up |

## Use

```bash
pip install -r ../requirements.txt
git clone --depth 1 https://github.com/ZIB-AOPT/QOBLIB.git
export QOBLIB_ROOT=$PWD/QOBLIB

PYTHONPATH=. python scripts/portfolio_solve.py --bases a003,a004,a005 --outdir results/small
```

## Rounding

The objective is never evaluated in floating point. Prices and covariances are
parsed into exact rationals, unit prices are rebased exactly as
`p[i,t] = raw_p[i,t] * unit / raw_p[i,0]`, and every model coefficient is
rounded once, exactly where the reference model rounds it, with Zimpl's `round`:

```
round(x) = trunc(x + 1/2)   if x >= 0
round(x) = trunc(x - 1/2)   if x <  0
```

That is half away from zero, so `0.5` goes to 1 and `-0.5` goes to -1. IEEE and
Python's `round` send both to 0, and using them shifts coefficients by a unit.
After rounding every coefficient is an integer, so the dynamic program runs in
integer arithmetic with no accumulation error.

## Runtimes

Timings come from a single-process run with nothing else on the machine. Running
eight concurrent workers on an 11-core box inflates them by 2.27x on the `a010`
families (238.5 min against 105.1 min for the same 64 instances), with identical
objectives. Two effects are mixed in there: core type accounts for 1.57x
(75.2 s against 118.2 s for the same solve on performance versus efficiency
cores), and the rest is memory and cache pressure from eight solves at once.

## Validation

Three checks, in order of how much they are worth:

1. The objective implementation reproduces the published objective **exactly**
   on the shipped `a010` reference solutions, including the bit-exact Zimpl
   `round` behaviour (half away from zero on exact rationals).
2. The dynamic program returns the published optimum exactly on every instance
   whose published value is marked proven optimal.
3. Every emitted solution is verified by the official Rust checker
   (`06-portfolio/check`), which recomputes the objective in exact rational
   arithmetic.
