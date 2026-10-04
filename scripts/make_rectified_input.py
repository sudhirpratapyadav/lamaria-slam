#!/usr/bin/env python3
"""Apply the Aria factory IMU rectification to a sequence's raw IMU (the ASL export
omits it) and build a parallel sequence folder for the driver, everything else linked.

The device is identified by the md5 prefix of its aria_calibrations json; the factory
model (raw = M @ rectified + bias, projectaria_tools ImuCalibration, imu-right) is read
from <factory_dir>/<device>.json, as recovered in v4 F08 from the v1 .vrs rectification.

Usage: make_rectified_input.py <seq_dir> <out_dir> [factory_dir=configs/aria_factory_imu] [--gyro-only|--no-bias]
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    seq, out = Path(args[0]).resolve(), Path(args[1])
    fdir = Path(args[2]) if len(args) > 2 else Path("configs/aria_factory_imu")
    dev = hashlib.md5(open(next(seq.glob("aria_calibrations/*.json")), "rb").read()).hexdigest()[:8]
    fac = json.load(open(fdir / f"{dev}.json"))
    out.mkdir(parents=True)
    for p in seq.iterdir():
        if p.name != "runner_input":
            os.symlink(os.path.relpath(p, out), out / p.name)
    (out / "runner_input").mkdir()
    for p in (seq / "runner_input").iterdir():
        if p.name != "imu.csv":
            os.symlink(os.path.relpath(p, out / "runner_input"), out / "runner_input" / p.name)
    d = np.loadtxt(seq / "runner_input" / "imu.csv", delimiter=",", comments="#")
    for name, cols in (("gyro", slice(1, 4)), ("accel", slice(4, 7))):
        if name == "accel" and "--gyro-only" in flags:
            continue
        M = np.array(fac[name]["M"]); b = np.zeros(3) if "--no-bias" in flags else np.array(fac[name]["bias"])
        d[:, cols] = (np.linalg.inv(M) @ (d[:, cols] - b).T).T
    with open(out / "runner_input" / "imu.csv", "w") as fh:
        fh.write(f"# t_seconds,gx,gy,gz,ax,ay,az (right IMU, factory-rectified, device {dev}, flags {sorted(flags)})\n")
        for r in d:
            fh.write(f"{r[0]:.9f}," + ",".join(f"{v:.10g}" for v in r[1:]) + "\n")
    print(f"{out}: IMU rectified with {fdir / (dev + '.json')} {sorted(flags)}")


if __name__ == "__main__":
    main()
