#!/usr/bin/env bash
# Post-process a Basalt run folder that has trajectory.tum but no evaluation (submission conversion + official
# evaluators), e.g. after the driver script was edited while runs were in flight (bash reads scripts incrementally).
# Usage: finish_basalt_run.sh SEQ_DIR OUT_DIR   (same SEQ_DIR the run used; DROP_PRE_INIT honoured as in the driver)
set -e
cd "$(dirname "$0")/.."
ROOT=$PWD; PY=$ROOT/.venv/bin/python
SEQ_DIR="$(cd "$1" && pwd)"; OUT_DIR="$(cd "$2" && pwd)"; SEQ="$(basename "$SEQ_DIR")"
"$PY" "$ROOT/scripts/tum_to_submission.py" "$OUT_DIR/trajectory.tum" "$SEQ_DIR/runner_input/image_timestamps_ns.txt" \
  "$OUT_DIR/$SEQ.txt" ${DROP_PRE_INIT:+--drop-before-first} | tee "$OUT_DIR/submission_stats.json"
ARIA_CALIB="$(ls "$SEQ_DIR"/aria_calibrations/*.json 2>/dev/null | head -1 || true)"
cd "$ROOT/third_party/lamaria"
"$PY" "$ROOT/scripts/evaluate.py" "$OUT_DIR/$SEQ.txt" "$SEQ_DIR" --out-dir "$OUT_DIR" ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OUT_DIR/eval.log"
