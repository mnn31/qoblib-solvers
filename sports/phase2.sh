#!/bin/bash
# Second exploration phase, started only after retime.sh has finished.
# Stream a: competition instances not yet tried (600 s), then half of the 600 s
# timeouts at 3600 s. Stream b: the other half of the timeouts at 3600 s, then the
# Medium instances at 3600 s, then the Large instances at 600 s.
cd /workspace/sports
python3 - <<'PY'
import glob, json, os
names = [l.strip() for l in open("code/open_instances.txt") if l.strip()]
done = {}
for jf in glob.glob("results/x600/*.json"):
    if jf.endswith(".robinx.json"): continue
    r = json.load(open(jf)); done[r["instance"]] = r.get("checked_feasible", False)
itc_todo = [n for n in names if "ITC2021" in n and n not in done]
unknown = sorted(n for n, ok in done.items() if not ok and "Medium" not in n)
open("lists/itc_rest.txt", "w").write("\n".join(itc_todo) + "\n")
open("lists/unk_a.txt", "w").write("\n".join(unknown[0::2]) + "\n")
open("lists/unk_b.txt", "w").write("\n".join(unknown[1::2]) + "\n")
print(len(itc_todo), "untried competition instances;", len(unknown), "timeouts to retry at 3600 s")
PY
S="python3 -u code/sweep.py --instances instances --workers 8"
tmux new-session -d -s phase2_a "$S --list lists/itc_rest.txt --out results/x600 --seconds 600 2>&1 | tee -a phase2_a.log; $S --list lists/unk_a.txt --out results/x3600 --seconds 3600 2>&1 | tee -a phase2_a.log"
tmux new-session -d -s phase2_b "$S --list lists/unk_b.txt --out results/x3600 --seconds 3600 2>&1 | tee -a phase2_b.log; $S --list lists/med.txt --out results/x3600 --seconds 3600 2>&1 | tee -a phase2_b.log; $S --list lists/large_a.txt --out results/x600 --seconds 600 2>&1 | tee -a phase2_b.log; $S --list lists/large_b.txt --out results/x600 --seconds 600 2>&1 | tee -a phase2_b.log"
tmux ls
