#!/usr/bin/env python3
"""Measure how much of each camera's image is covered by something attached to the camera
(hair, hat, glasses frame, robot body): pixels whose intensity barely changes over a short
burst of consecutive frames while the rest of the image changes a lot.

Per window (every --every seconds) a burst of --burst consecutive frames is loaded,
downsampled, and the per-pixel temporal std computed; the window counts as "moving" when
the median std is above --moving; occluder pixels are those with std below --frac times
the median. Prints per camera the mean and max occluder fraction over moving windows and
writes a CSV (t_s, cam, moving_median_std, occluder_fraction).

Usage: occluder_check.py SEQ_DIR [--every 60] [--burst 40] [--csv out.csv]
"""
import argparse
import csv
import glob
from pathlib import Path

import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("--every", type=float, default=60.0)
    ap.add_argument("--burst", type=int, default=40)
    ap.add_argument("--moving", type=float, default=6.0, help="median temporal std (grey levels) for a window to count as moving")
    ap.add_argument("--frac", type=float, default=0.15)
    ap.add_argument("--csv")
    a = ap.parse_args()
    rows = []
    summary = {}
    for cam in ("cam0", "cam1"):
        files = sorted(glob.glob(str(a.seq_dir / "runner_input" / cam / "data" / "*.png")), key=lambda f: int(Path(f).stem))
        t = np.array([int(Path(f).stem) for f in files]) * 1e-9
        fr = []
        for t0 in np.arange(t[0], t[-1], a.every):
            i = int(np.searchsorted(t, t0))
            if i + a.burst > len(files):
                break
            imgs = np.stack([np.asarray(Image.open(f).convert("L").reduce(4), dtype=np.float32) for f in files[i:i + a.burst]])
            sd = imgs.std(axis=0)
            med = float(np.median(sd))
            moving = med > a.moving
            occ = float((sd < a.frac * med).mean()) if moving else float("nan")
            rows.append((round(t0 - t[0], 1), cam, round(med, 2), round(occ, 4) if moving else ""))
            if moving:
                fr.append(occ)
        summary[cam] = (np.mean(fr) if fr else float("nan"), np.max(fr) if fr else float("nan"), len(fr))
    print(f"{a.seq_dir.name:14s} " + " | ".join(f"{c}: occluder mean {100*m:4.1f}% max {100*x:4.1f}% ({n} moving windows)" for c, (m, x, n) in summary.items()))
    if a.csv:
        with open(a.csv, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["t_s", "cam", "median_std", "occluder_fraction"]); w.writerows(rows)


if __name__ == "__main__":
    main()
