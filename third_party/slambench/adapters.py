"""Run a SLAM/VIO system on a recording and return its trajectory plus timing.

An adapter returns {'trajectory': (N,8) TUM array, 'frame': 'imu'|'body', 'timing': {...}}. 'imu' means the poses are of the IMU
frame (OpenVINS) and are converted to the reference body frame before scoring; 'body' means they are already comparable.
New systems (Basalt, ORB-SLAM3, ...) plug in through run_command with a JSON spec; no code changes needed.
"""
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

from .metrics import read_tum

ROOT = Path(__file__).resolve().parents[1]

OPENVINS_VARIANTS = {'full': 'stationary_v2',          # 600 features, 11 clones, 50 SLAM: the desktop-class settings
                     'balanced': 'jetson_balanced',    # 200 / 6 / 25
                     'robust': 'jetson_robust',        # 300 / 8 / 40, 1.5 px pixel noise
                     'recorded': 'recorded'}           # the dataset authors' own estimator settings


def run_openvins(dataset, variant, raw_out, cache, max_seconds=0., augment='', sets=()):
    profile = OPENVINS_VARIANTS.get(variant)
    if profile is None:
        raise ValueError(f'Unknown OpenVINS variant {variant!r}; use one of {", ".join(OPENVINS_VARIANTS)}')
    cmd = [sys.executable, str(ROOT / 'scripts/replay_benchmark.py'), str(dataset.recording), '--config', str(dataset.config_dir(cache)),
           '--out', str(raw_out), '--profile', profile, '--mode', 'all']
    if max_seconds:
        cmd += ['--max-seconds', str(max_seconds)]
    if augment:
        cmd += ['--augment', augment]
    for item in sets:
        cmd += ['--set', item]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    summary = json.loads((Path(raw_out) / 'summary.json').read_text())
    return {'trajectory': read_tum(Path(raw_out) / 'trajectory.tum'), 'frame': 'imu',
            'timing': {'compute_ms': summary['compute_ms'], 'image_read_ms': summary.get('image_read_ms'), 'wall_s': summary['wall_s'],
                       'peak_rss_mb': summary['peak_rss_mb'], 'cpu_cores_avg': summary['cpu_cores_avg'], 'input_pairs': summary['input']['pairs']}}


def run_command(dataset, spec, raw_out, cache, max_seconds=0.):
    """Run any external system. spec = {"cmd": [...], "trajectory": "path/to/tum", "frame": "body", "cwd": "..."}; the strings may use
    {recording} {config} {out} {max_seconds}."""
    fields = {'recording': dataset.recording, 'config': dataset.config_dir(cache), 'out': raw_out, 'max_seconds': max_seconds}
    Path(raw_out).mkdir(parents=True, exist_ok=True)
    cmd = [str(part).format(**fields) for part in spec['cmd']]
    before = time.perf_counter()
    subprocess.run(cmd, cwd=spec.get('cwd'), check=True, env={**os.environ, **spec.get('env', {})},
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    wall = time.perf_counter() - before
    trajectory = read_tum(str(spec['trajectory']).format(**fields))
    return {'trajectory': trajectory, 'frame': spec.get('frame', 'body'),
            'timing': {'wall_s': wall, 'peak_rss_mb': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.}}
