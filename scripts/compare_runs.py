#!/usr/bin/env python3
"""Per-sequence comparison of experiment result folders against a reference.

usage: compare_runs.py REF_DIR EXP_DIR [EXP_DIR ...] [--md]

Prints ATE (controlled set, both start offsets), control-point score (additional
set) and restarts per run, then the two aggregates used on the scoreboard:
controlled two-offset mean ATE and additional-set mean score. Only sequences
present in every folder enter the aggregates ("common"), the full reference
aggregate is printed next to it.
"""
import glob, json, os, re, sys

def load(d):
    r = {}
    for e in glob.glob(os.path.join(d, '*', 'eval.json')):
        run = os.path.basename(os.path.dirname(e))
        try:
            j = json.load(open(e))
        except Exception:
            continue
        rs = 0
        ss = os.path.join(os.path.dirname(e), 'segments_summary.json')
        if os.path.exists(ss):
            try:
                rs = json.load(open(ss)).get('restarts', 0)
            except Exception:
                rs = -1  # summary holds error text
        j['restarts'] = rs
        r[run] = j
    return r

def fmt(v, p=3):
    return '-' if v is None else f'{v:.{p}f}'

def main():
    md = '--md' in sys.argv
    dirs = [a for a in sys.argv[1:] if not a.startswith('--')]
    names = [os.path.basename(d.rstrip('/')) for d in dirs]
    data = [load(d) for d in dirs]
    runs = sorted(set().union(*[set(d) for d in data]))
    ctrl = [r for r in runs if r.startswith('R_')]
    addl = [r for r in runs if r.startswith('sequence_')]
    sep = ' | ' if md else '  '
    head = ['run'] + [f'{n} ate/score/rs' for n in names]
    print(sep.join(head))
    if md:
        print('|' + '---|' * len(head))
    for r in ctrl + addl:
        row = [r]
        for d in data:
            j = d.get(r)
            if j is None:
                row.append('(missing)')
            else:
                row.append(f"{fmt(j.get('ate_rmse_m'),2)} / {fmt(j.get('cp_score'),1)} / {j['restarts']}")
        print(sep.join(row))
    # aggregates
    def agg(d, keys, field):
        v = [d[k][field] for k in keys if k in d and d[k].get(field) is not None]
        return (sum(v) / len(v), len(v)) if v else (None, 0)
    cc = [r for r in ctrl if all(r in d for d in data)]
    ca = [r for r in addl if all(r in d for d in data)]
    print()
    for n, d in zip(names, data):
        a, na = agg(d, cc, 'ate_rmse_m')
        s, ns = agg(d, ca, 'cp_score')
        af, naf = agg(d, [r for r in ctrl if r in d], 'ate_rmse_m')
        sf, nsf = agg(d, [r for r in addl if r in d], 'cp_score')
        rs = sum(d[r]['restarts'] for r in d)
        print(f'{n}: controlled mean ATE {fmt(a)} on {na} common runs (own {fmt(af)} on {naf}); '
              f'additional mean score {fmt(s,1)} on {ns} common (own {fmt(sf,1)} on {nsf}); restarts {rs}')

if __name__ == '__main__':
    main()
