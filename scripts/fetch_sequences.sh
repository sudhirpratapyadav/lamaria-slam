#!/usr/bin/env bash
# Download LaMAria training sequences one at a time (ASL format), unzip, delete
# the zip, prepare the runner input, and fetch the aria calibration JSON (needed
# by the control-point evaluator). Resumable: already complete sequences are skipped.
#
# Usage: scripts/fetch_sequences.sh SEQ [SEQ ...]
# Env: DATA (default data), LAMARIA (default third_party/lamaria), PY (default .venv/bin/python)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${DATA:-$ROOT/data}"; LAMARIA="${LAMARIA:-$ROOT/third_party/lamaria}"; PY="${PY:-$ROOT/.venv/bin/python}"
BASE="https://cvg-data.inf.ethz.ch/lamaria"
for seq in "$@"; do
  d="$DATA/training/$seq"
  echo "== $seq  $(date -Is)  free: $(df -h --output=avail "$DATA" | tail -1 | tr -d ' ')"
  if [ ! -f "$d/runner_input/stereo.csv" ]; then
    (cd "$LAMARIA" && "$PY" -m tools.download_lamaria --output_dir "$DATA" --sequences "$seq" --type asl 2>&1 | tr '\r' '\n' | grep -v "%|" || true)
    "$PY" "$ROOT/scripts/prepare_runner_input.py" "$d"
  fi
  rm -f "$d"/asl_folder/*.zip
  mkdir -p "$d/aria_calibrations"
  [ -s "$d/aria_calibrations/$seq.json" ] || curl -sf "$BASE/aria_calibrations/training/$seq.json" -o "$d/aria_calibrations/$seq.json"
  echo "   done: $(du -sh "$d" | cut -f1), aria calib $( [ -s "$d/aria_calibrations/$seq.json" ] && echo ok || echo MISSING)"
done
