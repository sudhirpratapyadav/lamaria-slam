#!/usr/bin/env python3
"""How much heading would the gyro alone lose, against what the estimator lost?

Fits a constant gyro bias against the pseudo-GT (linear least squares on the rotation-vector
difference per pGT interval), integrates the bias-corrected gyro over the whole sequence, and
reports the heading (rotation about the pGT's z axis) error of the gyro-only orientation and of
the estimate, both referenced to the pGT at the start. Prints one JSON line; optional CSV of
error versus time. Inputs: imu.csv (t_s gx gy gz ax ay az, IMU frame), pGT and estimate in
submission format (ts_ns tx ty tz qx qy qz qw, IMU frame).

Usage: gyro_yaw_check.py IMU_CSV PGT.txt [EST.txt] [--csv out.csv] [--label name]
"""
import argparse
import json

import numpy as np
from scipy.spatial.transform import Rotation as R


def load_poses(path):
    a = np.loadtxt(path, comments="#")
    a = a[np.argsort(a[:, 0])]
    return a[:, 0] / 1e9, R.from_quat(a[:, 4:8])


def integrate(t, w):
    """Cumulative rotation R_0_k from body rates w (N x 3) at times t."""
    dt = np.diff(t)
    dv = (w[:-1] + w[1:]) * 0.5 * dt[:, None]
    out = [R.identity()]
    rots = R.from_rotvec(dv)
    cur = out[0]
    # chunked product keeps it reasonably fast for ~2M samples
    quats = np.empty((len(t), 4))
    q = np.array([0.0, 0.0, 0.0, 1.0])
    quats[0] = q
    rq = rots.as_quat()
    for k in range(len(rq)):
        x1, y1, z1, w1 = q
        x2, y2, z2, w2 = rq[k]
        q = np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                      w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                      w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
                      w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])
        q /= np.linalg.norm(q)
        quats[k + 1] = q
    return R.from_quat(quats)


def kabsch(A, B):
    """Rotation matrix M with B ~= A @ M.T (rows are vectors)."""
    H = A.T @ B
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    return Vt.T @ np.diag([1, 1, d]) @ U.T


def body_from_imu(t, w, tp, Rp):
    """Fixed rotation X_from_imu between the pGT body frame X and the gyro frame, solved from the
    angular rates over the whole sequence (Wahba); 0 deg means the pGT is already in the IMU frame."""
    dp = (Rp[:-1].inv() * Rp[1:]).as_rotvec()
    dt = np.diff(tp)
    good = dt < 1.0
    wX = dp[good] / dt[good, None]
    cw = np.vstack([[0, 0, 0], np.cumsum((w[:-1] + w[1:]) * 0.5 * np.diff(t)[:, None], axis=0)])
    i0 = np.clip(np.searchsorted(t, tp[:-1][good]), 0, len(t) - 1)
    i1 = np.clip(np.searchsorted(t, tp[1:][good]), 0, len(t) - 1)
    wI = (cw[i1] - cw[i0]) / dt[good, None]
    sel = np.linalg.norm(wX, axis=1) > 0.3
    return R.from_matrix(kabsch(wI[sel], wX[sel]))


