#!/usr/bin/env bash
# Basalt with script-level divergence recovery (basalt_segments.py), scored like the others.
# Usage: scripts/run_basalt_robust.sh CONFIG_DIR SEQ_DIR OUT_DIR
# Env: SKIP_FRAMES, DROP_PRE_INIT, MAX_SPEED (6), MAX_JUMP (1), BACK (20), plus config options.sh (NOISE_SCALE, WALK_SCALE, THREADS)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$(cd "$1" && pwd)"; SEQ_DIR="$(cd "$2" && pwd)"; OUT_DIR="$3"
PY="${PY:-$ROOT/.venv/bin/python}"
SEQ="$(basename "$SEQ_DIR")"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"
NOISE_SCALE=1.0; WALK_SCALE=1.0; THREADS=3
[ -f "$CONFIG_DIR/options.sh" ] && . "$CONFIG_DIR/options.sh"
CALIB="$(ls "$SEQ_DIR"/pinhole_calibrations/*.json | head -1)"
"$PY" "$ROOT/scripts/make_basalt_calib.py" "$CALIB" "$OUT_DIR/calib.json" --noise-scale "$NOISE_SCALE" --walk-scale "$WALK_SCALE" > /dev/null
cp "$CONFIG_DIR/config.json" "$OUT_DIR/config.json"
{
  echo "sequence: $SEQ"; echo "config: $CONFIG_DIR (robust segments)"; echo "host: $(hostname)"
  echo "commit: $(git -C "$ROOT" rev-parse --short HEAD)$(git -C "$ROOT" diff --quiet || echo '-dirty')"
  echo "binary: ${BASALT_VIO:-~/.local/bin/basalt_vio} BASALT_CLAHE=${BASALT_CLAHE:-}"
  echo "command: basalt_segments.py $SEQ_DIR $OUT_DIR --skip-frames ${SKIP_FRAMES:-0} --max-speed ${MAX_SPEED:-6} --max-jump ${MAX_JUMP:-1} --back ${BACK:-20} (NOISE_SCALE=$NOISE_SCALE WALK_SCALE=$WALK_SCALE THREADS=$THREADS)"
  echo "started: $(date -Is)"
} > "$OUT_DIR/run_info.txt"
/usr/bin/time -f "wall_s=%e max_rss_kb=%M cpu_pct=%P" -o "$OUT_DIR/time.txt" \
  "$PY" "$ROOT/scripts/basalt_segments.py" "$SEQ_DIR" "$OUT_DIR" --calib "$OUT_DIR/calib.json" --config "$OUT_DIR/config.json" \
  --threads "$THREADS" --skip-frames "${SKIP_FRAMES:-0}" --max-speed "${MAX_SPEED:-6}" --max-jump "${MAX_JUMP:-1}" --back "${BACK:-20}" \
  | tee "$OUT_DIR/segments_summary.json"
"$PY" "$ROOT/scripts/tum_to_submission.py" "$OUT_DIR/trajectory.tum" "$SEQ_DIR/runner_input/image_timestamps_ns.txt" \
  "$OUT_DIR/$SEQ.txt" ${DROP_PRE_INIT:+--drop-before-first} | tee "$OUT_DIR/submission_stats.json"
ARIA_CALIB="$(ls "$SEQ_DIR"/aria_calibrations/*.json 2>/dev/null | head -1 || true)"
cd "$ROOT/third_party/lamaria"
"$PY" "$ROOT/scripts/evaluate.py" "$OUT_DIR/$SEQ.txt" "$SEQ_DIR" --out-dir "$OUT_DIR" ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OUT_DIR/eval.log"
cat "$OUT_DIR/time.txt"
