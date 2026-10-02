#!/usr/bin/env python3
"""Apply the Aria factory IMU rectification (from the .vrs device calibration) to a
sequence's raw IMU input and build a parallel sequence folder for the runner.

The ASL IMU data is raw sensor output; the factory calibration holds, per IMU, a
3x3 rectification matrix and a bias such that
    rectified = inv(M) @ (raw - bias)
(projectaria_tools ImuCalibration.raw_to_rectified_accel / _gyro). This script
reads the right IMU calibration from the .vrs and writes
  <out_root>/<seq>/runner_input/imu.csv  (rectified, same format as the raw one)
with symlinks for everything else, so scripts/run_sequence.sh works unchanged on
<out_root>/<seq>.

Usage: rectify_imu_from_vrs.py data/training/R_01_easy data/training_rect [--imu imu-right]
"""
import argparse
import os
from pathlib import Path

import numpy as np
from projectaria_tools.core import data_provider


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("out_root", type=Path)
    ap.add_argument("--imu", default="imu-right")
    args = ap.parse_args()
    seq = args.seq_dir.name
    vrs = next(iter(args.seq_dir.glob("raw_data/*.vrs")))
    provider = data_provider.create_vrs_data_provider(str(vrs))
    calib = provider.get_device_calibration().get_imu_calib(args.imu)
    acc, gyr = calib.get_accel_model(), calib.get_gyro_model()
    Ma, ba = np.array(acc.get_rectification()), np.array(acc.get_bias())
    Mg, bg = np.array(gyr.get_rectification()), np.array(gyr.get_bias())
    print(f"{seq} {args.imu}: accel rectification diag {np.diag(Ma).round(5)} bias {ba.round(4)} | gyro diag {np.diag(Mg).round(5)} bias {bg.round(5)}")
    print("  accel rectification full:\n", Ma.round(5))

    out = args.out_root / seq
    (out / "runner_input").mkdir(parents=True, exist_ok=True)
    for name in ("pinhole_calibrations", "aria_calibrations", "ground_truth", "raw_data"):
        link = out / name
        if (args.seq_dir / name).exists() and not link.exists():
            os.symlink(os.path.relpath((args.seq_dir / name).resolve(), out), link)
    src = args.seq_dir / "runner_input"
    for name in ("cam0", "cam1", "stereo.csv", "image_timestamps_ns.txt"):
        link = out / "runner_input" / name
        if not link.exists():
            os.symlink(os.path.relpath((src / name).resolve(), out / "runner_input"), link)

    imu = np.loadtxt(src / "imu.csv", delimiter=",", comments="#")
    Ma_inv, Mg_inv = np.linalg.inv(Ma), np.linalg.inv(Mg)
    gyro = (Mg_inv @ (imu[:, 1:4] - bg).T).T
    accel = (Ma_inv @ (imu[:, 4:7] - ba).T).T
    with open(out / "runner_input" / "imu.csv", "w") as f:
        f.write(f"# t_seconds,gx,gy,gz,ax,ay,az (right IMU, factory-rectified from {vrs.name})\n")
        for t, g, a in zip(imu[:, 0], gyro, accel):
            f.write(f"{t:.9f}," + ",".join(f"{v:.9g}" for v in g) + "," + ",".join(f"{v:.9g}" for v in a) + "\n")
    print(f"  wrote {out}/runner_input/imu.csv ({len(imu)} rows); mean |a| raw {np.linalg.norm(imu[:,4:7],axis=1).mean():.4f} rectified {np.linalg.norm(accel,axis=1).mean():.4f}")


if __name__ == "__main__":
    main()
