#!/bin/bash
# Build the heuristic portfolio submission on the pod, validate it with the
# official submission checker and the attribution check, then leave a tarball
# ready to pull. Run inside tmux; progress goes to /workspace/package.log.
set -u
LOG=/workspace/package.log; : > $LOG
export PATH=$HOME/.cargo/bin:$PATH
cd /workspace/qoblib-solvers/portfolio
rm -rf /workspace/sub06h
python3 scripts/build_heuristic_submission.py \
  --results results/heuristic_open_seed0 results/heuristic_open_seed1 \
            results/heuristic_open_seed2 results/heuristic_a050 \
  --out /workspace/sub06h --published /workspace/QOBLIB/06-portfolio/solutions/README.md >> $LOG 2>&1
SUB=20261009_RestrictedChainDP_Gupta
cd /workspace/QOBLIB
rm -rf 06-portfolio/submissions/$SUB && cp -r /workspace/sub06h/$SUB 06-portfolio/submissions/
echo "--- check_submission ---" >> $LOG
python3 misc/ci/check_submission.py 06-portfolio/submissions/$SUB --strict-problem-match --generate-readme > /workspace/sub06h_check.log 2>&1
tail -2 /workspace/sub06h_check.log >> $LOG
echo "--- a050 status counts (improves / matches / worse) ---" >> $LOG
grep -l "Improves the published" 06-portfolio/submissions/$SUB/a050*/*_summary.csv | wc -l >> $LOG
grep -l "Reaches the published" 06-portfolio/submissions/$SUB/a050*/*_summary.csv | wc -l >> $LOG
grep -l "Does not reach" 06-portfolio/submissions/$SUB/a050*/*_summary.csv | wc -l >> $LOG
echo "--- update_bkv credited ---" >> $LOG
python3 misc/ci/update_bkv.py --check 2>&1 | grep -c "$SUB" >> $LOG
cd 06-portfolio/submissions && tar czf /workspace/$SUB.tgz $SUB && ls -la /workspace/$SUB.tgz >> $LOG
echo "=== PACKAGE DONE ===" >> $LOG
