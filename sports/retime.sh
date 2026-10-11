#!/bin/bash
# Re-run every instance solved during exploration, strictly one at a time with all
# 16 workers, into results/excl. Exploration results are never reported directly.
cd /workspace/sports
ls results/x600/*.sol results/x3600/*.sol 2>/dev/null | xargs -n1 basename | sed 's/\.s[0-9]*\.sol$//' | sort -u > lists/solved.txt
echo "$(wc -l < lists/solved.txt) solved instances to re-time"
python3 -u code/sweep.py --list lists/solved.txt --instances instances --out results/excl --seconds 600 --workers 16
python3 code/validate_robinx.py --robinx /workspace/robinx/RobinX --instances instances results/excl
echo RETIME_DONE
