# Status: v4, stereo quality gate and non-causal backend (opened 2026-10-05)

**Reference**: `configs/basalt_v3_ref` on the repeatable build (v3 F21): controlled two-offset mean 2.38 m, additional-set mean score 23.7; dark walks 20.6 / 56.9; long walks 3_17 / 3_18 scores 6.0 / 1.7 (ATE 47 / 56 m).

**Owner's goal**: "start v4, stereo quality gate as well as non causal backend, let's see how far we can go."

## What is known about the long-walk loss (X01 to X07, F01 to F10)

- The long walks never revisit a place: loop closure cannot help them. Their error is a **steady heading drift of 2 to 4.5 degrees per minute**, same sign everywhere it occurs: 2_11, 2_12, 3_17, 3_18, and **R_12 of the controlled set** (13.9 m, the largest controlled error). Absent on the dark walks (4_10, 4_11), on 1_19 / 1_20 and on the short indoor sequences.
- **It belongs to one device and one camera**: the training set has two Aria units (device A: all walks except 1_19 / 1_20, and all controlled sequences except R_08; device B: 1_19, 1_20, R_08). Every drifting sequence is device A; both device-B walks are clean. On device A the drift comes with landmarks hosted in **cam0** (left camera): with cam1 as the primary camera it is gone (X02), landmarks in both cameras halve it (F02: 2_11 21.5 to 12.5 m, 3_18 56 to 34 m, and indoor gains R_04 0.70 to 0.55, R_08 1.03 to 0.75, R_12 13.9 to 11.0, at 2x cost; the dark walk is worse). Device A's sim3 scale is also 1 to 3 % low on every sequence, device B's is 1.00.
- **Ruled out, each with a measurement**: the IMU weights (F01: gyro x2 removes the drift but breaks 1_19, 1_20, the dark walks and the indoor set); far-landmark triangulation (F04); the camera-IMU time offset as the cause (X04 / F05: a real 5 ms offset exists, but on cam0-only geometry the heading is simply linear in the shift at 5 deg/ms, zero near +11 ms, and with both cameras the sensitivity drops to 0.5 deg/ms with the drift still there); the factory IMU model (F08: gyro scale, 0.26 deg of misalignment, device A's 0.25 to 0.39 m/s^2 accelerometer bias; neutral); the cam0 extrinsic rotation (F09: 0.3 deg moves the heading 3 to 6 deg, a 3 to 5 deg error would be needed); self-occlusion by hair (X07: present in some frames, uncorrelated with the drift); time-reversal symmetry (X06: the backward pass drifts the opposite way at half the rate, so a two-pass fusion only halves it).
- **Still to probe**: cam0 intrinsics on device A (F10, focal x0.98 to x1.02, running). If that is insensitive too, the mechanism hunt stops and the general defences are what we keep: both-camera landmarks (F02) and, in the backend, per-sequence self-calibration.
- **Restarts** were initialisation blow-ups (speed 0 to 8 m/s in the first 3 s of a segment; the first state's attitude came from one accelerometer sample taken mid-stride, 10 deg off on a walking start). Fixed in steps (F11 to F14d): a 1 s window with the accelerometer mean rotated through the gyro, a linear solve of the initial velocity from the first tracks (gravity from the mean), and a weak gauge prior on the first pose: restarts on the restart-prone reference runs go from 10 to 1, at 0 to 0.1 m of ATE on the short sequences. The initialisation is now the general, platform-independent part of v4.

## Running

- F12 (`lamaria-v4-f12`): both-camera landmarks + plain 1 s window on the full sets (controlled set done, mixed; walks running).
- G01 (`lamaria-v4-g01-r12`, `lamaria-v4-g01-211`): dumped VIO runs of R_12 and 2_11 for the backend's first test on the heading drift. Backend state: `tools/vi_ba` works end to end (R_01: 0.166 to 0.090 with the time offset free, +3.4 ms).
- F15 (`lamaria-v4-f15`): the candidate v4 causal reference: both-camera landmarks + initialisation (1 s window, gravity from the gyro-rotated accelerometer mean, velocity from the first tracks, gauge prior 1e2), full sets, F14d snapshot.

## Plan

1. Close the mechanism hunt with F10; record the device finding in `docs/benchmark_notes.md`.
2. Robustness first: F11's initialisation window if it removes the restarts, then F02 (both cameras) on the full sets on one snapshot, with and without the 5 ms shift, to make the v4 causal reference. The 5 ms is a measured sensor constant and is kept only if it does not hurt device B and the dark walks.
3. Non-causal backend: global visual-inertial bundle adjustment over Basalt's keyframes (Ceres 2.0 installed; Basalt's own mapper was parked in v2 for injecting wrong loop matches), with per-sequence calibration parameters (cam0 intrinsics / extrinsics / time offset) as the one thing a non-causal pass can estimate that the filter cannot. Stereo observations enter there with a quality gate judged against the converged solution.
4. Stereo quality gate (causal side): `BASALT_STEREO_INIT=1 BASALT_STEREO_CHECK=0.3` is the indoor option from v3 F19; the open problem is the dark walk, where wrong stereo matches agree with wrong temporal depths.

## Tools added in v4

`tools/vi_ba` + `scripts/vi_ba_prepare.py` + `scripts/run_vi_ba.sh` (non-causal backend, G01), `scripts/compare_runs.py` (per-sequence tables against a reference), `scripts/gyro_yaw_check.py` (heading error vs pGT, body frame detected), `cam_imu_check.py` (time offset from images), `make_timeshift_input.py`, `make_swapped_input.py`, `make_rectified_input.py` (+ `configs/aria_factory_imu/`), `occluder_check.py`, `fuse_bidirectional.py`, `finish_basalt_run.sh` (re-does conversion + evaluation), `show_runs.sh`; Basalt options `BASALT_MONO_CAMS`, `BASALT_INIT_WINDOW_S`, `BASALT_INIT_VEL`, `BASALT_OBS_DUMP`; calibration probes `CAM0_ROT_DEG`, `CAM0_FOCAL_SCALE`.
