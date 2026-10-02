#!/usr/bin/env python3
"""Build a time-reversed runner input for the first W seconds of a sequence.

Used by the bidirectional pass (experiment 023): the forward estimator is poor
during its first minute (biases and velocity still converging), so a second
estimator is run backwards in time over that segment, starting where the
forward run is already good, and stitched onto it.

Time reversal: t' = t_pivot_twice - t with t_pivot = t0 + W (so t' increases as t
decreases and the first frame of the reversed input is the one at t0 + W).
Gyro is negated (dq/dt' = -w), accelerometer is unchanged (second derivative).

Usage: make_reversed_input.py SEQ_RUNNER_INPUT OUT_DIR --window W [--imu-margin 3]
Writes OUT_DIR/{imu.csv, stereo.csv, cam0, cam1, image_timestamps_ns.txt, reverse_info.json}
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runner_input", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--window", type=float, default=120.0, help="seconds of the sequence start to reverse")
    ap.add_argument("--imu-margin", type=float, default=3.0, help="extra IMU seconds beyond the window")
    args = ap.parse_args()
    src = args.runner_input
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    for cam in ("cam0", "cam1"):
        link = out / cam
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(os.path.relpath((src / cam).resolve(), out), link)

    stereo = [l.split(",") for l in (src / "stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    t_img = np.array([float(r[0]) for r in stereo])
    t0 = t_img[0]
    t_end = t0 + args.window
    pivot2 = 2.0 * t_end  # t' = pivot2 - t
    sel = [r for r in stereo if float(r[0]) <= t_end]
    sel.reverse()
    with open(out / "stereo.csv", "w") as f, open(out / "image_timestamps_ns.txt", "w") as h:
        f.write(f"# reversed: t' = {pivot2:.9f} - t\n")
        for r in sel:
            tp = pivot2 - float(r[0])
            f.write(f"{tp:.9f},{r[1]},{r[2]}\n")
            h.write(f"{int(round(float(r[0]) * 1e9))}\n")

    imu = np.loadtxt(src / "imu.csv", delimiter=",", comments="#")
    imu = imu[imu[:, 0] <= t_end + args.imu_margin][::-1]
    rev = imu.copy()
    rev[:, 0] = pivot2 - imu[:, 0]
    rev[:, 1:4] = -imu[:, 1:4]
    with open(out / "imu.csv", "w") as f:
        f.write("# reversed time, gyro negated\n")
        for row in rev:
            f.write(f"{row[0]:.9f}," + ",".join(f"{v:.9g}" for v in row[1:]) + "\n")
    info = {"t0": t0, "window_s": args.window, "pivot2": pivot2, "frames": len(sel), "imu_rows": int(len(rev))}
    (out / "reverse_info.json").write_text(json.dumps(info) + "\n")
    print(json.dumps(info))


if __name__ == "__main__":
    main()
