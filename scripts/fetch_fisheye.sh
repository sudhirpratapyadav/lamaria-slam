#!/usr/bin/env bash
# For each sequence: download the raw .vrs (if missing), extract the fisheye runner input,
# fit the equidistant lens, then delete the .vrs to save disk (re-downloadable).
# Usage: scripts/fetch_fisheye.sh SEQ [SEQ ...]   Env: DATA, LAMARIA, PY as in fetch_sequences.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${DATA:-$ROOT/data}"; LAMARIA="${LAMARIA:-$ROOT/third_party/lamaria}"; PY="${PY:-$ROOT/.venv/bin/python}"
for seq in "$@"; do
  d="$DATA/training/$seq"; f="$DATA/training_fisheye/$seq"
  echo "== $seq $(date -Is) free: $(df -h --output=avail "$DATA" | tail -1 | tr -d ' ')"
  if [ -f "$f/runner_input/stereo.csv" ] && [ -f "$f/pinhole_calibrations/$seq.json" ]; then echo "   already done"; continue; fi
  ls "$d"/raw_data/*.vrs > /dev/null 2>&1 || (cd "$LAMARIA" && "$PY" -m tools.download_lamaria --output_dir "$DATA" --sequences "$seq" --type raw 2>&1 | tr '\r' '\n' | grep -v "%|" || true)
  "$PY" "$ROOT/scripts/vrs_to_runner_input.py" "$d" "$f" 2>&1 | grep -v "^\[" | tail -1
  rm -f "$f/pinhole_calibrations"; mkdir -p "$f/pinhole_calibrations"
  "$PY" "$ROOT/scripts/fit_fisheye_kb.py" "$d" "$d/aria_calibrations/$seq.json" "$f/pinhole_calibrations/$seq.json" 2>&1 | grep -v "^\[" | grep "reproj" | cut -c1-140
  rm -f "$d"/raw_data/*.vrs
  echo "   done: $(du -sh "$f" | cut -f1)"
done
