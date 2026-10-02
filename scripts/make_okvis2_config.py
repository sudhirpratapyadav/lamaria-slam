#!/usr/bin/env python3
"""Write an OKVIS2 yaml from a LaMAria calibration JSON (pinhole or the fitted
EQUIDISTANT one) plus an options JSON for the estimator knobs.

T_SC in OKVIS2 is the camera pose in the IMU ("sensor") frame, i.e. T_imu_cam,
which is exactly T_b_s in the LaMAria JSON (body = right IMU).

Usage: make_okvis2_config.py CALIB_JSON OUT_YAML [--options OPTIONS_JSON] [--noise-scale 1] [--walk-scale 1]
Options JSON keys override the defaults in DEFAULTS below (flat dict, same names as the yaml).
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

DEFAULTS = {
    # frontend
    "detection_threshold": 34.0, "absolute_threshold": 200.0, "matching_threshold": 60.0, "octaves": 0,
    "max_num_keypoints": 900, "keyframe_overlap": 0.62, "num_matching_threads": 2,
    # estimator
    "num_keyframes": 5, "num_loop_closure_frames": 5, "num_imu_frames": 3, "do_loop_closures": True,
    "do_final_ba": True, "enforce_realtime": False, "realtime_min_iterations": 3, "realtime_max_iterations": 10,
    "realtime_time_limit": 0.035, "realtime_num_threads": 4, "full_graph_iterations": 15, "full_graph_num_threads": 2,
    "p_dbow": 0.4, "drift_percentage_heuristic": 1.35,
    # imu priors
    "sigma_bg": 0.01, "sigma_ba": 0.1,
    # camera
    "timestamp_tolerance": 0.005, "image_delay": 0.0, "do_extrinsics": False, "do_extrinsics_final_ba": False,
}


def mat(T):
    return "[" + ", ".join(f"{v:.9f}" for v in T.ravel()) + "]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("calib_json", type=Path)
    ap.add_argument("out_yaml", type=Path)
    ap.add_argument("--options", type=Path)
    ap.add_argument("--noise-scale", type=float, default=1.0)
    ap.add_argument("--walk-scale", type=float, default=1.0)
    args = ap.parse_args()
    calib = json.loads(args.calib_json.read_text())
    o = dict(DEFAULTS)
    if args.options:
        o.update(json.loads(args.options.read_text()))
    cams = []
    for key in ("cam0", "cam1"):
        c = calib[key]
        T = np.eye(4)
        T[:3, :3] = R.from_quat(c["T_b_s"]["qvec"]).as_matrix()
        T[:3, 3] = c["T_b_s"]["tvec"]
        if c["model"] == "PINHOLE":
            dist_type, dist = "radialtangential", [0.0, 0.0, 0.0, 0.0]
        elif c["model"] == "EQUIDISTANT":
            dist_type, dist = "equidistant", [float(v) for v in c["params"][4:8]]
        else:
            raise SystemExit(f"unsupported model {c['model']}")
        fx, fy, cx, cy = c["params"][:4]
        cams.append(
            f"     - {{T_SC: {mat(T)},\n"
            f"        image_dimension: [{c['resolution']['width']}, {c['resolution']['height']}],\n"
            f"        distortion_coefficients: [{', '.join(f'{v:.10g}' for v in dist)}],\n"
            f"        distortion_type: {dist_type},\n"
            f"        focal_length: [{fx:.6f}, {fy:.6f}],\n"
            f"        principal_point: [{cx:.6f}, {cy:.6f}],\n"
            f"        camera_type: gray,\n        slam_use: okvis}}\n")
    imu = calib["imu0"]
    s, w = args.noise_scale, args.walk_scale
    b = lambda v: "true" if v else "false"
    yaml = (
        "%YAML:1.0\ncameras:\n" + "".join(cams) +
        f"camera_parameters:\n    timestamp_tolerance: {o['timestamp_tolerance']}\n    image_delay: {o['image_delay']}\n    sync_cameras: [0,1]\n"
        f"    online_calibration:\n        do_extrinsics: {b(o['do_extrinsics'])}\n        do_extrinsics_final_ba: {b(o['do_extrinsics_final_ba'])}\n"
        f"        sigma_r: 0.01\n        sigma_alpha: 0.1\n        sigma_r_final_ba: 0.03\n        sigma_alpha_final_ba: 0.3\n"
        f"imu_parameters:\n    use: true\n    a_max: {imu['acc_saturation_max']}\n    g_max: {imu['gyro_saturation_max']}\n"
        f"    sigma_g_c: {imu['gyro_noise_density'] * s:.10g}\n    sigma_a_c: {imu['acc_noise_density'] * s:.10g}\n"
        f"    sigma_bg: {o['sigma_bg']}\n    sigma_ba: {o['sigma_ba']}\n"
        f"    sigma_gw_c: {imu['gyro_bias_random_walk_sigma'] * w:.10g}\n    sigma_aw_c: {imu['acc_bias_random_walk_sigma'] * w:.10g}\n"
        f"    g: {imu['gravity_magnitude']}\n    a0: [0.0, 0.0, 0.0]\n    g0: [0.0, 0.0, 0.0]\n"
        f"    T_BS: [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]\n"
        f"frontend_parameters:\n    detection_threshold: {o['detection_threshold']}\n    absolute_threshold: {o['absolute_threshold']}\n"
        f"    matching_threshold: {o['matching_threshold']}\n    octaves: {o['octaves']}\n    max_num_keypoints: {o['max_num_keypoints']}\n"
        f"    keyframe_overlap: {o['keyframe_overlap']}\n    use_cnn: false\n    parallelise_detection: false\n    num_matching_threads: {o['num_matching_threads']}\n"
        f"estimator_parameters:\n    num_keyframes: {o['num_keyframes']}\n    num_loop_closure_frames: {o['num_loop_closure_frames']}\n"
        f"    num_imu_frames: {o['num_imu_frames']}\n    do_loop_closures: {b(o['do_loop_closures'])}\n    do_final_ba: {b(o['do_final_ba'])}\n"
        f"    enforce_realtime: {b(o['enforce_realtime'])}\n    realtime_min_iterations: {o['realtime_min_iterations']}\n"
        f"    realtime_max_iterations: {o['realtime_max_iterations']}\n    realtime_time_limit: {o['realtime_time_limit']}\n"
        f"    realtime_num_threads: {o['realtime_num_threads']}\n    full_graph_iterations: {o['full_graph_iterations']}\n"
        f"    full_graph_num_threads: {o['full_graph_num_threads']}\n    p_dbow: {o['p_dbow']}\n    drift_percentage_heuristic: {o['drift_percentage_heuristic']}\n"
        "output_parameters:\n    display_matches: false\n    display_overhead: false\n"
    )
    args.out_yaml.parent.mkdir(parents=True, exist_ok=True)
    args.out_yaml.write_text(yaml)
    print(f"wrote {args.out_yaml} (noise x{s}, walk x{w}, loop closures {o['do_loop_closures']}, final BA {o['do_final_ba']})")


if __name__ == "__main__":
    main()
