# Experiments

Timestamped but editable. This is the single record of what was tried: a scoreboard at the top, then one section per experiment with hypothesis, change, exact command, per-sequence numbers, cost, decision, and insights. Raw outputs live in `results/<exp>/` (git-ignored); each run folder has `run_info.txt` with the commit, host and command, plus the exact yaml used.

## Scoreboard

ATE = RMSE in metres after sim3 Umeyama against the controlled-set pseudo-GT (official `evaluate_wrt_mps`). "Start-offset spread" = min to max over 6 start frames (0, 20, 50, 100, 200, 400). Published stereo+IMU numbers for the same metric are in `docs/benchmark_notes.md` (paper Table 2): OpenVINS+Maplab 0.65 / 1.05 / 3.97, OKVIS2 0.02 / 1.36 / 6.81 on R_01 / R_04 / R_08.

| # | Date | Host | Config | R_01_easy | R_04_medium | R_08_hard | Notes |
|---|---|---|---|---|---|---|---|
| 001 | 2026-10-02 | pc | `ov_ref001`: OpenVINS stereo+IMU, pinhole ASL, dynamic init, time offset fixed, IMU noise densities x10 | 0.301 | 0.739 | 4.49 | reference; datasheet-noise first attempt: 0.169 / diverged / 10.59 |
| 002 | 2026-10-02 | pc | same, 6 start offsets each | 0.17 to 0.34 (mean 0.25) | 0.74 to 1.08 (mean 0.90) | 3.3 to 7.4 (mean 4.85) | no divergence in 18 runs; this spread is the noise floor |
| 009 | 2026-10-02 | pc | + runner divergence detection / re-init | unchanged | unchanged | unchanged | no false triggers; rescues the one diverging x3 run (67.6 to 11.4 m) |
| 013 | 2026-10-02 | pc | `ov_ref002` = + re-init + iteration-bounded init | 0.300 / 0.281 | 0.736 / 1.078 | 4.46 / 3.59 | reference; identical to ov_ref001 numbers |
| 012 | 2026-10-02 | pc | + 400 KLT features (k=0 / k=100) | 0.254 / 0.239 | 0.716 / 0.706 | 2.93 / 4.71 | kept; R_11: 0.81 / 0.75 m, score 69.5 / 69.7 (init luck, see 016) |
| 016 | 2026-10-02 | pc | `ov_ref003` = ov_ref002 + 400 features | 0.254 / 0.239 | 0.716 / 0.706 | 2.93 / 4.71 | **reference**; R_11 2.62 / 1.58 m, score 41.3 / 59.6: init-dominated |
| 022 | 2026-10-02 | pc | ov_ref003 on all 13 controlled sequences (k=0) | mean 3.73 m vs open baseline 4.01 m (paper) | | | better on 7/13 incl. R_12, R_13; losses R_06, R_07, R_10, R_11 |
| 026 | 2026-10-02 | pc | `ov_ref004` = ov_ref003 + CLAHE, 2 offsets x 13 sequences | mean 3.23 m (ref003: 3.59 m) | | | R_06/R_08/R_11 gain 1.2 to 2.0 m |
| 036 | 2026-10-02 | pc | `ov_ref005` = ov_ref004 + 8x8 extraction grid, 2 offsets x 13 | mean 2.83 m | | | **reference**; R_10 10.1 to 6.2 m, R_06, R_09, R_11 gain |
| discarded | 2026-10-02 | pc | 004 cam extrinsics/intrinsics online, 005 noise x3/x5, 006 IMU intrinsics online, 007 stereo off, 008 noise x20, 010 dt +4.3 ms, 012 clones 15 | | | | see sections; 011 acc scale 1.03 fixes metric scale but worsens sim3 ATE, open |

Leaderboard-metric sequences (the main-set metrics, computed locally with the official evaluators):

| # | Config | Sequence | score 2D | CP recall @ 1 m | pose recall @ 5 m | pose recall @ 1 m | ATE sim3 (paper: OpenVINS / OV+Maplab / OKVIS2) |
|---|---|---|---|---|---|---|---|
| 003 | `ov_ref001` | R_11_5cp (477 s, 5 CPs, 1627 pGT keyframes) | 58.9 | 40.0 | 100.0 | 35.8 | 1.36 (1.04 / 1.62 / 1.85) |
| 012 | `ov_ref001` + 400 features, k=0 / k=100 | R_11_5cp | 69.5 / 69.7 | 80.0 / 80.0 | 100 / 100 | 78.5 / 77.3 | 0.81 / 0.75 |
| 016 | `ov_ref003`, k=0 / k=100 | R_11_5cp | 41.3 / 59.6 | - | 100 / 100 | 3.4 / 27.9 | 2.62 / 1.58 |
| 022 | `ov_ref003`, k=0 | R_12_10cp (1012 s, 10 CPs) | 15.9 | - | 30.3 | 7.0 | 8.30 (18.72 / 16.59 / 16.55) |
| 022 | `ov_ref003`, k=0 | R_13_15cp (1404 s, 15 CPs) | 39.1 | - | 92.5 | 10.1 | 3.55 (10.35 / 8.37 / 6.65) |
| 030 | `ov_ref004`, k=0 | sequence_1_19 / 1_20 / 2_11 / 2_12 (additional set) | 41.0 / 13.9 / 15.0 / 21.4 | 7 / 0 / 0 / 5 | 99.7 / 36.6 / 23.6 / 48.5 | 13.8 / 0 / 0 / 3.8 | 2.87 / 10.57 / 9.65 / 6.09 |
| 033 | `ov_ref004` on raw fisheye, k=0 / k=100 | R_11_5cp | 83.4 / 83.1 | 80 / 80 | 100 / 100 | 93.2 / 90.7 | 0.54 / 1.20 |

## 030: reference on the first four additional-set sequences (2026-10-02, pc, commit 1fdab68)

**Hypothesis**: the additional set (long city walks with control points, scored like the test set) shows where the leaderboard is decided.

**Change**: none; `ov_ref004`, start offset 0, single runs (each 15 to 28 min).

**Result** (leaderboard-style metrics computed locally):

| Sequence | length | score 2D | CP recall @ 1 m | pose recall @ 5 m | pose recall @ 1 m | ATE sim3 (scale) | drift / 100 m (median) | revisits |
|---|---|---|---|---|---|---|---|---|
| sequence_1_19 | 913 s, 1002 m | 41.0 | 7.1 % | 99.7 % | 13.8 % | 2.87 (0.969) | 0.43 m | 0 % |
| sequence_1_20 | 1010 s, 1145 m | 13.9 | 0 % | 36.6 % | 0 % | 10.57 (0.914) | 1.92 m | 2 % |
| sequence_2_11 | 1184 s, 1297 m | 15.0 | 0 % | 23.6 % | 0 % | 9.65 (0.995) | 1.49 m | 4 % |
| sequence_2_12 | 1673 s, 31 m of height | 21.4 | 5.0 % | 48.5 % | 3.8 % | 6.09 (0.968), 1 re-init | - | - |

Content: all walking (median 0.9 m/s), no moving platform among these four; sequence_2_11 and 2_12 have many blurred or texture-poor frames (Laplacian variance 3 to 6 against 15 to 70 elsewhere), consistent with long exposures in low light. No loops anywhere (revisit 0 to 4 %).

**Decision**: this is the real target. The per-challenge leaderboard scores of the open baseline (27.7 / 23.4 / 12.8 for short / medium / long) are averages of exactly these numbers, and ours (41 / 14 / 15 / 21) are in that range, not above it. Pose recall @ 5 m collapses on the sequences whose drift is 1.5 to 1.9 m per 100 m (2 to 4x the clean walks); without loops, the only lever on these is lower drift in blurred / low-texture stretches. Fisheye input (033) and tracker robustness are therefore the priorities; recall-at-5-m on these four is the number to move.

## 033: raw fisheye input with a fitted equidistant lens (2026-10-02, pc, commit 23e37ac; closed)

**Hypothesis**: the ASL pinhole images are a resampled, cropped view of the Aria fisheye; running OpenVINS on the raw 640x480 frames with its equidistant (Kannala-Brandt) model should keep the full field of view and the native pixels, which matters most on hard, texture-poor sequences.

