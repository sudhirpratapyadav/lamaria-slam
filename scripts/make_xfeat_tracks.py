#!/usr/bin/env python3
"""Descriptor-matching front end: XFeat keypoints matched frame to frame (mutual nearest
neighbour in descriptor space, chained into tracks) and left to right (stereo), written as
Basalt external tracks (v3 F11): SEQ_DIR/tracks_<name>/<stamp>.bin with records
(int32 track id, int32 cam, float32 x, float32 y). Read by BASALT_TRACKS_DIR.

Tracks: a keypoint in frame t that mutually matches a keypoint of frame t-1 inherits its track
id, otherwise it starts a new one; the stereo match of a cam0 keypoint gives the cam1 record
with the same id. Sequential by nature (ids chain), one process per sequence.

Usage: make_xfeat_tracks.py SEQ_DIR [--top-k 1000] [--min-cossim 0.82] [--max-flow 80] [--threads 2]
Run with .venv-ml.
"""
import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("--name", default="xfeat")
    ap.add_argument("--top-k", type=int, default=1000)
    ap.add_argument("--min-cossim", type=float, default=0.82)
    ap.add_argument("--max-flow", type=float, default=80.0, help="px; a frame-to-frame match farther than this is not chained")
    ap.add_argument("--max-stereo-dy", type=float, default=0.0, help="px; 0 = no row check (images are not rectified)")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--xfeat", type=Path, default=Path(__file__).resolve().parent.parent / "third_party/accelerated_features")
    args = ap.parse_args()
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = str(args.threads)
    import cv2
    import torch
    cv2.setNumThreads(args.threads)
    torch.set_num_threads(args.threads)
    sys.path.insert(0, str(args.xfeat))
    from modules.xfeat import XFeat
    xf = XFeat(top_k=args.top_k)

    out = args.seq_dir / f"tracks_{args.name}"
    out.mkdir(exist_ok=True)
    rows = [l.split(",") for l in (args.seq_dir / "runner_input/stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    stats = open(out / "stats.csv", "w")
    w = csv.writer(stats)
    w.writerow(["stamp", "n_cam0", "n_chained", "n_stereo"])

    def feats(rel):
        img = cv2.imread(str(args.seq_dir / "runner_input" / rel), cv2.IMREAD_GRAYSCALE)
        with torch.no_grad():
            r = xf.detectAndCompute(torch.from_numpy(img)[None, None].float(), top_k=args.top_k)[0]
        return r["keypoints"].cpu().numpy(), r["descriptors"]

    prev_kp, prev_desc, prev_ids = None, None, None
    next_id = 0
    rec_t = np.dtype([("id", "<i4"), ("cam", "<i4"), ("x", "<f4"), ("y", "<f4")])
    for i, (_, left, right) in enumerate(rows):
        stamp = Path(left).stem
        kp0, d0 = feats(left)
        kp1, d1 = feats(right)
        ids = np.full(len(kp0), -1, np.int64)
        chained = 0
        if prev_kp is not None and len(kp0) and len(prev_kp):
            i_prev, i_cur = xf.match(prev_desc, d0, min_cossim=args.min_cossim)
            i_prev, i_cur = i_prev.cpu().numpy(), i_cur.cpu().numpy()
            ok = np.linalg.norm(prev_kp[i_prev] - kp0[i_cur], axis=1) <= args.max_flow
            ids[i_cur[ok]] = prev_ids[i_prev[ok]]
            chained = int(ok.sum())
        new = ids < 0
        ids[new] = np.arange(next_id, next_id + new.sum())
        next_id += int(new.sum())
        recs = [np.array([(int(t), 0, float(x), float(y)) for t, (x, y) in zip(ids, kp0)], rec_t)]
        n_stereo = 0
        if len(kp0) and len(kp1):
            j0, j1 = xf.match(d0, d1, min_cossim=args.min_cossim)
            j0, j1 = j0.cpu().numpy(), j1.cpu().numpy()
            if args.max_stereo_dy > 0:
                ok = np.abs(kp0[j0, 1] - kp1[j1, 1]) <= args.max_stereo_dy
                j0, j1 = j0[ok], j1[ok]
            recs.append(np.array([(int(ids[a]), 1, float(kp1[b, 0]), float(kp1[b, 1])) for a, b in zip(j0, j1)], rec_t))
            n_stereo = len(j0)
        np.concatenate(recs).tofile(out / f"{stamp}.bin")
        w.writerow([stamp, len(kp0), chained, n_stereo])
        prev_kp, prev_desc, prev_ids = kp0, d0, ids
        if i % 1000 == 0:
            stats.flush(); print(f"  {i}/{len(rows)} chained {chained} stereo {n_stereo}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
