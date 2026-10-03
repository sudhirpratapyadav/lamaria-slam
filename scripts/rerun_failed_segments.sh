#!/usr/bin/env bash
# Re-run Basalt robust-driver runs in a results folder whose segments.json has a "failed"
# (crashed) segment, with the env variables recorded in the run's env.txt (written by the
# v3 batches) or passed through. Usage: rerun_failed_segments.sh RESULTS_DIR [--wait-for LOGFILE]
# Each run dir must contain run_info.txt with "sequence: <seq>" and env.txt with VAR=VALUE lines.
set -u
cd "$(dirname "$0")/.."
DIR="$1"; shift
if [ "${1:-}" = "--wait-for" ]; then while ! grep -q "batch done" "$2" 2>/dev/null; do sleep 120; done; fi
export BASALT_VIO=$PWD/third_party/basalt/build/release/basalt_vio DROP_PRE_INIT=1 SKIP_FRAMES=0
for seg in "$DIR"/*/segments.json; do
  grep -q '"failed"' "$seg" 2>/dev/null || continue
  d=$(dirname "$seg"); seq=$(grep "^sequence:" "$d/run_info.txt" | awk '{print $2}')
  [ -f "$d/env.txt" ] || { echo "no env.txt in $d, skipped"; continue; }
  mv "$d" "${d}_crashed"
  (env $(cat "${d}_crashed/env.txt" | tr '\n' ' ') scripts/run_basalt_robust.sh configs/basalt_ref1 data/training/$seq "$d" > "$d.log" 2>&1; echo "exit=$?" >> "$d.log"; echo "rerun $(basename $d) done") &
done; wait
echo "rerun done $(date -Is)" >> "$DIR/batch.log"
