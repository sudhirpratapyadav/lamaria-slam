# Current status

Last updated: 2026-10-02 19:31 IST. Edit in place; this is the "where are we now" page.

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
| GitHub | `git@github.com:sudhirpratapyadav/lamaria-slam.git`, last push 6d6abc8 (experiments 001-016) |
| `data/training/*` | 12 of 13 controlled-set sequences ready, R_13 downloading, then the 10 additional-set sequences (`results/fetch_all.log`) |

## Numbers (ATE RMSE after sim3, official evaluator, single deterministic runs)

| Config | R_01_easy | R_04_medium | R_08_hard | R_11_5cp (ATE; score 2D / recall@1m) |
|---|---|---|---|---|
| ov_ref003 (reference), start 0 / 100 | 0.254 / 0.239 | 0.716 / 0.706 | 2.93 / 4.71 | 2.62 / 1.58; 41.3 / 59.6 score, 3 / 28 % recall@1m |
| ov_ref001 (first reference) | 0.301 / 0.281 | 0.739 / 1.078 | 4.49 / 3.59 | 1.36 / 2.84; 58.9 / 38.9 score |
| ov_baseline (datasheet noise, dt calib on) | 0.169 | diverged (41.7) | 10.59 | - |

Against the published stereo+IMU baselines on the same sequences and metric (paper Table 2, see `docs/benchmark_notes.md`):

| Method | R_01_easy | R_04_medium | R_08_hard |
|---|---|---|---|
| ours, ov_ref003 (start 0 / 100) | 0.254 / 0.239 | 0.716 / 0.706 | 2.93 / 4.71 |
| ours, ov_ref001, 6 start offsets: mean (min-max) | 0.25 (0.17-0.34) | 0.90 (0.74-1.08) | 4.85 (3.3-7.4) |
| OpenVINS (paper) | 0.66 | 0.94 | 4.25 |
| OpenVINS + Maplab (paper, open baseline on the leaderboard) | 0.65 | 1.05 | 3.97 |
| OKVIS2 (paper) | 0.02 | 1.36 | 6.81 |

So on these three we are at open-baseline level: ahead on the easy and medium sequence, slightly behind on the hard one.

Leaderboard main-set metrics, computed locally on R_11_5cp: best run so far score 2D 69.7, CP recall @ 1 m 80 %, pose recall @ 5 m 100 %, pose recall @ 1 m 78 % (012, 400 features, lucky init); with the reproducible initialiser (ov_ref003) 41 to 60 score, 3 to 28 % recall @ 1 m. R_11 is initialisation-dominated. R_12 downloaded, R_13 downloading. Cost: 2 to 2.4x faster than realtime, ~1.2 cores, under 140 MB RAM.

## What we learned today

- OpenVINS is deterministic on this harness (repeat runs identical), so variance comes from the start frame: 18 runs across 6 offsets never diverged, and the spread (above) is the minimum effect size for any change.
- Static initialisation never triggers on head-worn data; dynamic init is required and is the fragile part: small noise/offset changes decide whether a sequence diverges, and divergence is silent (poses keep coming).
- Scale is 2 to 4 % off in every surviving run.

## Next (in order)

1. The systematic scale error (estimate 2 to 4.5 % too large, confirmed against surveyed control points on R_11). Found: the raw Aria accelerometer reads ~1.03 g; dividing it by 1.03 (011) brings the metric scale to 1.00 and halves the SE3 error on R_04, but the sim3 ATE gets worse because stereo and IMU then disagree (007 showed the stereo-free scale is equally large). Running/queued: 012 (features 400 / clones 15), 013 (ov_ref002 candidate = re-init + load-independent init), 014 (init window 4 s / init features 100), 015 (stereo off + accel correction). Discarded: 004, 005, 006, 008, 010.
2. Determinism caveat (009): OpenVINS's dynamic init is bounded by wall-clock time, so results depend on machine load; ov_ref002 bounds it by iterations instead.
3. Then: fisheye input (needs `.vrs` download approval), loop closure for the long sequences.
4. Extend every comparison to all controlled-set sequences as they arrive (R_02 ... R_10).

## Blockers

None.
