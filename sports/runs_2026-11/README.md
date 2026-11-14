# Sports run records, 2026-11-12 to 2026-11-13

Five independent runs of `run_independent.py` (commit 9c3bbd2) for every
instance in `../rerun_2026-11.txt`: the 26 ITC2021 instances and every Tiny,
Small and Medium instance with a value in the best known table, 173 instances
and 865 runs. CP-SAT seeds 0 to 4, 8 workers, 600 s limit, OR-Tools 9.14.6206,
Python 3.11.7, on an Apple M3 Pro laptop (5 performance and 6 efficiency
cores) on AC power, strictly one run at a time.

Per run: `<instance>_seed<k>.json` (status, wall and process CPU time, build
time, time series, commit, versions), `.sol` (timetable, when one was found)
and `.xml` (the same timetable in RobinX format).

`run_log.txt` is the log of the main sweep, `rerun_log.txt` the log of the
reruns, `sweep_meta.jsonl` holds the settings of every sweep part.

`set_aside/` holds 40 runs that overlapped other work on the laptop. 37 of
them overlapped work on 2026-11-12 between 17:15 and 18:15 and between 20:15
and 20:50 (building and checking submission files, an audit script and short
test runs); `move_interfered.py` moved them aside. The other 3 overlapped a
file system search and git commands on 2026-11-13 between 21:58:50 and
22:03:10 and were moved by hand. Each `moved.txt` lists the runs with their
own time windows. All 40 were run again with the same seed and are not used
for any reported number.

The reruns stopped at 07:14 on 2026-11-13 when the laptop was unplugged (a
guard stops the sweep off AC power, and a run cut off that way writes no
record) and resumed at 21:58 the same day ("resumed after the battery stop" in
`rerun_log.txt`). One kept run ended about 2 s after the power was
disconnected: Addition_046_Medium seed 0, which found no timetable in 600 s.
No run of that instance found a timetable, so it has no submission row.

An earlier pilot on OR-Tools 9.15 hung after its first solution and wrote no
records.

`../build_from_runs.py` builds the QOBLIB submission rows from these records.
