#!/bin/bash
# Third pass: every competition instance still without a timetable gets 3600 s
# (if it only had 600 s so far) or 7200 s (if it already failed at 3600 s).
# Two streams of 8 workers. Run only when phase 2 has finished.
cd /workspace/sports
python3 - <<'PY'
import glob, json
names = [l.strip() for l in open("code/open_instances.txt") if l.strip() and "ITC2021" in l]
solved, tried3600 = set(), set()
for d in ("x600", "x3600", "excl"):
    for jf in glob.glob(f"results/{d}/*.json"):
        if jf.endswith(".robinx.json"): continue
        r = json.load(open(jf))
        if r.get("checked_feasible"): solved.add(r["instance"])
        if d == "x3600": tried3600.add(r["instance"])
need3600 = [n for n in names if n not in solved and n not in tried3600]
need7200 = [n for n in names if n not in solved and n in tried3600]
open("lists/p3_3600_a.txt", "w").write("\n".join(need3600[0::2]) + "\n")
open("lists/p3_3600_b.txt", "w").write("\n".join(need3600[1::2]) + "\n")
open("lists/p3_7200_a.txt", "w").write("\n".join(need7200[0::2]) + "\n")
open("lists/p3_7200_b.txt", "w").write("\n".join(need7200[1::2]) + "\n")
print(len(solved), "solved;", len(need3600), "to try at 3600 s;", len(need7200), "to try at 7200 s")
PY
S="python3 -u code/sweep.py --instances instances --workers 8"
for h in a b; do
  tmux new-session -d -s phase3_$h "$S --list lists/p3_3600_$h.txt --out results/x3600 --seconds 3600 2>&1 | tee -a phase3_$h.log; $S --list lists/p3_7200_$h.txt --out results/x7200 --seconds 7200 2>&1 | tee -a phase3_$h.log"
done
tmux ls