**Change**: `scripts/vrs_to_runner_input.py` (raw frames + validity masks from the `.vrs`), `scripts/fit_fisheye_kb.py` (equidistant fit of the Aria FISHEYE624 lens with free principal point: residual 0.12 to 0.43 px mean), runner static masks (outside the lens circle, 7.6 % of pixels), `make_openvins_config.py` EQUIDISTANT support. Estimator config unchanged (`ov_ref004`), so 400 features now sit on 640x480 instead of 758x572.

**Result** (ATE m sim3; R_11 also score 2D / pose recall @ 1 m):

| Input | R_01 k=0 | R_01 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|
| pinhole ASL (ov_ref004) | 0.191 | 0.195 | 2.47 | 1.18 | 0.74, 72.4 / 88.9 | 1.06, 70.2 / 54.9 |
| raw fisheye | 0.268 | 0.323 | 0.76 | 2.57 | **0.538, 83.4 / 93.2** | **1.196, 83.1 / 90.7** |

Runtime on R_01: 78 s against 60 s for pinhole at the same load (equidistant projection is costlier).

| raw fisheye, R_04 | k=0 3.478 | k=100 2.281 | (pinhole 0.982 / 0.659) | | | |
| raw fisheye, rays > 65 deg masked (033b) | R_01 0.306 / 0.354 | R_04 2.829 / 2.878 | | | | |

| ideal equidistant resample (033c, `scripts/fisheye_remap.py`, exact model, full FOV) | R_01 0.226 / 0.245 | R_04 2.309 / 1.447 | | | | |

**Decision**: discard fisheye as the default input. With an exact lens model R_04 is still 2.3 / 1.4 m against 1.0 / 0.7 m for pinhole and R_01 0.23 / 0.25 against 0.19 / 0.20; model fidelity explained only part of the loss, the outer field none of it. OpenVINS's KLT front-end simply does better on the undistorted pinhole images (uniform pixel footprint; the 758x572 canvas keeps most of the field anyway). R_11's gain (score 83 at both offsets) is an isolated case worth remembering. The pipeline stays (`vrs_to_runner_input.py`, `fit_fisheye_kb.py`, `fisheye_remap.py`); the fetch of the other nine `.vrs` was cancelled and the resampled frames deleted to save disk.

## 036: 8x8 extraction grid at the second offset, adoption as ov_ref005 (2026-10-02, pc, commit 3f3f3fc)

**Result** (ATE m sim3, per-sequence mean of offsets 0 and 100):

| Seq | R_01 | R_02 | R_03 | R_04 | R_05 | R_06 | R_07 | R_08 | R_09 | R_10 | R_11 | R_12 | R_13 | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ov_ref004 | 0.19 | 0.81 | 0.20 | 0.82 | 1.42 | 2.89 | 2.38 | 1.82 | 6.02 | 10.07 | 0.90 | 8.83 | 5.64 | 3.23 |
| grid 8x8 (ov_ref005) | 0.23 | **0.47** | 0.21 | 1.08 | 1.51 | **1.99** | 2.59 | 1.72 | **5.27** | **6.22** | **0.58** | 8.89 | 6.06 | **2.83** |

R_11 at offset 100: 0.476 m. R_13 offset 100: 6.94 m, score 29.8, recall @ 5 m 61.8 %.

**Decision**: keep; `configs/ov_ref005` = ov_ref004 + `grid_x: 8, grid_y: 8` is the reference. Mean −0.40 m over 26 runs, better on 6 of 13 but the gains are the large ones on the hard and long sequences (R_10 −3.9 m) and the losses are all inside the offset spread (R_04 +0.26, R_13 +0.42, R_07 +0.21). Rationale: with 400 features a 5x5 grid lets features clump on textured patches; 8x8 forces coverage of the periphery, which constrains rotation and reduces heading drift.

## 035: timing on R_01 (2026-10-02, pc; not at idle, load 19)

ov_ref001: 121 s wall, 108 MB; ov_ref004: 213 s wall, 109 MB, for 144.9 s of data (2898 frames), both at 95 to 104 % of one core while 13 other estimators ran. Relative cost of the kept changes (400 features + CLAHE): about 1.75x. At light load the original reference ran 2.4x faster than realtime (001), so ov_ref004 is roughly 1.4x realtime on one core of this PC; the Jetson budget needs a real idle measurement and a per-stage profile (front-end dominates).

## 032: 8x8 extraction grid, FAST 15 (2026-10-02, pc, commit 5abf68a; offset 0, second offset running as 036)

**Hypothesis**: a finer extraction grid spreads the 400 features over the image more evenly (fewer clumps on high-texture patches, more coverage of the periphery that constrains rotation); a lower FAST threshold adds features in low texture.

**Change** (one knob each from `ov_ref004`): `grid_x: 8, grid_y: 8` (grid8); `fast_threshold: 15` (fast15). `configs/explore-032/`.

**Result** (ATE m sim3, start offset 0):

| Seq | R_01 | R_02 | R_03 | R_04 | R_05 | R_06 | R_07 | R_08 | R_09 | R_10 | R_11 | R_12 | R_13 | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ov_ref004 | 0.191 | 0.693 | 0.223 | 0.982 | 1.462 | 3.683 | 3.445 | 2.470 | 5.938 | 10.021 | 0.740 | 9.079 | 6.544 | 3.50 |
| grid 8x8 | 0.289 | 0.584 | 0.216 | 1.480 | 1.307 | **2.081** | 3.203 | **1.484** | **3.843** | **6.102** | 0.684 | 9.211 | **5.188** | **2.74** |
| FAST 15 | 0.191 | 0.615 | 0.136 | 1.316 | 1.195 | 1.339 | 2.971 | 2.582 | 7.693 | 13.242 | 0.698 | 9.254 | 3.783 | 3.46 |

**Decision**: grid 8x8 is the strongest single-run signal so far (better on 10 of 13, mean −0.75 m, gains concentrated on the hard and long sequences); second offset on all 13 running (036) before adoption. FAST 15 is mixed (helps R_06/R_13, hurts R_09/R_10): discard.

## 031: factory-rectified IMU from the .vrs device calibration (2026-10-02, pc, commit 4f9e4ca)

**Hypothesis**: the ASL IMU is raw; applying the factory rectification (per-axis scale/misalignment and bias) from the `.vrs` should remove the suspected accelerometer scale error and give the initialiser a bias-free start.

