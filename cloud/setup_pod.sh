#!/bin/bash
# One-shot setup for a fresh Ubuntu CPU pod used to run QOBLIB experiments.
# Everything is pulled from public git, so no files need copying to the box.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
log() { echo "[setup $(date +%T)] $*"; }

log "apt"
apt-get update -qq && apt-get install -y -qq build-essential cmake git tmux curl \
  pkg-config libtbb-dev python3-venv python3-dev >/dev/null

log "rust (for the QOBLIB checkers)"
if ! command -v cargo >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y -q
fi
export PATH="$HOME/.cargo/bin:$PATH"

log "python deps"
pip3 install -q --break-system-packages numpy scipy highspy ortools 2>&1 | tail -1 || true

mkdir -p /workspace && cd /workspace
log "clone QOBLIB (shallow)"
[ -d QOBLIB ] || git clone -q --depth 1 https://github.com/ZIB-AOPT/QOBLIB.git
log "clone qoblib-solvers"
[ -d qoblib-solvers ] || git clone -q https://github.com/mnn31/qoblib-solvers.git

log "build checkers: 07-independentset, 04-steiner, 06-portfolio"
for d in 07-independentset 04-steiner 06-portfolio; do
  (cd QOBLIB/$d/check && cargo build --release -q 2>&1 | tail -1 || true)
done

log "KaMIS (MIS solver)"
if [ ! -d KaMIS ]; then
  git clone -q https://github.com/KarlsruheMIS/KaMIS.git
  (cd KaMIS && ./compile_withcmake.sh >/tmp/kamis_build.log 2>&1 || tail -20 /tmp/kamis_build.log)
fi
ls KaMIS/deploy 2>/dev/null || true

log "hardware"
lscpu | grep -E "Model name|^CPU\(s\)|Thread|Core|Socket" | sed 's/  */ /g'
free -g | sed -n 2p
log "DONE"
