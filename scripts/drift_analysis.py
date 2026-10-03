#!/usr/bin/env python3
"""Decompose a trajectory's error against the pseudo-GT into scale, heading drift and local
consistency, window by window, to see what kind of drift dominates on long walks.

For each window of --window seconds the estimate is sim3-aligned (Umeyama) to the pGT on its own:
the window's scale, the heading (yaw about the pGT's gravity axis) of its alignment, and the
residual RMSE. Heading drift is the change of that yaw between consecutive windows, per minute.

Usage: drift_analysis.py EST.txt PGT.txt [--window 60] [--label name]
Both files: "ts_ns tx ty tz qx qy qz qw" (submission / pGT format). Prints one JSON line.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R


def load(path):
    a = np.loadtxt(path, comments="#")
    return a[np.argsort(a[:, 0])]


def umeyama(src, dst):
    """sim3 (s, R, t) with dst ~ s R src + t."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    cov = xd.T @ xs / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    Rm = U @ S @ Vt
    var_s = (xs ** 2).sum() / len(src)
    s = np.trace(np.diag(D) @ S) / var_s
    t = mu_d - s * Rm @ mu_s
    return s, Rm, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("est", type=Path)
    ap.add_argument("pgt", type=Path)
    ap.add_argument("--window", type=float, default=60.0)
    ap.add_argument("--label", default="")
    ap.add_argument("--dump", type=Path, help="write per-window rows (t_mid_s, scale, yaw_deg, rmse_m, path_m) as csv")
    args = ap.parse_args()
    est, gt = load(args.est), load(args.pgt)
    # associate pGT stamps to the nearest estimate within 1 ms
    i = np.clip(np.searchsorted(est[:, 0], gt[:, 0]), 1, len(est) - 1)
    i = np.where(np.abs(est[i - 1, 0] - gt[:, 0]) < np.abs(est[i, 0] - gt[:, 0]), i - 1, i)
    ok = np.abs(est[i, 0] - gt[:, 0]) <= 1e6
    gt, e = gt[ok], est[i[ok]]
    t = (gt[:, 0] - gt[0, 0]) / 1e9
    pg, pe = gt[:, 1:4], e[:, 1:4]
    s_g, R_g, t_g = umeyama(pe, pg)
    ate = float(np.sqrt((((s_g * (R_g @ pe.T).T + t_g) - pg) ** 2).sum(1).mean()))
    path_len = float(np.linalg.norm(np.diff(pg, axis=0), axis=1).sum())
    # windows
    rows = []
    for w0 in np.arange(0, t[-1], args.window):
        m = (t >= w0) & (t < w0 + args.window)
        if m.sum() < 10:
            continue
        seg_len = np.linalg.norm(np.diff(pg[m], axis=0), axis=1).sum()
        if seg_len < 3.0:
            continue
        s, Rm, tt = umeyama(pe[m], pg[m])
        res = float(np.sqrt((((s * (Rm @ pe[m].T).T + tt) - pg[m]) ** 2).sum(1).mean()))
        yaw = R.from_matrix(Rm).as_euler("zyx")[0]
        rows.append((float(w0 + args.window / 2), float(s), float(yaw), res, float(seg_len)))
    rows = np.array(rows)
    if args.dump and len(rows):
        np.savetxt(args.dump, np.c_[rows[:, 0], rows[:, 1], np.degrees(np.unwrap(rows[:, 2])), rows[:, 3], rows[:, 4]], fmt="%.4f", delimiter=",", header="t_mid_s,scale,yaw_deg,rmse_m,path_m", comments="")
    out = {"label": args.label or args.est.stem, "pairs": int(len(gt)), "duration_s": round(float(t[-1]), 1),
           "path_m": round(path_len, 1), "ate_sim3": round(ate, 3), "global_scale": round(float(s_g), 4), "windows": int(len(rows))}
    if len(rows) >= 2:
        yaw = np.unwrap(rows[:, 2])
        dyaw = np.degrees(np.diff(yaw)) / (np.diff(rows[:, 0]) / 60.0)
        out.update({"scale_median": round(float(np.median(rows[:, 1])), 4), "scale_min": round(float(rows[:, 1].min()), 4),
                    "scale_max": round(float(rows[:, 1].max()), 4), "scale_std": round(float(rows[:, 1].std()), 4),
                    "yaw_rate_deg_per_min_median_abs": round(float(np.median(np.abs(dyaw))), 3),
                    "yaw_rate_deg_per_min_max_abs": round(float(np.abs(dyaw).max()), 3),
                    "yaw_total_deg": round(float(np.degrees(yaw[-1] - yaw[0])), 2),
                    "window_rmse_median": round(float(np.median(rows[:, 3])), 3), "window_rmse_max": round(float(rows[:, 3].max()), 3)})
        # where does the heading drift happen: top 3 windows by |dyaw|
        top = np.argsort(-np.abs(dyaw))[:3]
        out["worst_yaw_windows_s"] = [(round(float(rows[k + 1, 0]), 0), round(float(dyaw[k]), 2)) for k in top]
    print(json.dumps(out))


if __name__ == "__main__":
    main()
