"""Robustness suite: run a system on clean images and on darkened/noisy versions over several noise seeds, and count failures.

A run fails if it jumps (a pose step over 2 m), loses more than 20 % of its poses, or its ATE is more than 3x the clean run's (and at
least 0.5 m worse). Single runs are misleading here: divergence is chaotic, so each condition is repeated over several seeds.
"""
from concurrent.futures import ThreadPoolExecutor

from . import runner

CONDITIONS = {'noise': 'noise=10', 'dark': 'gamma=1.8,gain=.6', 'dark_noise': 'gamma=1.6,gain=.6,noise=6'}


def is_failure(clean, record, ate_factor=3.0, ate_margin_m=0.5, min_pose_fraction=0.8):
    m, c = record['metrics'], clean['metrics']
    if m.get('jumps'):
        return 'jump'
    if m.get('poses', 0) < min_pose_fraction * c.get('poses', 0):
        return 'lost poses'
    a, b = (m.get('ate_yaw') or {}).get('rmse_m'), (c.get('ate_yaw') or {}).get('rmse_m')
    if a is None or b is None:
        return None
    if a > max(ate_factor * b, b + ate_margin_m):
        return 'ATE blow-up'
    return None


def run_suite(dataset, system, variant, out_root, max_seconds, seeds=4, conditions=None, workers=2, sets=(), command_spec=None):
    conditions = conditions or CONDITIONS
    clean = runner.run(dataset, system, variant, out_root, max_seconds, '', sets, command_spec)
    jobs = [(name, seed, f'{spec},seed={seed}') for name, spec in conditions.items() for seed in range(1, seeds + 1)]
    with ThreadPoolExecutor(workers) as pool:
        records = list(pool.map(lambda j: runner.run(dataset, system, variant, out_root, max_seconds, j[2], sets, command_spec), jobs))
    summary = {}
    for (name, seed, _), record in zip(jobs, records):
        entry = summary.setdefault(name, {'ate': [], 'fails': 0, 'reasons': []})
        entry['ate'].append((record['metrics'].get('ate_yaw') or {}).get('rmse_m'))
        reason = is_failure(clean, record)
        if reason:
            entry['fails'] += 1
            entry['reasons'].append(reason)
    return {'clean_ate_m': (clean['metrics'].get('ate_yaw') or {}).get('rmse_m'), 'conditions': summary, 'seeds': seeds}


def format_suite(result, label=''):
    lines = [f"{label} clean ATE {result['clean_ate_m']:.2f} m"]
    for name, e in result['conditions'].items():
        ates = ' '.join('–' if a is None else f'{a:.2f}' for a in sorted(x for x in e['ate'] if x is not None))
        lines.append(f"  {name:11} fails {e['fails']}/{result['seeds']}   ATE (m, sorted): {ates}" + (f"   [{', '.join(sorted(set(e['reasons'])))}]" if e['reasons'] else ''))
    return '\n'.join(lines)
