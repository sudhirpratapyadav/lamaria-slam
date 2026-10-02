#!/usr/bin/env python3
"""Propagate Basalt mapper keyframe poses (after global BA) to every VIO frame.

For a VIO frame at time t with pose V(t) and the nearest-in-time keyframe k with VIO
pose V(k) and mapper pose M(k): out(t) = M(k) * inv(V(k)) * V(t). Between two
keyframes the correction is taken from the nearer one (no interpolation), which keeps
the VIO's local motion intact and moves whole segments by the BA correction.

Usage: basalt_propagate_keyframes.py VIO_TUM MAPPER_TUM OUT_TUM [--max-dt 0.5]
Both inputs are TUM (seconds, IMU pose). Keyframe times must match VIO times.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R


def load(path):
    rows = [l.split() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith("#")]
    a = np.array([[float(v) for v in r[:8]] for r in rows])
    return a


def T(row):
    M = np.eye(4)
    M[:3, :3] = R.from_quat(row[4:8]).as_matrix()
    M[:3, 3] = row[1:4]
    return M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vio", type=Path)
    ap.add_argument("mapper", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--max-dt", type=float, default=0.5, help="max time distance (s) from a frame to its keyframe")
    args = ap.parse_args()
    vio, kf = load(args.vio), load(args.mapper)
    if len(kf) < 2:
        sys.exit("mapper trajectory has fewer than 2 keyframes")
    tv, tk = vio[:, 0], kf[:, 0]
    # match keyframes to VIO frames by time (exact or nearest within 2 ms)
    idx = np.searchsorted(tv, tk)
    kf_vio_idx = []
    for i, t in zip(idx, tk):
        c = [j for j in (i - 1, i) if 0 <= j < len(tv)]
        j = min(c, key=lambda j: abs(tv[j] - t))
        kf_vio_idx.append(j if abs(tv[j] - t) < 2e-3 else -1)
    kf_vio_idx = np.array(kf_vio_idx)
    good = kf_vio_idx >= 0
    kf, kf_vio_idx, tk = kf[good], kf_vio_idx[good], tk[good]
    corr = [T(kf[i]) @ np.linalg.inv(T(vio[kf_vio_idx[i]])) for i in range(len(kf))]
    n_far = 0
    with open(args.out, "w") as f:
        f.write("# timestamp tx ty tz qx qy qz qw; IMU frame; basalt mapper keyframes propagated to all VIO frames\n")
        for row in vio:
            i = int(np.argmin(np.abs(tk - row[0])))
            if abs(tk[i] - row[0]) > args.max_dt:
                n_far += 1
            M = corr[i] @ T(row)
            q = R.from_matrix(M[:3, :3]).as_quat()
            f.write(f"{row[0]:.9f} " + " ".join(f"{v:.9f}" for v in M[:3, 3]) + " " + " ".join(f"{v:.9f}" for v in q) + "\n")
    print(f"propagated {len(vio)} frames from {len(kf)} keyframes ({int((~good).sum())} keyframes unmatched, {n_far} frames farther than {args.max_dt} s from a keyframe)")


if __name__ == "__main__":
    main()
