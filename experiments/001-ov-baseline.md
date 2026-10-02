# 001 OpenVINS stereo+IMU baseline on LaMAria pinhole ASL data

Date: 2026-10-02 / host: pc (16 cores, 15 GB, no GPU use) / commit: 95d4f3b + uncommitted harness (committed as the next commit; each run's `results/001-*/<seq>/run_info.txt` records the exact command and the yaml files used).

**Hypothesis**: OpenVINS (MSCKF, stereo KLT) on the pinhole-undistorted ASL images with the IMU noise values from the LaMAria calibration JSON gives a working end-to-end harness and a reference number per sequence. Expected: tracks R_01_easy, drifts on the longer ones.

**Change**: none to compare against; this experiment establishes the reference. Because the first configuration diverged on R_04_medium, a small bring-up exploration (two knobs) was needed to get a configuration that survives all three sequences. All of it is recorded here; nothing was tuned on the test set.

Setup common to all runs: `configs/ov_baseline/estimator.yaml` (200 KLT points, 11 clones, 50 SLAM features, dynamic initialisation, ZUPT at start only, FEJ, RK4), per-sequence `imucam.yaml`/`imu.yaml` generated from the sequence's pinhole calibration JSON. The right image (757x569) is padded to the left image size (758x572) with the padding masked. One pose per image: frames before initialisation (about 45) get the first estimated pose; later gaps carry the previous pose forward. Scoring: official `evaluate_wrt_mps` (ATE RMSE after Umeyama with scale, 1 ms association, 1 pose per image in the pGT of the controlled set).

Command: `scripts/run_sequence.sh configs/<cfg> data/training/<seq> results/<exp>/<seq>`

Knobs explored: `dt` = online camera-IMU time offset calibration (`calib_cam_timeoffset`), `n10` = IMU noise x10 (all four values), `n10d` = only the two white-noise densities x10, random walks unchanged.

**Result**: ATE RMSE in metres after sim3 alignment (sim3 scale in brackets). Single run per cell; OpenVINS was verified to be deterministic on this harness (two repeats reproduced positions exactly), so repeats would not add information, but different start frames would (not done yet).

| Config | R_01_easy (145 s, 2898 fr) | R_04_medium (263 s, 5253 fr) | R_08_hard (616 s, 12328 fr, 746 m path) |
|---|---|---|---|
| ov_baseline: JSON noise, dt calib on | **0.169** (0.993) | 41.7 diverged (0.002) | 10.59 (0.959) |
| dt calib off | 0.329 (0.986) | 1.63 (0.948) | 66.5 diverged (0.518) |
| n10, dt on | 0.492 (0.960) | 1.11 (0.929) | not run |
| n10d, dt on | 0.403 (0.980) | 42.2 diverged (0.002) | not run |
| n10, dt off | not run | 7.75 (0.833) | not run |
| **n10d, dt off** (reference going forward, `configs/ov_ref001`) | 0.301 (0.982) | **0.739** (0.962) | **4.49** (0.964) |

Poses: the estimator produced a pose for every frame after initialisation on every run (no tracking loss detected by OpenVINS; divergence is silent). Error over time on R_08_hard (baseline): 5 to 18 m per minute-window, worst at the start and end, i.e. drift plus a poor initial segment, not a single jump.

Diagnostics of the baseline divergence on R_04_medium: speed already 2.2 m/s median in the first 10 s (walking is ~1.3), accelerometer bias runs to 3.5 m/s^2, the online time offset jumps to -15.6 ms at init. Both knobs change which sequence diverges rather than fixing it, so the root cause is a fragile dynamic initialisation plus no divergence detection, not the noise values as such.

Frame check on R_01_easy: expressing the estimate in the left-camera frame (lever arm 13.4 cm) raises the ATE from 0.169 m to 0.206 m, so the controlled-set pseudo-GT is compared directly against IMU poses; we keep `world_from_imu` as the submission guide says.

**Cost**: 2.0 to 2.4x faster than realtime on this PC, about 1.2 cores (OpenCV threads 4), 106 to 138 MB RSS. R_08_hard takes 274 to 312 s.

**Decision**: keep. Reference config for experiment 002 onwards is `configs/ov_ref001` (= n10d, dt off): 0.301 / 0.739 / 4.49 m on R_01 / R_04 / R_08. The datasheet baseline stays recorded as `configs/ov_baseline` (diverges on R_04). Scale is 2 to 4 % off in every surviving run; worth a dedicated look.

Next, one at a time, each on all three sequences: (1) initialisation robustness: start-frame sweep to measure how often init goes wrong, and divergence detection + re-initialisation so a bad start cannot cost the whole sequence; (2) IMU noise sweep between x1 and x10 on densities, random walk separately; (3) tracking knobs (features, clones, CLAHE for dark frames); (4) raw fisheye from `.vrs` (needs a download approval); (5) loop closure / mapping for the long sequences.
