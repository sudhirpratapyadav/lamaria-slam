#!/usr/bin/env python3
"""Precompute learned keypoints per frame for Basalt's tracker seeding (v3 F10).

Detector: XFeat (accelerated_features, CPU). Output: SEQ_DIR/kp_<name>/cam0/<stamp>.bin with
float32 (x, y, score) triples in image pixels, sorted by score, plus stats.csv (count per frame).
Basalt reads them with BASALT_KP_DIR (frame_to_frame_optical_flow.h).

Usage: make_learned_keypoints.py SEQ_DIR [--top-k 500] [--workers 6] [--threads 1] [--xfeat PATH]
Run with .venv-ml. CPU: about 0.3 s per frame per worker at 640x480.
"""
import argparse
import csv
import os
import sys

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path

import cv2
import numpy as np

cv2.setNumThreads(1)
ARGS = None
MODEL = None


def init(args):
    global ARGS, MODEL
    ARGS = args
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = str(args.threads)
    cv2.setNumThreads(args.threads)
    sys.path.insert(0, str(args.xfeat))
    import torch
    torch.set_num_threads(args.threads)
    from modules.xfeat import XFeat
    MODEL = XFeat(top_k=args.top_k)


def work(item):
    ts, rel = item
    out = ARGS.out / f"{ts}.bin"
    if out.exists():
        return ts, -1
    img = cv2.imread(str(ARGS.seq_dir / "runner_input" / rel), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return ts, -2
    import torch
    torch.set_num_threads(ARGS.threads)
    with torch.no_grad():
        r = MODEL.detectAndCompute(torch.from_numpy(img)[None, None].float(), top_k=ARGS.top_k)[0]
    kp = r["keypoints"].cpu().numpy().astype(np.float32)
    sc = r["scores"].cpu().numpy().astype(np.float32)
    order = np.argsort(-sc)
    arr = np.concatenate([kp[order], sc[order, None]], 1).astype(np.float32)
    arr.tofile(out)
    return ts, len(arr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("--name", default="xfeat")
    ap.add_argument("--top-k", type=int, default=500)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--xfeat", type=Path, default=Path(__file__).resolve().parent.parent / "third_party/accelerated_features")
    args = ap.parse_args()
    args.out = args.seq_dir / f"kp_{args.name}" / "cam0"
    args.out.mkdir(parents=True, exist_ok=True)
    rows = [l.split(",") for l in (args.seq_dir / "runner_input/stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    items = [(Path(left).stem, left) for _, left, _ in rows]
    stats_path = args.out.parent / "stats.csv"
    done = set()
    if stats_path.exists():
        with open(stats_path) as f:
            done = {r[0] for r in csv.reader(f) if r and r[0] != "stamp"}
    todo = [it for it in items if it[0] not in done]
    print(f"{args.seq_dir.name}: {len(items)} frames, {len(todo)} to do", flush=True)
    with mp.get_context("spawn").Pool(args.workers, initializer=init, initargs=(args,)) as pool, open(stats_path, "a") as f:
        w = csv.writer(f)
        if not done:
            w.writerow(["stamp", "n_keypoints"])
        for i, (ts, n) in enumerate(pool.imap(work, todo, chunksize=8)):
            if n >= 0:
                w.writerow([ts, n])
            if i % 2000 == 0:
                f.flush(); print(f"  {i}/{len(todo)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
