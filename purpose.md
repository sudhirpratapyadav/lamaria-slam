# Purpose

## Vision

Build a visual-inertial SLAM stack good enough to run a home robot: accurate, fast on cheap embedded hardware, and robust enough that it never loses track for long. The robot (Matic-like, on Jetson Orin Nano and RK3588 boards) carries a global-shutter stereo pair (HJY1A-G8-SM, AR0234 sensors, 60 mm baseline, wide fisheye) and an ICM-42688-P IMU. That hardware arrives in about a month.

## Why LaMAria

Until the robot hardware is here, we need a measurable proxy with the same kind of sensor suite. LaMAria (ETH Zurich, ICCV 2025) records Project Aria glasses: two global-shutter grayscale fisheye cameras at 20 Hz plus a 1 kHz IMU, over 22 hours and 70 km of city-scale walking, with centimetre-accurate surveyed ground truth. Its hard cases (low light, moving platforms, long sequences, loop closures) are exactly the ones a real robot must survive. A public leaderboard gives an honest, external score.

Target: the Stereo + IMU track at https://lamaria.ethz.ch/leaderboard. Ladder: beat the open baseline (OpenVINS+Maplab, score 27.7 / 23.4 / 12.8 on short / medium / long), then AnonSLAM (75.3 / 61.1 / 59.9), then approach Aria's own closed-source SLAM (90.7 / 78.5 / 70.9).

## What "good" means here

In priority order, as set by the owner:

1. **Accurate**: low drift, correct scale, good loop closure on long sequences.
2. **Fast and optimised**: accuracy per CPU cycle matters more than accuracy at any cost, because the result must run on a 4 GB Jetson Nano and later an Orin Nano / RK3588.
3. **Robust**: never lose track for long; always output a pose for every image (the recall metric punishes gaps hard).

## How we work

- Start from OpenVINS (MSCKF, GPL acceptable) copied into this repo, reproduce the published open baseline, then change one thing at a time.
- Every change is an experiment: hypothesis, change, per-sequence result, cost, decision. Multiple sequences and seeds before any decision; validate on long and degraded sequences, not just easy ones.
- Hosts in order: this PC, then the A100 server, then the Jetson Nano. The owner decides when to move.
- Submit to the leaderboard only finished versions, only with the owner's go-ahead.

## What transfers to the robot

The estimator, its configs, the failure-recovery logic, the loop-closure / mapping layer, and the measurement habits (per-sequence numbers, drift over long windows, scale checks, timing-offset checks). The calibration and dataset loaders are LaMAria-specific and will be swapped for the robot's.

Related: `README.md` (plan and layout), `AGENTS.md` (constraints and conventions for agents), `docs/benchmark_notes.md` (benchmark facts), `log_tracks/` (running logs, status, experiments).
