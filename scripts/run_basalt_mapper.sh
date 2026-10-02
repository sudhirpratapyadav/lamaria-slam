#!/usr/bin/env bash
# Basalt VIO + offline mapper (global BA, non-causal) on one sequence, scored like the others.
# Uses the source build (third_party/basalt/build/release) whose mapper saves its trajectory headless.
#
# Usage: scripts/run_basalt_mapper.sh CONFIG_DIR SEQ_DIR OUT_DIR
# Env: SKIP_FRAMES, DROP_PRE_INIT, THREADS, plus config options.sh (NOISE_SCALE, WALK_SCALE)
# Outputs: vio/trajectory.txt (VIO, TUM), mapper/keyframeTrajectory.txt, trajectory.tum (propagated),
# <SEQ>.txt submission + eval.json (mapper path), vio/<SEQ>.txt + vio/eval.json (VIO path).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$(cd "$1" && pwd)"; SEQ_DIR="$(cd "$2" && pwd)"; OUT_DIR="$3"
BIN="$ROOT/third_party/basalt/build/release"
export LD_LIBRARY_PATH="$HOME/.local/lib:${LD_LIBRARY_PATH:-}"
PY="${PY:-$ROOT/.venv/bin/python}"
SEQ="$(basename "$SEQ_DIR")"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"
NOISE_SCALE=1.0; WALK_SCALE=1.0; THREADS="${THREADS:-3}"
[ -f "$CONFIG_DIR/options.sh" ] && . "$CONFIG_DIR/options.sh"
SKIP="${SKIP_FRAMES:-0}"; OKIN="$SEQ_DIR/okvis_input"; [ "$SKIP" = "0" ] || OKIN="$SEQ_DIR/okvis_input_skip$SKIP"
"$PY" "$ROOT/scripts/make_okvis2_input.py" "$SEQ_DIR/runner_input" "$OKIN" --skip-frames "$SKIP" > "$OUT_DIR/input.log"
BIN_DIR="$SEQ_DIR/basalt_input"; [ "$SKIP" = "0" ] || BIN_DIR="$SEQ_DIR/basalt_input_skip$SKIP"
mkdir -p "$BIN_DIR"; [ -L "$BIN_DIR/mav0" ] || ln -sfn "../$(basename "$OKIN")" "$BIN_DIR/mav0"
CALIB="$(ls "$SEQ_DIR"/pinhole_calibrations/*.json | head -1)"
"$PY" "$ROOT/scripts/make_basalt_calib.py" "$CALIB" "$OUT_DIR/calib.json" --noise-scale "$NOISE_SCALE" --walk-scale "$WALK_SCALE" > /dev/null
cp "$CONFIG_DIR/config.json" "$OUT_DIR/config.json"
{
  echo "sequence: $SEQ"; echo "config: $CONFIG_DIR (vio + mapper, source build)"; echo "host: $(hostname)"
  echo "commit: $(git -C "$ROOT" rev-parse --short HEAD)$(git -C "$ROOT" diff --quiet || echo '-dirty')"
  echo "basalt: $(git -C "$ROOT/third_party/basalt" rev-parse --short HEAD) (+ mapper headless save, no -Werror, no realsense)"
  echo "started: $(date -Is)"
} > "$OUT_DIR/run_info.txt"
mkdir -p "$OUT_DIR/vio" "$OUT_DIR/marg" "$OUT_DIR/mapper"
cd "$OUT_DIR/vio"
/usr/bin/time -f "wall_s=%e max_rss_kb=%M cpu_pct=%P" -o "$OUT_DIR/vio/time.txt" \
  "$BIN/basalt_vio" --dataset-path "$BIN_DIR" --dataset-type euroc --cam-calib "$OUT_DIR/calib.json" --config-path "$OUT_DIR/config.json" \
  --save-trajectory tum --show-gui false --num-threads "$THREADS" --use-imu true --marg-data "$OUT_DIR/marg" > "$OUT_DIR/vio/basalt.log" 2>&1 \
  || { echo "basalt_vio failed"; tail -3 "$OUT_DIR/vio/basalt.log"; exit 1; }
{ echo "# timestamp tx ty tz qx qy qz qw; IMU frame, basalt vio"; grep -v "^#" "$OUT_DIR/vio/trajectory.txt"; } > "$OUT_DIR/vio/trajectory.tum"
cd "$OUT_DIR/mapper"
/usr/bin/time -f "wall_s=%e max_rss_kb=%M cpu_pct=%P" -o "$OUT_DIR/mapper/time.txt" \
  "$BIN/basalt_mapper" --cam-calib "$OUT_DIR/calib.json" --marg-data "$OUT_DIR/marg" --config-path "$OUT_DIR/config.json" --show-gui false \
  > "$OUT_DIR/mapper/mapper.log" 2>&1 || { echo "basalt_mapper failed"; tail -3 "$OUT_DIR/mapper/mapper.log"; exit 1; }
[ -f "$OUT_DIR/mapper/keyframeTrajectory.txt" ] || { echo "mapper wrote no keyframeTrajectory.txt"; ls "$OUT_DIR/mapper"; exit 1; }
"$PY" "$ROOT/scripts/basalt_propagate_keyframes.py" "$OUT_DIR/vio/trajectory.tum" "$OUT_DIR/mapper/keyframeTrajectory.txt" "$OUT_DIR/trajectory.tum" | tee "$OUT_DIR/propagate.log"
ARIA_CALIB="$(ls "$SEQ_DIR"/aria_calibrations/*.json 2>/dev/null | head -1 || true)"
for variant in "" vio; do
  if [ -z "$variant" ]; then T="$OUT_DIR/trajectory.tum"; OD="$OUT_DIR"; else T="$OUT_DIR/vio/trajectory.tum"; OD="$OUT_DIR/vio"; fi
  "$PY" "$ROOT/scripts/tum_to_submission.py" "$T" "$SEQ_DIR/runner_input/image_timestamps_ns.txt" "$OD/$SEQ.txt" ${DROP_PRE_INIT:+--drop-before-first} > "$OD/submission_stats.json"
  (cd "$ROOT/third_party/lamaria" && "$PY" "$ROOT/scripts/evaluate.py" "$OD/$SEQ.txt" "$SEQ_DIR" --out-dir "$OD" ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OD/eval.log" > /dev/null)
done
cat "$OUT_DIR/vio/time.txt" "$OUT_DIR/mapper/time.txt"
