#!/usr/bin/env python3
"""Camera-IMU consistency check from the images themselves (no estimator involved).

For consecutive frames of one camera, the frame-to-frame rotation is estimated from KLT tracks
(essential matrix, RANSAC, recoverPose) and compared with the gyro integrated over the same
interval, rotated into the camera frame with the calibration. Reports: the extrinsic rotation
implied by the data against the calibration (Wahba), the camera-IMU time offset (grid search),
the per-axis rotation scale (regression) and, most importantly, the mean rotation-rate
difference vision minus gyro per axis in deg/s, i.e. a systematic visual rotation bias.

Usage: cam_imu_check.py SEQ_DIR --cam 0 [--start 3000 --count 2000] [--label x]
SEQ_DIR has runner_input/{stereo.csv,imu.csv,cam*/data} and pinhole_calibrations/*.json.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R


def kabsch(A, B):
    H = A.T @ B
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    return Vt.T @ np.diag([1, 1, d]) @ U.T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq", type=Path)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--start", type=int, default=3000)
    ap.add_argument("--count", type=int, default=2000)
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    ri = a.seq / "runner_input"
    calib = json.loads(next((a.seq / "pinhole_calibrations").glob("*.json")).read_text())
    cam = calib[f"cam{a.cam}"]
    fx, fy, cx, cy = cam["params"][:4]
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
    q = cam["T_b_s"]["qvec"]  # xyzw, b_from_s
    R_i_c = R.from_quat(q)
    rows = [l.split(",") for l in (ri / "stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    rows = rows[a.start:a.start + a.count + 1]
    imu = np.loadtxt(ri / "imu.csv", delimiter=",", comments="#")
    t_imu, w = imu[:, 0], imu[:, 1:4]
    cw = np.vstack([[0, 0, 0], np.cumsum((w[:-1] + w[1:]) * 0.5 * np.diff(t_imu)[:, None], axis=0)])

    def gyro_rotvec(t0, t1):
        i0, i1 = np.searchsorted(t_imu, t0), np.searchsorted(t_imu, t1)
        i0, i1 = np.clip([i0, i1], 1, len(t_imu) - 1)
        return cw[i1] - cw[i0]

    prev = None
    r_vis, times, n_in = [], [], []
    for tstr, c0, c1 in rows:
        path = ri / (c0 if a.cam == 0 else c1)
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        t = float(tstr)
        if prev is not None:
            p0 = cv2.goodFeaturesToTrack(prev[1], 600, 0.01, 8)
            if p0 is not None and len(p0) > 50:
                p1, st, _ = cv2.calcOpticalFlowPyrLK(prev[1], img, p0, None, winSize=(21, 21), maxLevel=3)
                p0b, stb, _ = cv2.calcOpticalFlowPyrLK(img, prev[1], p1, None, winSize=(21, 21), maxLevel=3)
                ok = (st[:, 0] == 1) & (stb[:, 0] == 1) & (np.linalg.norm(p0b - p0, axis=2)[:, 0] < 0.5)
                if ok.sum() > 30:
                    # rotation-only fit on bearings (consecutive frames: the baseline is a few cm, the
                    # essential matrix is degenerate; far features dominate the rotation anyway)
                    b0 = cv2.undistortPoints(p0[ok], K, None).reshape(-1, 2)
                    b1 = cv2.undistortPoints(p1[ok], K, None).reshape(-1, 2)
                    B0 = np.hstack([b0, np.ones((len(b0), 1))]); B0 /= np.linalg.norm(B0, axis=1)[:, None]
                    B1 = np.hstack([b1, np.ones((len(b1), 1))]); B1 /= np.linalg.norm(B1, axis=1)[:, None]
                    rng = np.random.default_rng(0)
                    best_in, best_R = None, None
                    for _ in range(60):
                        idx = rng.choice(len(B0), 3, replace=False)
                        Rc = kabsch(B0[idx], B1[idx])
                        ang = np.arccos(np.clip(np.sum((B0 @ Rc.T) * B1, axis=1), -1, 1))
                        inl = ang < 1.5 / fx  # 1.5 px
                        if best_in is None or inl.sum() > best_in.sum():
                            best_in, best_R = inl, Rc
                    if best_in is not None and best_in.sum() >= 15:
                        Rc = kabsch(B0[best_in], B1[best_in])  # bearings of frame k rotated into frame k+1: X1 = Rc X0
                        r_vis.append(R.from_matrix(Rc).as_rotvec())
                        times.append((prev[0], t))
                        n_in.append(int(best_in.sum()))
        prev = (t, img)
    r_vis = np.array(r_vis); times = np.array(times)
    # the camera rotation between frames: Rm is the point transform (frame k -> k+1), so the camera rotated by Rm^T
    r_cam = -r_vis
    out = {"label": a.label or f"cam{a.cam}", "pairs": len(r_cam), "inliers_median": float(np.median(n_in)),
           "calib_R_c_i_angle_deg": float(np.degrees(np.linalg.norm(R_i_c.inv().as_rotvec())))}
    # time offset: visual rotation (camera frame) against gyro integrated over the shifted interval
    best = None
    for dt_ms in np.arange(-30, 31, 1.0):
        d = dt_ms / 1000
        g = np.array([R_i_c.inv().apply(gyro_rotvec(t0 + d, t1 + d)) for t0, t1 in times])
        res = np.linalg.norm(r_cam - g, axis=1)
        med = np.median(res)
        if best is None or med < best[1]:
            best = (dt_ms, med, g)
    dt_ms, med, g = best
    out["time_offset_ms"] = float(dt_ms)
    out["median_residual_deg_per_frame"] = float(np.degrees(med))
    # extrinsic rotation implied by the data (Wahba between gyro rotvecs in the IMU frame and visual ones in the camera frame)
    gi = np.array([gyro_rotvec(t0 + dt_ms / 1000, t1 + dt_ms / 1000) for t0, t1 in times])
    big = np.linalg.norm(gi, axis=1) > np.radians(1.0)
    M = kabsch(gi[big], r_cam[big])  # c_from_i
    dev = (R.from_matrix(M) * R_i_c).as_rotvec()
    out["extrinsic_rotation_data_vs_calib_deg"] = [round(float(x), 3) for x in np.degrees(dev)]
    out["extrinsic_rotation_data_vs_calib_total_deg"] = round(float(np.degrees(np.linalg.norm(dev))), 3)
    # per-axis scale (camera frame) and mean difference, robust to outliers (inliers: residual below 3 x median)
    good = np.linalg.norm(r_cam - g, axis=1) < 3 * med
    dts = (times[:, 1] - times[:, 0])[good]
    diff = (r_cam[good] - g[good]) / dts[:, None]
    out["mean_rate_diff_vis_minus_gyro_deg_s_camframe"] = [round(float(x), 4) for x in np.degrees(diff.mean(0))]
    out["mean_rate_diff_std_err_deg_s"] = [round(float(x), 4) for x in np.degrees(diff.std(0) / np.sqrt(len(diff)))]
    # the same expressed about the IMU frame's axes (x is close to vertical when worn)
    diff_i = R_i_c.apply(diff)
    out["mean_rate_diff_vis_minus_gyro_deg_s_imuframe"] = [round(float(x), 4) for x in np.degrees(diff_i.mean(0))]
    sc = []
    for k in range(3):
        x, y = g[good][:, k], r_cam[good][:, k]
        sel = np.abs(x) > np.radians(0.5)
        sc.append(float(np.sum(x[sel] * y[sel]) / np.sum(x[sel] ** 2)) if sel.sum() > 20 else None)
    out["rotation_scale_vis_over_gyro_per_cam_axis"] = [None if v is None else round(v, 4) for v in sc]
    out["frames_used_fraction"] = round(float(good.mean()), 3)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
