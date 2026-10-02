# Current status

Last updated: 2026-10-02 18:22 IST. Edit in place; this is the "where are we now" page.

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
| GitHub | `git@github.com:sudhirpratapyadav/lamaria-slam.git`, last push 2ecc5c2 (harness + experiment 001). Uncommitted: experiments/ removal, runner skip option, 002 write-up |
| `data/training/*` | full training set downloading one sequence at a time (`results/fetch_all.log`); R_01, R_04, R_08, R_11_5cp ready |

## Numbers (ATE RMSE after sim3, official evaluator, single deterministic runs)

| Config | R_01_easy | R_04_medium | R_08_hard |
|---|---|---|---|
| ov_ref001 (reference) | 0.301 m | 0.739 m | 4.49 m |
| ov_baseline (datasheet noise, dt calib on) | 0.169 m | diverged (41.7 m) | 10.59 m |

Against the published stereo+IMU baselines on the same sequences and metric (paper Table 2, see `docs/benchmark_notes.md`):

| Method | R_01_easy | R_04_medium | R_08_hard |
|---|---|---|---|
| ours, ov_ref001 (start 0) | 0.301 | 0.739 | 4.49 |
| ours, ov_ref001, 6 start offsets: mean (min-max) | 0.25 (0.17-0.34) | 0.90 (0.74-1.08) | 4.85 (3.3-7.4) |
| OpenVINS (paper) | 0.66 | 0.94 | 4.25 |
| OpenVINS + Maplab (paper, open baseline on the leaderboard) | 0.65 | 1.05 | 3.97 |
| OKVIS2 (paper) | 0.02 | 1.36 | 6.81 |

So on these three we are at open-baseline level: ahead on the easy and medium sequence, slightly behind on the hard one.

Leaderboard main-set metrics, computed locally (R_11_5cp, ov_ref001, single run): score 2D 58.9, CP recall @ 1 m 40 %, pose recall @ 5 m 100 %, pose recall @ 1 m 36 %, ATE 1.36 m (paper OpenVINS 1.04, OV+Maplab 1.62). More control-point sequences (R_12, R_13, additional set) are downloading. Cost: 2 to 2.4x faster than realtime, ~1.2 cores, under 140 MB RAM.

## What we learned today

- OpenVINS is deterministic on this harness (repeat runs identical), so variance comes from the start frame: 18 runs across 6 offsets never diverged, and the spread (above) is the minimum effect size for any change.
- Static initialisation never triggers on head-worn data; dynamic init is required and is the fragile part: small noise/offset changes decide whether a sequence diverges, and divergence is silent (poses keep coming).
- Scale is 2 to 4 % off in every surviving run.

## Next (in order)

1. The systematic scale error (estimate 2 to 4.5 % too large, confirmed against surveyed control points on R_11). Discarded so far: online camera extrinsics (004), online intrinsics (004), IMU noise x3/x5 (005), online IMU intrinsics (006). Running or queued: stereo constraints off (007, decides IMU-vs-stereo as scale source), noise x20 (008), divergence detection + re-init (009), fixed camera-IMU offset +4.3 ms (010).
3. IMU noise sweep (densities x1..x10, walks separately), tracking knobs, then fisheye input (needs `.vrs` download approval), then loop closure for the long sequences.
4. Extend every comparison to all controlled-set sequences as they arrive (R_02 ... R_10).

## Blockers

None.
