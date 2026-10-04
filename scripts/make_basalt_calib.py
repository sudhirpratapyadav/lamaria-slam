#!/usr/bin/env python3
"""Write a Basalt calibration JSON from a LaMAria calibration JSON (pinhole, or the
fitted EQUIDISTANT one which maps to Basalt's "kb4").

T_imu_cam in Basalt = T_b_s in the LaMAria JSON (body = right IMU). Basalt's IMU
noise fields are per-axis std values in continuous-time units; the LaMAria JSON
gives Kalibr-style densities, which are the same quantities.

Usage: make_basalt_calib.py CALIB_JSON OUT_JSON [--noise-scale 1] [--walk-scale 1] [--gyro-noise-scale S] [--gyro-walk-scale W]
"""
import argparse
import json
import os
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("calib_json", type=Path)
    ap.add_argument("out_json", type=Path)
    ap.add_argument("--noise-scale", type=float, default=1.0)
    ap.add_argument("--walk-scale", type=float, default=1.0)
    ap.add_argument("--gyro-noise-scale", type=float, help="gyro noise factor (default: --noise-scale)")
    ap.add_argument("--gyro-walk-scale", type=float, help="gyro bias walk factor (default: --walk-scale)")
    ap.add_argument("--cam0-rot-deg", type=float, nargs=3, metavar=("RX", "RY", "RZ"), help="rotate cam0 about its own axes (deg), T_i_c0 * Exp(r)")
    ap.add_argument("--cam1-rot-deg", type=float, nargs=3, metavar=("RX", "RY", "RZ"))
    ap.add_argument("--cam0-focal-scale", type=float, default=float(os.environ.get("CAM0_FOCAL_SCALE", "1")), help="multiply cam0 fx, fy (v4 F10 intrinsics probe; also env CAM0_FOCAL_SCALE)")
    args = ap.parse_args()
    c = json.loads(args.calib_json.read_text())
    T, intr, res = [], [], []
    for key in ("cam0", "cam1"):
        cam = c[key]
        q, t = cam["T_b_s"]["qvec"], cam["T_b_s"]["tvec"]
        rot = args.cam0_rot_deg if key == "cam0" else args.cam1_rot_deg
        if rot:  # extrinsic-rotation probe (v4 F09): camera frame rotated about its own axes
            from scipy.spatial.transform import Rotation as R
            q = list((R.from_quat(q) * R.from_euler("xyz", rot, degrees=True)).as_quat())
        T.append({"px": t[0], "py": t[1], "pz": t[2], "qx": q[0], "qy": q[1], "qz": q[2], "qw": q[3]})
        fx, fy, cx, cy = cam["params"][:4]
        if key == "cam0" and args.cam0_focal_scale != 1.0:
            fx, fy = fx * args.cam0_focal_scale, fy * args.cam0_focal_scale
        if cam["model"] == "PINHOLE":
            intr.append({"camera_type": "pinhole", "intrinsics": {"fx": fx, "fy": fy, "cx": cx, "cy": cy}})
        elif cam["model"] == "EQUIDISTANT":
            k = cam["params"][4:8]
            intr.append({"camera_type": "kb4", "intrinsics": {"fx": fx, "fy": fy, "cx": cx, "cy": cy, "k1": k[0], "k2": k[1], "k3": k[2], "k4": k[3]}})
        else:
            raise SystemExit(f"unsupported model {cam['model']}")
        res.append([cam["resolution"]["width"], cam["resolution"]["height"]])
    imu = c["imu0"]
    s, w = args.noise_scale, args.walk_scale
    gs = s if args.gyro_noise_scale is None else args.gyro_noise_scale
    gw = w if args.gyro_walk_scale is None else args.gyro_walk_scale
    # vignette and bias blocks have fixed lengths that cereal checks: copy them from Basalt's own template
    tmpl = json.loads(Path.home().joinpath(".local/etc/basalt/euroc_eucm_calib.json").read_text())["value0"]
    out = {"value0": {
        "T_imu_cam": T, "intrinsics": intr, "resolution": res,
        "vignette": tmpl["vignette"],
        "calib_accel_bias": [0.0] * len(tmpl["calib_accel_bias"]), "calib_gyro_bias": [0.0] * len(tmpl["calib_gyro_bias"]),
        "imu_update_rate": float(imu["imu_rate"]),
        "accel_noise_std": [imu["acc_noise_density"] * s] * 3,
        "gyro_noise_std": [imu["gyro_noise_density"] * gs] * 3,
        "accel_bias_std": [imu["acc_bias_random_walk_sigma"] * w] * 3,
        "gyro_bias_std": [imu["gyro_bias_random_walk_sigma"] * gw] * 3,
        "T_mocap_world": {"px": 0.0, "py": 0.0, "pz": 0.0, "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0},
        "T_imu_marker": {"px": 0.0, "py": 0.0, "pz": 0.0, "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0},
        "mocap_time_offset_ns": 0, "mocap_to_imu_offset_ns": 0, "cam_time_offset_ns": 0,
    }}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=4) + "\n")
    print(f"wrote {args.out_json} ({intr[0]['camera_type']}, noise x{s}, walk x{w}, gyro noise x{gs}, gyro walk x{gw})")


if __name__ == "__main__":
    main()
