#!/usr/bin/env bash
# Bidirectional pass (experiment 023): forward run via run_sequence.sh, then a
# time-reversed run over the first WINDOW seconds, stitched onto the forward
# trajectory, then the usual submission file and evaluation. Non-causal.
#
# Usage: scripts/run_sequence_bidir.sh CONFIG_DIR SEQ_DIR OUT_DIR
# Env: WINDOW (default 200), ALIGN_FROM (80), ALIGN_TO (140), CROSSOVER_AT (110), plus run_sequence.sh env
# (SKIP_FRAMES applies to the forward run only; DROP_PRE_INIT as usual).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$(cd "$1" && pwd)"; SEQ_DIR="$(cd "$2" && pwd)"; OUT_DIR="$3"
RUNNER="${RUNNER:-$ROOT/build/runner/stereo_offline}"
PY="${PY:-$ROOT/.venv/bin/python}"
SEQ="$(basename "$SEQ_DIR")"
WINDOW="${WINDOW:-200}"; ALIGN_FROM="${ALIGN_FROM:-80}"; ALIGN_TO="${ALIGN_TO:-140}"; CROSSOVER_AT="${CROSSOVER_AT:-110}"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"

# 1. forward pass (writes $OUT_DIR/forward/<SEQ>.txt and its own eval.json); reused if present
[ -f "$OUT_DIR/forward/eval.json" ] || "$ROOT/scripts/run_sequence.sh" "$CONFIG_DIR" "$SEQ_DIR" "$OUT_DIR/forward"

# 2. reversed input over the sequence start, run with the same yaml files
"$PY" "$ROOT/scripts/make_reversed_input.py" "$SEQ_DIR/runner_input" "$OUT_DIR/reversed_input" --window "$WINDOW" > "$OUT_DIR/reverse_info.log"
mkdir -p "$OUT_DIR/backward"
cp "$OUT_DIR/forward"/*.yaml "$OUT_DIR/backward/"
/usr/bin/time -f "wall_s=%e max_rss_kb=%M" -o "$OUT_DIR/backward/time.txt" \
  "$RUNNER" "$OUT_DIR/backward/estimator.yaml" "$OUT_DIR/reversed_input" "$OUT_DIR/backward" 0 > "$OUT_DIR/backward/runner.log" 2>&1 \
  || { echo "backward runner failed, see $OUT_DIR/backward/runner.log"; tail -3 "$OUT_DIR/backward/runner.log"; exit 1; }

# 3. stitch, submission file, evaluation
"$PY" "$ROOT/scripts/stitch_bidir.py" "$OUT_DIR/forward/trajectory.tum" "$OUT_DIR/backward/trajectory.tum" \
  "$OUT_DIR/reversed_input/reverse_info.json" "$OUT_DIR/trajectory.tum" --align-from "$ALIGN_FROM" --align-to "$ALIGN_TO" --crossover-at "$CROSSOVER_AT" | tee "$OUT_DIR/stitch_stats.json"
"$PY" "$ROOT/scripts/tum_to_submission.py" "$OUT_DIR/trajectory.tum" "$SEQ_DIR/runner_input/image_timestamps_ns.txt" \
  "$OUT_DIR/$SEQ.txt" ${DROP_PRE_INIT:+--drop-before-first} | tee "$OUT_DIR/submission_stats.json"
cp "$OUT_DIR/forward/run_info.txt" "$OUT_DIR/run_info.txt"
echo "bidir: WINDOW=$WINDOW ALIGN_FROM=$ALIGN_FROM ALIGN_TO=$ALIGN_TO CROSSOVER_AT=$CROSSOVER_AT" >> "$OUT_DIR/run_info.txt"
ARIA_CALIB="$(ls "$SEQ_DIR"/aria_calibrations/*.json 2>/dev/null | head -1 || true)"
cd "$ROOT/third_party/lamaria"
"$PY" "$ROOT/scripts/evaluate.py" "$OUT_DIR/$SEQ.txt" "$SEQ_DIR" --out-dir "$OUT_DIR" ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OUT_DIR/eval.log"
