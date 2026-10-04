#!/usr/bin/env bash
# Freeze the current installed Basalt binaries into an experiment folder (EXP_DIR/bin), so every run of
# the experiment uses one binary even if the install dir is updated meanwhile (X08: runs of identical
# code built at different times differ on sequences with divergences, most likely through differences
# in floating-point contraction). Prints the path to use as BASALT_VIO.
set -e
cd "$(dirname "$0")/.."
D="$1/bin"; mkdir -p "$D"
for f in basalt_vio libbasalt.so; do cp third_party/basalt/install/$f "$D/.$f.tmp" && mv -f "$D/.$f.tmp" "$D/$f"; done
# both files: the estimator code lives in libbasalt.so, basalt_vio alone does not change with it
(cd "$D" && md5sum basalt_vio libbasalt.so | cut -c1-12 | paste -sd" ") > "$D/md5.txt"
echo "$PWD/$D/basalt_vio"
