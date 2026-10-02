"""Trajectory metrics for comparing SLAM/VIO systems: ATE, drift per distance, relative error, loop gap, jumps.

All trajectories are TUM arrays of shape (N, 8): t, x, y, z, qx, qy, qz, qw (Hamilton, xyzw), world <- body.
Pure numpy/scipy so the same metrics run on a PC, the A100 server or a target board.
"""
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


def read_tum(path):
    rows = [list(map(float, line.split())) for line in Path(path).read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]
    traj = np.array(rows, dtype=float).reshape(-1, 8) if rows else np.zeros((0, 8))
    if len(traj) and np.any(np.diff(traj[:, 0]) < 0):
        traj = traj[np.argsort(traj[:, 0], kind='stable')]
    return traj


def write_tum(path, traj, header='timestamp tx ty tz qx qy qz qw; world <- body; Hamilton xyzw'):
    with Path(path).open('w') as f:
        f.write('# ' + header + '\n')
        for row in traj:
            f.write(' '.join(f'{x:.9f}' for x in row) + '\n')


def path_length(positions):
    return float(np.linalg.norm(np.diff(positions, axis=0), axis=1).sum()) if len(positions) > 1 else 0.


def cumulative_length(positions):
    return np.concatenate([[0.], np.cumsum(np.linalg.norm(np.diff(positions, axis=0), axis=1))]) if len(positions) else np.zeros(0)


def associate(est, ref, max_dt=0.05):
    """Nearest-in-time pairing of estimate poses to reference poses; returns index arrays (est_idx, ref_idx)."""
    if len(est) == 0 or len(ref) == 0:
        return np.zeros(0, int), np.zeros(0, int)
    j = np.clip(np.searchsorted(ref[:, 0], est[:, 0]), 1, len(ref) - 1)
    nearer = np.where(np.abs(ref[j - 1, 0] - est[:, 0]) <= np.abs(ref[j, 0] - est[:, 0]), j - 1, j)
    ok = np.abs(ref[nearer, 0] - est[:, 0]) <= max_dt
    return np.nonzero(ok)[0], nearer[ok]


def align_se3(src, dst):
    """Rigid alignment (rotation + translation, no scale): dst ~ R src + t."""
    ms, md = src.mean(0), dst.mean(0)
    u, _, vt = np.linalg.svd((dst - md).T @ (src - ms))
    d = np.diag([1, 1, np.sign(np.linalg.det(u @ vt))])
    r = u @ d @ vt
    return r, md - r @ ms


def align_sim3(src, dst):
    ms, md = src.mean(0), dst.mean(0)
    xs, xd = src - ms, dst - md
    u, sig, vt = np.linalg.svd(xd.T @ xs)
    d = np.diag([1, 1, np.sign(np.linalg.det(u @ vt))])
    r = u @ d @ vt
    scale = float((sig * np.diag(d)).sum() / (xs ** 2).sum())
    return scale, r, md - scale * r @ ms


