#!/usr/bin/env python3
"""Replay a recording through the VIO estimator on this machine and measure speed and accuracy.

Runs identically on the PC, the A100 server and the Jetson (no camera, browser or app session needed), so the
same recording gives comparable numbers everywhere. Variants (lower resolution or frame rate, estimator
settings) are derived from one full-quality recording, which shows what the estimator needs and what it can spare.

  python scripts/replay_benchmark.py REC --out runs_bench/ref                       # reference: every frame, as is
  python scripts/replay_benchmark.py REC --out runs_bench/v1 --scale .5 --stride 2 \\
         --set num_pts=300 --set max_clones=8 --reference runs_bench/ref/trajectory.tum
  python scripts/replay_benchmark.py REC --out runs_bench/rt --mode realtime        # emulate the live loop on this host
"""
import argparse
import csv
import json
import platform
import re
import resource
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from webapp.backend import slam_native
from webapp.backend.diagnostics import prepare_estimator, PROFILES
from webapp.backend.worker import replay_rows
from prepare_kimera import read_yaml, write_yaml


def apply_settings(config, settings):
    path = config/'estimator.yaml'
    text = path.read_text()
    for item in settings:
        key, value = item.split('=', 1)
        line = f'{key}: {value}'
        text = re.sub(rf'^{key}:.*$', line, text, flags=re.MULTILINE) if re.search(rf'^{key}:', text, re.MULTILINE) else text+'\n'+line+'\n'
    path.write_text(text)


def scale_calibration(config, scale):
    """Rewrite camera resolution and intrinsics for images resized by `scale`."""
    path = config/'imucam.yaml'
    chain = read_yaml(path)
    for cam in chain.values():
        fx, fy, cx, cy = cam['intrinsics']
        cam['intrinsics'] = [fx*scale, fy*scale, (cx+.5)*scale-.5, (cy+.5)*scale-.5]
        cam['resolution'] = [round(cam['resolution'][0]*scale), round(cam['resolution'][1]*scale)]
    write_yaml(path, chain)
    return chain['cam0']['resolution']


def read_tum(path):
    rows = [list(map(float, l.split())) for l in Path(path).read_text().splitlines() if l and not l.startswith('#')]
    return np.array(rows) if rows else np.zeros((0, 8))


def umeyama(src, dst):
    """Rigid (rotation+translation) alignment of src onto dst."""
    ms, md = src.mean(0), dst.mean(0)
    u, _, vt = np.linalg.svd((dst-md).T @ (src-ms))
    d = np.diag([1, 1, np.sign(np.linalg.det(u @ vt))])
    r = u @ d @ vt
    return r, md-r @ ms


def trajectory_error(estimate, reference, max_dt=.01):
    """ATE (rigid-aligned) and 1 s relative error of estimate vs reference, matched by timestamp."""
    if len(estimate) < 3 or len(reference) < 3:
        return None
    idx = np.searchsorted(reference[:, 0], estimate[:, 0])
    idx = np.clip(idx, 1, len(reference)-1)
    nearer = np.where(abs(reference[idx-1, 0]-estimate[:, 0]) < abs(reference[idx, 0]-estimate[:, 0]), idx-1, idx)
    ok = abs(reference[nearer, 0]-estimate[:, 0]) <= max_dt
    if ok.sum() < 3:
        return None
    est, ref = estimate[ok], reference[nearer[ok]]
    r, t = umeyama(est[:, 1:4], ref[:, 1:4])
    aligned = est[:, 1:4] @ r.T+t
    err = np.linalg.norm(aligned-ref[:, 1:4], axis=1)
    out = {'matched_poses': int(ok.sum()), 'ate_rmse_m': float(np.sqrt((err**2).mean())), 'ate_max_m': float(err.max()),
           'reference_path_m': float(np.linalg.norm(np.diff(ref[:, 1:4], axis=0), axis=1).sum())}
    # relative translation error over ~1 s segments (alignment independent)
    j = np.searchsorted(est[:, 0], est[:, 0]+1.)
    valid = j < len(est)
    if valid.sum() > 2:
        d_est = est[j[valid], 1:4]-est[valid, 1:4]
        d_ref = ref[j[valid], 1:4]-ref[valid, 1:4]
        out['rpe_1s_rmse_m'] = float(np.sqrt(((np.linalg.norm(d_est, axis=1)-np.linalg.norm(d_ref, axis=1))**2).mean()))
    return out


def read_kimera_gt(path):
    rows = [l.split(',') for l in Path(path).read_text().splitlines() if l and not l.startswith('#')]
    return np.array([[int(r[0])/1e9, *map(float, r[1:4]), *map(float, r[5:8]), float(r[4])] for r in rows])


def imu_to_body(poses, t_base_imu):
    from scipy.spatial.transform import Rotation
    out = poses.copy()
    t_imu_base = np.linalg.inv(np.array(t_base_imu))
    rot = Rotation.from_quat(poses[:, 4:8])
    out[:, 1:4] += rot.apply(t_imu_base[:3, 3])
    return out