def yaw_error(R_ref, R_est):
    """Heading error about the reference world z, degrees, with sign (unwrapped)."""
    err = (R_ref.inv() * R_est)  # body-frame error
    # express the error rotation vector in the world frame and take its z component
    v = R_ref.apply(err.as_rotvec())
    return np.degrees(v[:, 2]), np.degrees(np.linalg.norm(err.as_rotvec(), axis=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imu"); ap.add_argument("pgt"); ap.add_argument("est", nargs="?")
    ap.add_argument("--csv"); ap.add_argument("--label", default="")
    a = ap.parse_args()
    imu = np.loadtxt(a.imu, delimiter=",", comments="#")
    t, w = imu[:, 0], imu[:, 1:4]
    tp, Rp = load_poses(a.pgt)
    lo, hi = max(t[0], tp[0]), min(t[-1], tp[-1])
    m = (t >= lo) & (t <= hi); t, w = t[m], w[m]
    pm = (tp >= lo) & (tp <= hi); tp, Rp = tp[pm], Rp[pm]
    C = body_from_imu(t, w, tp, Rp)  # X_from_imu
    Rp = Rp * C  # pGT orientation re-expressed as world_from_imu
    # bias: per pGT interval, sum(w dt) - rotvec(R_i^T R_{i+1}) ~= b * dt
    cw = np.concatenate([[0, 0, 0], np.cumsum((w[:-1] + w[1:]) * 0.5 * np.diff(t)[:, None], axis=0).ravel()]).reshape(-1, 3)
    idx = np.searchsorted(t, tp)
    idx = np.clip(idx, 0, len(t) - 1)
    dg = cw[idx[1:]] - cw[idx[:-1]]
    dp = (Rp[:-1].inv() * Rp[1:]).as_rotvec()
    dti = (tp[1:] - tp[:-1])[:, None]
    ok = (dti[:, 0] < 2.0)
    b = ((dg - dp)[ok] * dti[ok]).sum(0) / (dti[ok] ** 2).sum()
    Rg = integrate(t, w - b)
    # reference the gyro orientation to the pGT at the start
    Rg = Rp[0] * Rg
    gi = np.clip(np.searchsorted(t, tp), 0, len(t) - 1)
    yaw_g, ang_g = yaw_error(Rp, Rg[gi])
    out = {"label": a.label, "duration_s": float(hi - lo), "pgt_body_from_imu_deg": round(float(np.degrees(np.linalg.norm(C.as_rotvec()))), 1), "gyro_bias_deg_s": list(np.degrees(b).round(5)),
           "gyro_only_yaw_err_end_deg": float(yaw_g[-1]), "gyro_only_yaw_err_max_deg": float(np.abs(yaw_g).max()),
           "gyro_only_angle_err_end_deg": float(ang_g[-1]), "pgt_total_turning_deg": float(np.degrees(np.abs(dp[:, 2]).sum()))}
    cols = {"t": tp - lo, "yaw_err_gyro": yaw_g}
    if a.est:
        te, Re = load_poses(a.est)
        ei = np.clip(np.searchsorted(te, tp), 0, len(te) - 1)
        close = np.abs(te[ei] - tp) < 0.1
        Re_s = Re[ei]
        # reference the estimate to the pGT at the first matched pose
        k0 = int(np.argmax(close))
        Re_s = (Rp[k0] * Re_s[k0].inv()) * Re_s
        yaw_e, ang_e = yaw_error(Rp, Re_s)
        yaw_e[~close] = np.nan
        out.update({"est_yaw_err_end_deg": float(yaw_e[close][-1]), "est_yaw_err_max_deg": float(np.nanmax(np.abs(yaw_e))),
                    "est_yaw_err_rms_deg": float(np.sqrt(np.nanmean(yaw_e ** 2))),
                    "gyro_only_yaw_err_rms_deg": float(np.sqrt(np.mean(yaw_g ** 2)))})
        # the five largest one-minute heading changes of the estimate's error
        tt = tp - lo; mins = (tt // 60).astype(int)
        per = [np.nanmean(yaw_e[mins == k]) for k in range(mins.max() + 1)]
        d = np.diff(per)
        worst = sorted(range(len(d)), key=lambda k: -abs(d[k]) if not np.isnan(d[k]) else 0)[:5]
        out["est_worst_minutes_s_deg"] = [[int(60 * k), round(float(d[k]), 1)] for k in worst]
        cols["yaw_err_est"] = yaw_e
    print(json.dumps(out))
    if a.csv:
        np.savetxt(a.csv, np.column_stack(list(cols.values())), delimiter=",", header=",".join(cols.keys()), comments="")


if __name__ == "__main__":
    main()
