# Experiments narrative

Timestamped but editable: what was tried, what came out, what we learned. The formal per-experiment records with exact commands and commits live in `experiments/NNN-*.md`; the scoreboard is `experiments/LOG.md`. This file is the readable story and the place for insights that span experiments.

## 2026-10-02: experiment 001, OpenVINS baseline (closed)

**Goal**: run OpenVINS stereo+IMU on `R_01_easy`, `R_04_medium`, `R_08_hard` (ASL, pinhole-undistorted), one `world_from_imu` pose per image, scored with the official evaluator.

**Bring-up problems and fixes**

- Stereo KLT crashed because the two pinhole images differ in size by a few pixels. Fix in the runner: pad the smaller image bottom/right, mask the padding. Intrinsics untouched.
- OpenVINS never initialised: the static initialiser wants an image disparity under 10 px over a window, and a person wearing glasses never holds that still. Dynamic initialisation (`init_dyn_use`) initialises about 2.3 s in.
- A YAML comment on the same line as a boolean breaks OpenCV's parser. Comments go on their own line.
- OpenVINS resolves relative config paths from the config file, so pass absolute paths.

**Results** (ATE RMSE after sim3, metres, single deterministic runs)

| Config | R_01 | R_04 | R_08 |
|---|---|---|---|
| datasheet noise, online time offset | 0.169 | diverged | 10.59 |
| time offset off | 0.329 | 1.63 | diverged |
| noise x10 (all) | 0.492 | 1.11 | - |
| densities x10 only | 0.403 | diverged | - |
| time offset off + densities x10 | 0.301 | 0.739 | 4.49 |

**Insights**

- Determinism: identical input gives identical output, so "several seeds" must mean different start frames or perturbed input, not reruns.
- The failure mode is a bad dynamic initialisation that the filter never recovers from, and it is silent: poses keep being produced while the trajectory flies off (speed 2.2 m/s in the first 10 s, accel bias to 3.5 m/s^2, time offset jumping to -15 ms). Divergence detection plus re-initialisation is the first robustness feature to build.
- Both knobs (time-offset calibration, noise inflation) only move which sequence diverges. The configuration that happens to survive all three is the reference, but it is not understood yet; treat it as a working point, not a tuned optimum.
- Datasheet IMU noise values are too optimistic for OpenVINS (standard finding); inflating only the white-noise densities keeps the bias walks sane.
- Scale is 2 to 4 % off in every surviving run. Stereo with a 6 cm-class baseline plus IMU should pin scale better than that; candidate causes are the init, the padded/undistorted images, or the accelerometer bias walk.
- Error on R_08_hard is drift-shaped (5 to 18 m per minute window over a 746 m walk), worst at start and end. That is the loop-closure / mapping gap the README talks about, but initialisation comes first.
- Expressing our IMU poses in the left-camera frame makes the ATE worse against the controlled-set pseudo-GT, so IMU poses are compared directly; submit `world_from_imu`.

**Cost**: 2 to 2.4x faster than realtime on this PC, ~1.2 cores, under 140 MB RAM. A full three-sequence pass takes about 8 minutes when run in parallel.
