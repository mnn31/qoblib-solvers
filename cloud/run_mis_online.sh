#!/bin/bash
# Stronger MIS attempt: KaMIS online_mis (ARW style local search) with a long
# budget, after the redumis runs finish. Sequential; every seed checked.
set -u
W=/workspace; Q=$W/QOBLIB/07-independentset; CHK=$Q/check/target/release/check_stableset
LOG=$W/mis_online.log
while tmux has-session -t mis 2>/dev/null; do sleep 60; done
for INST in frb100-40 frb59-26-2; do
  OUT=$W/mis_online/$INST; mkdir -p $OUT
  python3 $W/qoblib-solvers/explore/mis/dimacs2metis.py $Q/instances/$INST.gph $OUT/$INST.graph >> $LOG
  best=0
  for s in 0 1 2 3 4; do
    t0=$(date +%s.%N)
    $W/KaMIS/deploy/online_mis $OUT/$INST.graph --output=$OUT/seed$s.01 --time_limit=3600 --seed=$s > $OUT/seed$s.log 2>&1
    dt=$(python3 -c "print(round($(date +%s.%N)-$t0,1))")
    awk '$1==1{print NR}' $OUT/seed$s.01 > $OUT/seed$s.sol
    size=$(wc -l < $OUT/seed$s.sol | tr -d ' ')
    if $CHK $Q/instances/$INST.gph $OUT/seed$s.sol > $OUT/seed$s.check 2>&1; then ok=VALID; else ok=INVALID; fi
    echo "$INST online seed=$s size=$size $ok ${dt}s" | tee -a $OUT/summary.txt >> $LOG
    [ "$ok" = VALID ] && [ "$size" -gt "$best" ] && best=$size && cp $OUT/seed$s.sol $OUT/best.sol
  done
  echo "$INST online BEST=$best" | tee -a $OUT/summary.txt >> $LOG
done
echo "=== MIS ONLINE DONE ===" >> $LOG
