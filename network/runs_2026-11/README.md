# Network run records, 2026-11-13 to 2026-11-22

Five independent runs of `scripts/run_independent.py` (commit d695d35) on
network12, network20, network22, network23 and network24: seeds 0 to 4, 8
replicas, 7200 s of search per run, HiGHS 1.15.1 on one thread, Python 3.11.7,
on an Apple M3 Pro laptop (5 performance and 6 efficiency cores) on AC power,
strictly one run at a time. 25 runs.

Per run: `<instance>_seed<k>.json` (objective, checker output, wall and
process CPU time, time series, load average at start and end, commit,
versions) and `.sol` (the solution).

`run_log.txt` is the log of the queue that first finished the last sports
reruns and then ran this sweep, so it starts with sports lines.
`sweep_meta.jsonl` holds the settings of every start of the sweep.

The sweep was stopped and resumed several times. A guard stops it when the
laptop leaves AC power, and a run cut off that way writes no record and is run
again from the start after the resume. This happened five times (2026-11-14
06:56, 11-17 07:08, 11-18 07:11, 11-19 08:35 and 11-20 07:15); the
"resumed after the battery stop" lines in `run_log.txt` name the run that was
cut off each time.

`set_aside/` holds one run that was not alone on the machine. The first start
of the sweep, at 23:18:31 on 2026-11-13, was stopped at 23:20:03 to run three
sports reruns first, but only its parent process was stopped and the worker
kept computing until about 01:18 on 2026-11-14 (the broken pipe message in
`run_log.txt`). The network12 seed 0 run of the second start (23:28:15 to
01:28:15) overlapped it. This was noticed on 2026-11-22; the run was set aside
and run again with the same seed, and reached the same value (277527). The
guard also stops the worker processes, so the battery stops left nothing
running.

The load average at the start of a run is a trailing average, so it is high
right after a sports run with 8 workers (network12 seed 0) or after a resume.

`../scripts/build_from_runs.py` builds the QOBLIB submission rows from these
records.
