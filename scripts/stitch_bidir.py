#!/usr/bin/env python3
"""Merge a forward trajectory with a time-reversed pass over the sequence start.

Inputs are TUM files in seconds (IMU pose in world, xyzw). The backward run was
produced on reversed time t' = pivot2 - t, so its timestamps are mapped back
first. On the overlap window [t_end - overlap, t_end] both runs are converged;
a Sim3 (Umeyama) from backward to forward positions is estimated there, the
backward segment is transformed, and the output takes the backward poses before
the crossover time and the forward poses after it.

Usage: stitch_bidir.py forward.tum backward.tum reverse_info.json out.tum [--overlap 40] [--crossover 20]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R


def load_tum(path):
    rows = [l.split() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith("#")]
    a = np.array([[float(v) for v in r] for r in rows])
    return a[:, 0], a[:, 1:4], a[:, 4:8]


def umeyama(src, dst):
    """Sim3 s, R, t with dst ~ s * R @ src + t."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    cov = xd.T @ xs / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    Rm = U @ S @ Vt
    s = np.trace(np.diag(D) @ S) / (xs ** 2).sum() * len(src)
    t = mu_d - s * Rm @ mu_s
    return s, Rm, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("forward", type=Path)
    ap.add_argument("backward", type=Path)
    ap.add_argument("reverse_info", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--overlap", type=float, default=40.0, help="seconds before t_end used to align the two runs")
    ap.add_argument("--crossover", type=float, default=20.0, help="seconds before t_end where the output switches to forward")
    args = ap.parse_args()
    info = json.loads(args.reverse_info.read_text())
    t_end = info["t0"] + info["window_s"]

    tf, pf, qf = load_tum(args.forward)
    tb_rev, pb, qb = load_tum(args.backward)
    tb = info["pivot2"] - tb_rev
    order = np.argsort(tb)
    tb, pb, qb = tb[order], pb[order], qb[order]

    # overlap: forward poses matched to backward poses by timestamp (same image clock, exact)
    lo = t_end - args.overlap
    mb = (tb >= lo) & (tb <= t_end)
    idx_f = {round(t, 6): i for i, t in enumerate(tf)}
    pairs = [(i, idx_f[round(t, 6)]) for i, t in zip(np.where(mb)[0], tb[mb]) if round(t, 6) in idx_f]
    if len(pairs) < 50:
        sys.exit(f"overlap too small: {len(pairs)} matched poses")
    ib, i_f = zip(*pairs)
    s, Rm, t = umeyama(pb[list(ib)], pf[list(i_f)])
    resid = np.linalg.norm((s * (Rm @ pb[list(ib)].T).T + t) - pf[list(i_f)], axis=1)

    pb2 = s * (Rm @ pb.T).T + t
    qb2 = (R.from_matrix(Rm) * R.from_quat(qb)).as_quat()

    cross = t_end - args.crossover
    keep_b = tb < cross
    keep_f = tf >= cross
    T = np.concatenate([tb[keep_b], tf[keep_f]])
    P = np.concatenate([pb2[keep_b], pf[keep_f]])
    Q = np.concatenate([qb2[keep_b], qf[keep_f]])
    order = np.argsort(T)
    with open(args.out, "w") as f:
        f.write(f"# bidirectional stitch: backward before {cross:.3f}, forward after; sim3 scale {s:.5f}\n")
        for i in order:
            f.write(f"{T[i]:.9f} " + " ".join(f"{v:.9f}" for v in P[i]) + " " + " ".join(f"{v:.9f}" for v in Q[i]) + "\n")
    print(json.dumps({"overlap_pairs": len(pairs), "stitch_scale": s, "overlap_rmse_m": float(np.sqrt((resid ** 2).mean())),
                      "backward_poses_used": int(keep_b.sum()), "forward_poses_used": int(keep_f.sum()),
                      "backward_first_t": float(tb[0]), "forward_first_t": float(tf[0])}))


if __name__ == "__main__":
    main()
