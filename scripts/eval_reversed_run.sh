#!/usr/bin/env bash
# Map a time-reversed Basalt run (data/derived/<seq>_rev, t' = pivot2 - t) back to forward time and score it against the real sequence.
# Usage: eval_reversed_run.sh SEQ OUT_DIR   (OUT_DIR holds the reversed run's trajectory.tum; writes OUT_DIR/fwd/{trajectory.tum,<SEQ>.txt,eval.json})
set -e
cd "$(dirname "$0")/.."
ROOT=$PWD; PY=$ROOT/.venv/bin/python; SEQ=$1; OUT=$(cd "$2" && pwd); F=$OUT/fwd; mkdir -p "$F"
PIV=$($PY -c "import json; print(json.load(open('data/derived/${SEQ}_rev/runner_input/reverse_info.json'))['pivot2'])")
$PY - "$OUT/trajectory.tum" "$F/trajectory.tum" "$PIV" <<'EOP'
import sys, numpy as np
src, dst, piv = sys.argv[1], sys.argv[2], float(sys.argv[3])
a = np.array([l.split() for l in open(src) if l.strip() and not l.startswith('#')], dtype=float)
a[:, 0] = piv - a[:, 0]; a = a[np.argsort(a[:, 0])]
with open(dst, 'w') as f:
    f.write('# reversed run mapped to forward time\n')
    for r in a: f.write('%.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f\n' % tuple(r))
EOP
DROP_PRE_INIT=1 scripts/finish_basalt_run.sh "data/training/$SEQ" "$F" > /dev/null
echo "$SEQ reversed: $($PY -c "import json; d=json.load(open('$F/eval.json')); print('ate %.3f scale %.3f score %s rec5 %s'%(d['ate_rmse_m'], d['sim3_scale'], d.get('cp_score'), d.get('pose_recall_5m')))")"
