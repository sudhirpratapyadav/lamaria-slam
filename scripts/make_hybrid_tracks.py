#!/usr/bin/env python3
"""Hybrid front end for Basalt's external-tracks interface (v3 F13): KLT patch tracking for
precision, XFeat descriptors only to re-associate tracks that KLT lost (the "mixed" idea:
robustness of description matching, precision of patch tracking).

Per frame: (1) every live track is continued by pyramidal KLT with a forward-backward check;
(2) every --redetect frames XFeat runs on cam0: its descriptors are matched against the stored
descriptors of tracks lost within the last --memory frames (mutual nearest neighbour, cosine
>= --min-cossim, position within --max-jump px of where the lost track was last seen); a match
revives the old id at the new (KLT-refined) position; (3) new tracks start on FAST corners in
empty grid cells (like Basalt), each new or revived track gets its XFeat descriptor from the
nearest XFeat keypoint within --desc-radius px (if any); (4) stereo: KLT cam0 -> cam1 with a
backward check. Output records (int32 id, int32 cam, float x, float y) per frame.

Usage: make_hybrid_tracks.py SEQ_DIR [--name hybrid] [--redetect 5] [--memory 60] [--threads 2]
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
    ap.add_argument("--name", default="hybrid")
    ap.add_argument("--grid", type=int, default=50)
    ap.add_argument("--fast-thr", type=int, default=5, help="lowest adaptive FAST threshold (Basalt: 5)")
    ap.add_argument("--redetect", type=int, default=5)
    ap.add_argument("--memory", type=int, default=60, help="frames a lost track stays revivable")
    ap.add_argument("--max-jump", type=float, default=60.0)
    ap.add_argument("--min-cossim", type=float, default=0.85)
    ap.add_argument("--desc-radius", type=float, default=4.0)
    ap.add_argument("--fb-err", type=float, default=1.0)
    ap.add_argument("--top-k", type=int, default=1000)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--no-revive", action="store_true", help="ablation: plain KLT + FAST, no descriptors")
    ap.add_argument("--xfeat", type=Path, default=Path(__file__).resolve().parent.parent / "third_party/accelerated_features")
    args = ap.parse_args()
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = str(args.threads)
    import cv2
    import torch
    cv2.setNumThreads(args.threads)
    torch.set_num_threads(args.threads)
    xf = None
    if not args.no_revive:
        sys.path.insert(0, str(args.xfeat))
        from modules.xfeat import XFeat
        xf = XFeat(top_k=args.top_k)

    out = args.seq_dir / f"tracks_{args.name}"
    out.mkdir(exist_ok=True)
    rows = [l.split(",") for l in (args.seq_dir / "runner_input/stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    stats = open(out / "stats.csv", "w")
    w = csv.writer(stats)
    w.writerow(["stamp", "n_tracks", "n_continued", "n_revived", "n_new", "n_stereo"])
    rec_t = np.dtype([("id", "<i4"), ("cam", "<i4"), ("x", "<f4"), ("y", "<f4")])
    lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    fast = cv2.FastFeatureDetector_create(threshold=args.fast_thr)

    def klt(img0, img1, pts):
        if len(pts) == 0:
            return np.zeros((0, 2), np.float32), np.zeros(0, bool)
        p0 = pts.astype(np.float32).reshape(-1, 1, 2)
        p1, st, _ = cv2.calcOpticalFlowPyrLK(img0, img1, p0, None, **lk)
        p0b, st2, _ = cv2.calcOpticalFlowPyrLK(img1, img0, p1, None, **lk)
        ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm(p0b[:, 0] - p0[:, 0], axis=1) <= args.fb_err)
        h, wd = img1.shape
        q = p1[:, 0]
        ok &= (q[:, 0] >= 19) & (q[:, 1] >= 19) & (q[:, 0] < wd - 19) & (q[:, 1] < h - 19)
        return q, ok

    prev0 = None
    live = {}        # id -> (x, y)
    desc = {}        # id -> descriptor (torch, normalised)
    lost = {}        # id -> (frame, x, y) when lost
    next_id = 0
    for i, (_, left, right) in enumerate(rows):
        stamp = Path(left).stem
        img0 = cv2.imread(str(args.seq_dir / "runner_input" / left), cv2.IMREAD_GRAYSCALE)
        img1 = cv2.imread(str(args.seq_dir / "runner_input" / right), cv2.IMREAD_GRAYSCALE)
        if img1.shape != img0.shape:  # the undistorted cam1 frames are a few pixels smaller; pad (coordinates unchanged)
            pad = np.zeros_like(img0); h1, w1 = img1.shape; pad[:min(h1, pad.shape[0]), :min(w1, pad.shape[1])] = img1[:pad.shape[0], :pad.shape[1]]; img1 = pad
        n_cont = n_rev = n_new = 0
        # 1. continue live tracks
        if prev0 is not None and live:
            ids = list(live.keys())
            q, ok = klt(prev0, img0, np.array([live[k] for k in ids]))
            new_live = {}
            for k, pt, good in zip(ids, q, ok):
                if good:
                    new_live[k] = (float(pt[0]), float(pt[1]))
                else:
                    lost[k] = (i, *live[k])
            live = new_live
            n_cont = len(live)
        # 2. re-association and descriptors
        kp = dsc = None
        if xf is not None and (i % args.redetect == 0):
            with torch.no_grad():
                r = xf.detectAndCompute(torch.from_numpy(img0)[None, None].float(), top_k=args.top_k)[0]
            kp = r["keypoints"].cpu().numpy()
            dsc = r["descriptors"]
            cand = [k for k, (f, _, _) in lost.items() if i - f <= args.memory and k in desc]
            if cand and len(kp):
                d_lost = torch.stack([desc[k] for k in cand])
                i_l, i_k = xf.match(d_lost, dsc, min_cossim=args.min_cossim)
                i_l, i_k = i_l.cpu().numpy(), i_k.cpu().numpy()
                occupied = np.array(list(live.values())) if live else np.zeros((0, 2))
                for a, b in zip(i_l, i_k):
                    k = cand[a]
                    lx, ly = lost[k][1], lost[k][2]
                    x, y = kp[b]
                    if np.hypot(x - lx, y - ly) > args.max_jump:
                        continue
                    if len(occupied) and np.min(np.hypot(occupied[:, 0] - x, occupied[:, 1] - y)) < 5:
                        continue
                    live[k] = (float(x), float(y))
                    desc[k] = dsc[b]
                    del lost[k]
                    n_rev += 1
            for k in [k for k, (f, _, _) in lost.items() if i - f > args.memory]:
                lost.pop(k); desc.pop(k, None)
        # 3. new tracks on FAST corners in empty cells
        g = args.grid
        occ = set()
        for (x, y) in live.values():
            occ.add((int(x // g), int(y // g)))
        # adaptive threshold per cell like Basalt: 40, 20, 10, 5; one corner per empty cell
        for thr in (40, 20, 10, 5):
            if thr < args.fast_thr:
                break
            fast.setThreshold(thr)
            corners = sorted(fast.detect(img0, None), key=lambda c: -c.response)
            for c in corners:
                x, y = c.pt
                cell = (int(x // g), int(y // g))
                if cell in occ or x < 19 or y < 19 or x >= img0.shape[1] - 19 or y >= img0.shape[0] - 19:
                    continue
                occ.add(cell)
                live[next_id] = (float(x), float(y))
                if kp is not None and len(kp):
                    d = np.hypot(kp[:, 0] - x, kp[:, 1] - y)
                    j = int(np.argmin(d))
                    if d[j] <= args.desc_radius:
                        desc[next_id] = dsc[j]
                next_id += 1
                n_new += 1
        if False:
            x = y = 0
            live[next_id] = (float(x), float(y))
            if kp is not None and len(kp):
                d = np.hypot(kp[:, 0] - x, kp[:, 1] - y)
                j = int(np.argmin(d))
                if d[j] <= args.desc_radius:
                    desc[next_id] = dsc[j]
            next_id += 1
            n_new += 1
        # refresh descriptors of live tracks when a detection is available
        if kp is not None and len(kp) and live:
            ids = list(live.keys())
            pts = np.array([live[k] for k in ids])
            for k, (x, y) in zip(ids, pts):
                d = np.hypot(kp[:, 0] - x, kp[:, 1] - y)
                j = int(np.argmin(d))
                if d[j] <= args.desc_radius:
                    desc[k] = dsc[j]
        # 4. stereo
        ids = list(live.keys())
        pts = np.array([live[k] for k in ids]) if ids else np.zeros((0, 2))
        q1, ok1 = klt(img0, img1, pts)
        recs = [np.array([(k, 0, x, y) for k, (x, y) in zip(ids, pts)], rec_t)]
        recs.append(np.array([(k, 1, float(p[0]), float(p[1])) for k, p, good in zip(ids, q1, ok1) if good], rec_t))
        np.concatenate(recs).tofile(out / f"{stamp}.bin")
        w.writerow([stamp, len(live), n_cont, n_rev, n_new, int(ok1.sum())])
        prev0 = img0
        if i % 1000 == 0:
            stats.flush(); print(f"  {i}/{len(rows)} tracks {len(live)} continued {n_cont} revived {n_rev} new {n_new} stereo {int(ok1.sum())}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
