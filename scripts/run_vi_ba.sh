#!/usr/bin/env bash
# Non-causal backend on one finished Basalt run (made with OBS_DUMP=1): prepare -> vi_ba -> propagate -> score.
# Usage: run_vi_ba.sh RUN_DIR SEQ_DIR OUT_DIR [CONFIG_DIR=configs/vi_ba_base]
# Env: VI_BA (binary, default tools/vi_ba/build/vi_ba), DROP_PRE_INIT (as in the driver), VERBOSE=1
set -e
cd "$(dirname "$0")/.."
ROOT=$PWD; PY=$ROOT/.venv/bin/python
RUN_DIR="$(cd "$1" && pwd)"; SEQ_DIR="$(cd "$2" && pwd)"; OUT_DIR="$3"; CFG="${4:-configs/vi_ba_base}"
VI_BA="${VI_BA:-$ROOT/tools/vi_ba/build/vi_ba}"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"
{
  echo "sequence: $(basename "$SEQ_DIR")"; echo "vio run: $RUN_DIR"; echo "config: $CFG"; echo "host: $(hostname)"
  echo "commit: $(git rev-parse --short HEAD)$(git diff --quiet || echo '-dirty')"; echo "vi_ba md5: $(md5sum "$VI_BA" | cut -c1-12)"
  echo "started: $(date -Is)"
} > "$OUT_DIR/run_info.txt"
cp "$CFG/vi_ba.json" "$OUT_DIR/vi_ba.json"
"$PY" scripts/vi_ba_prepare.py "$RUN_DIR" "$SEQ_DIR" "$OUT_DIR/vi_ba.json" "$OUT_DIR/problem" | tee "$OUT_DIR/prepare.log"
/usr/bin/time -f "wall_s=%e max_rss_kb=%M cpu_pct=%P" -o "$OUT_DIR/time.txt" \
  "$VI_BA" "$OUT_DIR/problem" "$OUT_DIR/vi_ba.json" "$OUT_DIR" ${VERBOSE:+--verbose} > "$OUT_DIR/vi_ba.log" 2>&1 || { echo "vi_ba failed"; tail -5 "$OUT_DIR/vi_ba.log"; exit 1; }
tail -4 "$OUT_DIR/vi_ba.log"
"$PY" scripts/basalt_propagate_keyframes.py "$RUN_DIR/trajectory.tum" "$OUT_DIR/kf_poses.tum" "$OUT_DIR/trajectory.tum" | tee "$OUT_DIR/propagate.log"
rm -rf "$OUT_DIR/problem/obs.bin" "$OUT_DIR/problem/imu.txt"   # large and reproducible
scripts/finish_basalt_run.sh "$SEQ_DIR" "$OUT_DIR" > "$OUT_DIR/finish.log" 2>&1 || { echo "scoring failed"; tail -3 "$OUT_DIR/finish.log"; exit 1; }
echo "finished: $(date -Is)" >> "$OUT_DIR/run_info.txt"
cat "$OUT_DIR/eval.json"; echo
