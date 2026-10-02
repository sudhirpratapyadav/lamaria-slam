#!/usr/bin/env python3
"""Write OpenVINS imucam.yaml and imu.yaml from a LaMAria calibration JSON.

The JSON (pinhole or aria flavour) stores T_b_s per sensor with body = right IMU,
so T_b_s is T_imu_cam; OpenVINS wants T_cam_imu. qvec is xyzw.

Usage: make_openvins_config.py CALIB_JSON OUT_DIR [--noise-scale S]
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


def rigid(qvec_xyzw, tvec):
    T = np.eye(4)
    T[:3, :3] = Rotation.from_quat(qvec_xyzw).as_matrix()
    T[:3, 3] = tvec
    return T


def mat_rows(T):
    return "\n".join("    - [" + ", ".join(f"{v:.12g}" for v in row) + "]" for row in T)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("calib_json", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--noise-scale", type=float, default=1.0,
                    help="multiply the JSON IMU white-noise densities by this")
    ap.add_argument("--timeshift", type=float, default=0.0, help="initial camera-IMU time offset written as timeshift_cam_imu (s)")
    ap.add_argument("--acc-scale", type=float, default=1.0,
                    help="accelerometer scale factor k (measured = k * true); written as kalibr Ta = diag(k), OpenVINS applies 1/k")
    ap.add_argument("--focal-scale", type=float, default=float(os.environ.get("FOCAL_SCALE", "1.0")),
                    help="multiply both focal lengths (diagnostic for a stereo scale error); env FOCAL_SCALE")
    ap.add_argument("--walk-scale", type=float, default=None,
                    help="multiply the JSON bias random walks by this (default: same as --noise-scale)")
    args = ap.parse_args()
    calib = json.loads(args.calib_json.read_text())
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # OpenVINS stereo KLT needs equal image sizes; the runner pads the smaller
    # image at the bottom/right (intrinsics unchanged) and masks the padding.
    W = max(calib[k]["resolution"]["width"] for k in ("cam0", "cam1"))
    H = max(calib[k]["resolution"]["height"] for k in ("cam0", "cam1"))
    cams = []
    for i, key in enumerate(["cam0", "cam1"]):
        c = calib[key]
        T_imu_cam = rigid(c["T_b_s"]["qvec"], c["T_b_s"]["tvec"])
        T_cam_imu = np.linalg.inv(T_imu_cam)
        if c["model"] == "PINHOLE":
            model, dist_model, dist = "pinhole", "radtan", [0.0, 0.0, 0.0, 0.0]
            intr = [c["params"][0] * args.focal_scale, c["params"][1] * args.focal_scale, c["params"][2], c["params"][3]]
        elif c["model"] == "EQUIDISTANT":  # Kannala-Brandt fit of the Aria lens, see fit_fisheye_kb.py
            model, dist_model, dist = "equidistant", "equidistant", [float(v) for v in c["params"][4:8]]
            intr = [c["params"][0] * args.focal_scale, c["params"][1] * args.focal_scale, c["params"][2], c["params"][3]]
        else:
            raise SystemExit(f"{c['model']} not supported; use the pinhole or the fitted EQUIDISTANT calibration")
        cams.append(
            f"cam{i}:\n  T_cam_imu:\n{mat_rows(T_cam_imu)}\n  cam_overlaps: [{1 - i}]\n"
            f"  camera_model: {model}\n  distortion_coeffs: {dist}\n  distortion_model: {dist_model}\n"
            f"  intrinsics: {intr}\n  resolution: [{W}, {H}]\n"
            f"  rostopic: /cam{i}/image_raw\n  timeshift_cam_imu: {args.timeshift}\n"
        )
    (args.out_dir / "imucam.yaml").write_text("%YAML:1.0\n---\n" + "".join(cams))

    imu = calib["imu0"]
    s = args.noise_scale
    w = s if args.walk_scale is None else args.walk_scale
    eye3 = mat_rows(np.eye(3))
    imu_yaml = (
        "%YAML:1.0\n---\nimu0:\n  T_i_b:\n" + mat_rows(np.eye(4)) + "\n"
        f"  accelerometer_noise_density: {imu['acc_noise_density'] * s:.10g}\n"
        f"  accelerometer_random_walk: {imu['acc_bias_random_walk_sigma'] * w:.10g}\n"
        f"  gyroscope_noise_density: {imu['gyro_noise_density'] * s:.10g}\n"
        f"  gyroscope_random_walk: {imu['gyro_bias_random_walk_sigma'] * w:.10g}\n"
        f"  rostopic: /imu0\n  time_offset: 0.0\n  update_rate: {imu['imu_rate']:.1f}\n  model: kalibr\n"
        f"  Tw:\n{eye3}\n  R_IMUtoGYRO:\n{eye3}\n  Ta:\n{mat_rows(np.eye(3) * args.acc_scale)}\n  R_IMUtoACC:\n{eye3}\n"
        "  Tg:\n" + mat_rows(np.zeros((3, 3))) + "\n"
    )
    (args.out_dir / "imu.yaml").write_text(imu_yaml)
    print(f"wrote {args.out_dir}/imucam.yaml and imu.yaml (noise scale {s}, walk scale {w}, acc scale {args.acc_scale}, focal scale {args.focal_scale}, timeshift {args.timeshift}, gravity {imu['gravity_magnitude']})")


if __name__ == "__main__":
    main()
