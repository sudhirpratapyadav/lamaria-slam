#!/usr/bin/env python3
"""Rewrite the fisheye validity masks of a fisheye runner input so that rays beyond
--max-theta degrees from the optical axis are masked too (255 = ignore).
Usage: fisheye_mask_theta.py SEQ_DIR_WITH_RAW_DATA FISHEYE_RUNNER_INPUT --max-theta 65
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
from projectaria_tools.core import data_provider
LABELS = {0: "camera-slam-left", 1: "camera-slam-right"}
ap = argparse.ArgumentParser(); ap.add_argument("seq_dir", type=Path); ap.add_argument("runner_input", type=Path); ap.add_argument("--max-theta", type=float, default=65.0)
a = ap.parse_args()
vrs = next(iter(a.seq_dir.glob("raw_data/*.vrs")))
dc = data_provider.create_vrs_data_provider(str(vrs)).get_device_calibration()
for c, label in LABELS.items():
    calib = dc.get_camera_calib(label); w, h = calib.get_image_size()
    m = np.full((h, w), 255, dtype=np.uint8); lim = np.cos(np.radians(a.max_theta))
    for y in range(h):
        for x in range(w):
            ray = calib.unproject(np.array([x, y], dtype=float))
            if ray is not None and ray[2] / np.linalg.norm(ray) >= lim:
                m[y, x] = 0
    Image.fromarray(m).save(a.runner_input / f"mask{c}.png")
    print(f"cam{c}: masked fraction {(m > 0).mean():.3f} at theta <= {a.max_theta} deg")
