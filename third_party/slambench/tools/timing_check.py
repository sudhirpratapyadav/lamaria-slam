"""Estimate the camera-to-IMU time offset of a recording by matching how fast the image rotates with how fast the gyro says it rotates.

  python -m slambench.tools.timing_check RECORDING [--config CONFIG_DIR] [--frames 600] [--json out.json]

Convention (same as OpenVINS timeshift_cam_imu and Kalibr): t_imu = t_cam + offset. A positive offset means the camera timestamps are
early (the image really was taken later than stamped). Use a recording with plenty of rotation; a smooth peak well above the noise and an
offset stable across segments mean timing is trustworthy. A flat or jumpy curve means timing is NOT trustworthy: fix it in hardware.
HOW TO RECORD: hold the camera and shake or rotate it briskly by hand (about 2-4 Hz, a few degrees to tens of degrees) for 30-60 s in a
textured scene. Slow smooth sweeps cannot reveal a timing error (a 25 ms shift barely changes them).
This is a sanity check, not a calibration: OpenVINS and Kalibr refine the offset, but an offset of tens of ms or an unstable one cannot be refined away.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def read_camera(config_dir):
    sys.path.insert(0, str(ROOT / 'scripts'))
    from prepare_kimera import read_yaml
    cam = read_yaml(Path(config_dir) / 'imucam.yaml')['cam0']
    fx, fy, cx, cy = cam['intrinsics']
    return {'K': np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.]]), 'dist': np.array(cam['distortion_coeffs'], float),
            'model': 'equidistant' if cam.get('distortion_model') == 'equidistant' else 'radtan'}


def rotation_from_bearings(n0, n1, iterations=4, keep=0.7):
    """Rotation R with n1 ~ R n0 for unit bearing vectors (Kabsch), refitted on the best fraction of points so tracking outliers and
    translation parallax do not dominate. Unlike the essential matrix this stays well-posed when the motion is mostly rotation."""
    r = np.eye(3)
    use = np.ones(len(n0), bool)
    for _ in range(iterations):
        u, _, vt = np.linalg.svd(n1[use].T @ n0[use])
        d = np.diag([1, 1, np.sign(np.linalg.det(u @ vt))])
        r = u @ d @ vt
        angle_error = np.arccos(np.clip(np.sum(n1 * (n0 @ r.T), axis=1), -1, 1))
        use = angle_error <= np.quantile(angle_error, keep)
    return r


def visual_rotation_speeds(images, times, camera, max_corners=400):
    """Angular speed magnitude (rad/s) between consecutive frames from tracked features. NaN where tracking fails."""
    speeds = np.full(len(images) - 1, np.nan)
    K, dist = camera['K'], camera['dist']
    for i in range(len(images) - 1):
        a, b = images[i], images[i + 1]
        p0 = cv2.goodFeaturesToTrack(a, max_corners, 0.01, 8)
        if p0 is None or len(p0) < 30:
            continue
        p1, status, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(21, 21), maxLevel=3)
        good = status.ravel() == 1
        if good.sum() < 30:
            continue
        q0, q1 = p0[good].reshape(-1, 1, 2), p1[good].reshape(-1, 1, 2)
        if camera['model'] == 'equidistant':
            n0, n1 = (cv2.fisheye.undistortPoints(q, K, dist[:4]).reshape(-1, 2) for q in (q0, q1))
        else:
            n0, n1 = (cv2.undistortPoints(q, K, dist).reshape(-1, 2) for q in (q0, q1))
        v0 = np.column_stack([n0, np.ones(len(n0))])
        v1 = np.column_stack([n1, np.ones(len(n1))])
        v0 /= np.linalg.norm(v0, axis=1, keepdims=True)
        v1 /= np.linalg.norm(v1, axis=1, keepdims=True)
        r = rotation_from_bearings(v0, v1)
        speeds[i] = np.linalg.norm(cv2.Rodrigues(r)[0]) / (times[i + 1] - times[i])
    return speeds


def gyro_interval_means(imu_t, gyro_mag, starts, ends):
    """Mean |gyro| over [start, end] for each interval, from a cumulative integral."""
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (gyro_mag[1:] + gyro_mag[:-1]) * np.diff(imu_t))])
    def integral(x):
        return np.interp(x, imu_t, cum)
    return (integral(ends) - integral(starts)) / (ends - starts)


def estimate_offset(frame_times, visual_speed, imu_t, gyro_mag, search_s=0.06, step_s=0.0005, min_speed=0.05):
    """Offset maximising the correlation between visual and gyro angular speed; returns offset, peak correlation, and the curve."""
    starts, ends = frame_times[:-1], frame_times[1:]
    ok = np.isfinite(visual_speed) & (visual_speed > min_speed)
    if ok.sum() < 30:
        return None
    offsets = np.arange(-search_s, search_s + step_s / 2, step_s)
    corr = []
    for tau in offsets:
        gyro = gyro_interval_means(imu_t, gyro_mag, starts[ok] + tau, ends[ok] + tau)
        corr.append(np.corrcoef(visual_speed[ok], gyro)[0, 1])
    corr = np.array(corr)
    k = int(np.nanargmax(corr))
    best = offsets[k]
    if 0 < k < len(offsets) - 1:        # parabolic refinement
        a, b, c = corr[k - 1], corr[k], corr[k + 1]
        denom = a - 2 * b + c
        if denom < 0:
            best = offsets[k] + 0.5 * (a - c) / denom * step_s
    return {'offset_s': float(best), 'peak_correlation': float(corr[k]), 'correlation_at_zero_offset': float(corr[np.argmin(np.abs(offsets))]),
            'samples': int(ok.sum()), 'offsets_s': offsets, 'correlation': corr}


def check_recording(recording, config, frames=600, start_frame=0, segments=3):
    recording = Path(recording)
    camera = read_camera(config)
    rows = [l.split(',') for l in (recording / 'stereo.csv').read_text().splitlines() if l and not l.startswith('#')]
    rows = rows[start_frame:start_frame + frames]
    times = np.array([float(r[0]) for r in rows])
    images = [cv2.imread(str(recording / r[1]), cv2.IMREAD_GRAYSCALE) for r in rows]
    imu = np.loadtxt(recording / 'imu.csv', delimiter=',', comments='#', ndmin=2)
    imu_t, gyro_mag = imu[:, 0], np.linalg.norm(imu[:, 1:4], axis=1)
    speeds = visual_rotation_speeds(images, times, camera)
    whole = estimate_offset(times, speeds, imu_t, gyro_mag)
    if whole is None:
        return {'error': 'not enough rotation in this recording to estimate an offset (rotate the camera)'}
    per_segment = []
    n = len(times) - 1
    for k in range(segments):
        lo, hi = k * n // segments, (k + 1) * n // segments + 1
        est = estimate_offset(times[lo:hi + 1], speeds[lo:hi], imu_t, gyro_mag)
        if est:
            per_segment.append(est['offset_s'])
    return {'offset_s': whole['offset_s'], 'offset_ms': whole['offset_s'] * 1000, 'peak_correlation': whole['peak_correlation'],
            'correlation_at_zero_offset': whole['correlation_at_zero_offset'], 'samples': whole['samples'],
            'segment_offsets_ms': [x * 1000 for x in per_segment],
            'segment_spread_ms': float((max(per_segment) - min(per_segment)) * 1000) if len(per_segment) > 1 else None,
            'frames': len(times)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('recording', type=Path)
    ap.add_argument('--config', type=Path, help='folder with imucam.yaml (default: RECORDING/config)')
    ap.add_argument('--frames', type=int, default=600)
    ap.add_argument('--start-frame', type=int, default=0)
    ap.add_argument('--json')
    args = ap.parse_args(argv)
    result = check_recording(args.recording, args.config or args.recording / 'config', args.frames, args.start_frame)
    print(json.dumps(result, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2))
    return 0 if 'error' not in result else 1


if __name__ == '__main__':
    sys.exit(main())
