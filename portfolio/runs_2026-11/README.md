Records of the 2978 portfolio runs behind the 06-portfolio RestrictedChainDP
submission, made from 2026-11-05 to 2026-11-09 on an Apple M3 Pro laptop with code
at commit 7d5de733 and these commands:

    python scripts/run_independent.py --bases a050,a200,a400 --seeds 1,2,3,4,5,6,7,8,9,10 \
        --workers 5 --outdir runs_2026-11
    python scripts/run_independent.py --bases a050,a200,a400 --cells cells_33_seeds.tsv \
        --seeds 11,12,...,33 --workers 5 --outdir runs_2026-11

The first command gives ten runs for each of the 192 instances. The second adds
seeds 11 to 33 for the 46 instances listed in cells_33_seeds.tsv, which are the
ones where another open submission reported a value at least as good as this
method's earlier one, so those rows have 33 runs. No other submission's solution
is read by any run, only the instance.

The first sweep was stopped once after 1831 runs when the laptop went off AC power
and restarted with the same command and the same code on 2026-11-08. Finished runs
are skipped on restart and the runs that were cut off were run again from scratch.
run_log.txt has every part and sweep_meta.jsonl the start settings of each part.

One json per run with the objective, wall clock and process CPU time, time to best
and every incumbent, the search settings and the checker output, plus the solution
of each run. The rows were built with

    python scripts/build_from_runs.py runs_2026-11 <submission dir> --date 2026-11-09 ...
