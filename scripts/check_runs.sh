#!/usr/bin/env bash
# List runs in a results folder whose stitched trajectory covers fewer than 97 % of the frames
# (truncated writes when the disk was full, or a driver that gave up). Usage: check_runs.sh RESULTS_DIR...
for D in "$@"; do
  for s in "$D"/*/segments_summary.json; do
    [ -f "$s" ] || continue
    python3 - "$s" <<'PY'
import json, sys, os
p=sys.argv[1]
try: d=json.load(open(p))
except Exception: sys.exit(0)  # still being written
skip=0
try:
    s0=json.load(open(os.path.join(os.path.dirname(p),'segments.json')))['segments'][0]; skip=int(s0.get('skip',0))
except Exception: pass
if d.get('frames') and d.get('poses', 0) < 0.97 * (d['frames'] - skip):
    print(f"TRUNCATED {p.rsplit('/',2)[-2]}: {d['poses']} of {d['frames']} poses ({d.get('restarts')} restarts)")
PY
  done
done
