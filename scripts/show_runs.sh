#!/usr/bin/env bash
# one line per finished run dir: ATE, scale, score, recall, restarts
cd "$(dirname "$0")/.."
for d in "$@"; do [ -f "$d/eval.json" ] || continue; .venv/bin/python - "$d" <<'EOP'
import json,sys,os
d=sys.argv[1]; e=json.load(open(d+"/eval.json")); s=json.load(open(d+"/segments_summary.json")) if os.path.exists(d+"/segments_summary.json") else {}
f=lambda k: ("%.3f"%e[k]) if isinstance(e.get(k),(int,float)) else "-"
print("%-48s ate %7s scale %6s score %6s rec5 %6s restarts %s"%(os.path.basename(os.path.dirname(d))+"/"+os.path.basename(d),f("ate_rmse_m"),f("sim3_scale"),f("cp_score"),f("pose_recall_5m"),s.get("restarts","-")))
EOP
done
