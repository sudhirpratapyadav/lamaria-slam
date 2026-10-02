#!/usr/bin/env bash
# Run ORB-SLAM3 stereo-inertial on one LaMAria sequence and score it like the others.
#
# Usage: scripts/run_orbslam3.sh CONFIG_DIR SEQ_DIR OUT_DIR
#   CONFIG_DIR  holds options.json (ORB extractor / stereo knobs, see make_orbslam3_settings.py)
#               and optional options.sh (NOISE_SCALE, WALK_SCALE)
#   SEQ_DIR     a sequence folder with runner_input/ (pinhole ASL or data/training_fisheye/<seq>)
# Env: ORB_BIN (default third_party/ORB_SLAM3/Examples/Stereo-Inertial/stereo_inertial_euroc), ORB_VOC, PY, DROP_PRE_INIT
# Output f_<name>.txt: "timestamp_ns tx ty tz qx qy qz qw", body (IMU) pose in world. Lost frames are absent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$(cd "$1" && pwd)"; SEQ_DIR="$(cd "$2" && pwd)"; OUT_DIR="$3"
ORB_BIN="${ORB_BIN:-$ROOT/third_party/ORB_SLAM3/Examples/Stereo-Inertial/stereo_inertial_euroc}"
ORB_VOC="${ORB_VOC:-$ROOT/third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt}"
PY="${PY:-$ROOT/.venv/bin/python}"
export LD_LIBRARY_PATH="$ROOT/third_party/Pangolin/install/lib:${LD_LIBRARY_PATH:-}"
SEQ="$(basename "$SEQ_DIR")"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"
NOISE_SCALE=1.0; WALK_SCALE=1.0
[ -f "$CONFIG_DIR/options.sh" ] && . "$CONFIG_DIR/options.sh"

"$PY" "$ROOT/scripts/make_okvis2_input.py" "$SEQ_DIR/runner_input" "$SEQ_DIR/okvis_input" > "$OUT_DIR/input.log"
mkdir -p "$SEQ_DIR/basalt_input"; [ -L "$SEQ_DIR/basalt_input/mav0" ] || ln -sfn ../okvis_input "$SEQ_DIR/basalt_input/mav0"
CALIB="$(ls "$SEQ_DIR"/pinhole_calibrations/*.json | head -1)"
"$PY" "$ROOT/scripts/make_orbslam3_settings.py" "$CALIB" "$OUT_DIR/orbslam3.yaml" --options "$CONFIG_DIR/options.json" \
  --noise-scale "$NOISE_SCALE" --walk-scale "$WALK_SCALE"
cp "$CONFIG_DIR/options.json" "$OUT_DIR/"
# timestamps file: ORB-SLAM3 loads <mav0/camX/data>/<ts>.png for each listed ts
cp "$SEQ_DIR/runner_input/image_timestamps_ns.txt" "$OUT_DIR/timestamps.txt"
{
  echo "sequence: $SEQ"; echo "config: $CONFIG_DIR"; echo "host: $(hostname)"
  echo "commit: $(git -C "$ROOT" rev-parse --short HEAD)$(git -C "$ROOT" diff --quiet || echo '-dirty')"
  echo "orbslam3: $(git -C "$ROOT/third_party/ORB_SLAM3" rev-parse --short HEAD) (+ c++14, viewer off)"
  echo "command: $ORB_BIN $ORB_VOC $OUT_DIR/orbslam3.yaml $SEQ_DIR/basalt_input $OUT_DIR/timestamps.txt run  (NOISE_SCALE=$NOISE_SCALE WALK_SCALE=$WALK_SCALE)"
  echo "started: $(date -Is)"
} > "$OUT_DIR/run_info.txt"
cd "$OUT_DIR"
/usr/bin/time -f "wall_s=%e max_rss_kb=%M cpu_pct=%P" -o "$OUT_DIR/time.txt" \
  "$ORB_BIN" "$ORB_VOC" "$OUT_DIR/orbslam3.yaml" "$SEQ_DIR/basalt_input" "$OUT_DIR/timestamps.txt" run \
  > "$OUT_DIR/orbslam3.log" 2>&1 || { echo "orbslam3 failed, see $OUT_DIR/orbslam3.log"; tail -5 "$OUT_DIR/orbslam3.log"; exit 1; }
[ -f "$OUT_DIR/f_run.txt" ] || { echo "no f_run.txt written; files: $(ls "$OUT_DIR")"; exit 1; }
"$PY" - "$OUT_DIR" <<'EOF'
import sys
from pathlib import Path
out = Path(sys.argv[1]); n = 0
with open(out / "trajectory.tum", "w") as f:
    f.write("# timestamp tx ty tz qx qy qz qw; body (IMU) frame, from ORB-SLAM3 f_run.txt (ns)\n")
    for line in (out / "f_run.txt").read_text().splitlines():
        v = line.split()
        if len(v) < 8: continue
        f.write(f"{float(v[0]) / 1e9:.9f} " + " ".join(v[1:8]) + "\n"); n += 1
print(f"trajectory.tum: {n} poses")
EOF
"$PY" "$ROOT/scripts/tum_to_submission.py" "$OUT_DIR/trajectory.tum" "$SEQ_DIR/runner_input/image_timestamps_ns.txt" \
  "$OUT_DIR/$SEQ.txt" ${DROP_PRE_INIT:+--drop-before-first} | tee "$OUT_DIR/submission_stats.json"
ARIA_CALIB="$(ls "$SEQ_DIR"/aria_calibrations/*.json 2>/dev/null | head -1 || true)"
cd "$ROOT/third_party/lamaria"
"$PY" "$ROOT/scripts/evaluate.py" "$OUT_DIR/$SEQ.txt" "$SEQ_DIR" --out-dir "$OUT_DIR" ${ARIA_CALIB:+--aria-calib "$ARIA_CALIB"} 2> "$OUT_DIR/eval.log"
cat "$OUT_DIR/time.txt"