def stats(values):
    v = np.asarray(values, float)
    if not len(v):
        return {}
    return {'mean': float(v.mean()), 'p50': float(np.percentile(v, 50)), 'p95': float(np.percentile(v, 95)),
            'p99': float(np.percentile(v, 99)), 'max': float(v.max())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('recording', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--config', type=Path, help='estimator/calibration config dir (default: RECORDING/config)')
    ap.add_argument('--profile', default='stationary_v2', choices=list(PROFILES))
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE', help='override an estimator.yaml setting')
    ap.add_argument('--scale', type=float, default=1., help='resize images (and intrinsics) by this factor')
    ap.add_argument('--stride', type=int, default=1, help='use every Nth stereo pair (30 Hz recording, stride 2 = 15 Hz)')
    ap.add_argument('--mode', choices=['all', 'realtime'], default='all',
                    help='all: process every pair; realtime: emulate the live loop and drop frames when compute falls behind')
    ap.add_argument('--keep', type=int, default=2, help='realtime: newest frames kept when behind (live app uses 2)')
    ap.add_argument('--compute-scale', type=float, default=1., help='realtime: multiply measured compute by this to emulate a slower host (Nano is ~6x this PC)')
    ap.add_argument('--overhead-ms', type=float, default=0., help='realtime: extra per-frame loop cost (UI snapshot) to emulate')
    ap.add_argument('--augment', default='', help='degrade the images: comma list of gain=,gamma=,contrast=,noise=,blur= (e.g. gamma=2,gain=.5,noise=6)')
    ap.add_argument('--prefilter', type=float, default=0., help='Gaussian blur sigma (px) applied to both images before the estimator')
    ap.add_argument('--max-seconds', type=float, default=0., help='only the first N seconds of the recording')
    ap.add_argument('--reference', type=Path, help='TUM trajectory to compute ATE/RPE against')
    ap.add_argument('--gt', type=Path, help='Kimera-format ground-truth CSV (#timestamp_kf,x,y,z,qw,qx,qy,qz)')
    ap.add_argument('--gt-frame', type=Path, help='evaluation_frame.json with T_base_imu, to express IMU poses in the GT body frame')
    args = ap.parse_args()
    if args.scale <= 0 or args.stride < 1:
        ap.error('scale must be > 0 and stride >= 1')

    source = args.recording.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(args.config.resolve() if args.config else source/'config', args.out/'config')
    prepare_estimator(args.out/'config', args.profile)
    resolution = None
    if args.scale != 1.:
        resolution = scale_calibration(args.out/'config', args.scale)
    apply_settings(args.out/'config', args.set)
    cv2.setNumThreads(1)
    vio = slam_native.Vio(str(args.out/'config/estimator.yaml'))
    rows, imus = replay_rows(source)
    rows = rows[::args.stride]
    if args.max_seconds:
        rows = [r for r in rows if r[0]-rows[0][0] <= args.max_seconds]

    aug = {k: float(v) for k, v in (x.split('=') for x in args.augment.split(',') if x)}
    rng = np.random.default_rng(int(aug.get('seed', 0)))

    def degrade(img):
        x = img.astype(np.float32)/255.
        if 'contrast' in aug:
            x = (x-x.mean())*aug['contrast']+x.mean()
        if 'gamma' in aug:
            x = np.clip(x, 0, 1)**aug['gamma']
        if 'gain' in aug:
            x = x*aug['gain']
        if 'blur' in aug:
            x = cv2.GaussianBlur(x, (0, 0), aug['blur'])
        if 'noise' in aug:
            x = x+rng.normal(0, aug['noise']/255., x.shape).astype(np.float32)
        return (np.clip(x, 0, 1)*255+.5).astype(np.uint8)

    def load(t, ln, rn):
        left, right = [cv2.imread(str(source/n), 0) for n in (ln, rn)]
        if left is None or right is None:
            raise ValueError(f'Cannot decode pair at {t}')
        if aug:
            left, right = degrade(left), degrade(right)
        if args.prefilter:   # candidate pre-processing in front of the estimator (not a degradation)
            left, right = (cv2.GaussianBlur(i, (0, 0), args.prefilter) for i in (left, right))
        if args.scale != 1.:
            size = (round(left.shape[1]*args.scale), round(left.shape[0]*args.scale))
            left, right = (cv2.resize(i, size, interpolation=cv2.INTER_AREA) for i in (left, right))
        return left, right

    idx = 0
    poses = []
    per_frame = []   # (timestamp, compute_ms, lag_ms or nan)
    state = {'last_pose': None, 'processed': 0, 'dropped': 0, 'skipped_before_imu': 0}
    read_ms = []

    def process(t, ln, rn):
        nonlocal idx
        target = t+vio.offset()
        if target < imus[0, 0] or target >= imus[-1, 0]:
            state['skipped_before_imu'] += 1
            return None
        while idx < len(imus) and imus[idx, 0] <= target:
            vio.imu(float(imus[idx, 0]), imus[idx, 1:].tolist()); idx += 1
        if idx < len(imus):
            vio.imu(float(imus[idx, 0]), imus[idx, 1:].tolist()); idx += 1
        read_started = time.perf_counter()
        left, right = load(t, ln, rn)
        read_ms.append((time.perf_counter()-read_started)*1000)
        started = time.perf_counter()
        snapshot = vio.camera(t, left, right)
        compute = (time.perf_counter()-started)*1000
        state['processed'] += 1
        if snapshot['initialized'] and snapshot['diagnostics']['state_advanced'] and snapshot['timestamp'] != state['last_pose']:
            poses.append([snapshot['timestamp'], *snapshot['position'], *snapshot['quaternion']])
            state['last_pose'] = snapshot['timestamp']
        return compute

    wall_start, cpu_start = time.perf_counter(), time.process_time()
    if args.mode == 'all':
        for n, (t, ln, rn) in enumerate(rows):
            compute = process(t, ln, rn)
            if compute is not None:
                per_frame.append((t, compute, float('nan')))
            if (n+1) % 300 == 0:
                print(f'{n+1}/{len(rows)} pairs', flush=True)
    else:
        clock = 0.   # virtual host time in seconds since the first frame was captured
        t0 = rows[0][0]
        pending = []
        i = 0
        while i < len(rows) or pending:
            while i < len(rows) and rows[i][0]-t0 <= clock:
                pending.append(rows[i]); i += 1
            if not pending:
                clock = rows[i][0]-t0
                continue
            while len(pending) > args.keep:   # same policy as the live loop
                pending.pop(0); state['dropped'] += 1
            t, ln, rn = pending.pop(0)
            compute = process(t, ln, rn)
            if compute is None:
                continue
            clock = max(clock, t-t0)+(compute*args.compute_scale+args.overhead_ms)/1000
            per_frame.append((t, compute, (clock-(t-t0))*1000))
    wall = time.perf_counter()-wall_start
    cpu = time.process_time()-cpu_start

    with (args.out/'trajectory.tum').open('w') as f:
        f.write('# timestamp tx ty tz qx qy qz qw; IMU to world; Hamilton xyzw\n')
        for p in poses:
            f.write(' '.join(f'{x:.9f}' for x in p)+'\n')
    with (args.out/'per_frame.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['timestamp', 'compute_ms', 'lag_ms'])
        w.writerows(per_frame)

    duration = rows[-1][0]-rows[0][0] if len(rows) > 1 else 0.
    compute = [c for _, c, _ in per_frame]
    summary = {
        'recording': str(source), 'out': str(args.out.resolve()),
        'host': {'machine': platform.machine(), 'node': platform.node(), 'cpus': __import__('os').cpu_count(), 'python': platform.python_version()},
        'variant': {'augment': args.augment, 'profile': args.profile, 'settings': args.set, 'scale': args.scale, 'stride': args.stride, 'mode': args.mode,
                    'resolution': resolution, 'keep': args.keep if args.mode == 'realtime' else None, 'overhead_ms': args.overhead_ms},
        'input': {'pairs': len(rows), 'duration_s': duration, 'input_hz': (len(rows)-1)/duration if duration else None},
        'processed': state['processed'], 'dropped_for_lag': state['dropped'], 'skipped_before_imu': state['skipped_before_imu'],
        'compute_ms': stats(compute), 'image_read_ms': stats(read_ms),
        'wall_s': wall, 'cpu_s': cpu, 'cpu_cores_avg': cpu/wall if wall else None,
        'throughput_hz': state['processed']/wall if wall else None,
        'realtime_factor': duration/wall if wall else None,   # >1: faster than the recording ran
        'peak_rss_mb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        'poses': len(poses),
        'path_length_m': float(np.linalg.norm(np.diff(np.array(poses)[:, 1:4], axis=0), axis=1).sum()) if len(poses) > 1 else 0.,
    }
    if args.mode == 'realtime':
        lags = [l for _, _, l in per_frame]
        summary['live_hz'] = state['processed']/duration if duration else None
        summary['lag_ms'] = stats(lags)
        summary['drop_pct'] = 100*state['dropped']/max(1, state['processed']+state['dropped'])
    if args.reference:
        summary['accuracy_vs_reference'] = trajectory_error(np.array(poses), read_tum(args.reference))
        summary['reference'] = str(args.reference)
    if args.gt:
        body = np.array(poses)
        if args.gt_frame:
            body = imu_to_body(body, json.loads(args.gt_frame.read_text())['T_base_imu'])
        summary['accuracy_vs_ground_truth'] = trajectory_error(body, read_kimera_gt(args.gt), max_dt=.06)
    (args.out/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in summary if k not in ('host', 'recording', 'out')}, indent=1))


if __name__ == '__main__':
    main()
