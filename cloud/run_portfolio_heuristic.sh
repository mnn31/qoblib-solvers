#!/bin/bash
# Full heuristic sweep over the open a200/a400 families (3 seeds, best kept
# later) plus a050 for an honest comparison against published values.
# Strictly one process at a time. Every .sol is verified by the official
# checker (--check) as it is produced.
set -u
cd /workspace/qoblib-solvers/portfolio
export PYTHONPATH=. QOBLIB_ROOT=/workspace/QOBLIB
LOG=/workspace/port_heur.log
for seed in 0 1 2; do
  echo "$(date '+%F %T') seed $seed open families" >> $LOG
  python3 -u scripts/portfolio_heuristic.py \
    --bases a200_t10,a200_t15,a400_t10,a400_t15 --seed $seed --check \
    --outdir results/heuristic_open_seed$seed >> $LOG 2>&1
done
echo "$(date '+%F %T') a050 comparison" >> $LOG
python3 -u scripts/portfolio_heuristic.py --bases a050 --seed 0 --check \
  --outdir results/heuristic_a050 >> $LOG 2>&1
echo "$(date '+%F %T') === PORTFOLIO HEURISTIC DONE ===" >> $LOG
