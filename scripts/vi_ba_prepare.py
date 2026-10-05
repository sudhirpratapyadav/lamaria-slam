#!/usr/bin/env python3
"""Build the problem folder for tools/vi_ba from a Basalt run that was made with OBS_DUMP=1.

usage: vi_ba_prepare.py RUN_DIR SEQ_DIR CONFIG_JSON OUT_DIR

RUN_DIR holds trajectory.tum (stitched VIO poses, IMU frame, seconds), segments.json and
segment_skip*/obs/<t_ns>.bin (records int32 id, int32 cam, float x, float y); SEQ_DIR holds
runner_input/imu.csv. Keyframes are picked every kf_interval_s seconds (first and last frame of
every segment always), track ids are made unique per segment, and each observation gets its
pixel velocity from the neighbouring frames (for the time-offset parameter).
Writes problem.json, keyframes.txt, imu.txt, obs.bin.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np

REC = struct.Struct("<iiff")  # id cam x y
OUT = struct.Struct("<iiiffff")  # kf cam id x y vx vy


def load_obs(path):
    b = path.read_bytes()
    n = len(b) // REC.size
    out = {}
    for i in range(n):
        tid, cam, x, y = REC.unpack_from(b, i * REC.size)
        out[(tid, cam)] = (x, y)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("config", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    interval = float(cfg.get("kf_interval_s", 0.5))
    a.out.mkdir(parents=True, exist_ok=True)

    # VIO poses by frame time
    rows = [l.split() for l in (a.run_dir / "trajectory.tum").read_text().splitlines() if l.strip() and not l.startswith("#")]
    traj = np.array([[float(v) for v in r[:8]] for r in rows])
    t_ns = np.round(traj[:, 0] * 1e9).astype(np.int64)
    pose_by_t = {int(t): traj[i, 1:8] for i, t in enumerate(t_ns)}
    order = np.argsort(t_ns)
    t_sorted = t_ns[order]
    p_sorted = traj[order, 1:4]
    # velocity by central difference
    vel_by_t = {}
    for i in range(len(t_sorted)):
        i0, i1 = max(i - 1, 0), min(i + 1, len(t_sorted) - 1)
        dt = (t_sorted[i1] - t_sorted[i0]) * 1e-9
        vel_by_t[int(t_sorted[i])] = (p_sorted[i1] - p_sorted[i0]) / dt if dt > 0 else np.zeros(3)

    segs = json.load(open(a.run_dir / "segments.json"))["segments"]
    segs = [s for s in segs if s.get("status") != "failed" and "t_start" in s]
    # frames per segment: those with a kept pose inside the segment's kept range
    frames = []  # (t_ns, seg_index, obs_path)
    used = set()
    for si, s in enumerate(segs):
        obs_dir = a.run_dir / f"segment_skip{s['skip']}" / "obs"
        if not obs_dir.exists():
            print(f"warning: no obs dump in {obs_dir}", file=sys.stderr)
            continue
        t0, t1 = int(round(s["t_start"] * 1e9)) - 1000, int(round(s["t_end_kept"] * 1e9)) + 1000
        for t in t_sorted:
            t = int(t)
            if t0 <= t <= t1 and t not in used and (obs_dir / f"{t}.bin").exists():
                frames.append((t, si, obs_dir / f"{t}.bin"))
                used.add(t)
    frames.sort()
    print(f"frames with pose and tracks: {len(frames)} of {len(t_sorted)} poses, {len(segs)} segment(s)")

    # keyframe selection
    kf_idx_of_t = {}
    kfs = []
    for si in range(len(segs)):
        fs = [f for f in frames if f[1] == si]
        if not fs:
            continue
        last_t = None
        for k, f in enumerate(fs):
            take = last_t is None or (f[0] - last_t) * 1e-9 >= interval - 1e-6 or k == len(fs) - 1
            if take:
                kf_idx_of_t[f[0]] = len(kfs)
                kfs.append(f)
                last_t = f[0]
    print(f"keyframes: {len(kfs)}")

    # observations with pixel velocities from neighbouring frames of the same segment
    by_seg = {}
    for i, f in enumerate(frames):
        by_seg.setdefault(f[1], []).append(i)
    cache = {}

    def obs_of(i):
        if i not in cache:
            if len(cache) > 8:
                cache.clear()
            cache[i] = load_obs(frames[i][2])
        return cache[i]

    n_obs = 0
    with open(a.out / "obs.bin", "wb") as fo:
        for si, idxs in by_seg.items():
            pos_in_seg = {i: k for k, i in enumerate(idxs)}
            for i in idxs:
                t = frames[i][0]
                if t not in kf_idx_of_t:
                    continue
                kf = kf_idx_of_t[t]
                cur = obs_of(i)
                k = pos_in_seg[i]
                prev = obs_of(idxs[k - 1]) if k > 0 else {}
                nxt = obs_of(idxs[k + 1]) if k + 1 < len(idxs) else {}
                tp = frames[idxs[k - 1]][0] if k > 0 else None
                tn = frames[idxs[k + 1]][0] if k + 1 < len(idxs) else None
                for (tid, cam), (x, y) in cur.items():
                    vx = vy = 0.0
                    if (tid, cam) in prev and (tid, cam) in nxt:
                        dt = (tn - tp) * 1e-9
                        vx, vy = (nxt[(tid, cam)][0] - prev[(tid, cam)][0]) / dt, (nxt[(tid, cam)][1] - prev[(tid, cam)][1]) / dt
                    elif (tid, cam) in nxt:
                        dt = (tn - t) * 1e-9
                        vx, vy = (nxt[(tid, cam)][0] - x) / dt, (nxt[(tid, cam)][1] - y) / dt
                    elif (tid, cam) in prev:
                        dt = (t - tp) * 1e-9
                        vx, vy = (x - prev[(tid, cam)][0]) / dt, (y - prev[(tid, cam)][1]) / dt
                    fo.write(OUT.pack(kf, cam, tid + (si << 28), x, y, vx, vy))
                    n_obs += 1
    print(f"observations on keyframes: {n_obs}")

    with open(a.out / "keyframes.txt", "w") as f:
        f.write("# idx t_ns tx ty tz qx qy qz qw vx vy vz\n")
        for i, (t, si, _) in enumerate(kfs):
            p = pose_by_t[t]
            v = vel_by_t[t]
            f.write(f"{i} {t} " + " ".join(f"{x:.9f}" for x in p) + " " + " ".join(f"{x:.6f}" for x in v) + "\n")

    # IMU (seconds -> ns)
    imu = np.loadtxt(a.seq_dir / "runner_input" / "imu.csv", delimiter=",", comments="#")
    with open(a.out / "imu.txt", "w") as f:
        for r in imu:
            f.write(f"{int(round(r[0] * 1e9))} " + " ".join(f"{x:.9f}" for x in r[1:7]) + "\n")

    calib = json.load(open(a.run_dir / "calib.json"))["value0"]
    cams = []
    for c in range(2):
        it = calib["intrinsics"][c]
        assert it["camera_type"] == "pinhole", it["camera_type"]
        T = calib["T_imu_cam"][c]
        cams.append({"fx": it["intrinsics"]["fx"], "fy": it["intrinsics"]["fy"], "cx": it["intrinsics"]["cx"], "cy": it["intrinsics"]["cy"],
                     "w": calib["resolution"][c][0], "h": calib["resolution"][c][1],
                     "T_i_c": [T["px"], T["py"], T["pz"], T["qx"], T["qy"], T["qz"], T["qw"]]})
    problem = {"cams": cams,
               "imu": {"accel_noise_std": calib["accel_noise_std"], "gyro_noise_std": calib["gyro_noise_std"],
                       "accel_bias_std": calib["accel_bias_std"], "gyro_bias_std": calib["gyro_bias_std"], "rate": calib["imu_update_rate"]},
               "n_keyframes": len(kfs), "n_obs": n_obs, "n_frames": len(frames), "n_segments": len(segs), "run_dir": str(a.run_dir)}
    json.dump(problem, open(a.out / "problem.json", "w"), indent=1)


if __name__ == "__main__":
    main()
