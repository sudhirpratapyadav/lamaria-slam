#!/usr/bin/env python3
"""Per-window context for a sequence: what the input looked like when the estimator drifted.

For each window of --window seconds (clock relative to the pGT start, same bins as
drift_analysis.py --dump): mean image brightness and blur (Laplacian variance, left image,
one frame per second), pGT speed and turning rate, gyro norm, and the OpenVINS feature counts
(from a runner's frame_times.csv) if given. Joined with any --drift csv files (label=path),
printing their yaw change per window (deg) and local scale.

Usage: sequence_timeline.py SEQ_DIR [--window 60] [--frame-times CSV] [--drift name=CSV ...] [--out CSV]
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import laplace
from scipy.spatial.transform import Rotation as R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("--window", type=float, default=60.0)
    ap.add_argument("--frame-times", type=Path)
    ap.add_argument("--drift", action="append", default=[])
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    seq = args.seq_dir.name
    gt = np.loadtxt(next(args.seq_dir.glob("ground_truth/**/pGT/*.txt")), comments="#")
    t0 = gt[0, 0] / 1e9
    tg = gt[:, 0] / 1e9 - t0
    W = args.window
    nbins = int(np.ceil(tg[-1] / W))
    mid = (np.arange(nbins) + 0.5) * W
    # pGT speed and turning rate
    speed = np.linalg.norm(np.diff(gt[:, 1:4], axis=0), axis=1) / np.diff(tg)
    rots = R.from_quat(gt[:, 4:8])
    rel = (rots[:-1].inv() * rots[1:]).magnitude()
    turn = np.degrees(rel) / np.diff(tg)
    b = np.clip((tg[:-1] // W).astype(int), 0, nbins - 1)
    gt_speed = np.array([speed[b == k].mean() if (b == k).any() else np.nan for k in range(nbins)])
    gt_turn = np.array([turn[b == k].mean() if (b == k).any() else np.nan for k in range(nbins)])
    # gyro
    imu = np.loadtxt(args.seq_dir / "runner_input" / "imu.csv", delimiter=",", comments="#")
    ti = imu[:, 0] - t0  # imu.csv is already in seconds
    gyro = np.linalg.norm(imu[:, 1:4], axis=1)
    bi = np.clip((ti // W).astype(int), 0, nbins - 1)
    gyro_mean = np.array([np.degrees(gyro[bi == k]).mean() if (bi == k).any() else np.nan for k in range(nbins)])
    # images, one per second
    stereo = [l.split(",") for l in (args.seq_dir / "runner_input" / "stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    bright, blur = np.full(nbins, np.nan), np.full(nbins, np.nan)
    acc = {}
    last = -1e9
    for ts, left, _ in stereo:
        t = float(ts) - t0
        if t - last < 1.0 or t < 0:
            continue
        last = t
        try:
            img = np.asarray(Image.open(args.seq_dir / "runner_input" / left).convert("L"), dtype=np.float64)
        except OSError:
            continue
        k = min(int(t // W), nbins - 1)
        acc.setdefault(k, []).append((img.mean(), laplace(img).var()))
    for k, v in acc.items():
        v = np.array(v); bright[k], blur[k] = v[:, 0].mean(), np.median(v[:, 1])
    cols = {"t_mid_s": mid, "gt_speed_mps": gt_speed, "gt_turn_dps": gt_turn, "gyro_dps": gyro_mean, "brightness": bright, "blur_lapvar": blur}
    if args.frame_times:
        ft = np.loadtxt(args.frame_times, delimiter=",", comments="#")
        tf = ft[:, 0] - t0
        bf = np.clip((tf // W).astype(int), 0, nbins - 1)
        cols["ov_msckf_pts"] = np.array([ft[bf == k, 3].mean() if (bf == k).any() else np.nan for k in range(nbins)])
        cols["ov_slam_pts"] = np.array([ft[bf == k, 4].mean() if (bf == k).any() else np.nan for k in range(nbins)])
    for d in args.drift:
        name, path = d.split("=", 1)
        a = np.loadtxt(path, delimiter=",", skiprows=1)
        k = np.clip((a[:, 0] // W).astype(int), 0, nbins - 1)
        yaw = np.full(nbins, np.nan); sc = np.full(nbins, np.nan)
        yaw[k], sc[k] = a[:, 2], a[:, 1]
        dy = np.full(nbins, np.nan); dy[1:] = np.diff(yaw)
        cols[f"{name}_dyaw_deg"], cols[f"{name}_scale"] = dy, sc
    names = list(cols)
    M = np.c_[tuple(cols[n] for n in names)]
    if args.out:
        np.savetxt(args.out, M, fmt="%.3f", delimiter=",", header=",".join(names), comments="")
    print(seq)
    print(" ".join(f"{n[:14]:>14}" for n in names))
    for row in M:
        print(" ".join(f"{v:14.3f}" for v in row))


if __name__ == "__main__":
    main()
