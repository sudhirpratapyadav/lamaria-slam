#!/usr/bin/env python3
"""Count detectable keypoints per time bin on a sequence: FAST (Basalt-style adaptive threshold,
per grid cell) against XFeat (learned, CPU). Diagnostic for v3: does a learned detector find
points where FAST finds none (dark, low texture, overexposed stretches)?

Usage: keypoint_density.py SEQ_DIR [--window 60] [--step 2.0] [--grid 50] [--xfeat PATH]
  --xfeat: path to the accelerated_features checkout (default third_party/accelerated_features)
Prints one row per window: t_mid, frames sampled, FAST corners (mean per frame, detected in
grid cells with threshold 40 down to 5 like Basalt), XFeat keypoints with score > 0.1 (mean).
Run with .venv-ml (torch CPU).
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def fast_grid(img, grid):
    """Basalt-style detection: per grid cell, lower the FAST threshold from 40 until a corner appears."""
    h, w = img.shape
    n = 0
    for y in range(0, h - grid + 1, grid):
        for x in range(0, w - grid + 1, grid):
            sub = img[y:y + grid, x:x + grid]
            thr = 40
            while thr >= 5:
                kps = cv2.FastFeatureDetector_create(thr).detect(sub)
                if kps:
                    n += 1
                    break
                thr //= 2
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("--window", type=float, default=60.0)
    ap.add_argument("--step", type=float, default=2.0, help="seconds between sampled frames")
    ap.add_argument("--grid", type=int, default=50)
    ap.add_argument("--xfeat", type=Path, default=Path(__file__).resolve().parent.parent / "third_party/accelerated_features")
    ap.add_argument("--top-k", type=int, default=1000)
    args = ap.parse_args()
    sys.path.insert(0, str(args.xfeat))
    import torch
    from modules.xfeat import XFeat
    xfeat = XFeat(top_k=args.top_k)
    gt = next(args.seq_dir.glob("ground_truth/**/pGT/*.txt"), None)
    t0 = float(open(gt).readline().split()[0]) / 1e9 if gt else None
    rows = [l.split(",") for l in (args.seq_dir / "runner_input/stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    if t0 is None:
        t0 = float(rows[0][0])
    acc = {}
    last = -1e9
    for ts, left, _ in rows:
        t = float(ts) - t0
        if t < 0 or t - last < args.step:
            continue
        last = t
        img = cv2.imread(str(args.seq_dir / "runner_input" / left), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        n_fast = fast_grid(img, args.grid)
        with torch.no_grad():
            out = xfeat.detectAndCompute(torch.from_numpy(img)[None, None].float(), top_k=args.top_k)[0]
        n_x = int((out["scores"] > 0.1).sum()) if "scores" in out else len(out["keypoints"])
        k = int(t // args.window)
        acc.setdefault(k, []).append((n_fast, n_x, img.mean()))
    print(f"{'t_mid_s':>8} {'frames':>6} {'fast_cells':>10} {'xfeat>0.1':>10} {'bright':>7}")
    for k in sorted(acc):
        a = np.array(acc[k])
        print(f"{(k + 0.5) * args.window:8.0f} {len(a):6d} {a[:, 0].mean():10.1f} {a[:, 1].mean():10.1f} {a[:, 2].mean():7.1f}")


if __name__ == "__main__":
    main()
