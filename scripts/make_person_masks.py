#!/usr/bin/env python3
"""Precompute per-frame masks of people and the wearer's body with YOLO11n-seg (v3 F02).

The Aria cameras are mounted sideways: frames are rotated 90 degrees clockwise to upright
before detection (X03: that is where the detector works), and the mask is rotated back.
Masks are dilated by --dilate px. Output: SEQ_DIR/masks_person/cam0/<stamp>.png (255 = masked),
plus a stats csv (per frame: n_persons, masked fraction).

Usage: make_person_masks.py SEQ_DIR [--conf 0.25] [--dilate 12] [--classes person] [--workers 4]
Run with .venv-ml. CPU: about 0.13 s per frame per worker.
"""
import argparse
import csv
import os

# one worker = one core; must be set before numpy/torch/cv2 are imported anywhere
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
    # one worker = one core: without this every worker spawns a full thread pool and the box thrashes
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = str(args.threads)
    cv2.setNumThreads(args.threads)
    import torch
    torch.set_num_threads(args.threads)
    from ultralytics import YOLO
    MODEL = YOLO(args.model)


def work(item):
    ts, rel = item
    out = ARGS.out / f"{ts}.png"
    if out.exists():
        return ts, -1, -1.0
    img = cv2.imread(str(ARGS.seq_dir / "runner_input" / rel), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return ts, -2, 0.0
    up = cv2.rotate(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), cv2.ROTATE_90_CLOCKWISE)
    import torch
    torch.set_num_threads(ARGS.threads)  # ultralytics resets this to 8 on its own; 8 workers x 8 threads thrashed the box
    r = MODEL.predict(up, imgsz=640, conf=ARGS.conf, classes=ARGS.class_ids, verbose=False, device="cpu")[0]
    mask = np.zeros(up.shape[:2], np.uint8)
    n = 0
    if r.masks is not None and len(r.masks.data):
        m = r.masks.data.cpu().numpy().max(0)
        m = cv2.resize(m, (up.shape[1], up.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask[m > 0.5] = 255
        n = int(len(r.masks.data))
    if ARGS.dilate > 0 and n:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ARGS.dilate + 1, 2 * ARGS.dilate + 1))
        mask = cv2.dilate(mask, k)
    mask = cv2.rotate(mask, cv2.ROTATE_90_COUNTERCLOCKWISE)
    cv2.imwrite(str(out), mask)
    return ts, n, float((mask > 0).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--dilate", type=int, default=12)
    ap.add_argument("--classes", default="person")
    ap.add_argument("--model", default="yolo11n-seg.pt")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--threads", type=int, default=1, help="torch/cv threads per worker")
    args = ap.parse_args()
    args.seq_dir = args.seq_dir.resolve()
    args.out = args.seq_dir / "masks_person" / "cam0"
    args.out.mkdir(parents=True, exist_ok=True)
    from ultralytics import YOLO
    names = YOLO(args.model).names
    wanted = set(args.classes.split(","))
    args.class_ids = [i for i, n in names.items() if n in wanted]
    rows = [l.split(",") for l in (args.seq_dir / "runner_input/stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    items = [(Path(left).stem, left) for _, left, _ in rows]
    stats_path = args.seq_dir / "masks_person" / "stats.csv"
    done = {}
    if stats_path.exists():
        with open(stats_path) as f:
            for r in csv.reader(f):
                if r and r[0] != "stamp":
                    done[r[0]] = r
    todo = [it for it in items if it[0] not in done]
    print(f"{args.seq_dir.name}: {len(items)} frames, {len(todo)} to do, classes {args.class_ids}")
    with mp.get_context("spawn").Pool(args.workers, initializer=init, initargs=(args,)) as pool, open(stats_path, "a") as f:
        w = csv.writer(f)
        if not done:
            w.writerow(["stamp", "n_persons", "masked_fraction"])
        for i, (ts, n, frac) in enumerate(pool.imap(work, todo, chunksize=8)):
            if n >= 0:
                w.writerow([ts, n, f"{frac:.4f}"])
            if i % 2000 == 0:
                f.flush(); print(f"  {i}/{len(todo)}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
