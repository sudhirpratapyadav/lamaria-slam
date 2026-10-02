#!/usr/bin/env python3
"""Turn a LaMAria ASL sequence into the input the offline runner expects.

Creates <seq_dir>/runner_input/ with
  imu.csv     t_seconds,gx,gy,gz,ax,ay,az   (ASL imu0 is the right 1 kHz IMU, ns -> s)
  stereo.csv  t_seconds,cam0/data/<ts>.png,cam1/data/<ts>.png
  cam0, cam1  symlinks into the ASL folder
  image_timestamps_ns.txt  one nanosecond timestamp per image (for the submission file)

Unzips <seq_dir>/asl_folder/<seq>.zip first if the aria/ folder is missing.

Usage: prepare_runner_input.py data/training/R_01_easy
"""
import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path


def find_aria(seq_dir: Path) -> Path:
    hits = [p for p in seq_dir.rglob("imu0/data.csv") if "runner_input" not in p.parts]
    if not hits:
        zips = list((seq_dir / "asl_folder").glob("*.zip"))
        if not zips:
            sys.exit(f"no aria folder and no zip under {seq_dir}")
        print(f"unzipping {zips[0]} ...")
        subprocess.run(["unzip", "-q", "-o", str(zips[0]), "-d", str(zips[0].parent)], check=True)
        hits = [p for p in seq_dir.rglob("imu0/data.csv") if "runner_input" not in p.parts]
    if len(hits) != 1:
        sys.exit(f"expected one imu0/data.csv under {seq_dir}, found {hits}")
    return hits[0].parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    aria = find_aria(args.seq_dir)
    out = args.seq_dir / "runner_input"
    if (out / "stereo.csv").exists() and not args.force:
        print(f"{out} already prepared")
        return
    out.mkdir(exist_ok=True)
    for cam in ("cam0", "cam1"):
        link = out / cam
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(os.path.relpath(aria / cam, out), link)

    n_imu, last = 0, -1
    with open(aria / "imu0" / "data.csv") as f, open(out / "imu.csv", "w") as g:
        g.write("# t_seconds,gx,gy,gz,ax,ay,az (right IMU, ns/1e9)\n")
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or not row[0].strip().isdigit():
                continue
            ts = int(row[0])
            if ts <= last:
                continue  # drop duplicates / non-monotonic rows, the runner rejects them
            last = ts
            g.write(f"{ts / 1e9:.9f}," + ",".join(row[1:7]) + "\n")
            n_imu += 1

    left = {int(r[0]): r[1] for r in csv.reader(open(aria / "cam0" / "data.csv")) if r and r[0].strip().isdigit()}
    right = {int(r[0]): r[1] for r in csv.reader(open(aria / "cam1" / "data.csv")) if r and r[0].strip().isdigit()}
    common = sorted(set(left) & set(right))
    if len(common) != len(left) or len(common) != len(right):
        print(f"warning: {len(left)} left, {len(right)} right, {len(common)} common timestamps")
    with open(out / "stereo.csv", "w") as g, open(out / "image_timestamps_ns.txt", "w") as h:
        g.write("# t_seconds,left,right\n")
        for ts in common:
            g.write(f"{ts / 1e9:.9f},cam0/data/{left[ts]},cam1/data/{right[ts]}\n")
            h.write(f"{ts}\n")
    dur = (common[-1] - common[0]) / 1e9
    print(f"{out}: {len(common)} stereo pairs over {dur:.1f} s ({len(common) / dur:.2f} Hz), {n_imu} IMU rows "
          f"({n_imu / dur:.0f} Hz)")


if __name__ == "__main__":
    main()
