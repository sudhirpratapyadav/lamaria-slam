#!/usr/bin/env python3
"""Fit an equidistant (Kannala-Brandt, OpenVINS "equidistant") model to the Aria
FISHEYE624 calibration of both SLAM cameras and write a calibration JSON in the
same layout as the LaMAria pinhole JSON, so scripts/make_openvins_config.py can
consume it (model "EQUIDISTANT", params [fx, fy, cx, cy, k1, k2, k3, k4]).

Fit: sample valid pixels, unproject with the Aria model to a ray, compute the
angle theta to the optical axis and the pixel radius r about the Aria principal
point; least squares on r = f * (theta + k1 theta^3 + k2 theta^5 + k3 theta^7 + k4 theta^9).
Reports the reprojection residual, which tells how well OpenVINS's model can
represent the Aria lens.

Usage: fit_fisheye_kb.py SEQ_DIR_WITH_RAW_DATA ARIA_CALIB_JSON OUT_JSON
"""
import argparse
import json
from pathlib import Path

import numpy as np
from projectaria_tools.core import data_provider

LABELS = {"cam0": "camera-slam-left", "cam1": "camera-slam-right"}


def fit_kb(calib, step=8):
    w, h = calib.get_image_size()
    cx, cy = calib.get_principal_point()
    th, rr, pts = [], [], []
    for y in range(0, h, step):
        for x in range(0, w, step):
            ray = calib.unproject(np.array([x, y], dtype=float))
            if ray is None:
                continue
            ray = ray / np.linalg.norm(ray)
            theta = np.arccos(np.clip(ray[2], -1, 1))
            th.append(theta); rr.append(np.hypot(x - cx, y - cy)); pts.append((x, y, ray))
    th, rr = np.array(th), np.array(rr)
    A = np.stack([th, th**3, th**5, th**7, th**9], axis=1)
    coef, *_ = np.linalg.lstsq(A, rr, rcond=None)
    f = coef[0]; k = coef[1:] / f
    # nonlinear refinement with a free principal point (the Aria model has tangential and
    # thin-prism terms that a radially symmetric model can only absorb this way)
    from scipy.optimize import least_squares
    P = np.array([[x, y] for (x, y, _) in pts], dtype=float)
    rays = np.array([r for (_, _, r) in pts])
    def project(params):
        f_, k1, k2, k3, k4, cx_, cy_ = params
        theta = np.arccos(np.clip(rays[:, 2], -1, 1)); phi = np.arctan2(rays[:, 1], rays[:, 0])
        rd = f_ * (theta + k1 * theta**3 + k2 * theta**5 + k3 * theta**7 + k4 * theta**9)
        return np.stack([cx_ + rd * np.cos(phi), cy_ + rd * np.sin(phi)], axis=1)
    sol = least_squares(lambda q: (project(q) - P).ravel(), x0=[f, *k, cx, cy])
    f, k1, k2, k3, k4, cx, cy = sol.x; k = np.array([k1, k2, k3, k4])
    errs = np.linalg.norm(project(sol.x) - P, axis=1)
    return f, k, cx, cy, (w, h), np.degrees(th.max()), errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("aria_calib_json", type=Path)
    ap.add_argument("out_json", type=Path)
    args = ap.parse_args()
    vrs = next(iter(args.seq_dir.glob("raw_data/*.vrs")))
    dc = data_provider.create_vrs_data_provider(str(vrs)).get_device_calibration()
    aria = json.loads(args.aria_calib_json.read_text())
    out = {"imu0": aria["imu0"]}
    for cam, label in LABELS.items():
        f, k, cx, cy, (w, h), fov, errs = fit_kb(dc.get_camera_calib(label))
        print(f"{cam} ({label}): f {f:.3f} k {np.round(k, 5).tolist()} pp ({cx:.3f}, {cy:.3f}) size {w}x{h} max theta {fov:.1f} deg | "
              f"reproj err mean {errs.mean():.3f} px, 95th {np.percentile(errs, 95):.3f}, max {errs.max():.3f}")
        out[cam] = {"model": "EQUIDISTANT", "params": [f, f, cx, cy, *k.tolist()], "resolution": {"width": int(w), "height": int(h)},
                    "T_b_s": aria[cam]["T_b_s"], "fit_reproj_err_px": {"mean": float(errs.mean()), "p95": float(np.percentile(errs, 95)), "max": float(errs.max())}}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2) + "\n")
    print("wrote", args.out_json)


if __name__ == "__main__":
    main()
