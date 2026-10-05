#!/usr/bin/env bash
# Two-pass per-recording camera-IMU time offset (v4 G02): pass 1 = causal VIO with observation dumps on the unshifted
# input, backend with the offset free -> td_ms, then pass 2 = the same VIO on the input shifted by td_ms.
# Usage: two_pass_td.sh CONFIG_DIR SEQ_DIR OUT_DIR   (SEQ_DIR: the unshifted sequence folder, e.g. data/derived/<seq>_rect)
# Env: SKIP_FRAMES, DROP_PRE_INIT and the driver's variables as usual; BA_CFG (default configs/vi_ba_td); KEEP_DUMP=1 keeps pass 1's dumps.
set -e
cd "$(dirname "$0")/.."
ROOT=$PWD; PY=$ROOT/.venv/bin/python; [ -x "$PY" ] || PY=python3
CFG="$1"; SEQ="$(cd "$2" && pwd)"; OUT="$3"; BA_CFG="${BA_CFG:-configs/vi_ba_td}"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"; seq=$(basename "$SEQ")
echo "pass1 start $(date -Is)" > "$OUT/two_pass.log"
OBS_DUMP=1 scripts/run_basalt_robust.sh "$CFG" "$SEQ" "$OUT/pass1" >> "$OUT/two_pass.log" 2>&1
scripts/run_vi_ba.sh "$OUT/pass1" "$SEQ" "$OUT/pass1_ba" "$BA_CFG" >> "$OUT/two_pass.log" 2>&1
td_ms=$("$PY" -c "import json,sys; print(round(json.load(open(sys.argv[1]))['calib']['td_ms'],2))" "$OUT/pass1_ba/report.json")
echo "td_ms=$td_ms" | tee -a "$OUT/two_pass.log" > "$OUT/td.txt"
[ "${KEEP_DUMP:-0}" = 1 ] || rm -rf "$OUT"/pass1/segment_*/obs "$OUT/pass1_ba/problem"
dt=$("$PY" -c "print($td_ms/1000.0)")
IN="$OUT/input_td"; rm -rf "$IN"; "$PY" scripts/make_timeshift_input.py "$SEQ" "$IN" "$dt" >> "$OUT/two_pass.log" 2>&1
head -1 "$IN/runner_input/imu.csv" >> "$OUT/two_pass.log"
echo "pass2 start $(date -Is)" >> "$OUT/two_pass.log"
scripts/run_basalt_robust.sh "$CFG" "$IN" "$OUT/pass2" >> "$OUT/two_pass.log" 2>&1
echo "done $(date -Is)" >> "$OUT/two_pass.log"
for p in pass1 pass1_ba pass2; do printf "%-9s %s\n" $p "$(grep -o '"ate_rmse_m": [0-9.]*\|"cp_score": [0-9.]*' "$OUT/$p/eval.json" 2>/dev/null | tr '\n' ' ')"; done | tee -a "$OUT/two_pass.log"
