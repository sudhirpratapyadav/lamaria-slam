#!/usr/bin/env bash
# Run OpenVINS stereo+IMU on one LaMAria sequence, write the submission file and score it.
#
# Usage: scripts/run_sequence.sh CONFIG_DIR SEQ_DIR OUT_DIR
#   CONFIG_DIR  e.g. configs/ov_baseline (estimator.yaml + imucam.yaml + imu.yaml)
#   SEQ_DIR     e.g. data/training/R_01_easy
#   OUT_DIR     e.g. results/001-ov-baseline/R_01_easy
# Env: RUNNER (default build/runner/stereo_offline), PY (default .venv/bin/python)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$(cd "$1" && pwd)"; SEQ_DIR="$(cd "$2" && pwd)"; OUT_DIR="$3"
RUNNER="${RUNNER:-$ROOT/build/runner/stereo_offline}"
PY="${PY:-$ROOT/.venv/bin/python}"
SEQ="$(basename "$SEQ_DIR")"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"

"$PY" "$ROOT/scripts/prepare_runner_input.py" "$SEQ_DIR"
# Calibration is per sequence (Aria calibrations vary between recordings), so the
# camera/IMU yaml files are generated here; the config dir holds estimator.yaml
# and optional options.sh (e.g. NOISE_SCALE=5).
NOISE_SCALE=1.0
WALK_SCALE=
TIMESHIFT=0.0
ACC_SCALE=1.0
[ -f "$CONFIG_DIR/options.sh" ] && . "$CONFIG_DIR/options.sh"
cp "$CONFIG_DIR/estimator.yaml" "$OUT_DIR/"
CALIB="$(ls "$SEQ_DIR"/pinhole_calibrations/*.json | head -1)"
"$PY" "$ROOT/scripts/make_openvins_config.py" "$CALIB" "$OUT_DIR" --noise-scale "$NOISE_SCALE" ${WALK_SCALE:+--walk-scale "$WALK_SCALE"} --timeshift "$TIMESHIFT" --acc-scale "$ACC_SCALE"
{
  echo "sequence: $SEQ"; echo "config: $CONFIG_DIR"; echo "host: $(hostname)"
  echo "commit: $(git -C "$ROOT" rev-parse --short HEAD)$(git -C "$ROOT" diff --quiet || echo '-dirty')"
  echo "command: $RUNNER $OUT_DIR/estimator.yaml $SEQ_DIR/runner_input $OUT_DIR  (NOISE_SCALE=$NOISE_SCALE WALK_SCALE=${WALK_SCALE:-$NOISE_SCALE} TIMESHIFT=$TIMESHIFT ACC_SCALE=$ACC_SCALE SKIP_FRAMES=${SKIP_FRAMES:-0})"
  echo "started: $(date -Is)"
} > "$OUT_DIR/run_info.txt"

/usr/bin/time -f "wall_s=%e max_rss_kb=%M cpu_pct=%P" -o "$OUT_DIR/time.txt" \
  "$RUNNER" "$OUT_DIR/estimator.yaml" "$SEQ_DIR/runner_input" "$OUT_DIR" "${SKIP_FRAMES:-0}" > "$OUT_DIR/runner.log" 2>&1 \
  || { echo "runner failed, see $OUT_DIR/runner.log"; tail -5 "$OUT_DIR/runner.log"; exit 1; }

"$PY" "$ROOT/scripts/tum_to_submission.py" "$OUT_DIR/trajectory.tum" \
  "$SEQ_DIR/runner_input/image_timestamps_ns.txt" "$OUT_DIR/$SEQ.txt" ${DROP_PRE_INIT:+--drop-before-first} | tee "$OUT_DIR/submission_stats.json"

ARIA_CALIB="$(ls "$SEQ_DIR"/aria_calibrations/*.json 2>/dev/null | head -1 || true)"
cd "$ROOT/third_party/lamaria"
"$PY" "$ROOT/scripts/evaluate.py" "$OUT_DIR/$SEQ.txt" "$SEQ_DIR" --out-dir "$OUT_DIR" \
  ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OUT_DIR/eval.log"
cat "$OUT_DIR/time.txt"
