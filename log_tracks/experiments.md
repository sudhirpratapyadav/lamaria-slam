# Experiments narrative

Timestamped but editable: what was tried, what came out, what we learned. The formal per-experiment records with exact commands and commits live in `experiments/NNN-*.md`; the scoreboard is `experiments/LOG.md`. This file is the readable story and the place for insights that span experiments.

## 2026-10-02: harness setup, no numbers yet

**Goal**: run OpenVINS stereo+IMU on `R_01_easy`, `R_04_medium`, `R_08_hard` (ASL, pinhole-undistorted), produce one `world_from_imu` pose per image, score with the official evaluators, record as experiment 001.

**Insights from reading the evaluators before any run**

- The ATE metric (controlled set) aligns with Umeyama including scale, so scale drift is forgiven there but not in the recall metric used on the test set. Always check the fitted scale.
- Pose recall @ 5 m is 2D (xy) error after Sim3 alignment from control points, over every pseudo-GT keyframe. A pose missing for a keyframe counts as a miss. This is why "always output a pose" is the first robustness rule.
- Estimates shorter than half the ground-truth duration are rejected outright by the ATE evaluator.
- The benchmark uses only the right 1 kHz IMU; the ASL `imu0` is that IMU and the body frame of the calibration is the IMU, so `T_b_s` for each camera is `T_imu_cam` directly.
- ASL images are pinhole-undistorted at slightly different sizes per camera (758x572 left, 757x569 right); focal ~241 px, so the field of view is still wide.

**Status**: data downloading, OpenVINS building. Results will go to experiment 001.
