# Current status

Last updated: 2026-10-02 19:15 IST. Edit in place; this is the "where are we now" page.

## Host

This PC (16 cores, 15 GB RAM, Quadro P620). A100 and Jetson Nano not started.

## Setup

| Piece | State |
|---|---|
| `third_party/lamaria` | cloned, upstream, used for download + evaluators (git-ignored) |
| `.venv` | evaluator deps installed (pycolmap, pyceres, evo, projectaria-tools); no hloc/torch |
| `third_party/open_vins` | copied from sibling repo (upstream 6948812 + 6-line viz-skip patch), tracked in git |
| `build/open_vins`, `build/runner` | built (Release, ROS off) |
| `src/runner/stereo_offline.cpp` | runner: pads smaller image + masks padding, writes image-clock timestamps, honours `verbosity` |
| `scripts/` | `prepare_runner_input.py`, `make_openvins_config.py`, `tum_to_submission.py`, `evaluate.py`, `run_sequence.sh`, `summarize_experiment.py` |
| `configs/ov_ref001` | **current reference** (dynamic init, time offset fixed, noise densities x10) |
| `configs/ov_baseline`, `configs/explore-001/` | experiment 001 first attempt and its bring-up variants |
| `data/training/{R_01_easy,R_04_medium,R_08_hard}` | downloaded and unpacked (13 GB) |
| GitHub | `git@github.com:sudhirpratapyadav/lamaria-slam.git`, last push 95d4f3b. **Harness, configs, experiment 001 not yet committed** (waiting for owner approval) |

## Numbers (ATE RMSE after sim3, official evaluator, single deterministic runs)

| Config | R_01_easy | R_04_medium | R_08_hard |
|---|---|---|---|
| ov_ref001 (reference) | 0.301 m | 0.739 m | 4.49 m |
| ov_baseline (datasheet noise, dt calib on) | 0.169 m | diverged (41.7 m) | 10.59 m |

Against the published stereo+IMU baselines on the same sequences and metric (paper Table 2, see `docs/benchmark_notes.md`):

| Method | R_01_easy | R_04_medium | R_08_hard |
|---|---|---|---|
| ours, ov_ref001 | 0.301 | 0.739 | 4.49 |
| OpenVINS (paper) | 0.66 | 0.94 | 4.25 |
| OpenVINS + Maplab (paper, open baseline on the leaderboard) | 0.65 | 1.05 | 3.97 |
| OKVIS2 (paper) | 0.02 | 1.36 | 6.81 |

So on these three we are at open-baseline level: ahead on the easy and medium sequence, slightly behind on the hard one. The leaderboard's main-set metrics (score 2D, CP recall @ 1 m, pose recall @ 5 m) need control-point sequences (R_11/R_12/R_13, additional set), not downloaded yet. Cost: 2 to 2.4x faster than realtime, ~1.2 cores, under 140 MB RAM.

## What we learned today

- OpenVINS is deterministic on this harness (repeat runs identical), so variance must come from varying the input (start frame), not reruns.
- Static initialisation never triggers on head-worn data; dynamic init is required and is the fragile part: small noise/offset changes decide whether a sequence diverges, and divergence is silent (poses keep coming).
- Scale is 2 to 4 % off in every surviving run.

## Next (in order)

1. Owner: approve commit of the harness + experiment 001.
2. Experiment 002: initialisation robustness. Start-frame sweep on all three sequences to measure how often init goes bad; then divergence detection + re-initialisation.
3. Experiment 003: IMU noise sweep (densities x1..x10, walks separately).
4. Tracking knobs, fisheye input (needs `.vrs` download approval), then loop closure.

## Blockers

None.
