#!/usr/bin/env python3
"""Where in the image and when do the IMU-gated observations (v3 F01, BASALT_GATE_DUMP) fall?
Usage: gate_map.py DUMP.txt SEQ_DIR [--grid 6x4] [--window 60]
Prints a coarse image grid of drop counts (cam0) and the drops per time window, with the
window's share of all observations unknown (counts only)."""
import argparse
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("dump", type=Path); ap.add_argument("seq_dir", type=Path)
ap.add_argument("--grid", default="6x4"); ap.add_argument("--window", type=float, default=60.0)
ap.add_argument("--width", type=int, default=758); ap.add_argument("--height", type=int, default=572)
a = ap.parse_args()
d = np.loadtxt(a.dump)
if d.ndim == 1: d = d[None]
gx, gy = (int(v) for v in a.grid.split("x"))
cam0 = d[d[:, 1] == 0]
H = np.zeros((gy, gx), int)
for _, _, u, v, _ in cam0:
    i, j = min(int(v / a.height * gy), gy - 1), min(int(u / a.width * gx), gx - 1)
    H[i, j] += 1
print(f"{len(d)} drops ({len(cam0)} cam0); image grid of cam0 drops (rows = top to bottom):")
for row in H: print("  " + " ".join(f"{x:6d}" for x in row))
gt = next(a.seq_dir.glob("ground_truth/**/pGT/*.txt"), None)
t0 = float(open(gt).readline().split()[0]) / 1e9 if gt else d[0, 0] / 1e9
t = d[:, 0] / 1e9 - t0
bins = np.bincount(np.clip((t // a.window).astype(int), 0, None))
print("drops per window (s):", " ".join(f"{(k + 0.5) * a.window:.0f}:{n}" for k, n in enumerate(bins)))
