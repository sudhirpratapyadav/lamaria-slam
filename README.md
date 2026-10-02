# lamaria-slam

Climb the [LaMAria](https://lamaria.ethz.ch) benchmark (Stereo + IMU track) with our own visual-inertial SLAM. Try things, measure, keep what helps, repeat.

This is a separate project from `~/sudhir/slam` (the Jetson/P3-DX robot app). It may borrow ideas and code from there (OpenVINS tuning, the `slambench` metrics) but has its own history, data and goals.

## Why LaMAria

City-scale egocentric data from Project Aria glasses: two synchronised global-shutter grayscale cameras (640x480, 20 Hz, fisheye), two IMUs, 22 h / 70 km, with centimetre-accurate ground truth from surveyed control points. The sensor suite is the same kind we will have on the robot (global-shutter stereo + IMU), and the hard cases (low light, moving platforms, long sequences, loop closure) are the ones that matter for a real robot.

## Target

Leaderboard snapshot (checked 2026-10-02, [leaderboard](https://lamaria.ethz.ch/leaderboard)), Stereo + IMU track, score per challenge:

| Rank | Method | Short | Medium | Long |
|---|---|---|---|---|
| 1 | Aria's SLAM (closed source) | 90.7 | 78.5 | 70.9 |
| 2 | AnonSLAM | 75.3 | 61.1 | 59.9 |
| 5 | OpenVINS+Maplab (open baseline) | 27.7 | 23.4 | 12.8 |

Goal ladder: beat the open baseline (OpenVINS+Maplab) first, then AnonSLAM, then approach Aria's SLAM. A method only appears if it submits all sequences of a challenge.

## Benchmark facts that shape the work

- 23 training sequences with ground truth (3 controlled easy/medium/hard sets plus control-point and pseudo-GT sequences), 63 test sequences with hidden ground truth. Develop on training; submit test only when a version is final (test results can be updated every 24 h).
- Metrics: controlled set = ATE after Umeyama alignment; main and additional sets = pose recall at 5 m against pseudo ground truth; control-point sequences also report a 2D score and recall at 1 m. Recall rewards **never losing track and always producing a pose**, more than the last centimetre.
- Submission: a zip with `/slam/<sequence>.txt`, lines `timestamp tx ty tz qx qy qz qw` (ns), **one pose for every image** (20 Hz; no keyframe-only output, 1 ms timestamp matching, no interpolation). Stereo+IMU methods submit `world_from_imu` poses.
- Data: raw `.vrs` plus Aria calibration (about 890 GB for everything), or ASL folders / ROS1 bags with pinhole calibration (1.1 / 1.5 TB). Training sequences range from 1.2 GB (`R_01_easy`) to 15 GB each. License: dataset CC BY 4.0, tooling MIT. Official tooling: [cvg/lamaria](https://github.com/cvg/lamaria).

## Plan

1. **Harness (this PC first)**: download a small slice (`R_01_easy`, `R_04_medium`, `R_08_hard`), run the official evaluators on a baseline (OpenVINS stereo+IMU), and log the numbers in `track_logs_v1/`. Reproduce a published baseline before changing anything.
2. **Iterate**, one change at a time, each with a written hypothesis and result: calibration and IMU noise settings, feature tracking (KLT vs descriptor), number of features and clones, fisheye handling, initialisation, failure recovery so a pose is always output, then loop closure and mapping (the big gap to Aria's SLAM on medium/long sequences).
3. **Three setups**: this PC, then the A100 server, then the Jetson Nano. Same code, same configs; only the host differs. The Nano is the constrained case (4 GB RAM, no heavy builds there). We decide when to move on.
4. **Submit** only versions that win on the training set across all sequences of a challenge.

## Layout

```
docs/          design notes and benchmark notes
track_logs_v1/ decision log, current status, experiments (scoreboard + per-experiment records)
scripts/       download, run, evaluate, package-submission helpers
configs/       estimator configurations (added as we go)
data/          datasets (git-ignored)
results/       run outputs (git-ignored)
```

Hosts and results are tracked in `track_logs_v1/experiments.md` (scoreboard at the top) and `track_logs_v1/status.md`.
