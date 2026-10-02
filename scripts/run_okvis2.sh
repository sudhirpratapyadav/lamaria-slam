#!/usr/bin/env bash
# Run OKVIS2 on one LaMAria sequence and score it with the same pipeline as OpenVINS.
#
# Usage: scripts/run_okvis2.sh CONFIG_DIR SEQ_DIR OUT_DIR
#   CONFIG_DIR  holds options.json (estimator knobs, see make_okvis2_config.py) and optional options.sh
#               (NOISE_SCALE, WALK_SCALE)
#   SEQ_DIR     e.g. data/training/R_01_easy (or a data/training_fisheye/<seq> folder)
# Env: OKVIS_APP (default third_party/okvis2/build/okvis_app_synchronous), PY, DROP_PRE_INIT
# Outputs in OUT_DIR: okvis2-slam_trajectory.csv (live states), okvis2-slam-final_trajectory.csv
# (after the final bundle adjustment, non-causal), trajectory.tum (live) and trajectory_final.tum,
# <SEQ>.txt (submission from the LIVE trajectory) and <SEQ>_final.txt, eval.json and eval_final.json.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$(cd "$1" && pwd)"; SEQ_DIR="$(cd "$2" && pwd)"; OUT_DIR="$3"
OKVIS_APP="${OKVIS_APP:-$ROOT/third_party/okvis2/build/okvis_app_synchronous}"
PY="${PY:-$ROOT/.venv/bin/python}"
SEQ="$(basename "$SEQ_DIR")"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"
NOISE_SCALE=1.0; WALK_SCALE=1.0
[ -f "$CONFIG_DIR/options.sh" ] && . "$CONFIG_DIR/options.sh"

SKIP="${SKIP_FRAMES:-0}"; OKIN="$SEQ_DIR/okvis_input"; [ "$SKIP" = "0" ] || OKIN="$SEQ_DIR/okvis_input_skip$SKIP"
"$PY" "$ROOT/scripts/make_okvis2_input.py" "$SEQ_DIR/runner_input" "$OKIN" --skip-frames "$SKIP" > "$OUT_DIR/input.log"
CALIB="$(ls "$SEQ_DIR"/pinhole_calibrations/*.json | head -1)"
"$PY" "$ROOT/scripts/make_okvis2_config.py" "$CALIB" "$OUT_DIR/okvis2.yaml" --options "$CONFIG_DIR/options.json" \
  --noise-scale "$NOISE_SCALE" --walk-scale "$WALK_SCALE"
cp "$CONFIG_DIR/options.json" "$OUT_DIR/"
{
  echo "sequence: $SEQ"; echo "config: $CONFIG_DIR"; echo "host: $(hostname)"
  echo "commit: $(git -C "$ROOT" rev-parse --short HEAD)$(git -C "$ROOT" diff --quiet || echo '-dirty')"
  echo "okvis2: $(git -C "$ROOT/third_party/okvis2" rev-parse --short HEAD)"
  echo "command: $OKVIS_APP $OUT_DIR/okvis2.yaml $OKIN  (SKIP_FRAMES=$SKIP NOISE_SCALE=$NOISE_SCALE WALK_SCALE=$WALK_SCALE)"
  echo "started: $(date -Is)"
} > "$OUT_DIR/run_info.txt"

# OKVIS2 writes its csv files next to the dataset; run from OUT_DIR and point it at a symlink so
# outputs land here.
rm -f "$OUT_DIR/dataset"; ln -s "$OKIN" "$OUT_DIR/dataset"
cd "$OUT_DIR"
/usr/bin/time -f "wall_s=%e max_rss_kb=%M cpu_pct=%P" -o "$OUT_DIR/time.txt" \
  "$OKVIS_APP" "$OUT_DIR/okvis2.yaml" "$OUT_DIR/dataset" > "$OUT_DIR/okvis2.log" 2>&1 \
  || { echo "okvis2 failed, see $OUT_DIR/okvis2.log"; tail -5 "$OUT_DIR/okvis2.log"; exit 1; }
# outputs may land in the dataset dir or next to it depending on the build; collect both
for f in okvis2-slam_trajectory.csv okvis2-slam-final_trajectory.csv okvis2-slam-final_map.csv; do
  [ -f "$OUT_DIR/dataset/$f" ] && mv "$OUT_DIR/dataset/$f" "$OUT_DIR/$f" || true
  [ -f "$OKIN/$f" ] && mv "$OKIN/$f" "$OUT_DIR/$f" || true
done

"$PY" - "$OUT_DIR" <<'EOF'
import sys
from pathlib import Path
out = Path(sys.argv[1])
for src, dst in (("okvis2-slam_trajectory.csv", "trajectory.tum"), ("okvis2-slam-final_trajectory.csv", "trajectory_final.tum")):
    p = out / src
    if not p.exists():
        print(f"missing {src}"); continue
    n = 0
    with open(out / dst, "w") as f:
        f.write("# timestamp tx ty tz qx qy qz qw; IMU (okvis S) frame, converted from " + src + "\n")
        for line in p.read_text().splitlines():
            if not line or line.startswith("#") or line.startswith("timestamp"):
                continue
            v = [x.strip() for x in line.split(",")]
            if len(v) < 8:
                continue
            f.write(f"{int(v[0]) / 1e9:.9f} " + " ".join(v[1:8]) + "\n"); n += 1
    print(f"{dst}: {n} poses")
EOF

"$PY" "$ROOT/scripts/tum_to_submission.py" "$OUT_DIR/trajectory.tum" "$SEQ_DIR/runner_input/image_timestamps_ns.txt" \
  "$OUT_DIR/$SEQ.txt" ${DROP_PRE_INIT:+--drop-before-first} | tee "$OUT_DIR/submission_stats.json"
ARIA_CALIB="$(ls "$SEQ_DIR"/aria_calibrations/*.json 2>/dev/null | head -1 || true)"
cd "$ROOT/third_party/lamaria"
"$PY" "$ROOT/scripts/evaluate.py" "$OUT_DIR/$SEQ.txt" "$SEQ_DIR" --out-dir "$OUT_DIR" ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OUT_DIR/eval.log"
if [ -f "$OUT_DIR/trajectory_final.tum" ]; then
  "$PY" "$ROOT/scripts/tum_to_submission.py" "$OUT_DIR/trajectory_final.tum" "$SEQ_DIR/runner_input/image_timestamps_ns.txt" \
    "$OUT_DIR/${SEQ}_final.txt" ${DROP_PRE_INIT:+--drop-before-first} > "$OUT_DIR/submission_stats_final.json"
  mkdir -p "$OUT_DIR/final"
  "$PY" "$ROOT/scripts/evaluate.py" "$OUT_DIR/${SEQ}_final.txt" "$SEQ_DIR" --out-dir "$OUT_DIR/final" ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OUT_DIR/eval_final.log"
fi
cat "$OUT_DIR/time.txt"
