#!/usr/bin/env python3
"""Build an OKVIS2 (EuRoC-layout) dataset folder from a runner input.

OKVIS2's DatasetReader wants <dir>/cam{0,1}/data.csv and <dir>/imu0/data.csv, each
with a header line that it skips, timestamps in nanoseconds, and images under
<dir>/cam{i}/data/. Our runner input has the same images (symlinked) and seconds
timestamps, so this writes the csv files and symlinks the image folders.

Usage: make_okvis2_input.py RUNNER_INPUT_DIR OUT_DIR
"""
import argparse
import os
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runner_input", type=Path)
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    src, out = args.runner_input.resolve(), args.out
    # Idempotent and atomic: other estimators may be reading these files concurrently.
    marker = out / "built_from.txt"
    if marker.exists() and marker.read_text().strip() == str(src) and (out / "imu0" / "data.csv").exists():
        print(f"{out}: already built")
        return
    for cam in ("cam0", "cam1"):
        (out / cam).mkdir(parents=True, exist_ok=True)
        link = out / cam / "data"
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(os.path.relpath((src / cam / "data").resolve(), out / cam), link)
    (out / "imu0").mkdir(exist_ok=True)
    rows = [l.split(",") for l in (src / "stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    for cam, col in (("cam0", 1), ("cam1", 2)):
        tmp = out / cam / "data.csv.tmp"
        with open(tmp, "w") as f:
            f.write("#timestamp [ns],filename\n")
            for r in rows:
                f.write(f"{int(round(float(r[0]) * 1e9))},{Path(r[col]).name}\n")
        tmp.replace(out / cam / "data.csv")
    n = 0
    tmp = out / "imu0" / "data.csv.tmp"
    with open(src / "imu.csv") as f, open(tmp, "w") as g:
        g.write("#timestamp [ns],w_RS_S_x [rad s^-1],w_RS_S_y [rad s^-1],w_RS_S_z [rad s^-1],a_RS_S_x [m s^-2],a_RS_S_y [m s^-2],a_RS_S_z [m s^-2]\n")
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.strip().split(",")
            g.write(f"{int(round(float(p[0]) * 1e9))}," + ",".join(p[1:7]) + "\n")
            n += 1
    tmp.replace(out / "imu0" / "data.csv")
    marker.write_text(str(src) + "\n")
    print(f"{out}: {len(rows)} stereo frames, {n} IMU rows")


if __name__ == "__main__":
    main()
