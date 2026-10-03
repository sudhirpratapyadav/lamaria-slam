#!/usr/bin/env python3
"""Robust Basalt driver: run basalt_vio, detect divergence in its output, restart it
from just before the divergence on a trimmed input, and stitch the segments onto
each other (the same idea as the OpenVINS runner's re-initialisation, done at
script level because Basalt is a binary release here).

Divergence = per-frame speed above --max-speed (m/s) or a per-frame jump above
--max-jump (m). On detection at frame index f (into the segment), poses up to
f - back are kept, and the next segment starts at f - back; its first pose is
mapped onto the last kept pose (SE3 composition), as in the runner.

Env: BASALT_VIO (binary, default ~/.local/bin/basalt_vio), BASALT_CLAHE (source build only)
Usage: basalt_segments.py SEQ_DIR OUT_DIR --calib CALIB_JSON --config CONFIG_JSON
       [--threads 3] [--max-speed 6] [--max-jump 1] [--back 20] [--max-segments 12] [--skip-frames 0]
Writes OUT_DIR/trajectory.tum (seconds, IMU pose) and OUT_DIR/segments.json.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run_basalt(seq_dir, out, skip, calib, config, threads):
    okin = seq_dir / (f"okvis_input_skip{skip}" if skip else "okvis_input")
    subprocess.run([PY, str(ROOT / "scripts" / "make_okvis2_input.py"), str(seq_dir / "runner_input"), str(okin), "--skip-frames", str(skip)],
                   check=True, stdout=subprocess.DEVNULL)
    bin_dir = seq_dir / (f"basalt_input_skip{skip}" if skip else "basalt_input")
    bin_dir.mkdir(exist_ok=True)
    link = bin_dir / "mav0"
    if not link.is_symlink():
        os.symlink("../" + okin.name, link)
    seg = out / f"segment_skip{skip}"
    seg.mkdir(exist_ok=True)
    env = dict(os.environ, LD_LIBRARY_PATH=str(Path.home() / ".local/lib") + ":" + os.environ.get("LD_LIBRARY_PATH", ""))
    with open(seg / "basalt.log", "w") as log:
        r = subprocess.run([os.environ.get("BASALT_VIO", str(Path.home() / ".local/bin/basalt_vio")), "--dataset-path", str(bin_dir), "--dataset-type", "euroc",
                            "--cam-calib", str(calib), "--config-path", str(config), "--save-trajectory", "tum", "--show-gui", "false",
                            "--num-threads", str(threads), "--use-imu", "true"], cwd=seg, env=env, stdout=log, stderr=subprocess.STDOUT)
    traj = seg / "trajectory.txt"
    if r.returncode != 0 or not traj.exists():
        return None
    a = np.loadtxt(traj, comments="#")
    return a if a.ndim == 2 and len(a) > 2 else None


def first_divergence(a, max_speed, max_jump):
    t, p = a[:, 0], a[:, 1:4]
    d = np.linalg.norm(np.diff(p, axis=0), axis=1)
    dt = np.diff(t)
    bad = np.where((d > max_jump) | (d / np.maximum(dt, 1e-3) > max_speed))[0]
    return int(bad[0]) + 1 if len(bad) else None


def to_T(row):
    T = np.eye(4)
    T[:3, :3] = R.from_quat(row[4:8]).as_matrix()
    T[:3, 3] = row[1:4]
    return T


def from_T(T, t):
    q = R.from_matrix(T[:3, :3]).as_quat()
    return np.r_[t, T[:3, 3], q]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--calib", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--max-speed", type=float, default=6.0)
    ap.add_argument("--max-jump", type=float, default=1.0)
    ap.add_argument("--back", type=int, default=20)
    ap.add_argument("--max-segments", type=int, default=12)
    ap.add_argument("--skip-frames", type=int, default=0)
    args = ap.parse_args()
    seq_dir, out = args.seq_dir.resolve(), args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    stereo = [l for l in (seq_dir / "runner_input" / "stereo.csv").read_text().splitlines() if l and not l.startswith("#")]
    n_frames = len(stereo)
    skip = args.skip_frames
    pieces, segments = [], []
    world_from_seg = np.eye(4)
    last_good = None
    while skip < n_frames - 50 and len(segments) < args.max_segments:
        a = run_basalt(seq_dir, out, skip, args.calib, args.config, args.threads)
        if a is None:
            segments.append({"skip": skip, "status": "failed"})
            skip += 100
            continue
        f = first_divergence(a, args.max_speed, args.max_jump)
        keep = a if f is None else a[:max(f - args.back, 1)]
        # stitch: first pose of this segment onto the last good pose
        if last_good is not None:
            world_from_seg = last_good @ np.linalg.inv(to_T(keep[0]))
        rows = []
        for row in keep:
            T = world_from_seg @ to_T(row)
            rows.append(from_T(T, row[0]))
        pieces.append(np.array(rows))
        last_good = world_from_seg @ to_T(keep[-1])
        segments.append({"skip": skip, "poses_total": int(len(a)), "poses_kept": int(len(keep)), "diverged_at_index": f,
                         "t_start": float(a[0, 0]), "t_end_kept": float(keep[-1, 0])})
        if f is None:
            break
        # restart from the frame of the last kept pose: find its index in stereo.csv
        t_restart = keep[-1, 0]
        idx = next((i for i, l in enumerate(stereo) if abs(float(l.split(",")[0]) - t_restart) < 2e-3), None)
        skip = (idx if idx is not None else skip + f) + 1
    traj = np.concatenate(pieces) if pieces else np.zeros((0, 8))
    with open(out / "trajectory.tum", "w") as fh:
        fh.write("# timestamp tx ty tz qx qy qz qw; IMU frame; basalt segments stitched\n")
        for row in traj:
            fh.write(f"{row[0]:.9f} " + " ".join(f"{v:.9f}" for v in row[1:]) + "\n")
    (out / "segments.json").write_text(json.dumps({"segments": segments, "poses": int(len(traj)), "frames": n_frames}, indent=1) + "\n")
    print(json.dumps({"segments": len(segments), "restarts": sum(1 for s in segments if s.get("diverged_at_index") is not None), "poses": int(len(traj)), "frames": n_frames}))


if __name__ == "__main__":
    main()
