#!/usr/bin/env bash
# Run Basalt VIO on one LaMAria sequence and score it with the same pipeline as OpenVINS.
#
# Usage: scripts/run_basalt.sh CONFIG_DIR SEQ_DIR OUT_DIR
#   CONFIG_DIR  holds config.json (Basalt VIO config) and optional options.sh (NOISE_SCALE, WALK_SCALE, THREADS)
#   SEQ_DIR     e.g. data/training/R_01_easy (or a data/training_fisheye/<seq> folder)
# Env: BASALT_BIN (default ~/.local/bin/basalt_vio), BASALT_LIB (default ~/.local/lib), PY, DROP_PRE_INIT
# Basalt reads EuRoC layout at <path>/mav0/{cam0,cam1,imu0}; we reuse the OKVIS2 input folder
# (same layout) through a mav0 symlink. The saved TUM trajectory is T_w_i (IMU pose), seconds.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$(cd "$1" && pwd)"; SEQ_DIR="$(cd "$2" && pwd)"; OUT_DIR="$3"
BASALT_BIN="${BASALT_BIN:-$HOME/.local/bin/basalt_vio}"
export LD_LIBRARY_PATH="${BASALT_LIB:-$HOME/.local/lib}:${LD_LIBRARY_PATH:-}"
PY="${PY:-$ROOT/.venv/bin/python}"
SEQ="$(basename "$SEQ_DIR")"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"
NOISE_SCALE=1.0; WALK_SCALE=1.0; THREADS=4
[ -f "$CONFIG_DIR/options.sh" ] && . "$CONFIG_DIR/options.sh"

"$PY" "$ROOT/scripts/make_okvis2_input.py" "$SEQ_DIR/runner_input" "$SEQ_DIR/okvis_input" > "$OUT_DIR/input.log"
mkdir -p "$SEQ_DIR/basalt_input"; rm -f "$SEQ_DIR/basalt_input/mav0"; ln -s ../okvis_input "$SEQ_DIR/basalt_input/mav0"
CALIB="$(ls "$SEQ_DIR"/pinhole_calibrations/*.json | head -1)"
"$PY" "$ROOT/scripts/make_basalt_calib.py" "$CALIB" "$OUT_DIR/calib.json" --noise-scale "$NOISE_SCALE" --walk-scale "$WALK_SCALE"
cp "$CONFIG_DIR/config.json" "$OUT_DIR/config.json"
{
  echo "sequence: $SEQ"; echo "config: $CONFIG_DIR"; echo "host: $(hostname)"
  echo "commit: $(git -C "$ROOT" rev-parse --short HEAD)$(git -C "$ROOT" diff --quiet || echo '-dirty')"
  echo "basalt: $(cat "$HOME/.basalt/install.json" 2>/dev/null | tr -d '\n' | cut -c1-200)"
  echo "command: $BASALT_BIN --dataset-path $SEQ_DIR/basalt_input --dataset-type euroc --cam-calib $OUT_DIR/calib.json --config-path $OUT_DIR/config.json --save-trajectory tum --num-threads $THREADS (NOISE_SCALE=$NOISE_SCALE WALK_SCALE=$WALK_SCALE)"
  echo "started: $(date -Is)"
} > "$OUT_DIR/run_info.txt"
cd "$OUT_DIR"
/usr/bin/time -f "wall_s=%e max_rss_kb=%M cpu_pct=%P" -o "$OUT_DIR/time.txt" \
  "$BASALT_BIN" --dataset-path "$SEQ_DIR/basalt_input" --dataset-type euroc --cam-calib "$OUT_DIR/calib.json" \
  --config-path "$OUT_DIR/config.json" --save-trajectory tum --show-gui false --num-threads "$THREADS" --use-imu true \
  > "$OUT_DIR/basalt.log" 2>&1 || { echo "basalt failed, see $OUT_DIR/basalt.log"; tail -5 "$OUT_DIR/basalt.log"; exit 1; }
TRAJ="$(ls "$OUT_DIR"/trajectory*.txt "$OUT_DIR"/*.tum 2>/dev/null | head -1 || true)"
[ -n "$TRAJ" ] || { echo "no trajectory written; files: $(ls "$OUT_DIR")"; exit 1; }
{ echo "# timestamp tx ty tz qx qy qz qw; IMU frame, from basalt $TRAJ"; grep -v "^#" "$TRAJ"; } > "$OUT_DIR/trajectory.tum"
"$PY" "$ROOT/scripts/tum_to_submission.py" "$OUT_DIR/trajectory.tum" "$SEQ_DIR/runner_input/image_timestamps_ns.txt" \
  "$OUT_DIR/$SEQ.txt" ${DROP_PRE_INIT:+--drop-before-first} | tee "$OUT_DIR/submission_stats.json"
ARIA_CALIB="$(ls "$SEQ_DIR"/aria_calibrations/*.json 2>/dev/null | head -1 || true)"
cd "$ROOT/third_party/lamaria"
"$PY" "$ROOT/scripts/evaluate.py" "$OUT_DIR/$SEQ.txt" "$SEQ_DIR" --out-dir "$OUT_DIR" ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OUT_DIR/eval.log"
cat "$OUT_DIR/time.txt"
