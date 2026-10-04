#!/usr/bin/env python3
"""Sequence folder with the IMU timestamps shifted by DT seconds (camera-IMU time offset probe).

imu'(t) = imu(t) with t' = t - DT, so DT > 0 means the images are treated as taken DT later
relative to the IMU than their stamps say. Everything else is linked.
Usage: make_timeshift_input.py SEQ_DIR OUT_DIR DT_SECONDS
"""
import os
import sys
from pathlib import Path

import numpy as np


def main():
    seq, out, dt = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), float(sys.argv[3])
    ri = out / "runner_input"
    ri.mkdir(parents=True, exist_ok=True)
    for f in ("cam0", "cam1", "stereo.csv", "image_timestamps_ns.txt"):
        link = ri / f
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(os.path.relpath(seq / "runner_input" / f, ri), link)
    rows = (seq / "runner_input" / "imu.csv").read_text().splitlines()
    with open(ri / "imu.csv", "w") as fh:
        fh.write(f"# IMU time shifted by {-dt:+.6f} s (camera-IMU offset probe)\n")
        for l in rows:
            if not l or l.startswith("#"):
                continue
            v = l.split(",")
            fh.write(f"{float(v[0]) - dt:.9f}," + ",".join(v[1:]) + "\n")
    for d in ("pinhole_calibrations", "aria_calibrations", "ground_truth"):
        link = out / d
        if (seq / d).exists() and not link.exists():
            os.symlink(os.path.relpath(seq / d, out), link)
    print(f"{out}: IMU shifted by {-dt:+.4f} s")


if __name__ == "__main__":
    main()
