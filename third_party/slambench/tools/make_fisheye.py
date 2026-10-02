"""Re-render a pinhole stereo recording through an ideal equidistant fisheye lens (r = f * theta).

  python -m slambench.tools.make_fisheye RECORDING CONFIG OUT_RECORDING OUT_CONFIG [--frames 300] [--focal-scale 0.85]

Purpose: test that an estimator handles a fisheye calibration (distortion_model: equidistant) end to end, before a real wide-angle camera
exists. The source images only cover their own field of view (about 87 degrees for a D455), so this proves the model and tracking
pipeline, not the benefit of a 140+ degree field of view. Pixels outside the source field of view are black.
"""
import argparse
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def fisheye_maps(src_K, src_dist, out_size, out_f, out_c=None):
    """Remap tables from an equidistant fisheye image (out_size = (w, h), focal out_f px) back into the source (pinhole + radtan) image."""
    w, h = out_size
    cx, cy = out_c or ((w - 1) / 2., (h - 1) / 2.)
    u, v = np.meshgrid(np.arange(w, dtype=np.float64), np.arange(h, dtype=np.float64))
    x, y = (u - cx) / out_f, (v - cy) / out_f
    r = np.hypot(x, y)                                    # equidistant: r = theta
    scale = np.where(r > 1e-12, np.sin(r) / np.maximum(r, 1e-12), 1.0)
    X, Y, Z = scale * x, scale * y, np.cos(r)
    valid = Z > 0.05
    pts = np.stack([X[valid] / Z[valid], Y[valid] / Z[valid], np.ones(valid.sum())], axis=-1).reshape(-1, 1, 3)
    pixels, _ = cv2.projectPoints(pts, np.zeros(3), np.zeros(3), src_K, np.asarray(src_dist, float))
    map_x = np.full((h, w), -1.0, np.float32)
    map_y = np.full((h, w), -1.0, np.float32)
    map_x[valid], map_y[valid] = pixels[:, 0, 0], pixels[:, 0, 1]
    return map_x, map_y


def convert(recording, config, out_recording, out_config, frames=0, focal_scale=0.85):
    sys.path.insert(0, str(ROOT / 'scripts'))
    from prepare_kimera import read_yaml, write_yaml
    recording, out_recording, out_config = Path(recording), Path(out_recording), Path(out_config)
    chain = read_yaml(Path(config) / 'imucam.yaml')
    maps, new_chain = {}, {}
    for cam in ('cam0', 'cam1'):
        c = chain[cam]
        fx, fy, cx, cy = c['intrinsics']
        w, h = c['resolution']
        K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.]])
        f = focal_scale * fx
        maps[cam] = fisheye_maps(K, c['distortion_coeffs'], (w, h), f)
        new_chain[cam] = {**c, 'intrinsics': [f, f, (w - 1) / 2., (h - 1) / 2.], 'distortion_model': 'equidistant',
                          'distortion_coeffs': [0.0, 0.0, 0.0, 0.0]}
    shutil.copytree(config, out_config, dirs_exist_ok=True)
    write_yaml(out_config / 'imucam.yaml', new_chain)
    rows = [l.split(',') for l in (recording / 'stereo.csv').read_text().splitlines() if l and not l.startswith('#')]
    if frames:
        rows = rows[:frames]
    for side in ('left', 'right'):
        (out_recording / side).mkdir(parents=True, exist_ok=True)
    for t, left, right in rows:
        for cam, name in (('cam0', left), ('cam1', right)):
            image = cv2.imread(str(recording / name), cv2.IMREAD_GRAYSCALE)
            out = cv2.remap(image, maps[cam][0], maps[cam][1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            cv2.imwrite(str(out_recording / name), out)
    (out_recording / 'stereo.csv').write_text('# timestamp,left,right\n' + '\n'.join(','.join(r) for r in rows) + '\n')
    last = float(rows[-1][0]) + 0.5
    with (recording / 'imu.csv').open() as src, (out_recording / 'imu.csv').open('w') as dst:
        for line in src:
            if line.startswith('#') or float(line.split(',')[0]) <= last:
                dst.write(line)
            else:
                break
    return len(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('recording', type=Path)
    ap.add_argument('config', type=Path)
    ap.add_argument('out_recording', type=Path)
    ap.add_argument('out_config', type=Path)
    ap.add_argument('--frames', type=int, default=0)
    ap.add_argument('--focal-scale', type=float, default=0.85, help='fisheye focal length as a fraction of the source focal length (smaller = wider)')
    args = ap.parse_args(argv)
    print(f'converted {convert(args.recording, args.config, args.out_recording, args.out_config, args.frames, args.focal_scale)} frames')
    return 0


if __name__ == '__main__':
    sys.exit(main())
