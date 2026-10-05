#!/usr/bin/env python3
"""Signed reprojection-residual map of a vi_ba solve (residuals.bin written by tools/vi_ba).

Usage: residual_map.py BA_DIR [--grid 3] [--label L]
Prints, per camera: the mean signed residual (projected minus observed, px) in x and y over a grid of image
regions, and split by the host camera. A systematic signed mean on one side of the image is a tracking or
model bias; zero means everywhere means the drift is not in the reprojection residuals.
"""
import json
import struct
import sys

import numpy as np


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    grid = 3
    label = ""
    for i, a in enumerate(sys.argv):
        if a == "--grid":
            grid = int(sys.argv[i + 1])
        if a == "--label":
            label = sys.argv[i + 1]
    d = args[0]
    rec = struct.Struct("<iiifffff")
    raw = open(d + "/residuals.bin", "rb").read()
    n = len(raw) // rec.size
    a = np.array([rec.unpack_from(raw, i * rec.size) for i in range(n)])
    kf, cam, hcam = a[:, 0].astype(int), a[:, 1].astype(int), a[:, 2].astype(int)
    x, y, rx, ry, rho = a[:, 3], a[:, 4], a[:, 5], a[:, 6], a[:, 7]
    pj = json.load(open(d + "/problem/problem.json")) if False else None
    out = {"label": label, "n": int(n)}
    for c in (0, 1):
        m = cam == c
        if not m.any():
            continue
        w, h = x[m].max(), y[m].max()
        cx, cy = np.digitize(x[m], np.linspace(0, w + 1, grid + 1)[1:-1]), np.digitize(y[m], np.linspace(0, h + 1, grid + 1)[1:-1])
        print(f"cam{c}: n={m.sum()} mean rx {rx[m].mean():+.3f} ry {ry[m].mean():+.3f} px  rms {np.hypot(rx[m], ry[m]).std():.2f}")
        print("  mean rx by column (left..right) / row (top..bottom):")
        for r in range(grid):
            row = []
            for q in range(grid):
                mm = m.copy(); mm[m] = (cx == q) & (cy == r)
                row.append(f"{rx[mm].mean():+.3f}/{ry[mm].mean():+.3f} (n={mm.sum():6d})" if mm.sum() > 50 else "    -    ")
            print("   " + "  ".join(row))
        for hc in (0, 1):
            mm = m & (hcam == hc)
            if mm.sum() > 50:
                print(f"  hosted in cam{hc}: n={mm.sum()} mean rx {rx[mm].mean():+.3f} ry {ry[mm].mean():+.3f}")
        # near vs far
        for name, mm in (("near (rho>0.5, <2 m)", m & (rho > 0.5)), ("far (rho<0.1, >10 m)", m & (rho < 0.1))):
            if mm.sum() > 50:
                print(f"  {name}: n={mm.sum()} mean rx {rx[mm].mean():+.3f} ry {ry[mm].mean():+.3f}")
        out[f"cam{c}"] = {"mean_rx": float(rx[m].mean()), "mean_ry": float(ry[m].mean())}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
