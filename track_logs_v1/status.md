# Current status

Last updated: 2026-10-02 23:38 IST. Edit in place; this is the "where are we now" page.

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
| `scripts/` | run/evaluate: `prepare_runner_input.py`, `make_openvins_config.py`, `tum_to_submission.py`, `evaluate.py`, `run_sequence.sh`, `summarize_experiment.py`, `log.sh`; offline experiments: `run_sequence_bidir.sh` (+ `make_reversed_input.py`, `stitch_bidir.py`); raw data: `fetch_sequences.sh`, `rectify_imu_from_vrs.py`, `vrs_to_runner_input.py`, `fit_fisheye_kb.py` |
| `configs/ov_ref001` | **current reference** (dynamic init, time offset fixed, noise densities x10) |
| `configs/ov_baseline`, `configs/explore-001/` | experiment 001 first attempt and its bring-up variants |
| GitHub | `git@github.com:sudhirpratapyadav/lamaria-slam.git`, last push 6d6abc8 (experiments 001-016) |
| `data/training/*` | all 13 controlled sequences; additional set 7 of 10 downloaded (rest in progress); `.vrs` for R_01/R_04/R_08/R_11; `data/training_rect/` (factory-rectified IMU), `data/training_fisheye/` (raw fisheye input) for those |

## Numbers (ATE RMSE after sim3, official evaluator, single deterministic runs)

| Config | R_01_easy | R_04_medium | R_08_hard | R_11_5cp (ATE; score 2D / recall@1m) |
|---|---|---|---|---|
| ov_ref003 (reference), start 0 / 100 | 0.254 / 0.239 | 0.716 / 0.706 | 2.93 / 4.71 | 2.62 / 1.58; 41.3 / 59.6 score, 3 / 28 % recall@1m |
| ov_ref005 (reference since 036), start 0 / 100 | 0.289 / 0.176 | 1.480 / 0.675 | 1.484 / 1.964 | 0.684 / 0.476 |
| ov_ref004, start 0 / 100 | 0.191 / 0.195 | 0.982 / 0.659 | 2.47 / 1.18 | 0.74 / 1.06; 72.4 / 70.2 score, 89 / 55 % recall@1m |
| ov_ref001 (first reference) | 0.301 / 0.281 | 0.739 / 1.078 | 4.49 / 3.59 | 1.36 / 2.84; 58.9 / 38.9 score |
| ov_baseline (datasheet noise, dt calib on) | 0.169 | diverged (41.7) | 10.59 | - |

Against the published stereo+IMU baselines on the same sequences and metric (paper Table 2, see `docs/benchmark_notes.md`):

| Method | R_01_easy | R_04_medium | R_08_hard |
|---|---|---|---|
| ours, ov_ref005 (start 0 / 100) | 0.289 / 0.176 | 1.480 / 0.675 | 1.484 / 1.964 |
| ours, ov_ref001, 6 start offsets: mean (min-max) | 0.25 (0.17-0.34) | 0.90 (0.74-1.08) | 4.85 (3.3-7.4) |
| OpenVINS (paper) | 0.66 | 0.94 | 4.25 |
| OpenVINS + Maplab (paper, open baseline on the leaderboard) | 0.65 | 1.05 | 3.97 |
| OKVIS2 (paper) | 0.02 | 1.36 | 6.81 |

Whole controlled set, two start offsets per sequence: ov_ref005 mean ATE 2.83 m over 13 sequences (ov_ref004 3.23, ov_ref003 3.59) vs 4.01 m OpenVINS+Maplab and 4.39 m OpenVINS in the paper (single runs there). Per-sequence tables in experiments.md, sections 022 and 026. Offset spread is large on long sequences (R_13: 3.6 vs 6.4 m), so decisions use two-offset means over all 13.

Leaderboard main-set metrics, computed locally on R_11_5cp: best run so far score 2D 69.7, CP recall @ 1 m 80 %, pose recall @ 5 m 100 %, pose recall @ 1 m 78 % (012, 400 features, lucky init); with the reproducible initialiser (ov_ref003) 41 to 60 score, 3 to 28 % recall @ 1 m. R_11 is initialisation-dominated. R_12 downloaded, R_13 downloading. Cost: 2 to 2.4x faster than realtime, ~1.2 cores, under 140 MB RAM.

## What we learned today

- OpenVINS is deterministic on this harness (repeat runs identical), so variance comes from the start frame: 18 runs across 6 offsets never diverged, and the spread (above) is the minimum effect size for any change.
- Static initialisation never triggers on head-worn data; dynamic init is required and is the fragile part: small noise/offset changes decide whether a sequence diverges, and divergence is silent (poses keep coming).
- Scale is 2 to 4 % off in every surviving run.

## Next (in order)

1. Adopted: 8x8 extraction grid (036): two-offset mean 2.83 vs 3.23 m; ov_ref005 is the reference.
2. Queued: idle timing of ov_ref001/ov_ref004 (Nano budget), rebuild of OpenVINS with the new klt_win_size / klt_pyr_levels options, 034 (KLT window 21 px; pyramid 7) on the six hardest sequences for blurred frames.
3. Closed since the last update: fisheye input (033, worse than pinhole even with an exact lens model; R_11 an isolated gain), dense grid (028, tie), ZUPT/analytical (027), factory IMU rectification (031, neutral).
4. Target numbers to move: additional-set recall @ 5 m (030: 99.7 / 36.6 / 23.6 / 48.5 % on sequence_1_19 / 1_20 / 2_11 / 2_12), score 2D 41 / 14 / 15 / 21.
3. Then: fisheye input (needs `.vrs` download approval), loop closure for the long sequences.
4. Extend every comparison to all controlled-set sequences as they arrive (R_02 ... R_10).

## Blockers

None.
