#!/bin/bash
# Run KaMIS redumis on one QOBLIB independent-set instance with many seeds,
# verify every result with the official checker, keep the best.
#   run_mis.sh <instance> <seeds> <time_limit_s> [threads_per_run]
# Runs are sequential (one at a time) so runtimes are comparable.
set -u
INST=$1; SEEDS=${2:-10}; TL=${3:-3600}
W=/workspace; Q=$W/QOBLIB/07-independentset; OUT=$W/mis_results/$INST
mkdir -p $OUT
python3 $W/qoblib-solvers/explore/mis/dimacs2metis.py $Q/instances/$INST.gph $OUT/$INST.graph
CHK=$Q/check/target/release/check_stableset
best=0
for s in $(seq 0 $((SEEDS-1))); do
  t0=$(date +%s.%N)
  $W/KaMIS/deploy/redumis $OUT/$INST.graph --output=$OUT/seed$s.01 --time_limit=$TL --seed=$s > $OUT/seed$s.log 2>&1
  dt=$(python3 -c "print(round($(date +%s.%N)-$t0,1))")
  # 0/1 per line -> 1-indexed vertex list the checker accepts
  awk '$1==1{print NR}' $OUT/seed$s.01 > $OUT/seed$s.sol
  size=$(wc -l < $OUT/seed$s.sol | tr -d ' ')
  if $CHK $Q/instances/$INST.gph $OUT/seed$s.sol > $OUT/seed$s.check 2>&1; then ok=VALID; else ok=INVALID; fi
  echo "$INST seed=$s size=$size $ok ${dt}s" | tee -a $OUT/summary.txt
  if [ "$ok" = VALID ] && [ "$size" -gt "$best" ]; then best=$size; cp $OUT/seed$s.sol $OUT/best.sol; fi
done
echo "$INST BEST=$best" | tee -a $OUT/summary.txt
