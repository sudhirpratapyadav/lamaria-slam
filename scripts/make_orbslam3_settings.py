#!/usr/bin/env python3
"""Write an ORB-SLAM3 (v1.0 settings format) stereo-inertial yaml from a LaMAria
calibration JSON: "KannalaBrandt8" for the fitted EQUIDISTANT fisheye calibration
(unrectified stereo handled natively) or "PinHole" for the pinhole ASL calibration.

Frames: IMU.T_b_c1 = T_imu_cam0 = T_b_s of cam0; Stereo.T_c1_c2 = inv(T_imu_cam0) * T_imu_cam1.

Usage: make_orbslam3_settings.py CALIB_JSON OUT_YAML [--options OPTIONS_JSON] [--noise-scale 1] [--walk-scale 1]
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

DEFAULTS = {"nFeatures": 1200, "scaleFactor": 1.2, "nLevels": 8, "iniThFAST": 20, "minThFAST": 7,
            "ThDepth": 40.0, "fps": 20, "InsertKFsWhenLost": 1}


def rigid(c):
    T = np.eye(4)
    T[:3, :3] = R.from_quat(c["T_b_s"]["qvec"]).as_matrix()
    T[:3, 3] = c["T_b_s"]["tvec"]
    return T


def cvmat(T):
    rows = ",\n         ".join(", ".join(f"{v:.12f}" for v in row) for row in T)
    return f"!!opencv-matrix\n  rows: 4\n  cols: 4\n  dt: f\n  data: [{rows}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("calib_json", type=Path)
    ap.add_argument("out_yaml", type=Path)
    ap.add_argument("--options", type=Path)
    ap.add_argument("--noise-scale", type=float, default=1.0)
    ap.add_argument("--walk-scale", type=float, default=1.0)
    args = ap.parse_args()
    c = json.loads(args.calib_json.read_text())
    o = dict(DEFAULTS)
    if args.options:
        o.update(json.loads(args.options.read_text()))
    c0, c1 = c["cam0"], c["cam1"]
    T_i_c0, T_i_c1 = rigid(c0), rigid(c1)
    T_c1_c2 = np.linalg.inv(T_i_c0) @ T_i_c1
    w, h = c0["resolution"]["width"], c0["resolution"]["height"]
    lines = ["%YAML:1.0", 'File.version: "1.0"']
    if c0["model"] == "EQUIDISTANT":
        lines.append('Camera.type: "KannalaBrandt8"')
        for i, cam in ((1, c0), (2, c1)):
            fx, fy, cx, cy, k1, k2, k3, k4 = cam["params"][:8]
            lines += [f"Camera{i}.fx: {fx}", f"Camera{i}.fy: {fy}", f"Camera{i}.cx: {cx}", f"Camera{i}.cy: {cy}",
                      f"Camera{i}.k1: {k1}", f"Camera{i}.k2: {k2}", f"Camera{i}.k3: {k3}", f"Camera{i}.k4: {k4}",
                      f"Camera{i}.overlappingBegin: 0", f"Camera{i}.overlappingEnd: {cam['resolution']['width'] - 1}"]
    elif c0["model"] == "PINHOLE":
        lines.append('Camera.type: "PinHole"')
        for i, cam in ((1, c0), (2, c1)):
            fx, fy, cx, cy = cam["params"][:4]
            lines += [f"Camera{i}.fx: {fx}", f"Camera{i}.fy: {fy}", f"Camera{i}.cx: {cx}", f"Camera{i}.cy: {cy}",
                      f"Camera{i}.k1: 0.0", f"Camera{i}.k2: 0.0", f"Camera{i}.p1: 0.0", f"Camera{i}.p2: 0.0"]
    else:
        raise SystemExit(f"unsupported model {c0['model']}")
    imu = c["imu0"]
    s, wk = args.noise_scale, args.walk_scale
    lines += [f"Stereo.T_c1_c2: {cvmat(T_c1_c2)}", f"Camera.width: {w}", f"Camera.height: {h}", f"Camera.fps: {o['fps']}", "Camera.RGB: 1",
              f"Stereo.ThDepth: {o['ThDepth']}", f"IMU.T_b_c1: {cvmat(T_i_c0)}", f"IMU.InsertKFsWhenLost: {o['InsertKFsWhenLost']}",
              f"IMU.NoiseGyro: {imu['gyro_noise_density'] * s:.10g}", f"IMU.NoiseAcc: {imu['acc_noise_density'] * s:.10g}",
              f"IMU.GyroWalk: {imu['gyro_bias_random_walk_sigma'] * wk:.10g}", f"IMU.AccWalk: {imu['acc_bias_random_walk_sigma'] * wk:.10g}",
              f"IMU.Frequency: {float(imu['imu_rate'])}",
              f"ORBextractor.nFeatures: {o['nFeatures']}", f"ORBextractor.scaleFactor: {o['scaleFactor']}", f"ORBextractor.nLevels: {o['nLevels']}",
              f"ORBextractor.iniThFAST: {o['iniThFAST']}", f"ORBextractor.minThFAST: {o['minThFAST']}",
              "Viewer.KeyFrameSize: 0.05", "Viewer.KeyFrameLineWidth: 1.0", "Viewer.GraphLineWidth: 0.9", "Viewer.PointSize: 2.0",
              "Viewer.CameraSize: 0.08", "Viewer.CameraLineWidth: 3.0", "Viewer.ViewpointX: 0.0", "Viewer.ViewpointY: -0.7",
              "Viewer.ViewpointZ: -1.8", "Viewer.ViewpointF: 500.0", "Viewer.imageViewScale: 1.0"]
    args.out_yaml.parent.mkdir(parents=True, exist_ok=True)
    args.out_yaml.write_text("\n".join(lines) + "\n")
    print(f"wrote {args.out_yaml} ({lines[2]}, noise x{s}, walk x{wk})")


if __name__ == "__main__":
    main()