**Finding first**: the factory calibration has no scale term worth the name (accel and gyro scale within 0.15 % of 1 on both devices seen) but a large accelerometer bias on the device used for R_01/R_04/R_11 (0.25 / 0.21 / 0.39 m/s^2; R_08's device is near zero). The online bias estimate had already converged near that value, so rectification mostly changes the first seconds.

**Change**: `scripts/rectify_imu_from_vrs.py` builds `data/training_rect/<seq>` (rectified `imu.csv`, everything else symlinked); `ov_ref004` on it.

**Result** (ATE m sim3; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| ov_ref004, raw IMU | 0.191 | 0.195 | 0.982 | 0.659 | 2.47 | 1.18 | 0.74, 72.4 / 88.9 | 1.06, 70.2 / 54.9 |
| ov_ref004, rectified IMU | 0.183 | 0.174 | 0.837 | 0.731 | 2.08 | 1.66 | 0.94, 69.2 / 62.8 | 1.07, 68.2 / 58.1 |

**Decision**: discard (neutral within the spread; per-sequence means 0.18 vs 0.19, 0.78 vs 0.82, 1.87 vs 1.83, 1.01 vs 0.90), and it would need a `.vrs` per sequence. The sim3 scale is unchanged (0.965 to 0.986), which closes the IMU side of the scale question: the 2 to 4 % is not a sensor calibration term. The `.vrs` files remain useful for the fisheye-input experiment.

## 028: dense feature grid (min feature distance 10 px) on all 13, two offsets (2026-10-02, pc, commit 4f9e4ca)

**Hypothesis**: the 025 single-run gains on R_06/R_07 generalise.

**Result** (ATE m sim3, per-sequence mean of offsets 0 and 100; reference ov_ref004 from 024/026):

| Seq | R_01 | R_02 | R_03 | R_04 | R_05 | R_06 | R_07 | R_08 | R_09 | R_10 | R_11 | R_12 | R_13 | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ov_ref004 | 0.19 | 0.81 | 0.20 | 0.82 | 1.42 | 2.89 | 2.38 | 1.82 | 6.02 | 10.07 | 0.90 | 8.83 | 5.64 | 3.23 |
| min distance 10 px | 0.20 | 0.72 | 0.20 | 1.29 | 1.44 | 1.72 | 2.12 | 2.80 | 3.74 | 12.20 | 0.89 | 9.03 | 4.92 | 3.17 |

**Decision**: discard (tie: 0.06 m, better on 7 of 13, with ±2 m swings both ways: R_09 −2.3, R_06 −1.2, R_08 +1.0, R_10 +2.1, R_04 +0.5). The 025 effect on R_06/R_07 was real but it costs the long sequences. Tracker knobs are at a plateau with this front-end; the next steps are structural (fisheye input, additional-set behaviour).

## 027: zero-velocity updates throughout, analytical IMU integration (2026-10-02, pc, commit b88fdf7)

**Hypothesis**: ZUPTs whenever the walker stops (`zupt_only_at_beginning: false`) would re-anchor biases and cut drift; analytical covariance propagation might be more accurate than RK4.

**Result**: both identical to the reference on every cell (4 sequences x 2 offsets): the ZUPT disparity test never passes while walking (head motion), and at 1 kHz IMU rate RK4 and analytical propagation agree to the printed precision.

**Decision**: discard both; no-ops on this data.

## 026: ov_ref003 vs ov_ref004 at two start offsets on all 13 controlled sequences (2026-10-02, pc, commit b88fdf7)

**Hypothesis**: the CLAHE decision (024 was 6 better / 7 worse on single runs) needs a second start offset per sequence to separate the effect from initialisation luck.

**Change**: none; start offset 100 for both configs on all 13 (ov_ref004 k=0 runs from 024 reused; R_01 ov_ref004 k=0 replaced by its 1 s grace rerun, 0.191, since the 024 value 1.434 was the 3 s grace artefact).

**Result** (ATE m sim3):

| Seq | ref003 k=0 | ref003 k=100 | ref004 k=0 | ref004 k=100 | per-seq mean ref003 | per-seq mean ref004 |
|---|---|---|---|---|---|---|
| R_01 | 0.254 | 0.239 | 0.191 | 0.195 | 0.25 | 0.19 |
| R_02 | 0.605 | 0.643 | 0.693 | 0.925 | 0.62 | 0.81 |
| R_03 | 0.287 | 0.169 | 0.223 | 0.184 | 0.23 | 0.20 |
| R_04 | 0.716 | 0.706 | 0.982 | 0.659 | 0.71 | 0.82 |
| R_05 | 1.347 | 1.321 | 1.462 | 1.385 | 1.33 | 1.42 |
| R_06 | 6.155 | 3.255 | 3.683 | 2.092 | 4.71 | 2.89 |
| R_07 | 3.896 | 2.091 | 3.445 | 1.308 | 2.99 | 2.38 |
| R_08 | 2.931 | 4.706 | 2.470 | 1.178 | 3.82 | 1.82 |
| R_09 | 4.977 | 6.464 | 5.938 | 6.110 | 5.72 | 6.02 |
| R_10 | 12.893 | 9.407 | 10.021 | 10.113 | 11.15 | 10.07 |
| R_11 | 2.618 | 1.578 | 0.740 | 1.061 | 2.10 | 0.90 |
| R_12 | 8.296 | 7.801 | 9.079 | 8.578 | 8.05 | 8.83 |
| R_13 | 3.551 | 6.388 | 6.544 | 4.742 | 4.97 | 5.64 |
| **mean** | 3.73 | 3.44 | 3.50 | 2.96 | **3.59** | **3.23** |

**Decision**: keep CLAHE; `configs/ov_ref004` is the reference. Over 26 runs it is 0.36 m better on average, with large gains where it matters (R_06 −1.8, R_08 −2.0, R_11 −1.2 m) and small losses on five sequences that are inside the offset spread. Also note how large the offset spread is on the long sequences (R_13 3.6 vs 6.4 for the same config): from now on a change is judged on the two-offset mean over all 13, never on single runs.

## 025: tracker knobs for texture-poor stretches (2026-10-02, pc, commit c7b9614)

**Hypothesis**: heading drift through texture-poor stretches (R_06 diagnostic) comes from too few or too short feature tracks there; a lower FAST threshold, a denser feature grid, or more SLAM landmarks in the state should help.

**Change** (one knob each from `ov_ref004`, i.e. with CLAHE): `fast_threshold: 10` (fast10), `min_px_dist: 10` (pxdist10), `max_slam: 100` + `max_slam_in_update: 50` (slam100). Four hardest sequences, start 0, single runs.

**Result** (ATE m sim3; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_06 | R_07 | R_08 | R_11 |
|---|---|---|---|---|
| ov_ref004 (024) | 3.683 | 3.445 | 2.47 | 0.74, 72.4 / 88.9 |
| FAST 10 | 4.548 | 2.975 | **1.199** | 1.236, 60.8 / 42.8 |
| min feature distance 10 px | **0.991** | **1.374** | 4.228 | 0.993, 68.9 / 66.9 |
| 100 SLAM features | 3.919 | 3.624 | 2.207 | 1.172, 61.0 / 41.1 |

**Decision**: the dense grid is the most promising change since 400 features (R_06 and R_07 by 2.5 to 3.7 m); FAST 10 helps R_08 a lot but hurts two others; 100 SLAM features is mixed. Validate the dense grid on all 13 sequences (028) before adopting; then FAST 10 on top if 028 holds.

## 024: ov_ref004 (= ov_ref003 + CLAHE) on all 13 controlled sequences (2026-10-02, pc, commit c7b9614)

**Hypothesis**: CLAHE, which won 7 of 8 cells on the 4-sequence set (018), generalises to the whole controlled set.

**Change**: `configs/ov_ref004`, start 0, single run per sequence; runner now has the 3 s re-init grace period (not in 018).

**Result** (ATE m sim3; ov_ref003 from 022 for comparison):

| Seq | R_01 | R_02 | R_03 | R_04 | R_05 | R_06 | R_07 | R_08 | R_09 | R_10 | R_11 | R_12 | R_13 | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ov_ref003 | 0.254 | 0.605 | 0.287 | 0.716 | 1.347 | 6.155 | 3.896 | 2.93 | 4.977 | 12.893 | 2.62 | 8.296 | 3.551 | 3.73 |
| ov_ref004 (CLAHE) | 1.434 (1 re-init) | 0.693 | 0.223 | 0.982 | 1.462 | **3.683** | **3.445** | **2.47** | 5.938 | **10.021** | **0.74** | 9.079 | 6.544 | 3.59 |

R_11: score 72.4, recall @ 1 m 88.9 %. R_12: score 12.8, recall @ 5 m 29.4 %. R_13: score 29.4, recall @ 5 m 68.9 % (ov_ref003: 39.1, 92.5 %).

**Grace-period check** (R_01, CLAHE, k=0): grace 0 s and 1 s both give 0.191 m with one re-init 1.6 s after init; grace 3 s gives 1.434 m. A large jump right after initialisation is a real bad-init signal, so the runner default is now 1 s (026 onwards).

**Decision**: not adopted yet. Better on 6, worse on 7; the mean gain (3.59 vs 3.73) is inside single-run noise, and the two biggest losses need explanation: R_01 (0.25 to 1.43) was the 3 s grace period (above), and R_13 (3.6 to 6.5, recall @ 5 m 92 to 69 %) is a single long run that may be init luck. Next: both references at a second start offset on all 13 sequences (026) before deciding, and the grace period re-examined.

## Diagnostic: revisit structure and drift rate of the long controlled sequences (2026-10-02)

Loop closure was the planned big-ticket item for long sequences. Measured on the pGT: fraction of samples within 3 m of a point visited more than 60 s earlier is 0.00 (R_08), 0.05 (R_10), 0.00 (R_12), 0.01 (R_13). The controlled set has essentially no loops, so loop closure cannot reduce these ATEs. Local drift of ov_ref003 (sim3-aligned 100 m windows, end-point error): median 0.34 / 0.84 / 0.59 / 0.42 % per 100 m, 90th percentile 0.9 to 1.4 %. The ATE of 3 to 13 m over 0.7 to 1.3 km is accumulated heading drift from a decent odometry. Consequences: on the controlled set, work on drift (gyro-bias estimation, feature lifetime in texture-poor stretches, IMU model from the factory calibration); check the additional-set sequences for loops when they arrive before investing in loop closure.

## 023: bidirectional pass over the sequence start (2026-10-02, pc, commit a1bb2c6; closed)

**Hypothesis**: the first minute after initialisation dominates the ATE (022 diagnostic); running a second estimator on the time-reversed first W seconds, which starts where the forward run is converged, and stitching it onto the forward trajectory on a window where both are converged, should remove most of that early error. Non-causal; benchmark use only, flagged as such on any submission.

**Change**: `scripts/run_sequence_bidir.sh` (forward run, reversed input via `make_reversed_input.py` with gyro negated, backward run with the same yaml, Sim3 stitch on [t0+80, t0+140] s, crossover at t0+110 s, W = 200 s). First attempt used W = 120 and aligned inside the backward run's own unconverged minute (no gain, 6.06 m); corrected parameters below.

**Result so far** (ATE m sim3):

| Sequence | forward only (ov_ref003) | bidirectional W=200 | stitch overlap RMSE |
|---|---|---|---|
| R_04_medium | 0.716 | 0.770 | 0.09 m |
| R_06_medium | 6.155 | 5.758 | 0.18 m |
| R_07_medium | 3.896 | 3.886 | 0.17 m |
| R_08_hard | 2.931 | 3.023 | 0.23 m |
| R_11_5cp | 2.618 | 2.672 (score 40.7) | 0.09 m |

**Diagnostic that changed the picture**: on R_06 the error profile after aligning on t > 80 s is a smooth ramp (19 m at t = 0 down to 1.3 m at 120 s) and the backward run shows the same ramp. That is a heading error accumulated in the first 80 s, not an initialisation transient: image sharpness collapses between 30 and 60 s (Laplacian variance 5 to 9 against 40 to 140 later) with only 7 to 9 MSCKF features, so heading rests on the gyro there, and the drift is the same in both directions. A gyro scale error was ruled out (integrated gyro versus pGT rotation: 0.985 to 1.03, R_11 1.003 with a tight spread). So this is genuine visual-inertial drift through a texture-poor stretch that happens to be early in R_06; the bidirectional pass cannot remove it, only re-distribute it.

**Decision**: discard. No gain on five sequences (within ±0.1 m except R_06, −0.4 m). The 'first minute dominates' reading of 022 was a misinterpretation: aligning on t > 80 s makes the start look worst simply because it is farthest in time from the alignment window, i.e. this is ordinary drift. The scripts stay (useful for other offline experiments). What remains true: texture-poor stretches drive heading drift (R_06), and the remedy is a better tracker there and loop closure, not initialisation work.

## 022: reference on the whole controlled set (2026-10-02, pc, commit 6d6abc8)

**Hypothesis**: the reference (`ov_ref003`) should be at open-baseline level across all controlled sequences, not only the four used so far; and the per-sequence pattern tells where the losses are.

**Change**: none; `ov_ref003`, start offset 0, single run per sequence (R_13 still running when this was written). Paper Table 2 values for comparison (stereo+IMU rows).

**Result** (ATE m sim3; sim3 scale in brackets for ours):

| Sequence | ours ov_ref003 | OpenVINS (paper) | OpenVINS+Maplab (paper, leaderboard open baseline) | OKVIS2 (paper) |
|---|---|---|---|---|
| R_01_easy | 0.254 (0.983) | 0.66 | 0.65 | 0.02 |
| R_02_easy | 0.605 (0.908) | 2.36 | 2.30 | 0.72 |
| R_03_easy | 0.287 (0.973) | 0.68 | 0.68 | 0.03 |
| R_04_medium | 0.716 (0.962) | 0.94 | 1.05 | 1.36 |
| R_05_medium | 1.347 (0.991) | 1.43 | 1.22 | 0.80 |
| R_06_medium | 6.155 (0.998) | 1.35 | 1.19 | 3.78 |
| R_07_medium | 3.896 (0.980) | 2.96 | 2.01 | fail |
| R_08_hard | 2.93 (0.973) | 4.25 | 3.97 | 6.81 |
| R_09_hard | 4.977 (0.983) | 4.31 | 4.29 | 5.32 |
| R_10_hard | 12.893 (0.972) | 8.01 | 8.22 | 7.06 |
| R_11_5cp | 2.62 (0.971) | 1.04 | 1.62 | 1.85 |
| R_12_10cp | 8.296 (0.953) | 18.72 | 16.59 | 16.55 |
| R_13_15cp | 3.551 (0.966) | 10.35 | 8.37 | 6.65 |
| mean of 13 | **3.73** | 4.39 | 4.01 | - |

R_12_10cp leaderboard-style metrics: score 2D 15.9, pose recall @ 5 m 30.3 %, @ 1 m 7.0 % (1012 s). R_13_15cp: score 2D 39.1, pose recall @ 5 m 92.5 %, @ 1 m 10.1 % (1404 s, 1941 s wall under load). Runtime under load (9 to 16 concurrent runs): R_10 (934 s) took 1358 s wall, i.e. slower than realtime when sharing the machine; at idle the reference runs about 2x realtime.

**Where the error is**: aligning each trajectory only on t > 80 s, the remainder is 1.6 (R_06), 2.9 (R_07), 2.5 (R_08), 0.6 (R_04) m RMSE while the first 20 to 40 s are 8 to 19 m off. The first minute after initialisation (biases and velocity still converging, no smoothing) dominates the ATE of every medium and hard sequence; the losses against the open baseline are exactly those sequences.

**Decision**: the reference is ahead of the open baseline on the controlled set as a whole (mean 3.73 vs 4.01 m over 13 sequences, better on 7 of 13, including the two longest). The next lever is the initial segment: experiment 023 (bidirectional pass, non-causal, benchmark-only) and later a causal improvement of the initialiser. Also to note: R_02's scale 0.908 and R_12's 0.953 are the worst scale cases; R_12 at 1012 s is the first sequence where pose recall @ 5 m is far from 100 %.

## 020 / 021: dynamic-init MLE off, or to full convergence (2026-10-02, pc, commit a1bb2c6)

**Hypothesis**: 016 showed R_11 flips between 0.8 and 2.6 m depending on how far the init MLE runs; either skipping the refinement (closed-form init only, `init_dyn_mle_max_iter: 0`) or running it to convergence (200 iterations) might give a more reliable initial state.

**Change**: one knob each from `ov_ref003` (`configs/explore-020/mle0`, `configs/explore-021/mle200`).

**Result** (ATE m sim3, sim3 scale, re-inits; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference ov_ref003 (50 iter) | 0.254 | 0.239 | 0.716 | 0.706 | 2.93 | 4.71 | 2.62, 41.3 / 3.4 | 1.58, 59.6 / 27.9 |
| MLE off | 0.368, 1 re-init | 0.237 | 0.590 | 0.712 | 2.88 | 2.10, 2 re-inits | 2.62, 41.4 / 3.6 | 2.27, 54.0 / 17.6, 3 re-inits |
| MLE 200 iter | 0.254 | 0.239 | 0.716 | 0.706 | 2.93 | 4.71 | 2.62, 41.3 / 3.4 | 1.58, 59.6 / 27.9 |

**Decision**: discard both. 200 iterations is identical to 50 (the MLE converges). Without the MLE the closed-form init is poorer and the runner's divergence detector then fires 1 to 3 times, after which the result is sometimes better (R_08 k=100: 2.10, the best at that offset) and sometimes worse (R_01 k=0); not a consistent gain, but a useful observation: a re-init a few seconds in is cheap and the detector is doing its job.

## 018 / 019: CLAHE, and 2 px measurement noise (2026-10-02, pc, commit a1bb2c6)

**Hypothesis**: (018) CLAHE instead of global histogram equalisation gives KLT more local contrast in the dark and uneven frames; (019) the undistorted wide-angle images may deserve a larger pixel noise than 1 px.

**Change** (one knob each from `ov_ref003`): `histogram_method: "CLAHE"` (`configs/explore-018/clahe`); `up_msckf_sigma_px: 2`, `up_slam_sigma_px: 2` (`configs/explore-019/sigma2`).

**Result** (ATE m sim3, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference ov_ref003 | 0.254 (0.983) | 0.239 (0.979) | 0.716 (0.962) | 0.706 (0.964) | 2.93 (0.973) | 4.71 (0.959) | 2.62 (0.971), 41.3 / 3.4 | 1.58 (0.969), 59.6 / 27.9 |
| CLAHE | **0.191** (0.969), 1 re-init | **0.195** (0.978) | 0.982 (0.975) | **0.659** (0.963) | **2.47** (0.974) | **1.18** (0.980) | **0.74** (0.970), **72.4 / 88.9** | **1.06** (0.973), **70.2 / 54.9** |
| sigma 2 px | 0.363 (0.960) | 0.420 (0.958) | 0.982 (0.938) | 1.777 (0.945) | 4.33 (0.945) | 3.71 (0.946) | 1.82 (0.942), 53.5 / 20.2 | 2.55 (0.951), 43.0 / 7.9 |

**Decision**: keep CLAHE (better in 7 of 8 cells, R_08 k=100 and R_11 k=0 are the best values seen for those sequences); becomes `configs/ov_ref004`, validated on all 13 controlled sequences in 024. The one re-init on R_01 k=0 ended well (0.191) but needs a look: a false trigger costs ~2 s of poses. Discard sigma 2 px (worse everywhere, scale worse).

## 017: focal length x0.965, stereo-side scale probe (2026-10-02, pc, commit 6d6abc8)

**Hypothesis**: if the undistorted pinhole focal length in the calibration were 3.5 % larger than the true focal of the images, stereo depth and hence the trajectory would be 3.5 % too large; scaling both focal lengths by 0.965 would then bring the sim3 scale to 1.

**Change**: `FOCAL_SCALE=0.965` (`configs/explore-017/focal0965`) from `ov_ref002`.

**Result** (ATE m sim3, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference ov_ref002 | 0.300 (0.982) | 0.281 (0.979) | 0.736 (0.962) | 1.078 (0.952) | 4.46 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | 2.84 (0.964), 38.9 / 0.2 |
| focal x0.965 | 0.901 (1.016) | 0.856 (1.018) | 2.07 (1.071) | 2.71 (1.065) | 5.56 (1.109) | 12.03 (1.170) | 1.67 (1.068), 56.6 / 28.5 | 46.0 diverged |

**Decision**: discard. The scale overshoots to 1.02 to 1.17 and accuracy collapses: the calibration focal is right, and the filter is far more sensitive to the focal than a 3.5 % stereo-scale error would imply. Closes the stereo side of the scale investigation; the accelerometer model (011, 015) remains the only consistent explanation.

## 016: ov_ref003 = ov_ref002 + 400 features, validation (2026-10-02, pc, commit d06be7f)

**Hypothesis**: combining the kept changes (re-init, iteration-bounded init, 400 features) reproduces the 012 numbers.

**Result** (ATE m sim3, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Config | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| 012 pts400 (time-bounded init) | 0.254 | 0.239 | 0.716 | 0.706 | 2.93 | 4.71 | 0.81 (0.965), 69.5 / 78.5 | 0.75 (0.972), 69.7 / 77.3 |
| ov_ref003 (iteration-bounded init) | 0.254 (0.983) | 0.239 (0.979) | 0.716 (0.962) | 0.706 (0.964) | 2.93 (0.973) | 4.71 (0.959) | 2.62 (0.971), 41.3 / 3.4 | 1.58 (0.969), 59.6 / 27.9 |

**Decision**: keep ov_ref003 as the reference (R_01/R_04/R_08 identical to 012, all better than ov_ref002), but the R_11 lesson is important: the only difference is that the dynamic-init MLE now runs to its iteration cap instead of being cut at 50 ms, and that alone turns R_11 from 0.8 m into 1.6 to 2.6 m. R_11's result is decided by initialisation luck, not by tracking. The 012 R_11 numbers are therefore not a reliable property of "400 features". Next: initialiser variants that change what the MLE does (020: no MLE refinement, closed-form init only; 021: MLE to full convergence), and a look at why R_11's first seconds are hard (it starts at true rest; a static init might be the better path there).

## 015: stereo off + accelerometer scale 1.03 (2026-10-02, pc, commit d06be7f)

**Hypothesis**: if the sim3-ATE degradation in 011 came from the corrected IMU disagreeing with the stereo scale, removing the stereo constraints (scale from the corrected IMU alone) should give scale 1 and reference-level sim3 ATE.

**Change**: `use_stereo: false` + `ACC_SCALE=1.03` (`configs/explore-015/nostereo_acc103`).

**Result** (ATE m sim3, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| stereo off (007) | 0.358 (0.986) | 0.369 (0.984) | 0.774 (0.960) | 0.920 (0.966) | 3.50 (0.966) | 5.36 (0.968) | 1.62 (0.970), 50.8 / 9.2 | 1.50 (0.967), 55.1 / 19.3 |
| stereo off + acc 1.03 | 0.355 (1.007) | 0.404 (1.008) | 1.033 (0.995) | 1.324 (0.997) | 2.80 (0.999) | 4.63 (0.999) | 3.34 (0.993), 32.4 / 3.9 | 2.03 (0.991), 45.0 / 9.3 |

**Decision**: discard. The metric scale is right with the correction (0.99 to 1.01, IMU-only), but sim3 ATE is still worse on R_04 and R_11, so the loss is not a stereo-versus-IMU conflict: a single uniform factor is the wrong IMU model (per-axis scale and misalignment differ, and R_04's rest magnitude reads low rather than high). Conclusion of the scale investigation (004 to 015): the 2 to 4 % metric scale error comes from the raw, unrectified Aria accelerometer; fixing it properly needs the factory IMU rectification from the `.vrs` device calibration (not in the JSON calibrations we have). For the leaderboard metrics (Sim3 alignment on control points) the global scale is forgiven, so this is parked until the `.vrs` files are available; for the robot it matters and is noted in `purpose.md` terms as a calibration-quality lesson.

## 014: initialiser window 4 s or 100 init features (2026-10-02, pc, commit d06be7f)

**Hypothesis**: R_11 swings 0.85 to 3.2 m with the start offset, so a longer dynamic-init window (`init_window_time: 4.0`) or more init features (`init_max_features: 100`) might make the initial state more reliable.

**Change**: one knob each from `ov_ref002` (`configs/explore-014/`).

**Result** (ATE m sim3, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference ov_ref002 | 0.300 (0.982) | 0.281 (0.979) | 0.736 (0.962) | 1.078 (0.952) | 4.46 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | 2.84 (0.964), 38.9 / 0.2 |
| init window 4 s | 0.247 (0.992) | 0.418 (0.971) | 0.868 (0.964) | 0.721 (0.958) | 4.10 (0.971) | 4.16 (0.964) | 2.59 (0.970), 40.3 / 2.6 | 1.88 (0.964), 53.0 / 35.3 |
| init features 100 | 0.235 (0.990) | 0.361 (0.976) | 0.577 (0.957) | 0.795 (0.955) | 6.89 (0.964) | 3.86 (0.974) | 2.98 (0.956), 38.1 / 1.2 | 1.92 (0.958), 53.3 / 32.3, 1 re-init |

**Decision**: discard both; every cell moves within the start-offset spread, in both directions. The initial state is not improved by a longer window or more init features; the 400-feature change (012) did far more for R_11 than any init knob.

## 013: ov_ref002 = ov_ref001 + re-init + load-independent initialisation (2026-10-02, pc, commit d06be7f)

**Hypothesis**: bounding the dynamic initialiser by iterations (`init_dyn_mle_max_time: 10`, `init_dyn_mle_max_threads: 1`) instead of 50 ms of wall clock, plus the runner re-init of 009, gives the same accuracy as ov_ref001 with reproducible, load-independent results.

**Result**: identical to the reference in every cell (R_01 0.300 / 0.281, R_04 0.736 / 1.078, R_08 4.46 / 3.59, R_11 1.36 / 2.84 with score 58.9 / 38.9), 0 re-inits. The MLE evidently converged inside 50 ms at this load anyway; the change protects against the case where it does not.

**Decision**: keep; `configs/ov_ref002` is the reference from here (numbers unchanged from 001/002), `ov_ref003` adds the 400 features from 012 and is validated in 016.

## 012: tracking capacity, 400 features or 15 clones (2026-10-02, pc, commit a09458c)

**Hypothesis**: more tracked features (better-conditioned updates, more SLAM landmarks) or a longer sliding window should reduce drift; cost is front-end time.

**Change** (one knob each from `ov_ref001`): `num_pts: 400` (pts400) or `max_clones: 15` (clones15), `configs/explore-012/`.

**Result** (ATE m sim3, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference (200 pts, 11 clones) | 0.301 (0.982) | 0.281 (0.979) | 0.739 (0.962) | 1.078 (0.952) | 4.49 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | 2.84 (0.964), 38.9 / 0.2 |
| 400 features | **0.254** (0.983) | **0.239** (0.979) | **0.716** (0.962) | **0.706** (0.964) | **2.93** (0.973) | 4.71 (0.959) | **0.81** (0.965), **69.5 / 78.5** | **0.75** (0.972), **69.7 / 77.3** |
| 15 clones | 0.644 (0.969) | 0.206 (0.976) | 0.647 (0.960) | 0.779 (0.955) | 5.06 (0.966) | 3.52 (0.977) | 2.29 (0.962), 43.6 / 8.4 | 2.61 (0.960), 40.8 / 1.7 |

**Cost**: R_08 wall 629 s (pts400) and 585 s (clones15) against 274 s for the reference, but these ran with 16 to 24 estimators sharing 16 cores, so the ratio is not clean; a dedicated timing run at idle is owed before the config goes near the Nano.

**Decision**: keep 400 features (better on 7 of 8 cells, R_11 best so far and stable across offsets; the one worse cell, R_08 k=100, is inside the start-offset spread). Discard 15 clones (mixed, worse on R_11). Scale unchanged by either, as expected. 400 features goes into `configs/ov_ref003` (= ov_ref002 + num_pts 400), validated as experiment 016.

## 011: accelerometer scale factor 1.03 (2026-10-02, pc, commit a09458c)

**Hypothesis**: the Aria IMU in the ASL files is raw (no factory rectification) and reads about 1.03 g at rest, and 007 showed the IMU-derived scale is 2 to 4 % too large; dividing the accelerometer by 1.03 (kalibr `Ta = 1.03 I`, applied by OpenVINS as 1/k) should bring the metric scale to 1.

**Change**: `ACC_SCALE=1.03` (`configs/explore-011/acc103`), everything else as `ov_ref001`.

**Result** (ATE m sim3, sim3 scale; SE3 ATE = no scale fit; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference | 0.301 (0.982) | 0.281 (0.979) | 0.739 (0.962) | 1.078 (0.952) | 4.49 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | 2.84 (0.964), 38.9 / 0.2 |
| acc scale 1.03 | 0.375 (1.002) | 0.320 (1.000) | 0.878 (0.991) | 1.026 (0.986) | 5.68 (0.988) | 6.74 (0.993) | 3.35 (0.988), 33.3 / 0.6 | 5.43 (0.951) |

SE3 ATE (k=0): R_01 0.336 → 0.376, R_04 2.09 → 0.99, R_08 7.00 → 5.93, R_11 4.64 → 3.53. Control-point Sim3 scale on R_11: 0.955 → 0.990.

**Decision**: the hypothesis is confirmed for the scale (sim3 scale 0.99 to 1.00 everywhere, SE3 errors much lower), but the sim3 ATE and the R_11 score get worse, so it is not adopted as is. Reading: the corrected IMU scale now disagrees with the stereo scale, which 007 showed to be equally 3 to 4 % large on its own. Either the stereo baseline in the calibration is off by the same amount (unlikely by coincidence) or the raw-IMU scale error is not a uniform factor. Next: 015 = stereo off + accelerometer correction (IMU-only scale, corrected); if that gives scale 1 and reference-level sim3 ATE, the stereo geometry is the remaining conflict.

## 010: fixed camera-IMU time offset +4.3 ms (2026-10-02, pc, commit a09458c)

**Hypothesis**: with online offset calibration the baseline runs converged to about +4.3 ms; fixing that value (instead of 0) might improve accuracy without the instability of estimating it online.

**Change**: `TIMESHIFT=0.0043` written as `timeshift_cam_imu` (`configs/explore-010/dt4`), offset calibration still off.

**Result** (ATE m, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference dt=0 | 0.301 (0.982) | 0.281 (0.979) | 0.739 (0.962) | 1.078 (0.952) | 4.49 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | 2.84 (0.964), 38.9 / 0.2 |
| dt = +4.3 ms | 0.419 (0.980) | 0.256 (0.981) | 1.718 (0.939) | 2.198 (0.941) | 6.36 (0.961) | 6.82 (0.962) | 3.17 (0.974), 36.7 / 0.7 | 0.85 (0.976), 68.7 / 87.9 |

**Decision**: discard; worse on R_04 and R_08 by more than the spread. Side finding: R_11 at offset 100 reached 0.85 m / score 68.7 / recall @ 1 m 87.9, the best R_11 run so far, while offset 0 gave 3.2 m with the same config. R_11's outcome is dominated by how well the first seconds initialise; initialisation quality (window length, features) is the next lever (014).

## 009: divergence detection with re-initialisation (2026-10-02, pc, commit a09458c)

**Hypothesis**: divergence is silent (poses keep coming while the trajectory flies off) and costs the whole remainder of a sequence; detecting it from the state speed or a per-frame jump, rebuilding the estimator, and stitching the new segment onto the last good pose should bound the damage without hurting runs that never diverge.

**Change**: runner-level check after every update: speed above `reinit_max_velocity` (6 m/s) or per-frame jump above `reinit_max_jump` (1 m) rebuilds the VioManager, replays the last 3 s of IMU, and maps the new local frame onto the last good pose. Config `configs/explore-009/reinit` (= ov_ref001 + the three keys); `n3d_reinit` applies the same to the x3 config that diverged in 005.

**Result** (ATE m, sim3 scale, number of re-inits):

| Run | reference (005 for x3) | with re-init |
|---|---|---|
| R_01 k=0 / k=100 | 0.301 / 0.281 | 0.300 / 0.281, 0 re-inits |
| R_04 k=0 / k=100 | 0.739 / 1.078 | 0.736 / 1.078, 0 re-inits |
| R_08 k=0 / k=100 | 4.49 / 3.59 | 4.47 / 3.59, 0 re-inits |
| R_11 k=0 / k=100 | 1.36 (58.9 / 35.8) / not run | 1.36 (58.9 / 35.8) / 2.84 (38.9 / 0.2), 0 re-inits |
| R_08 x3 k=100 | 67.6 diverged | 11.4, 1 re-init at 490 s (speed 6.0 m/s) |
| R_11 x3 k=100 | 29.6 diverged | 2.30, 0 re-inits (see below) |

**Determinism finding**: the R_11 x3 k=100 run did not diverge this time, with no re-init. Two further parallel reruns of the exact 005 configuration both give 2.304 m, identical to each other but not to the 005 run, and the first pose differs: the 005 run initialised 0.25 s later. OpenVINS's dynamic initialiser has a wall-clock budget (`init_dyn_mle_max_time: 0.05` s), so under heavier CPU load (005 ran 16 jobs alongside 004) it does fewer optimisation iterations and initialises differently. Consequences: (1) results are reproducible only at equal machine load; (2) part of the divergence seen in 005 was a load artefact; (3) on the robot the initialisation quality would depend on CPU load. Fix queued as 013: `init_dyn_mle_max_time` raised so the iteration cap (`init_dyn_mle_max_iter: 50`) is what bounds it, single-threaded MLE.

**Cost**: none measurable when no re-init fires; a re-init costs about 2 s of poses (filled by carry-forward in the submission) plus the initialisation window.

**Decision**: keep the mechanism (no false triggers in 8 runs, saves the one real divergence). Thresholds are walking-specific (6 m/s); for moving-platform sequences a speed threshold will need to be higher or replaced by a consistency check. Becomes part of the next reference (013).

## 008: IMU white-noise densities x20 (2026-10-02, pc, commit a09458c)

**Hypothesis**: 005 showed less inflation (x3, x5) is worse than x10; if the trend is monotonic, x20 is better still.

**Change**: `NOISE_SCALE=20`, walks unchanged (`configs/explore-008/n20d`).

**Result** (ATE m, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference x10 | 0.301 (0.982) | 0.281 (0.979) | 0.739 (0.962) | 1.078 (0.952) | 4.49 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | not run |
| x20 | 0.331 (0.963) | 0.328 (0.965) | 0.740 (0.942) | 1.632 (0.931) | 4.09 (0.964) | 3.57 (0.970) | 3.00 (0.967), 41.0 / 7.1 | 0.95 (0.961), 66.4 / 63.7 |

**Decision**: discard. Not monotonic: x20 degrades the scale on R_01 and R_04 (0.93 to 0.965) and makes R_11 swing 3x between start offsets. x10 stays. Scale versus IMU weighting across 005/008 on R_01: x3 0.989, x5 0.991, x10 0.982, x20 0.963, so trusting the IMU more does pull the scale toward 1 on the easy sequence, but at the price of divergence on the others; a proper fix must address the IMU model, not the weighting.

## 007: stereo constraints off, scale from the IMU alone (2026-10-02, pc, commit 5bac949)

**Hypothesis**: if the systematic scale overestimate comes from the stereo geometry (baseline or focal length), running the two cameras as independent monocular trackers (`use_stereo: false`) so that metric scale comes only from the IMU should remove it.

**Change**: `use_stereo: false` from `ov_ref001` (`configs/explore-007/nostereo`).

**Result** (ATE m, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference (stereo) | 0.301 (0.982) | 0.281 (0.979) | 0.739 (0.962) | 1.078 (0.952) | 4.49 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | not run |
| stereo off | 0.358 (0.986) | 0.369 (0.984) | 0.774 (0.960) | 0.920 (0.966) | 3.50 (0.966) | 5.36 (0.968) | 1.62 (0.970), 50.8 / 9.2 | 1.50 (0.967), 55.1 / 19.3 |

**Cost**: slower (465 s for R_08 against ~300 s) because both cameras run full monocular tracking.

**Decision**: discard as a config, but the diagnostic answer is clear: the scale error is the same without stereo, so it is not the stereo baseline or focal length. The metric scale that the IMU provides is itself 2 to 4 % too large. Next: the Aria IMU data in the ASL folders is raw (projectaria_tools delivers it without the factory rectification), and R_11 reads 1.026 g at true rest; experiment 011 applies a fixed accelerometer scale correction (Ta = 1.03 I, OpenVINS divides the measurement by it).

## 006: online IMU intrinsic calibration (2026-10-02, pc, commit 5bac949)

**Hypothesis**: the Aria IMU data in the ASL files is raw (projectaria_tools `accel_msec2` without rectification), and the accelerometer magnitude at rest differs per recording by up to 2.6 %, so letting OpenVINS estimate the IMU scale/skew matrices online (`calib_imu_intrinsics: true`, kalibr model) might remove the systematic scale error.

**Change**: `calib_imu_intrinsics: true` from `ov_ref001` (`configs/explore-006/imuintr`).

**Result** (ATE m, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference | 0.301 (0.982) | 0.281 (0.979) | 0.739 (0.962) | 1.078 (0.952) | 4.49 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | not run |
| IMU intrinsics online | 0.375 (0.985) | 0.302 (0.980) | 0.667 (0.945) | 0.360 (0.950) | 6.60 (0.960) | 3.37 (0.976) | 1.63 (0.963), 55.7 / 24.3 | 1.62 (0.961), 54.0 / 17.6 |

**Decision**: discard. Scale unchanged (0.945 to 0.985), results inside the start-offset spread and inconsistent across sequences (better on R_04, worse on R_01 and R_11). The raw-IMU scale hypothesis does not explain the error.

## 005: IMU white-noise densities x3 and x5 instead of x10 (2026-10-02, pc, commit 5bac949)

**Hypothesis**: with densities x10 the filter trusts vision over the IMU; trusting the IMU more (x3, x5) should pull the metric scale toward 1 and reduce the systematic scale overestimate.

**Change**: `NOISE_SCALE=3` (n3d) or `5` (n5d), random walks unchanged (`configs/explore-005/`). Standard set is now 4 sequences (R_11_5cp added) x 2 offsets.

**Result** (ATE m, sim3 scale; R_11 also score 2D / pose recall @ 1 m):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 | R_11 k=0 | R_11 k=100 |
|---|---|---|---|---|---|---|---|---|
| reference x10 | 0.301 (0.982) | 0.281 (0.979) | 0.739 (0.962) | 1.078 (0.952) | 4.49 (0.964) | 3.59 (0.974) | 1.36 (0.954), 58.9 / 35.8 | not run |
| x3 | 0.277 (0.989) | 0.289 (0.985) | 1.255 (0.958) | 1.426 (0.952) | 7.77 (0.955) | diverged | 2.83 (0.948), 39.6 / 1.2 | diverged |
| x5 | 0.323 (0.991) | 0.311 (0.986) | 1.175 (0.960) | 1.399 (0.953) | 5.89 (0.968) | diverged | 2.01 (0.955), 46.6 / 12.1 | 2.75 (0.952), 40.8 / 3.1 |

**Decision**: discard. Less inflation is worse on every sequence beyond R_01 and brings back divergence (3 of 16 runs). Scale is unchanged, so the scale overestimate is not a question of IMU-versus-vision weighting. Follow-up: x20 (experiment 008), since the trend is monotonic in the other direction. The divergences (silent, at a particular start offset) renew the case for divergence detection with re-initialisation.

## 004: online camera extrinsic / intrinsic refinement (2026-10-02, pc, commit 5bac949)

**Hypothesis**: the systematic scale overestimate (estimated path 2 to 4 % too long, sim3 scale 0.95 to 0.98 in every run) could come from a slightly wrong stereo geometry; letting OpenVINS refine the camera extrinsics or intrinsics online would then pull the scale toward 1.

**Change** (one knob per variant, from `ov_ref001`): `calib_cam_extrinsics: true` (variant extr) or `calib_cam_intrinsics: true` (variant intr). Configs in `configs/explore-004/`.

Command: `SKIP_FRAMES=k DROP_PRE_INIT=1 scripts/run_sequence.sh configs/explore-004/<v> data/training/<seq> results/004-scale/<seq>_<v>_skip<k>` for k in 0, 100.

**Result** (ATE m, sim3 scale in brackets; reference = 002 rows for the same offsets):

| Variant | R_01 k=0 | R_01 k=100 | R_04 k=0 | R_04 k=100 | R_08 k=0 | R_08 k=100 |
|---|---|---|---|---|---|---|
| reference ov_ref001 | 0.301 (0.982) | 0.281 (0.979) | 0.739 (0.962) | 1.078 (0.952) | 4.49 (0.964) | 3.59 (0.974) |
| extrinsics online | 0.345 (0.984) | 0.343 (0.983) | 0.489 (0.964) | 1.265 (0.954) | 7.18 (0.966) | 4.78 (0.977) |
| intrinsics online | 0.461 (0.994) | 0.412 (0.984) | 0.896 (0.961) | 1.294 (0.951) | 9.73 (0.945) | 6.65 (0.959) |

**Cost**: same runtime as the reference.

**Decision**: discard both. Neither changes the scale (intrinsics only on R_01, and at the cost of accuracy), and both are worse on the long sequence. The scale error is not something the filter can calibrate away online with these knobs. Control-point check (003): the Sim3 scale against surveyed points on R_11 is 0.955, same as against the pseudo-GT, so the error is really in our estimate.

## 003: first control-point sequence, leaderboard metrics locally (2026-10-02, pc, commit 2ecc5c2 + evaluate.py fix)

**Hypothesis**: the harness can produce the leaderboard's main-set metrics (score 2D, CP recall @ 1 m, pose recall @ 5 m) on a training sequence with control points, so that from now on every change is reported in those terms as well as ATE.

**Change**: none to the estimator (`ov_ref001`). `scripts/evaluate.py` now runs the control-point triangulation, Sim3 alignment, score and recalls inline (the official script's steps), because reloading its `.npy` output loses the control-point classes.

Command: `scripts/run_sequence.sh configs/ov_ref001 data/training/R_11_5cp results/003-cp-eval/R_11_5cp` (aria calibration JSON picked up automatically from `data/training/R_11_5cp/aria_calibrations/`).

**Result** (single run, start offset 0): score 2D 58.9, CP recall @ 1 m 40.0 (2 of 5 control points within 1 m), pose recall @ 5 m 100.0, pose recall @ 1 m 35.8, median xy error against the pGT 1.33 m, ATE sim3 1.36 m (scale 0.954). Poses for all 9547 images (45 pre-init frames filled). Paper Table 2 ATE on this sequence: OpenVINS 1.04, OpenVINS+Maplab 1.62, OKVIS2 1.85.

**Cost**: run 2.3x faster than realtime; the control-point evaluation adds about 1 minute (pycolmap reconstruction with 9547 frames).

**Decision**: harness complete for both metric families. On this one sequence recall @ 5 m is already saturated, so the differentiating numbers on easy sequences are score 2D and recall @ 1 m, i.e. metre-level accuracy; the test set's hard sequences (low light, moving platforms, long) are where recall @ 5 m will drop. Reading of the leaderboard: the open baseline's 27.7 / 23.4 / 12.8 are averages of score-like numbers over whole challenges, so one sequence does not place us yet; the same metrics on R_12, R_13 and the additional set will, once downloaded.

## 002: initialisation robustness, start-frame sweep (2026-10-02, pc, commit 2ecc5c2 + runner skip option)

**Hypothesis**: since OpenVINS is deterministic, varying the start frame is the way to measure how sensitive the result is to initialisation; if the reference config diverges for some starts, divergence detection is the next feature; if not, the spread tells us the minimum effect size worth keeping.

**Change**: runner takes an optional `SKIP_FRAMES` (frames dropped before feeding the estimator); the scored file omits the skipped frames (`--drop-before-first`, diagnostics only, a real submission must contain every image). Config `ov_ref001` unchanged.

Command: `SKIP_FRAMES=k DROP_PRE_INIT=1 scripts/run_sequence.sh configs/ov_ref001 data/training/<seq> results/002-init-sweep/<seq>_skip<k>`

**Result** (ATE m, sim3 scale in brackets; k=0 is the 001 run):

| start offset k | R_01_easy | R_04_medium | R_08_hard |
|---|---|---|---|
| 0 | 0.301 (0.982) | 0.739 (0.962) | 4.49 (0.964) |
| 20 | 0.212 (0.977) | 0.918 (0.953) | 7.45 (0.958) |
| 50 | 0.335 (0.992) | 0.912 (0.957) | 3.26 (0.965) |
| 100 | 0.281 (0.979) | 1.078 (0.952) | 3.59 (0.974) |
| 200 | 0.180 (0.986) | 0.765 (0.961) | 3.80 (0.977) |
| 400 | 0.172 (0.978) | 0.998 (0.968) | 6.55 (0.963) |
| mean / spread | 0.25 / 0.17-0.34 | 0.90 / 0.74-1.08 | 4.85 / 3.3-7.4 |

**Cost**: 15 runs in parallel took about 8 minutes wall on 16 cores.

**Decision**: keep `ov_ref001` as reference; no divergence in 18 runs, so divergence detection drops in priority. Rule from now on: a change counts only if it beats the reference on all three sequences by more than this spread, or shifts the whole 6-offset distribution. Scale is 0.95 to 0.99 in every run (estimate 1 to 5 % too large), consistently, so it is systematic, not init noise; that is the next thing to understand. R_08 varies 2x with the start frame, so the long sequence is where init and drift interact most.

## 001: OpenVINS stereo+IMU baseline on LaMAria pinhole ASL data (2026-10-02, pc, commit 2ecc5c2)

**Hypothesis**: OpenVINS (MSCKF, stereo KLT) on the pinhole-undistorted ASL images with the IMU noise values from the LaMAria calibration JSON gives a working end-to-end harness and a reference number per sequence. Expected: tracks R_01_easy, drifts on the longer ones.

**Change**: none to compare against; this experiment establishes the reference. Because the first configuration diverged on R_04_medium, a small bring-up exploration (two knobs) was needed to get a configuration that survives all three sequences. All of it is recorded here; nothing was tuned on the test set.

Setup common to all runs: `configs/ov_baseline/estimator.yaml` (200 KLT points, 11 clones, 50 SLAM features, dynamic initialisation, ZUPT at start only, FEJ, RK4), per-sequence `imucam.yaml`/`imu.yaml` generated from the sequence's pinhole calibration JSON. The right image (757x569) is padded to the left image size (758x572) with the padding masked. One pose per image: frames before initialisation (about 45) get the first estimated pose; later gaps carry the previous pose forward. Scoring: official `evaluate_wrt_mps` (ATE RMSE after Umeyama with scale, 1 ms association, 1 pose per image in the pGT of the controlled set).

Command: `scripts/run_sequence.sh configs/<cfg> data/training/<seq> results/<exp>/<seq>`

Knobs explored: `dt` = online camera-IMU time offset calibration (`calib_cam_timeoffset`), `n10` = IMU noise x10 (all four values), `n10d` = only the two white-noise densities x10, random walks unchanged. Variant configs kept in `configs/explore-001/`.

**Result**: ATE RMSE in metres after sim3 alignment (sim3 scale in brackets). Single run per cell; OpenVINS was verified to be deterministic on this harness (two repeats reproduced positions exactly).

| Config | R_01_easy (145 s, 2898 fr) | R_04_medium (263 s, 5253 fr) | R_08_hard (616 s, 12328 fr, 746 m path) |
|---|---|---|---|
| ov_baseline: JSON noise, dt calib on | **0.169** (0.993) | 41.7 diverged (0.002) | 10.59 (0.959) |
| dt calib off | 0.329 (0.986) | 1.63 (0.948) | 66.5 diverged (0.518) |
| n10, dt on | 0.492 (0.960) | 1.11 (0.929) | not run |
| n10d, dt on | 0.403 (0.980) | 42.2 diverged (0.002) | not run |
| n10, dt off | not run | 7.75 (0.833) | not run |
| **n10d, dt off** (`configs/ov_ref001`) | 0.301 (0.982) | **0.739** (0.962) | **4.49** (0.964) |

Poses: the estimator produced a pose for every frame after initialisation on every run (no tracking loss detected by OpenVINS; divergence is silent). Error over time on R_08_hard (baseline): 5 to 18 m per minute-window, worst at the start and end, i.e. drift plus a poor initial segment, not a single jump.

Diagnostics of the baseline divergence on R_04_medium: speed already 2.2 m/s median in the first 10 s (walking is ~1.3), accelerometer bias runs to 3.5 m/s^2, the online time offset jumps to -15.6 ms at init. Both knobs change which sequence diverges rather than fixing it, so the root cause is a fragile dynamic initialisation plus no divergence detection, not the noise values as such.

Frame check on R_01_easy: expressing the estimate in the left-camera frame (lever arm 13.4 cm) raises the ATE from 0.169 m to 0.206 m, so the controlled-set pseudo-GT is compared directly against IMU poses; we keep `world_from_imu` as the submission guide says.

**Cost**: 2.0 to 2.4x faster than realtime on this PC, about 1.2 cores (OpenCV threads 4), 106 to 138 MB RSS. R_08_hard takes 274 to 312 s.

**Decision**: keep. Reference config from here on is `configs/ov_ref001`. The datasheet baseline stays recorded as `configs/ov_baseline` (diverges on R_04).

**Bring-up problems and fixes** (so nobody hits them again)

- Stereo KLT crashed because the two pinhole images differ in size by a few pixels. Fix in the runner: pad the smaller image bottom/right, mask the padding. Intrinsics untouched.
- OpenVINS never initialised: the static initialiser wants an image disparity under 10 px over a window, and a person wearing glasses never holds that still. Dynamic initialisation (`init_dyn_use`) initialises about 2.3 s in.
- A YAML comment on the same line as a boolean breaks OpenCV's parser. Comments go on their own line.
- OpenVINS resolves relative config paths from the config file, so pass absolute paths.

**Insights**

- Determinism: identical input gives identical output, so "several seeds" must mean different start frames or perturbed input, not reruns.
- The failure mode is a bad dynamic initialisation that the filter never recovers from, and it is silent: poses keep being produced while the trajectory flies off.
- Datasheet IMU noise values are too optimistic for OpenVINS (standard finding); inflating only the white-noise densities keeps the bias walks sane.
- Scale is 2 to 4 % off in every surviving run. Stereo with a short baseline plus IMU should pin scale better than that; candidate causes are the init, the padded/undistorted images, or the accelerometer bias walk.
- Error on R_08_hard is drift-shaped, worst at start and end. That is the loop-closure / mapping gap, but initialisation comes first.
