#!/usr/bin/env python3
"""Extract the raw fisheye SLAM camera frames from an Aria .vrs into a runner input
(no VRS command-line tools needed; uses projectaria_tools only).

Writes <out_seq_dir>/runner_input/{cam0/data/<ts>.png, cam1/data/<ts>.png, stereo.csv,
image_timestamps_ns.txt, imu.csv (copied from the ASL-derived runner input: same raw
right IMU in device time), mask0.png, mask1.png (255 where the camera model has no
valid ray, e.g. outside the fisheye circle)} and symlinks ground_truth, aria_calibrations,
raw_data. Images keep the raw sensor orientation, which is what the Aria calibration
describes.

Usage: vrs_to_runner_input.py data/training/R_01_easy data/training_fisheye/R_01_easy
"""
import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from projectaria_tools.core import data_provider
from projectaria_tools.core.sensor_data import TimeDomain
from projectaria_tools.core.stream_id import StreamId

STREAMS = {"cam0": ("1201-1", "camera-slam-left"), "cam1": ("1201-2", "camera-slam-right")}


def valid_mask(calib):
    w, h = calib.get_image_size()
    m = np.full((h, w), 255, dtype=np.uint8)
    ys, xs = np.mgrid[0:h, 0:w]
    for y in range(0, h):
        for x in range(0, w):
            if calib.unproject(np.array([x, y], dtype=float)) is not None:
                m[y, x] = 0
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()
    seq = args.seq_dir.name
    vrs = next(iter(args.seq_dir.glob("raw_data/*.vrs")))
    provider = data_provider.create_vrs_data_provider(str(vrs))
    dc = provider.get_device_calibration()
    out = args.out_dir / "runner_input"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("ground_truth", "aria_calibrations", "raw_data", "pinhole_calibrations"):
        link = args.out_dir / name
        if (args.seq_dir / name).exists() and not link.exists():
            os.symlink(os.path.relpath((args.seq_dir / name).resolve(), args.out_dir), link)

    stamps = {}
    for cam, (sid, label) in STREAMS.items():
        stream = StreamId(sid)
        n = provider.get_num_data(stream)
        d = out / cam / "data"
        d.mkdir(parents=True, exist_ok=True)
        ts_list = []
        for i in range(n):
            img, rec = provider.get_image_data_by_index(stream, i)
            ts = rec.capture_timestamp_ns
            ts_list.append(ts)
            p = d / f"{ts}.png"
            if not p.exists():
                Image.fromarray(img.to_numpy_array()).save(p, compress_level=1)
            if i % 500 == 0:
                print(f"{cam}: {i}/{n}", flush=True)
        stamps[cam] = ts_list
        Image.fromarray(valid_mask(dc.get_camera_calib(label))).save(out / f"mask{cam[-1]}.png")
    left, right = np.array(stamps["cam0"]), np.array(stamps["cam1"])
    j = np.searchsorted(right, left)
    pairs = []
    for i, t in enumerate(left):
        cands = [k for k in (j[i] - 1, j[i]) if 0 <= k < len(right)]
        k = min(cands, key=lambda k: abs(right[k] - t))
        if abs(right[k] - t) <= 1_000_000:
            pairs.append((t, right[k]))
    with open(out / "stereo.csv", "w") as f, open(out / "image_timestamps_ns.txt", "w") as h:
        f.write("# t_seconds,left,right (raw fisheye from vrs)\n")
        for t, r in pairs:
            f.write(f"{t / 1e9:.9f},cam0/data/{t}.png,cam1/data/{r}.png\n")
            h.write(f"{t}\n")
    src_imu = args.seq_dir / "runner_input" / "imu.csv"
    if src_imu.exists():
        (out / "imu.csv").write_bytes(src_imu.read_bytes())
    else:
        sys.exit("no ASL runner input imu.csv to copy; run prepare_runner_input.py on the ASL sequence first")
    print(f"{seq}: {len(pairs)} stereo pairs ({len(left)} left, {len(right)} right frames), masks written")


if __name__ == "__main__":
    main()
