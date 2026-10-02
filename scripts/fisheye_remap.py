#!/usr/bin/env python3
"""Resample raw Aria fisheye frames to an ideal equidistant image (r = f * theta) of
the same size, so that OpenVINS's "equidistant" model with zero coefficients is
exact by construction (the Aria lens has tangential and thin-prism terms that a
Kannala-Brandt fit leaves at up to 1.4 px on some cameras). Keeps the full field
of view, unlike the pinhole ASL images.

Two stages so each runs where its library lives:
  --make-maps   (projectaria_tools): writes map_cam{0,1}.npy (float32 x/y source
                coordinates) + the equidistant calibration JSON
  --remap       (OpenCV): writes the resampled PNGs for every frame listed in
                stereo.csv into <out>/runner_input, plus masks and copied csvs

Usage:
  fisheye_remap.py --make-maps SEQ_DIR_WITH_RAW ARIA_CALIB_JSON FISHEYE_INPUT_DIR OUT_SEQ_DIR [--theta-max 78]
  fisheye_remap.py --remap FISHEYE_INPUT_DIR OUT_SEQ_DIR
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

LABELS = {0: "camera-slam-left", 1: "camera-slam-right"}


def make_maps(seq_dir, aria_json, fisheye_in, out_seq, theta_max):
    from projectaria_tools.core import data_provider
    vrs = next(iter(Path(seq_dir).glob("raw_data/*.vrs")))
    dc = data_provider.create_vrs_data_provider(str(vrs)).get_device_calibration()
    aria = json.loads(Path(aria_json).read_text())
    seq = Path(seq_dir).name
    out = Path(out_seq); (out / "runner_input").mkdir(parents=True, exist_ok=True)
    calib_out = {"imu0": aria["imu0"]}
    for c, label in LABELS.items():
        calib = dc.get_camera_calib(label)
        w, h = calib.get_image_size(); f = float(calib.get_focal_lengths()[0]); cx, cy = [float(v) for v in calib.get_principal_point()]
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
        dx, dy = xs - cx, ys - cy
        r = np.hypot(dx, dy); theta = r / f
        phi = np.arctan2(dy, dx)
        valid = theta <= np.radians(theta_max)
        mapx = np.full((h, w), -1, dtype=np.float32); mapy = np.full((h, w), -1, dtype=np.float32)
        mask = np.full((h, w), 255, dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                if not valid[y, x]:
                    continue
                th = theta[y, x]; ray = np.array([np.sin(th) * np.cos(phi[y, x]), np.sin(th) * np.sin(phi[y, x]), np.cos(th)])
                px = calib.project(ray)
                if px is None or not (0 <= px[0] < w - 1 and 0 <= px[1] < h - 1):
                    continue
                mapx[y, x], mapy[y, x] = px[0], px[1]; mask[y, x] = 0
        np.save(out / "runner_input" / f"map_cam{c}.npy", np.stack([mapx, mapy]))
        from PIL import Image
        Image.fromarray(mask).save(out / "runner_input" / f"mask{c}.png")
        calib_out[f"cam{c}"] = {"model": "EQUIDISTANT", "params": [f, f, cx, cy, 0.0, 0.0, 0.0, 0.0], "resolution": {"width": int(w), "height": int(h)},
                                "T_b_s": aria[f"cam{c}"]["T_b_s"], "note": f"ideal equidistant resample of the Aria lens, theta <= {theta_max} deg"}
        print(f"cam{c}: f {f:.3f} pp ({cx:.3f},{cy:.3f}) valid fraction {(mask == 0).mean():.3f}")
    (out / "pinhole_calibrations").mkdir(exist_ok=True)
    (out / "pinhole_calibrations" / f"{seq}.json").write_text(json.dumps(calib_out, indent=2) + "\n")
    for name in ("ground_truth", "aria_calibrations"):
        link = out / name
        if not link.exists():
            os.symlink(os.path.relpath((Path(seq_dir) / name).resolve(), out), link)
    for name in ("imu.csv", "stereo.csv", "image_timestamps_ns.txt"):
        shutil.copy(Path(fisheye_in) / "runner_input" / name, out / "runner_input" / name)
    print("maps and calibration written to", out)


def remap(fisheye_in, out_seq):
    import cv2
    src = Path(fisheye_in) / "runner_input"; dst = Path(out_seq) / "runner_input"
    maps = {c: np.load(dst / f"map_cam{c}.npy") for c in (0, 1)}
    rows = [l.split(",") for l in (dst / "stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    for c in (0, 1):
        (dst / f"cam{c}" / "data").mkdir(parents=True, exist_ok=True)
    n = 0
    for r in rows:
        for c, rel in ((0, r[1]), (1, r[2])):
            o = dst / rel
            if o.exists():
                continue
            img = cv2.imread(str(src / rel), cv2.IMREAD_GRAYSCALE)
            res = cv2.remap(img, maps[c][0], maps[c][1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            cv2.imwrite(str(o), res, [cv2.IMWRITE_PNG_COMPRESSION, 1])
        n += 1
        if n % 1000 == 0:
            print(f"{n}/{len(rows)}", flush=True)
    print(f"remapped {n} stereo pairs into {dst}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-maps", action="store_true"); ap.add_argument("--remap", action="store_true")
    ap.add_argument("args", nargs="+"); ap.add_argument("--theta-max", type=float, default=78.0)
    a = ap.parse_args()
    if a.make_maps:
        make_maps(*a.args[:4], a.theta_max)
    elif a.remap:
        remap(*a.args[:2])
    else:
        sys.exit("choose --make-maps or --remap")


if __name__ == "__main__":
    main()
