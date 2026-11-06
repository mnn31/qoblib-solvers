Records of the 950 Steiner runs behind the 04-steiner submission, made from
2026-11-03 to 2026-11-05 on an Apple M3 Pro laptop with code at commit 95485bfe
and this command:

    python run_independent.py all_instances.txt --seeds 0,1,2,3,4 --lns-seconds 600 \
        --small-seconds 120 --workers 5 --outdir runs_2026-11

The sweep was stopped once after 540 runs and restarted with the same command and
the same code; finished runs are skipped on restart, and the five runs that were
cut off were run again from scratch. run_log.txt has both parts, and the start
settings of each part are in sweep_meta_night1.json and sweep_meta.json.

One json per run with cost, wall clock and process CPU time, time to best and
every incumbent, plus the solution and log of each run. The rows were built with

    python build_from_runs.py runs_2026-11 <submission dir> --date 2026-11-05 ...
