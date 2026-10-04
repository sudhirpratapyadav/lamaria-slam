#!/usr/bin/env python3
"""Fuse a forward and a backward (time-reversed, already mapped back to forward time)
trajectory of the same sequence into one non-causal estimate.

Both files are per-image submission files (timestamp_ns tx ty tz qx qy qz qw, world
frames gravity-aligned but with their own yaw and origin). The backward trajectory is
first brought into the forward frame with a yaw+translation alignment over the window
where the forward run is trusted most (its first --align-s seconds, after the backward
run's own tail has had time to converge); then, per pose, the two are blended with a
weight that moves linearly from the forward run (start) to the backward run (end):
positions as a weighted mean, orientations by slerp. The relative pose drift of each
run is thereby weighted by how far it has travelled from its own anchor.

Usage: fuse_bidirectional.py FORWARD.txt BACKWARD_FWDTIME.txt OUT.txt [--align-s 60] [--weight linear|hann]
"""
import argparse
import sys

import numpy as np
from scipy.spatial.transform import Rotation as R


def load(p):
    rows = [l.replace(",", " ").split() for l in open(p) if l.strip() and not l.startswith("#")]
    a = np.array(rows, dtype=float)
    return a[:, 0].astype(np.int64), a[:, 1:4], R.from_quat(a[:, 4:8])


def yaw_translation_align(p_src, r_src, p_dst, r_dst):
    """Rotation about z plus translation taking src onto dst (least squares on positions,
    yaw from the mean orientation difference about z)."""
    dyaw = []
    for a, b in zip(r_src, r_dst):
        d = (b * a.inv()).as_rotvec()
        dyaw.append(d[2])
    yaw = float(np.arctan2(np.mean(np.sin(dyaw)), np.mean(np.cos(dyaw))))
    Rz = R.from_rotvec([0, 0, yaw])
    t = (p_dst - Rz.apply(p_src)).mean(axis=0)
    return Rz, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("forward"); ap.add_argument("backward"); ap.add_argument("out")
    ap.add_argument("--align-s", type=float, default=60.0)
    ap.add_argument("--weight", default="linear", choices=["linear", "hann"])
    a = ap.parse_args()
    tf, pf, rf = load(a.forward)
    tb, pb, rb = load(a.backward)
    common, if_, ib = np.intersect1d(tf, tb, return_indices=True)
    if len(common) < 10:
        sys.exit("fewer than 10 common timestamps")
    pf, rf, pb, rb = pf[if_], rf[if_], pb[ib], rb[ib]
    t = (common - common[0]) * 1e-9
    win = t <= a.align_s
    Rz, tr = yaw_translation_align(pb[win], rb[win], pf[win], rf[win])
    pb = Rz.apply(pb) + tr
    rb = Rz * rb
    w = t / t[-1]
    if a.weight == "hann":
        w = 0.5 - 0.5 * np.cos(np.pi * w)
    p = (1 - w)[:, None] * pf + w[:, None] * pb
    # slerp per pose between rf and rb with weight w
    d = (rb * rf.inv()).as_rotvec()
    r = R.from_rotvec(d * w[:, None]) * rf
    q = r.as_quat()
    with open(a.out, "w") as fh:
        fh.write("# fused forward/backward: timestamp_ns tx ty tz qx qy qz qw\n")
        for ts, pp, qq in zip(common, p, q):
            fh.write(f"{ts} {pp[0]:.6f} {pp[1]:.6f} {pp[2]:.6f} {qq[0]:.8f} {qq[1]:.8f} {qq[2]:.8f} {qq[3]:.8f}\n")
    gap = np.linalg.norm(pf - pb, axis=1)
    print(f"{a.out}: {len(common)} poses, forward/backward gap after start alignment: median {np.median(gap):.2f} m, end {gap[-1]:.2f} m, yaw align {np.degrees(Rz.as_rotvec()[2]):.2f} deg")


if __name__ == "__main__":
    main()
