# Current status

Last updated: 2026-10-02 16:35 IST. Edit in place; this is the "where are we now" page.

## Host

This PC (16 cores, 15 GB RAM, Quadro P620). A100 and Jetson Nano not started.

## Setup

| Piece | State |
|---|---|
| `third_party/lamaria` | cloned, upstream, used for download + evaluators |
| `.venv` | evaluator deps installed (pycolmap, pyceres, evo, projectaria-tools); no hloc/torch |
| `third_party/open_vins` | copied from sibling repo (upstream 6948812 + 6-line viz-skip patch), tracked in git |
| `build/open_vins` | building (Release, ROS off) |
| `src/runner/stereo_offline.cpp` | copied from sibling; expects `imu.csv` + `stereo.csv` + images; not yet built here |
| `third_party/slambench` | copied; extra diagnostics only, not the official metric |
| `data/training/{R_01_easy,R_04_medium,R_08_hard}` | downloading (ASL, 9.4 GB) |
| `configs/` | empty; LaMAria OpenVINS config to be written from the pinhole calibration JSON |
| `scripts/` | empty; need: ASL to runner input, run, evaluate, package submission |

## Numbers

None yet. First target: experiment 001, OpenVINS stereo+IMU on the three sequences, scored with the official evaluators.

## Open questions

- Fisheye (raw `.vrs`) vs pinhole (ASL) input: pinhole first; fisheye later, needs a separate download approval.
- Pinhole image sizes differ per camera (758x572 vs 757x569): the runner checks image size against calibration, so each camera gets its own resolution in the config.
- IMU noise parameters: use the values in the calibration JSON first, tune later.
- Submission frame is `world_from_imu`; the runner already outputs IMU poses. Pseudo-GT is in the left-camera frame; check how much that constant offset matters in the ATE.

## Blockers

None. Waiting on the download and the build.
