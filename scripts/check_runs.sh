#!/usr/bin/env bash
# List runs in a results folder whose stitched trajectory covers fewer than 97 % of the frames
# (truncated writes when the disk was full, or a driver that gave up). Usage: check_runs.sh RESULTS_DIR...
for D in "$@"; do
  for s in "$D"/*/segments_summary.json; do
    [ -f "$s" ] || continue
    python3 - "$s" <<'PY'
import json, sys
p=sys.argv[1]; d=json.load(open(p))
if d.get('frames') and d.get('poses', 0) < 0.97 * d['frames']:
    print(f"TRUNCATED {p.rsplit('/',2)[-2]}: {d['poses']} of {d['frames']} poses ({d.get('restarts')} restarts)")
PY
  done
done