def align_yaw(src, dst):
    """4-DoF alignment (rotation about the vertical axis + translation): the right freedom for gravity-aligned VIO."""
    ms, md = src.mean(0), dst.mean(0)
    a, b = src[:, :2] - ms[:2], dst[:, :2] - md[:2]
    theta = np.arctan2((a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum(), (a * b).sum())
    c, s = np.cos(theta), np.sin(theta)
    r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return r, md - r @ ms


def ate(est, ref, mode='yaw', max_dt=0.05):
    """Absolute trajectory error of positions after alignment. mode: 'yaw' (4-DoF), 'se3', 'sim3' (monocular)."""
    ei, ri = associate(est, ref, max_dt)
    if len(ei) < 3:
        return None
    p, q = est[ei, 1:4], ref[ri, 1:4]
    if mode == 'yaw':
        r, t = align_yaw(p, q)
        aligned = p @ r.T + t
    elif mode == 'se3':
        r, t = align_se3(p, q)
        aligned = p @ r.T + t
    elif mode == 'sim3':
        scale, r, t = align_sim3(p, q)
        aligned = scale * (p @ r.T) + t
    else:
        raise ValueError(mode)
    err = np.linalg.norm(aligned - q, axis=1)
    return {'mode': mode, 'scale': float(scale) if mode == 'sim3' else None, 'rmse_m': float(np.sqrt((err ** 2).mean())), 'mean_m': float(err.mean()), 'median_m': float(np.median(err)),
            'max_m': float(err.max()), 'matched': int(len(ei)), 'ref_path_m': path_length(ref[:, 1:4])}


def _poses(traj):
    rot = Rotation.from_quat(traj[:, 4:8]).as_matrix()
    return rot, traj[:, 1:4]


def drift_per_distance(est, ref, deltas=(10., 50., 100., 200.), max_dt=0.05, step_m=None):
    """KITTI-style drift: for start points along the reference path, the relative pose error over a path segment of
    length delta, as translation error in percent of delta and rotation error in deg per 100 m. Insensitive to alignment."""
    ei, ri = associate(est, ref, max_dt)
    if len(ei) < 10:
        return {}
    e, r = est[ei], ref[ri]
    re, pe = _poses(e)
    rr, pr = _poses(r)
    s = cumulative_length(pr)
    out = {}
    for delta in deltas:
        if s[-1] < delta * 1.2:
            continue
        step = step_m or max(delta / 10., 1.)
        starts = np.arange(0., s[-1] - delta, step)
        i = np.searchsorted(s, starts)
        j = np.searchsorted(s, starts + delta)
        keep = j < len(s)
        i, j = i[keep], j[keep]
        trans, rots = [], []
        for a, b in zip(i, j):
            rel_ref = rr[a].T @ rr[b], rr[a].T @ (pr[b] - pr[a])
            rel_est = re[a].T @ re[b], re[a].T @ (pe[b] - pe[a])
            err_t = rel_est[1] - rel_ref[1]
            err_r = Rotation.from_matrix(rel_ref[0].T @ rel_est[0]).magnitude()
            trans.append(np.linalg.norm(err_t) / delta * 100.)
            rots.append(np.degrees(err_r) / delta * 100.)
        if trans:
            out[f'{int(delta)}m'] = {'trans_pct': float(np.mean(trans)), 'trans_pct_p95': float(np.percentile(trans, 95)),
                                     'rot_deg_per_100m': float(np.mean(rots)), 'segments': len(trans)}
    return out


def rpe_time(est, ref, dt=1.0, max_dt=0.05):
    """Relative translation error over a fixed time interval (local accuracy), RMSE in metres."""
    ei, ri = associate(est, ref, max_dt)
    if len(ei) < 10:
        return None
    e, r = est[ei], ref[ri]
    re, pe = _poses(e)
    rr, pr = _poses(r)
    j = np.searchsorted(r[:, 0], r[:, 0] + dt)
    ok = j < len(r)
    idx = np.nonzero(ok)[0]
    if len(idx) < 5:
        return None
    errs = []
    for a, b in zip(idx, j[ok]):
        d_ref = rr[a].T @ (pr[b] - pr[a])
        d_est = re[a].T @ (pe[b] - pe[a])
        errs.append(np.linalg.norm(d_est - d_ref))
    errs = np.array(errs)
    return {'dt_s': dt, 'rmse_m': float(np.sqrt((errs ** 2).mean())), 'median_m': float(np.median(errs))}


def loop_gap(est, ref=None, closed_threshold_m=3.0):
    """For a trajectory that ends where it started, how far apart do the estimated start and end land?"""
    p = est[:, 1:4]
    length = path_length(p)
    result = {'est_gap_m': float(np.linalg.norm(p[0] - p[-1])), 'est_path_m': length,
              'est_gap_pct_of_path': float(100. * np.linalg.norm(p[0] - p[-1]) / length) if length else None}
    if ref is not None and len(ref):
        q = ref[:, 1:4]
        result['ref_gap_m'] = float(np.linalg.norm(q[0] - q[-1]))
        result['closed_loop'] = bool(result['ref_gap_m'] <= closed_threshold_m)
    return result


def jumps(est, max_jump_m=2.0, max_gap_s=0.5):
    """Count tracking failures: pose steps larger than max_jump_m between samples closer than max_gap_s."""
    if len(est) < 2:
        return 0
    step = np.linalg.norm(np.diff(est[:, 1:4], axis=0), axis=1)
    dt = np.diff(est[:, 0])
    return int(np.sum((step > max_jump_m) & (dt < max_gap_s)))


def evaluate(est, ref, body_from_imu=None, max_dt=0.05):
    """Full metric set. body_from_imu (4x4) re-expresses the estimator's IMU poses in the reference body frame."""
    if body_from_imu is not None:
        est = imu_to_body(est, body_from_imu)
    result = {'poses': int(len(est))}
    if len(est) == 0:
        return result
    if ref is None:        # no reference: only self-contained measures (start-end gap on loops, tracking jumps, length)
        result['loop'] = loop_gap(est)
        result['jumps'] = jumps(est)
        result['est_path_m'] = path_length(est[:, 1:4])
        return result
    result['ate_yaw'] = ate(est, ref, 'yaw', max_dt)
    result['ate_se3'] = ate(est, ref, 'se3', max_dt)
    result['ate_sim3'] = ate(est, ref, 'sim3', max_dt)      # its 'scale' is the factor that makes the estimate match the reference's metric size
    result['drift'] = drift_per_distance(est, ref, max_dt=max_dt)
    result['rpe_1s'] = rpe_time(est, ref, 1.0, max_dt)
    covered_ref = ref[(ref[:, 0] >= est[0, 0] - max_dt) & (ref[:, 0] <= est[-1, 0] + max_dt)]       # the part of the reference the run covers
    result['loop'] = loop_gap(est, covered_ref if len(covered_ref) > 1 else ref)
    result['jumps'] = jumps(est)
    covered = (est[-1, 0] - est[0, 0]) / max(ref[-1, 0] - ref[0, 0], 1e-9)
    result['coverage_fraction'] = float(min(covered, 1.0))
    return result


def imu_to_body(poses, t_base_imu):
    """T_world_base = T_world_imu @ inverse(T_base_imu), keeping positions of the body frame origin."""
    t_imu_base = np.linalg.inv(np.asarray(t_base_imu, float))
    rot = Rotation.from_quat(poses[:, 4:8])
    out = poses.copy()
    out[:, 1:4] += rot.apply(t_imu_base[:3, 3])
    out[:, 4:8] = (rot * Rotation.from_matrix(t_imu_base[:3, :3])).as_quat()
    return out
