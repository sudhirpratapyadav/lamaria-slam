# Experiments (v2: exploration of estimator classes)

One section per experiment, newest first, same fields as v1 (hypothesis, change, command, per-sequence result, cost, decision). Scoreboard at the top. The v1 reference (`configs/ov_ref005`, OpenVINS) is the baseline every candidate is compared against: controlled set two-offset mean ATE 2.83 m; additional set scores in v1 experiments 030 / 037.

## Scoreboard

| Candidate | Stage | Controlled set, 2-offset mean ATE (13 seq) | Additional set score 2D / recall @ 5 m (seq_1_19, 1_20, 2_11, 2_12) | Notes |
|---|---|---|---|---|
| v1 OpenVINS ov_ref005 | tuned (v1) | 2.83 m | 40.0/99.9, 46.3/99.9, 11.6/15.7, 29.0/60.4; 3_17 9.9/21.6, 3_18 13.1/33.0, 4_10 0.9/0, 4_11 30.2/66.2 (v1 037) | causal, ~1.4x realtime on one core |
| A OKVIS2 | A07 x10 + 10 keyframes, final BA (non-causal) | 13-sequence mean **2.15** at offset 0 (Basalt 2.46); wins 7/13 incl. R_01 0.022, R_03 0.029, R_12 4.5; loses the medium set 2x; pair oracle with Basalt 1.66 | | 5-10x the CPU of Basalt, up to 4.4 GB; live path diverges on R_11 |
| B Basalt | B07/B08 robust | **2.43 m** (OpenVINS 2.83), better on 10/13 | mean score 16.9 vs 22.0 (wins 1_19, 2_11, 4_10; loses the 2 km walks) | ~2x realtime on <2 cores; X01: the walks are lost to heading events in low-feature stretches; B16 (CLAHE) running |
| C ORB-SLAM3 | C01-C03 fisheye | R_01 **0.031**; R_04 0.79-0.83 with 25 % frames lost; R_11 1.00 (score 65.6); R_08 1.38 after the example's IMU-loop crash was fixed (C03) | | ~1.2x realtime on 2 cores; poses missing before inertial init |
| D OpenVINS line | D01-D03 window variants | no broad win (2.83 m reference stands) | 2_11 up to 27.3 / 68.5 % with the fixed window; 2_12 32.1 / 73.1 % with D03 | parked; BA smoother deferred |

## C04: ORB-SLAM3 on the pinhole input (2026-10-03, pc)

**Change**: `orbslam3_c02_n10` with `Camera.type: PinHole` on `data/training/*` (ORB-SLAM3 rectifies pinhole stereo itself from `Stereo.T_c1_c2`), to cover the 13 controlled sequences without raw fisheye data.

**Result**: fails. R_01 / R_04 / R_11 produce one pose each: the tracker never gets 15 matches on the rectified pair and resets the map on every frame (932 resets on R_01); R_08 died twice in a pthread priority assertion inside ORB-SLAM3 and was stopped. The undistorted LaMAria pair (758x572 left, 757x569 right, cameras not coplanar) does not go through ORB-SLAM3's rectification path as is; the KannalaBrandt8 path on the raw fisheye (C02, C03) is the one that works.

**Decision**: parked. ORB-SLAM3 stays a fisheye-only candidate; scoring it on all 13 needs the raw `.vrs` of the other nine sequences (disk: 11 GB free, the four we had were deleted after extraction), the owner's call.

## C03: the ORB-SLAM3 R_08 crash (2026-10-03, pc)

**Finding**: under gdb the segfault is in the example's `main()`, at the last image. The EuRoC example walks its IMU vector with `while (t_imu[i] <= t_cam)` and no bounds check; R_08's last image is 2.9 ms after the last IMU sample, so the loop reads past the vector and the run dies after processing the whole sequence (and before writing `f_run.txt`). Deterministic, input-dependent, nothing to do with tracking.

**Change**: bounds check on both IMU loops in `stereo_inertial_euroc.cc` (in `docs/patches/ORB_SLAM3-4452a3c.patch`). Rerun: `orbslam3_c02_n10` on fisheye R_08 (`results/v2-C03-orbslam3-crash/`).

**Result**: R_08 completes on the first attempt: ATE sim3 **1.379 m** (scale 0.952), 11680 of 12328 poses (the first 648 images, 32 s, precede the inertial initialisation and have no pose); 730 s wall at 1.95 cores, 1.9 GB RSS. On R_08 that places ORB-SLAM3 between Basalt (1.01) and OpenVINS (1.48), ahead of OKVIS2's final BA (2.09). Its weak point is now the missing poses before initialisation (R_04: 1330 images, 66 s), which count as misses for the recall metrics.

**Decision**: ORB-SLAM3 is unparked; next, run it on the pinhole input to cover the 13 controlled sequences (C04).

## M03: three-system oracle on the controlled set (2026-10-03, pc, analysis only)

Offset 0, ATE sim3 m: OpenVINS ov_ref005 (v1 032), Basalt B07, OKVIS2 final BA (A07).

| | OpenVINS | Basalt | OKVIS2 final | best |
|---|---|---|---|---|
| R_01 | 0.289 | 0.151 | **0.022** | OKVIS2 |
| R_02 | 0.584 | **0.173** | 0.823 | Basalt |
| R_03 | 0.216 | 0.434 | **0.029** | OKVIS2 |
| R_04 | 1.480 | 0.781 | **0.681** | OKVIS2 |
| R_05 | 1.307 | **1.139** | 2.359 | Basalt |
| R_06 | 2.081 | **1.124** | 2.550 | Basalt |
| R_07 | 3.203 | **1.236** | 2.740 | Basalt |
| R_08 | 1.484 | **1.006** | 2.089 | Basalt |
| R_09 | 3.843 | **2.762** | 2.981 | Basalt |
| R_10 | 6.102 | 4.412 | **3.575** | OKVIS2 |
| R_11 | **0.684** | 2.605 | 1.935 | OpenVINS |
| R_12 | 9.211 | 12.857 | **4.496** | OKVIS2 |
| R_13 | 5.188 | **3.349** | 3.690 | Basalt |
| mean | 2.74 | 2.46 | 2.15 | oracle **1.56** (Basalt + OKVIS2 alone: 1.66) |

Basalt wins 7, OKVIS2 5, OpenVINS 1 (R_11). A per-sequence oracle would cut the controlled-set mean by a third relative to the best single system; most of that comes from Basalt + OKVIS2 (the OpenVINS term is worth 0.1 m). The selector signals of M02 (agreement, restarts, duration) have to be re-tested with OKVIS2 in the set; OKVIS2's live-vs-final disagreement is a new candidate signal. Single offset, single runs.

## A07: OKVIS2 (x10, 10 keyframes, final BA) on the 13 controlled sequences (2026-10-03, pc)

**Change**: `configs/okvis2_a04_n10_kf10`, offset 0, `DROP_PRE_INIT=1`, two runs at a time (`results/v2-A07-okvis2-all/batch.sh`). Live = causal estimate, final = after OKVIS2's full bundle adjustment (non-causal). Basalt = B07 (robust driver, offset 0), the current best.

| Seq | OKVIS2 live | OKVIS2 final | scale (final) | Basalt B07 | wall s (2 cores) |
|---|---|---|---|---|---|
| R_01 | 0.138 | **0.022** | | 0.151 | 612 |
| R_02 | 0.645 | 0.823 | 0.908 | **0.173** | 333 |
| R_03 | 0.131 | **0.029** | 1.013 | 0.434 | 515 |
| R_04 | (lost) | **0.681** | | 0.781 | |
| R_05 | 2.90 | 2.36 | 0.936 | **1.14** | 687 |
| R_06 | 2.68 | 2.55 | 0.950 | **1.12** | 1501 |
| R_07 | 3.12 | 2.74 | 0.960 | **1.24** | 1453 |
| R_08 | (lost) | 2.09 | | **1.01** | |
| R_09 | 3.21 | 2.98 | 0.946 | **2.76** | 3308 |
| R_10 | 3.77 | **3.57** | 0.907 | 4.41 | 3807 |
| R_11 | 37.6 (diverged) | **1.94** (score 56.7) | 0.807 | 2.60 (score 73.3) | |
| R_12 | 4.51 (score 27.8) | **4.50** (score 26.8) | 0.890 | 12.86 (score 12.0) | 4695 |
| R_13 | 5.74 (score 34.8) | 3.69 (score 41.6) | 0.886 | **3.35** (score 45.2) | 9768 |
| **13-sequence mean (offset 0)** | | **2.15** | | 2.46 | |

OKVIS2's final BA wins 7 of 13 and the single-offset mean (2.15 against Basalt's 2.46), carried by R_12 (4.5 against 12.9: the long control-point walk where Basalt's heading goes wrong, see B18) and the easy sequences; Basalt wins every medium sequence and R_08 by about 2x. The two are complementary: the per-sequence oracle of the pair is **1.66 m**. OKVIS2's live (causal) path diverges on R_11 and is 1.2 to 1.6x worse than its final BA elsewhere; its fitted scale sits at 0.81 to 0.96 (Basalt 0.97 to 0.99), so a scale drift is part of its error. Cost: R_13 took 2.7 h on two cores and 4.4 GB; 5 to 10x Basalt.

**Decision**: OKVIS2 stays in the mix as the non-causal, high-accuracy member for a selector (M03), not as the base to optimise. Next: A08 (CLAHE) on R_08/R_11, and a 13-sequence three-way oracle with OpenVINS.

## B20: Basalt, reject near landmarks (2026-10-03, pc)

**Hypothesis** (B18's R_12 analysis, X01): the heading excursions coincide with the wearer's own body (shoe, arm) and near moving objects in view. Basalt accepts any landmark triangulated farther than 0.33 m (a hard-coded inverse-distance cap of 3.0); refusing landmarks closer than 0.8 m or 1.5 m removes the body features at the cost of some close indoor structure.

**Change**: `sqrt_keypoint_vio.cpp`: the cap reads env `BASALT_MAX_INV_DIST` (default 3.0 = upstream; in `docs/patches/basalt-0f3b2b5.patch`), announced once in the log. `basalt_ref1` otherwise (Huber 1.0), robust driver, offset 0, caps 1.25 (0.8 m) and 0.67 (1.5 m) on R_12, R_08, R_11, sequence_4_11, 2_11, 3_18.

**Command**: `results/v2-B20-basalt-neardist/batch.sh`. **Result**: pending.

## B19: Basalt Huber 0.7 (2026-10-03, pc)

**Result** (ATE m; score 2D / recall @ 5 m where control points exist; reference basalt_ref1 and Huber 0.5 in brackets): R_08 0.890 (1.006 / 0.818); R_09 2.869 (2.762 / 3.880); R_11 2.376, 75.0 (2.605, 73.3 / 2.110, 76.7); R_12 offset 0 16.10, 7.2 (12.86, 12.0 / 16.22, 7.1) and offset 100 14.39, 12.6 (12.94, 14.0 / 16.07, 6.9); R_13 3.567, 43.1 (3.349, 45.2 / 3.589, 42.0); sequence_1_20 39.1 (39.6 / 38.3); 2_11 22.3 (20.7 / 24.1); 3_18 77.8, 2.5 (81.0, 2.4 / 71.5, 2.9); **4_11 3.60, 34.4 / 92.0 %** (14.9, 9.9 / 18.9 % / 3.11, 37.1 / 92.4 %), with three restarts (0.5: one; reference: none).

**Reading**: 0.7 sits between the two as expected: it recovers R_09 and half of R_12's second offset, keeps most of the dark-walk gain, and still loses R_12 at offset 0 and R_13. No Huber value fixes R_12, because the damage there comes from features on the wearer's own body (see B18), and a tighter loss only shifts the balance between "trust the near cluster" and "trust the IMU". Part of the 4_11 gain may come from the restarts that the tighter loss provokes (the driver cuts the bad stretch), not from the loss itself; worth separating later.

**Decision**: parked at a trade-off. `basalt_ref1` (Huber 1.0) stays the controlled-set reference (2.43 m two-offset); Huber 0.5 is the Basalt setting of record for the additional set (mean score 19.7 against 16.9). The next Basalt round goes after the cause (B20: reject near features) instead of the weighting.

## B18: Basalt Huber threshold 0.5 validated on the full sets (2026-10-03, pc)

**Change**: `basalt_r17_huber05` (B17's winner) on the 13 controlled sequences at offsets 0 and 100 and on the 10 additional sequences; `basalt_r17_huber03` (0.3) on R_08 / R_11 / 3_18 for the direction.

**Command**: `results/v2-B18-basalt-huber/batch.sh`.

**Result**, controlled set (ATE sim3 m, offsets 0 / 100; B07 reference in brackets):

| Seq | Huber 0.5 | basalt_ref1 (B07) |
|---|---|---|
| R_01 | 0.146 / 0.150 | 0.151 / 0.156 |
| R_02 | 0.141 / 0.185 | 0.173 / 0.215 |
| R_03 | 0.373 / 0.342 | 0.434 / 0.415 |
| R_04 | 0.628 / 0.632 | 0.781 / 0.935 |
| R_05 | 0.997 / 1.055 | 1.139 / 1.153 |
| R_06 | 1.121 / 0.851 | 1.124 / 0.764 |
| R_07 | 1.102 / 0.941 | 1.236 / 1.220 |
| R_08 | 0.818 / 1.022 | 1.006 / 1.368 |
| R_09 | 3.880 / 2.125 | 2.762 / 2.414 |
| R_10 | 4.379 / 3.224 | 4.412 / 3.877 |
| R_11 | 2.110 / 1.947 (score 76.7 / 78.4) | 2.605 / 2.078 (73.3 / 77.0) |
| R_12 | 16.22 / 16.07 (score 7.1 / 6.9) | 12.86 / 12.94 (12.0 / 14.0) |
| R_13 | 3.589 / 3.698 (score 42.0 / 41.1) | 3.349 / 3.544 (45.2 / 44.3) |
| **two-offset mean** | **2.61** | **2.43** |

Better on 20 of 26 runs, by 10 to 30 % on the easy and medium sequences, but worse on both offsets of the two long control-point walks (R_12 by 3.3 m and 5 to 7 score points, R_13 by 0.2 m and 3 points) and on one R_09 offset, which flips the 13-sequence mean the wrong way. Additional set (score 2D, B08 in brackets): 1_19 69.0 (64.1), 1_20 38.3 (39.6), 2_11 24.1 (20.7), 2_12 6.4 (5.3), 3_17 1.3 (4.3), 3_18 2.9 (2.4), 4_10 8.0 (8.4), **4_11 37.1 / recall 92.4 % (9.9 / 18.9 %; ATE 3.1 against 14.9)**, 5_11 6.7 (6.9), 5_12 3.6 (7.6): mean score **19.7** (B08 16.9; OpenVINS 22.0). Five up, five down, but the dark walk 4_11 is transformed (one restart instead of none, and the heading events of X01 are gone from it), which carries the mean. Huber 0.3 (direction check): R_08 0.862, R_11 1.638 / 78.9, 3_18 68.3 / 1.1: the ATE keeps falling with a tighter threshold, the control-point scores do not follow.

**Reading**: a tighter Huber threshold helps wherever features are plentiful (easy/medium) and on the dark walk, and hurts on the longest control-point walks (R_12, R_13, 3_17, 5_12), where it leaves too few effective observations and the drift grows. It is the same trade-off as D04 and B17's obs-std: more IMU weight, less vision. **Decision**: not kept as is; B19 tries 0.7 on the sequences that moved most (R_12, R_13, R_09, R_08, R_11, 2_11, 1_20, 3_18, 4_11).

**Why R_12 loses** (drift decomposition, `results/v2-X01-drift-analysis/R_12_*`): with Huber 0.5 or 0.7 the run picks up a heading excursion of -21 then +25 degrees in the 450 to 510 s windows (reference: 0.2 / 1.8) inside a continuous segment; the restart in those runs is a separate, harmless event at 2.2 s (one frame over 6 m/s during initialisation). The frames there show the wearer looking down with their own shoe filling a quarter of the image (`frames/R_12_470s.png`), after a parked van and a tree at 440 s; the reference's local scale also jumps to 1.24 in the same window. Same family as X01: features on the wearer's body and on near, moving objects pull the estimate, and a tighter robust loss makes it worse by trusting that consistent-looking cluster over the far features with larger residuals. A body/near-object rejection in the front end would address R_12, 3_18 and 2_11 together.



## B17: Basalt outlier handling, one knob each (2026-10-03, pc)

**Hypothesis** (X01): the heading events come from a few wrong features (reflections, pedestrians, the wearer's arm) in low-feature stretches; a stricter robust loss or outlier gate should limit their pull.

**Change** (one knob each on `basalt_ref1`, source build, robust driver, offset 0): `vio_obs_huber_thresh` 1.0 to 0.5; `vio_outlier_threshold` 3.0 to 2.0; `vio_obs_std_dev` 0.5 to 1.0 px; `optical_flow_epipolar_error` 0.005 to 0.0025.

**Result** (ATE sim3 m; R_11 and 3_18 also score 2D / recall @ 5 m; reference B07/B08 in the first row):

| Variant | R_08 | R_11 | sequence_3_18 |
|---|---|---|---|
| basalt_ref1 | 1.005 | 2.605, 73.3 / 96.5 | 81.0, 2.4 / 4.2 |
| huber 0.5 | **0.817** | **2.139, 76.6 / 97.5** | **71.7, 3.1 / 5.1** |
| outlier 2.0 | 1.003 | 2.588, 73.2 / 96.5 | 81.0, 2.5 / 4.2 |
| obs std 1.0 px | 1.388 | 1.338, 71.6 / 100 | 55.7, 0.9 / 4.6 (one restart) |
| epipolar 0.0025 | 1.013 | 2.592, 73.3 / 96.5 | 80.7, 2.1 / 4.0 |

Huber 0.5 improves all three (19 % on R_08, 18 % on R_11, 12 % on 3_18) with no cost. Doubling the pixel noise cuts the ATE on R_11 and 3_18 (more IMU trust limits the heading events) but costs the control-point scores and R_08: the sim3 ATE and the score disagree, so it is not a clean win. The epipolar check is a no-op here, and the outlier gate is a no-op by construction: `vio_outlier_threshold` is commented out in this Basalt version (`vio_config.cpp`), so the key in the config is read and ignored.

**Decision**: validate Huber 0.5 on the full sets (B18); keep the obs-std result as evidence for the "trust the IMU in degraded stretches" direction (see D04 for the OpenVINS version).

## D04: adaptive pixel noise when features collapse (2026-10-03, pc)

**Hypothesis** (from X01): the heading events happen while few features are tracked; the few that remain (reflections, pedestrians, the wearer's arm) pull the orientation. If the vision noise is inflated while the feature count is low, the IMU holds the heading through the stretch at the cost of some position drift.

**Change**: OpenVINS `VioManager::set_pixel_noise_scale(k)` (new, scales the MSCKF and SLAM `sigma_pix` at runtime); the runner reads `adapt_noise_min_feats` and `adapt_noise_factor` from `estimator.yaml` and, after each update, scales the noise by the factor for the next frame when MSCKF + SLAM features used were below the minimum; `run_stats.json` reports `degraded_frames`. Configs `configs/explore-v2D04/adapt30x3` (minimum 30, factor 3) and `adapt25x4` on ov_ref005.

**Command**: `results/v2-D04-adaptive-noise/batch.sh` (offset 0, R_01 sanity run, then sequence_2_11 / 3_18 / 4_11, R_08, R_11 per variant).

**Result**, minimum 30 / factor 3 (ov_ref005 offset 0 in brackets; ATE m, score 2D / recall @ 5 m; degraded frames as a share of all):

| Seq | adapt30x3 | ov_ref005 | degraded |
|---|---|---|---|
| R_01 | 0.227 | 0.289 | 1 % |
| R_08 | **1.045** | 1.484 | 12 % |
| R_11 | 1.741, 52.1 / 99.9 | **0.684, 72 / 100** | 10 % |
| sequence_2_11 | 10.9, 12.7 / 16.9 | 11.2, 11.6 / 15.7 | 24 % |
| sequence_3_18 | **20.5, 16.6 / 38.4** | 26.0, 13.1 / 33.0 | 15 % |
| sequence_4_11 | 7.2, 27.8 / 60.9 | **5.9, 30.2 / 66.2** | 42 % |

Mixed: 3_18 and R_08 gain, R_11 and 4_11 lose, and the rule fires on 10 to 40 % of the frames, far more than the stretches it was meant for (the per-frame count is noisier than the one-minute averages of X01). Variant 25 / 4 (fires less often, pushes harder): R_08 2.37, R_11 1.74 / 52.6, 2_11 10.6 / 13.5 / 21.8 %, 3_18 24.4 / 12.0 / 25.5 %, 4_11 11.1 / 22.4 / 48.7 %: worse than the reference on four of five. The strength of the push is the problem (R_11 loses with either variant, 4_11 loses more with factor 4); the gentler variant (minimum 20, factor 2) is no better: R_08 2.27, R_11 1.17 / 67.0, 2_11 10.6 / 12.7 / 17.7 %, 3_18 26.0 / 12.8 / 32.5 %, 4_11 7.2 / 29.1 / 61.3 % (worse on R_08, R_11, 4_11; ties elsewhere).

**Decision**: discard. The mechanism stays in the runner, off by default. Together with B17's obs-std result it says that trusting the IMU more in degraded stretches trades ATE for control-point score; a selective rule needs a better trigger than the raw per-frame count (v3 design item).

## B16: Basalt with CLAHE input (2026-10-03, pc)

**Hypothesis** (from X01): Basalt's heading errors sit in low-feature stretches (dark, low texture, overexposed). v1 found CLAHE worth 0.36 m mean and 1.2 to 2.0 m on the hard sequences for OpenVINS (v1 026); Basalt gets raw images, so the same preprocessing should recover texture for its optical flow.

**Change**: `third_party/basalt` source build, `dataset_io_euroc.h`: optional CLAHE (clip from env `BASALT_CLAHE`, 8x8 tiles, OpenVINS's clip 10) applied to the 8-bit image at load time, so no image copy on disk. `basalt_segments.py` takes the binary from `BASALT_VIO`. Control run: the source-built binary without CLAHE on R_04 (the results so far come from the release binary, `~/.local/bin/basalt_vio`).

**Command**: `results/v2-B16-basalt-clahe/batch.sh` (robust driver, `basalt_ref1`, offset 0, 2 runs at a time): R_04 control, then CLAHE on R_01 / R_04 / R_08 / R_11 / sequence_2_11 / 3_18 / 4_11.

**Result** (ATE sim3 m, offset 0; reference = B07 release binary): R_04 control with the source build 0.779 (B07 0.781: the source build reproduces the release); CLAHE 10: R_04 0.785, R_08 1.000 (1.005), R_11 2.589, score 73.2 (2.605, 73.3). R_01 0.151 (0.151). Long walks (score 2D / recall @ 5 m; B08 in brackets): sequence_2_11 ATE 30.4, 21.2 / 46.6 % (30.9, 20.7 / 45.9); 3_18 81.1, 0.0 / 0.2 % (81.0, 2.4 / 4.2); 4_11 15.6 with one restart, 15.3 / 36.3 % (14.9, 9.9 / 18.9). The drift decomposition is unchanged to the second decimal (3_18 worst window 28.0 deg both ways). Sanity: clip 100 against clip 10 on R_01 moves the trajectory by 1.6 mm on average (8.5 mm max), so the preprocessing is applied and Basalt is simply insensitive to it. Ties everywhere: Basalt's patch-based optical flow with its adaptive FAST threshold is insensitive to contrast, unlike OpenVINS's KLT front end.

**Decision**: discard; the patch stays (off by default). Next for Basalt: B17 (outlier handling) on the same stretches.

**Note**: the first pass of this experiment was void. The source-built `basalt_vio` had been loading the release `libbasalt.so` from `~/.local/lib` (the driver put that folder first in `LD_LIBRARY_PATH`), so the patched loader never ran; the one-time `BASALT_CLAHE:` announcement in the log exposed it. Fixed in `basalt_segments.py` and `run_basalt_mapper.sh` (binary folder first). The B12/B14 mapper results are unaffected (the mapper patch is in the executable).

## B15: tighter restart thresholds for the robust Basalt driver (2026-10-03, pc)

**Change**: `MAX_SPEED=4 MAX_JUMP=0.5` (default 6 / 1) on the standard four and the two long walks where Basalt is worst with restarts possible (sequence_2_12, 4_11).

**Result**: standard four identical to B07 (no restart triggers on either threshold: R_01 0.151, R_04 0.781, R_08 1.005, R_11 2.60 / score 73.3, recall@1m 60). sequence_4_11: 2 restarts, ATE 16.2 (B08: 14.9), score 6.7 (9.9), recall @ 5 m 11.7 % (18.9 %): worse. sequence_2_12: not completed (the harness job hit its time limit after 2 h); by then the driver had restarted eight times inside the first 25 s of the sequence (frames 28, 38, 97, 136, 137, 384, 415), so the thresholds fire on normal head motion; not rerun.

**Decision**: discard. The tighter thresholds fire on fast head motion, not on divergence, and each restart costs more than it saves.

## X01: where the drift on the long walks comes from (2026-10-03, pc, analysis only)

**Question**: Basalt and OpenVINS lose the 2 km walks (scores 2 to 30). Is it scale, heading, or local tracking, and when does it happen?

**Method**: `scripts/drift_analysis.py` sim3-aligns the estimate to the pGT in 60 s windows and reports each window's scale, heading (yaw of its own alignment) and residual; heading drift is the yaw change between consecutive windows. `scripts/sequence_timeline.py` adds per-window context: pGT speed and turning rate, gyro norm, image brightness and Laplacian variance (one frame per second), OpenVINS feature counts from `frame_times.csv`. Inputs: B08 (Basalt robust) and v1 037 (ov_ref005) on the additional set. Outputs in `results/v2-X01-drift-analysis/`.

**Result** (Basalt / OpenVINS):

| Seq | ATE sim3 | total heading drift | worst window (deg per min) | local scale range | 60 s residual median | restarts |
|---|---|---|---|---|---|---|
| 1_20 (1.1 km) | 3.6 / 2.1 | -5 / -4 deg | 2.2 / 2.2 | 0.95-1.02 / 0.95-0.99 | 0.18 / 0.14 m | 0 / 0 |
| 2_11 (1.3 km) | 30.9 / 11.2 | 67 / 14 deg | 14.6 @ 1110 s / 6.5 @ 630 s | 0.71-1.08 / 0.91-1.00 | 0.40 / 0.16 | 0 / 0 |
| 3_18 (1.7 km) | 81.0 / 26.0 | 123 / 46 deg | 28.0 @ 1170 s / 8.2 @ 810 s | 0.86-1.02 / 0.92-1.00 | 0.19 / 0.15 | 0 / 0 |
| 4_11 (1.1 km, dark) | 14.9 / 5.9 | 15 / -18 deg | +20 and -18 @ 510-570 s / 9.9 @ 570 s | 0.53-1.15 / 0.82-0.98 | 0.56 / 0.20 | 1 (start) / 0 |
| 2_12 (2.1 km) | 27.3 / 4.9 | 49 / 6 deg | 9.7 / 5.2 | 0.76-1.02 / 0.86-1.01 | 0.36 / 0.20 | 3 (start) / 1 |

1. **Heading, not scale and not local tracking.** Within any 60 s window both systems are consistent to 0.15 to 0.5 m; the global error is a few heading events of 5 to 28 degrees in one minute, on top of a slow 0.5 to 1.5 deg/min background. The gyro alone would drift well under 1 deg/min, so these events are vision pulling the orientation wrong, inside continuous tracking (no restarts or re-inits anywhere near them on 2_11 / 3_18).
2. **The events sit in low-feature stretches.** OpenVINS's feature counts there are 5 to 9 MSCKF and 13 to 27 SLAM points per frame against 12 to 15 / 35 to 40 elsewhere. The causes differ per walk: 4_11 is dark throughout (mean brightness 14 to 27 of 255); 2_11 and 2_12 have long low-texture stretches (Laplacian variance 7 to 10 against 20 to 30); 3_18 at 750 to 930 s is overexposed (brightness 95 to 109) and blurred. The worst Basalt window (3_18 at 1170 s, 28 deg) is a street with shop windows (reflections) and pedestrians at normal exposure; 2_11 at 1110 s is fast walking (1.5 m/s) with bright sky, pedestrians and the wearer's arm in view. Sample frames in `results/v2-X01-drift-analysis/frames/`.
3. Basalt's local scale also wanders in those stretches (0.5 to 1.15), OpenVINS's much less (0.82 to 1.0); OpenVINS's CLAHE and 400-feature front end is the visible difference between the two.

**Implications**: the lever for the long walks is the front end in degraded stretches (recover texture, reject reflections and moving people, trust the gyro when features are few), not the back end. Loop closure cannot help (no revisits). Immediate follow-ups: B16 (CLAHE for Basalt); the same for OKVIS2 once its batch is through; a yaw-protection rule (down-weight vision when the feature count collapses) as a v3 design item.

## A01: OKVIS2 out of the box (2026-10-03, pc, okvis2 a2ea006, USE_NN=OFF)

**Setup**: `scripts/run_okvis2.sh` with `configs/okvis2_default` (OKVIS2 defaults: loop closures on, final bundle adjustment on, realtime limit off, CNN off), calibration from the LaMAria pinhole JSON (radialtangential with zero coefficients), IMU noise as in the JSON (x1), pinhole ASL input. Two outputs: the live estimate (causal) and the trajectory after the final full BA (non-causal).

**Result**, R_01_easy: live ATE sim3 0.237 m (scale 0.958); final-BA ATE 0.043 m (scale 0.976); poses for all 2898 images. Paper: OKVIS2 0.02 m, OpenVINS 0.66 m; our OpenVINS ov_ref005 0.19 / 0.29 m. Cost: 1466 s wall (10x slower than realtime) at 0.83 cores average under a heavily loaded machine (15 other estimators running), 564 MB RSS. A clean timing is owed.

R_04_medium (defaults): live 1.555 m (scale 0.894), final BA 1.441 m (scale 0.898), all 5253 poses, 1988 s wall under load. Basalt 0.79, ORB-SLAM3 0.79 (with gaps), OpenVINS 1.48 on the same run. The low scale says the datasheet IMU noise makes OKVIS2 over-trust the IMU; noise scaling (A02) is the next round. R_08_hard and R_11_5cp (defaults): diverged (ATE 95 / 42 m, sim3 scale 0: the estimate runs off to kilometres), 87 / 65 min wall and 6.5 / 6.1 GB RSS under load. So the datasheet noise makes OKVIS2 fail on the hard sequences exactly as it did OpenVINS and Basalt before their noise scaling.

**Decision**: continue with high priority. The final-BA trajectory is the non-causal, benchmark-eligible path; the live one is the causal (robot) path. Next: A02 noise x10 on R_01/R_04, then keyframing and the fisheye input (OKVIS2 has a native equidistant model).

## D03: blur-adaptive KLT window, 21 px below sharpness 8 (2026-10-03, pc)

**Result** (offset 0; reference / D02 in brackets): R_01 0.418 (0.289 / 0.237); R_06 **0.894** (2.081 / 2.372); R_07 2.292 (3.203 / 2.121); R_08 **1.254** (1.484 / 2.203); R_10 8.531 (6.102 / 7.171); sequence_2_11 13.2 / 18.1 % (11.6 / 15.7; 23.0 / 51.8); sequence_2_12 **32.1 / 73.1 %** (29.0 / 60.4; 25.6 / 70.2); sequence_3_17 6.0 / 9.8 (9.9 / 21.6; 6.3 / 12.2).

**Decision**: parked. Across D01 to D03 the window variants move individual sequences by factors of 2 in both directions with no setting that wins broadly; single-run swings dominate on these sequences. The mechanism stays in the runner (off by default). The OpenVINS line has had its tracker rounds; its remaining idea is a non-causal BA smoother, which is deferred while the optimisation-based candidates (B, A) are ahead.

## D02: blur-adaptive KLT window (2026-10-03, pc)

**Change**: runner measures the left image's Laplacian variance per frame and sets the KLT window to `klt_win_blur` (25 px) when it is below `klt_blur_threshold` (15), else the base 15 px; pyramids are built with the larger border (TrackKLT `build_win_size`, a bug found on the first attempt). `configs/explore-v2D02/blur25` on ov_ref005.

**Result** (offset 0; ATE m, and score 2D / recall @ 5 m for the additional sequences):

| Seq | ov_ref005 | fixed window 21 (D01) | adaptive 25 @ <15 (D02) |
|---|---|---|---|
| R_01 | 0.289 | 0.194 | 0.237 |
| R_06 | 2.081 | 2.491 | 2.372 |
| R_07 | 3.203 | 4.447 | **2.121** |
| R_08 | 1.484 | 4.920 | 2.203 |
| R_10 | 6.102 | 11.130 | 7.171 (1 re-init) |
| sequence_2_11 | 11.6 / 15.7 | 27.3 / 68.5 | 23.0 / 51.8 |
| sequence_2_12 | 29.0 / 60.4 | 25.6 / 67.3 | 25.6 / 70.2 |
| sequence_3_17 | 9.9 / 21.6 | 7.8 / 18.0 | 6.3 / 12.2 |

Sharpness on sequence_2_11: median 13, range 0 to 100, so threshold 15 widens the window on half its frames.

**Decision**: the mechanism works as intended (most of the blur gain, a fraction of the sharp-sequence loss) but the operating point is off; D03 tries threshold 8 with window 21. Not adopted yet.

## D01: OpenVINS ov_ref005 + KLT window 21 px (2026-10-03, pc; complete)

**Hypothesis**: v1 034 found the 21 px window lifts the blurry additional-set walks (sequence_1_20 recall @ 5 m 37 to 94 %); on top of ov_ref005 it should keep the controlled-set numbers.

**Result** (ATE m sim3, two offsets; 11 of 13 controlled sequences done, R_12/R_13 and the additional set rerunning after a job time-out):

| Seq | ov_ref005 k=0 / k=100 | + window 21 k=0 / k=100 |
|---|---|---|
| R_01 | 0.289 / 0.176 | 0.194 / 0.349 |
| R_02 | 0.584 / 0.358 | 0.475 / 0.782 |
| R_03 | 0.216 / 0.195 | 0.141 / 0.183 |
| R_04 | 1.480 / 0.675 | 1.078 / 1.032 |
| R_05 | 1.307 / 1.715 | 1.205 / 0.629 |
| R_06 | 2.081 / 1.906 | 2.491 / 2.760 |
| R_07 | 3.203 / 1.974 | 4.447 / 2.354 |
| R_08 | 1.484 / 1.964 | 4.920 / 5.378 |
| R_09 | 3.843 / 6.696 | 3.800 / 4.991 |
| R_10 | 6.102 / 6.336 | 11.130 / 9.677 |
| R_11 | 0.684 / 0.476 | 1.190 / 0.528 |
| R_12 | 9.211 / 8.579 | 8.026 / 8.607 |
| R_13 | 5.188 / 6.940 | 4.986 / 3.598 |
| mean of 13 | 2.83 | 3.44 |

Additional set (score 2D / recall @ 5 m; ov_ref005 from v1 037 in brackets): 1_19 37.8 / 99.9 (40.0 / 99.9); 1_20 40.0 / 93.6 (46.3 / 99.9); 2_11 **27.3 / 68.5** (11.6 / 15.7); 2_12 25.6 / 67.3 (29.0 / 60.4); 3_17 7.8 / 18.0 (9.9 / 21.6); 3_18 11.2 / 25.2 (13.1 / 33.0); 4_10 3.1 / 0.5 (0.9 / 0); 4_11 24.2 / 51.1 (30.2 / 66.2); 5_11 38.3 (28.4); 5_12 7.7 (8.5). Mean score 22.3 vs 22.0.

**Decision**: not adopted as a fixed setting: controlled-set mean 3.44 vs 2.83, additional-set mean score a tie, with large swings both ways (2_11 and 5_11 up, 1_20 and 4_11 down). The window helps exactly where frames are blurred and hurts where they are sharp, which is the case for a blur-adaptive window (D02: `klt_win_blur` / `klt_blur_threshold`, wide only when the Laplacian variance is low).

## A02: OKVIS2, IMU noise x10 (2026-10-03, pc)

**Change**: `NOISE_SCALE=10` on the white-noise densities (`configs/okvis2_n10`), everything else default (loop closures, final BA, no realtime limit).

**Result** (ATE m sim3, offset 0):

| | R_01 live | R_01 final BA | R_04 live | R_04 final BA |
|---|---|---|---|---|
| A01 defaults | 0.237 | 0.043 | 1.555 (scale 0.894) | 1.441 |
| A02 noise x10 | 0.145 | **0.033** (scale 0.982) | 0.839 | **0.693** (scale 0.921) |
| Basalt ref1 / robust | 0.151 | | 0.788 | |
| ORB-SLAM3 (fisheye) | | 0.031 | 0.794 (25 % frames lost) | |
| OpenVINS ov_ref005 | 0.289 | | 1.480 | |

Cost: 2011 / 2579 s wall under heavy load (0.07 to 0.1x realtime, CPU share 70 %), 0.6 / 0.8 GB RSS. OKVIS2 runs its full optimisation budget without the realtime limit; a clean timing is owed.

R_08_hard: live 4.987 / final 5.152 (scale 0.94), 4034 s wall, 2.1 GB RSS (no divergence any more, but far behind OpenVINS 1.5 to 2.0 and Basalt 1.0 to 1.4). R_11_5cp: live 1.429 / final 1.640 (scale 0.79), score 67.2 / 62.8, recall @ 1 m 44.9 / 43.1 (OpenVINS 0.68 / 72, Basalt robust 2.6 / 73.3). The final BA does not help on the hard sequences (there are no loops; its loop-closure heuristic may even hurt).

**Decision**: continue; x10 fixes the divergence but OKVIS2 is now the slowest and, on hard sequences, the least accurate of the optimisation-based candidates. A03 = x20 with loop closures off, A04 = x10 with 10 keyframes / 5 IMU frames, both on R_04 and R_08.

## A06: OKVIS2 noise x10, 15 keyframes / 7 IMU frames (2026-10-03, pc)

R_04: live 0.852 / final 0.639 (A04 with 10 keyframes: 0.681). R_08: live 2.943 / final 2.880 (A04: 2.089). Wall 1248 / 2440 s.

**Decision**: 10 keyframes (A04, `configs/okvis2_a04_n10_kf10`) is OKVIS2's working point; 15 trades R_08 for a small R_04 gain. A04 is being completed on R_01 and R_11 for the four-sequence picture.

## A05: OKVIS2 noise x10 on the native fisheye input (2026-10-03, pc)

**Change**: `data/training_fisheye` (fitted equidistant lens, OKVIS2 "equidistant"), `configs/okvis2_n10`.

**Result** (ATE m sim3): R_01 live 0.129 / final BA **0.022** (scale 0.974; paper OKVIS2 0.02), 567 s wall; R_04 live 1.426 / final 1.442 (scale 0.94), 1113 s. Pinhole A02: R_01 0.145 / 0.033, R_04 0.839 / 0.693.

**Decision**: same split as Basalt's fisheye runs (B10/B11): the raw fisheye wins the easy sequence and loses the medium one. Not adopted as OKVIS2's default; the pinhole line continues with the keyframe-window rounds (A04/A06).

## A03 / A04: OKVIS2 noise x20 without loop closures; x10 with 10 keyframes (2026-10-03, pc)

**A03** (`okvis2_a03_n20_nolc`): diverged on both R_04 (26.7 m, scale 0.77) and R_08 (41.4 m), no final trajectory. Discard: OKVIS2 needs its loop-closure / pose-graph path even without loops, and x20 is too much.

**A04** (`okvis2_a04_n10_kf10`, num_keyframes 10, num_imu_frames 5): final-BA ATE R_04 0.681 (A02: 0.693), R_08 **2.089** (A02: 5.152). The live trajectories were lost to a shared-output collision with A03 (fixed next by per-run output folders). A longer keyframe window is OKVIS2's lever on the hard sequence; A06 pushes it further (15 keyframes, 7 IMU frames). Cost: 1207 / 3235 s wall under load, 0.8 / 1.9 GB. R_01 with this configuration: live 0.138 / final **0.022** (612 s at light load, 1.9 cores). R_11: the live estimate diverges (37.6 m) and the final BA recovers it to 1.935 m, score 56.7 (A02: 1.43 / 1.64, score 67). OKVIS2 four-sequence picture with x10 + 10 keyframes (final BA): R_01 0.022, R_04 0.681, R_08 2.089, R_11 1.935; live: 0.138, (lost), (lost), diverged.

## C02: ORB-SLAM3 noise x10, no keyframe insertion when lost (2026-10-03, pc)

R_04 fisheye: 0.825 m, again 3923 of 5253 poses (the same tracking loss as C01, so it is not the IMU weighting). R_08: crashes after the second inertial BA on every attempt (deterministic on this sequence as built). Parked; the ORB-SLAM3 line needs a code-level fix for the crash and for re-tracking after loss before more tuning makes sense.

## T01: timing at light load, R_01 (144.9 s of data) (2026-10-03, pc, load ~5 from two OKVIS2 runs)

| System | wall | CPU share | core-seconds per second of data | RSS |
|---|---|---|---|---|
| OpenVINS ov_ref005 (4 OpenCV threads) | 89 s (1.6x realtime) | 1.25 cores | 0.77 | 111 MB |
| Basalt ref1 (4 threads) | 31 s (4.7x realtime) | 3.55 cores | 0.75 | 79 MB |
| OKVIS2 (A02, under heavy load) | 2011 s | ~0.7 cores | ~10 (not comparable) | 600 MB |
| ORB-SLAM3 (C01) | 69+ s | 1.5 cores | ~0.7 | 600 MB to 1.5 GB |

OpenVINS and Basalt cost the same CPU per second of data (about three quarters of one core of this PC); Basalt spreads it over threads. Both fit a Jetson-class budget in principle; OKVIS2 as configured (full optimisation budget, no realtime limit) does not.

## M02: observable selectors between Basalt and OpenVINS, additional set (2026-10-03)

Signals available without ground truth: Basalt's restart count, OpenVINS's re-init count, and the agreement between the two trajectories (RMSE after sim3-aligning one onto the other).

| Selector | mean score 2D (10 sequences) |
|---|---|
| OpenVINS only | 21.8 |
| Basalt only | 16.9 |
| oracle | 25.9 |
| Basalt if it needed no restart, else OpenVINS | 22.8 |
| Basalt if the two agree within 5 to 20 m RMSE, else OpenVINS | 23.5 |
| Basalt if no restart and duration < 1300 s, else OpenVINS | 24.4 |

Agreement is a clean signal: the two estimates agree within 2.5 to 3.3 m exactly on the sequences where Basalt is better or equal (1_19, 1_20) and disagree by 20 to 64 m elsewhere; but above the threshold the selector can only fall back to OpenVINS, which is itself poor there. So a selector buys 2 to 3 points, and the remaining gap to the oracle (and beyond it) needs a better estimator on the long walks, not a better switch.

## B14: Basalt mapper with strict matching (2026-10-03, pc)

`mapper_min_matches 40, second_best_test_ratio 1.5, ransac 2e-5, frames_to_match_threshold 0.08`: R_01 5.79 m (VIO 0.151), R_04 1.13 m (VIO 0.787). Still worse than the VIO alone on both. **Decision**: Basalt's mapper is parked; on loop-free walks its place recognition only injects wrong constraints, and the global BA does not reduce drift by itself.

## B12: Basalt VIO + offline mapper (global BA) (2026-10-03, pc, source build)

**Change**: `scripts/run_basalt_mapper.sh`: `basalt_vio --marg-data`, then `basalt_mapper` headless (patched to save its keyframe trajectory; EuRoC csv converted to TUM), optimised keyframe poses propagated to every frame via the VIO's relative motion (`basalt_propagate_keyframes.py`). `basalt_ref1`, offset 0.

**Result** (ATE m sim3):

| | VIO (source build) | VIO + mapper |
|---|---|---|
| R_01 (411 keyframes) | 0.151 | 0.240 (scale 1.011) |
| R_04 (750 keyframes) | 0.786 | 49.4 (diverged, scale 0.0007) |

The mapper log shows rejected Levenberg-Marquardt steps ("increased error after update") on R_01 and the R_04 map is destroyed, most likely by wrong bag-of-words matches on sequences that have no real revisits. Mapper cost: 85 / 136 s, 1.5 / 1.7 GB.

**Decision**: not usable as is; one round with stricter matching (B14: min matches 40, ratio test 1.5, tighter RANSAC) and then park unless it turns around. The source build reproduces the binary release's VIO numbers.

## M01: mix-and-match analysis, per-sequence choice between Basalt and OpenVINS (2026-10-03)

Using B07/B08 (robust Basalt) and v1 036/037 (OpenVINS ov_ref005):

| | OpenVINS | Basalt | oracle (best per sequence) | rule: Basalt if < 1000 s else OpenVINS |
|---|---|---|---|---|
| controlled 13, two-offset mean ATE | 2.83 | 2.43 | **1.97** | - |
| additional 10, mean score 2D | 21.8 | 16.9 | **25.9** | 24.2 |

The two lines fail on different sequences (Basalt on the 2 km walks and the moving platform, OpenVINS on 1_19 / 2_11 / 4_10), so a selector would already beat both; a duration threshold captures most of it on the additional set but a selector on something the estimator can observe (restart count, visual-inertial consistency, agreement between the two runs) is the proper version. Noted as a v3 option: an ensemble is cheap here because Basalt + OpenVINS together cost about 3 cores at 1.4 to 2x realtime.

## B13: Basalt fisheye with a 40 px optical-flow grid (2026-10-03, pc)

R_01 0.214 (grid 50: 0.110), R_08 2.829 (3.693; pinhole 1.006). Discard: denser flow does not recover R_08 and hurts R_01.

## B11: Basalt fisheye at the second offset (2026-10-03, pc)

**Result** (ATE m, offset 100; two-offset means in the last row, pinhole robust / fisheye):

| | R_01 | R_04 | R_08 | R_11 |
|---|---|---|---|---|
| fisheye k=100 | 0.129 | 0.759 | 2.859 | 2.255 (score 76.4) |
| pinhole k=100 | 0.156 | 0.935 | 1.368 | 2.078 (score 77.0) |
| two-offset mean pinhole / fisheye | 0.15 / **0.12** | 0.86 / **0.78** | **1.19** / 3.28 | 2.34 / **2.13** (score 75 / 77) |

**Decision**: fisheye is better on three of four and consistently worse on R_08 (3x). R_08 is recorded with the other Aria unit; the raw image has fewer optical-flow cells at Basalt's 50 px grid on 640x480. B13 tries a 40 px grid on the fisheye input for R_08 and R_01.

## B10: Basalt on the native fisheye input (kb4) (2026-10-03, pc)

**Change**: `data/training_fisheye/<seq>` (raw 640x480 frames, fitted Kannala-Brandt lens as Basalt "kb4"), `basalt_ref1`, robust driver, offset 0.

**Result** (ATE m sim3; pinhole Basalt robust and OpenVINS at the same offset):

| | R_01 | R_04 | R_08 | R_11 |
|---|---|---|---|---|
| Basalt fisheye | **0.110** (0.991) | 0.799 (1.003) | 3.693 (0.980) | 1.999, **score 78.3** |
| Basalt pinhole | 0.151 | 0.781 | 1.006 | 2.605, score 73.3 |
| OpenVINS ov_ref005 | 0.289 | 1.480 | 1.484 | 0.684, score 72 |

No restarts in any fisheye run. Unlike OpenVINS (v1 033), Basalt handles the raw fisheye well: its sim3 scale is 0.98 to 1.00 everywhere.

**Decision**: continue; second offset on the four (B11) before deciding pinhole vs fisheye for Basalt; R_08 is the open question (drift without divergence).

## B09: Basalt knobs on the 2 km walks (2026-10-03, pc)

**Change** (robust driver, from `basalt_ref1` = noise x20, 4 levels, 10 keyframes): noise x10; keyframes 7; keyframes 15; 5 states (the last failed to run, see log). On sequence_3_17 and 3_18 only.

**Result** (score 2D / recall @ 5 m; ATE, sim3 scale):

| Variant | sequence_3_17 | sequence_3_18 |
|---|---|---|
| ref1 (B08) | 4.3 / 3.4 (48.1, 0.917) | 2.4 / 4.2 (81.0) |
| noise x10 | 6.3 / 9.0 (39.6, 0.901) | 2.5 / 5.5 (53.9, 1.063) |
| keyframes 7 | 0.2 / 0.0 (51.4) | 3.9 / 4.3 (70.6) |
| keyframes 15 | 1.7 / 3.0 (48.7) | 0.0 / 0.2 (82.5) |
| OpenVINS ov_ref005 | 9.9 / 21.6 (16.1) | 13.1 / 33.0 (26.0) |

**Decision**: none of Basalt's window / weighting knobs touches the 2 km drift (scale wanders 0.90 to 1.10 along these walks); this is structural, not a setting. Basalt stays the better system on short and medium walks, OpenVINS on the long ones; a per-sequence selection or a fusion of the two lines is a legitimate v3 option. Next for Basalt: the native kb4 fisheye input (B10) and the mapper.

## B08: robust Basalt on the ten additional-set sequences (2026-10-03, pc)

**Setup**: `basalt_ref1` with the robust driver, offset 0, pinhole input.

**Result** (score 2D / recall @ 5 m; OpenVINS ov_ref005 from v1 037 in brackets; restarts):

| Sequence | Basalt robust | OpenVINS | restarts |
|---|---|---|---|
| sequence_1_19 | **64.1 / 100** (ATE 1.02) | 40.0 / 99.9 | 0 |
| sequence_1_20 | 39.6 / 93.6 (3.56) | 46.3 / 99.9 | 0 |
| sequence_2_11 | **20.7 / 45.9** (30.9) | 11.6 / 15.7 | 0 |
| sequence_2_12 | 5.3 / 12.6 (27.3) | 29.0 / 60.4 | 3 |
| sequence_3_17 | 4.3 / 3.4 (48.1) | 9.9 / 21.6 | 0 |
| sequence_3_18 | 2.4 / 4.2 (81.0) | 13.1 / 33.0 | 0 |
| sequence_4_10 (low light) | **8.4 / 15.3** (29.1) | 0.9 / 0.0 | 2 |
| sequence_4_11 | 9.9 / 18.9 (14.9) | 30.2 / 66.2 | 1 |
| sequence_5_11 (moving platform) | 6.9 | 28.4 | 1 |
| sequence_5_12 (moving platform) | 7.6 | 8.5 | 1 |
| **mean score** | **16.9** | **22.0** | |

Diagnostic on 3_17 (2 km, 49 m of elevation, sharp frames): both systems drift horizontally with a scale of 0.92 to 0.93; Basalt 2.1 m per 100 m against 1.2 for OpenVINS. On 1_19 Basalt is 3x more accurate.

**Decision**: continue, but the picture is split: Basalt wins the controlled set (2.43 vs 2.83 m) and the shorter / dark walks, OpenVINS wins the long walks. Basalt's long-range drift is the thing to attack (B09: keyframe window, IMU weighting on 3_17 / 3_18), then its mapper. No decision between candidates yet, by design.

## B07: robust Basalt on all 13 controlled sequences, two offsets (2026-10-03, pc)

**Setup**: `basalt_ref1` through `run_basalt_robust.sh` (divergence restart + stitching), offsets 0 and 100, pinhole ASL input.

**Result** (ATE m sim3; restarts; score 2D for the control-point sequences; OpenVINS ov_ref005 for comparison):

| Seq | OV k=0 / k=100 | Basalt robust k=0 / k=100 | restarts | score (Basalt / OV) |
|---|---|---|---|---|
| R_01 | 0.289 / 0.176 | **0.151 / 0.156** | 0 / 0 | |
| R_02 | 0.584 / 0.358 | **0.173 / 0.215** | 0 / 3 | |
| R_03 | 0.216 / 0.195 | 0.434 / 0.415 | 1 / 0 | |
| R_04 | 1.480 / 0.675 | **0.781** / 0.935 | 0 / 1 | |
| R_05 | 1.307 / 1.715 | **1.139 / 1.153** | 0 / 0 | |
| R_06 | 2.081 / 1.906 | **1.124 / 0.764** | 0 / 0 | |
| R_07 | 3.203 / 1.974 | **1.236 / 1.220** | 1 / 0 | |
| R_08 | 1.484 / 1.964 | **1.006 / 1.368** | 0 / 1 | |
| R_09 | 3.843 / 6.696 | **2.762 / 2.414** | 0 / 0 | |
| R_10 | 6.102 / 6.336 | **4.412 / 3.877** | 1 / 0 | |
| R_11 | 0.684 / 0.476 | 2.605 / 2.078 | 0 / 0 | 73.3 / 77.0 vs 72 |
| R_12 | 9.211 / 8.579 | 12.857 / 12.936 | 0 / 3 | 12.0 / 14.0 vs 13 / 6 |
| R_13 | 5.188 / 6.940 | **3.349 / 3.544** | 0 / 0 | 45.2 / 44.3 vs 39 / 30 |
| **mean** | **2.83** | **2.43** | | |

**Decision**: robust Basalt (`basalt_ref1` + segments driver) is the best controlled-set result so far: better on 10 of 13 by two-offset mean, worse on R_03 (small), R_11 (ATE, though its score is higher) and R_12. At about 2x realtime on fewer than 2 cores. Next: the additional set (B08), then Basalt's own knobs again on top of the robust driver (restart thresholds, noise x20 vs x30, keyframes), the offline mapper, and the kb4 fisheye input.

## B06: Basalt with script-level divergence recovery (2026-10-03, pc)

**Change**: `scripts/basalt_segments.py` / `run_basalt_robust.sh`: run Basalt, detect divergence in its output (per-frame speed > 6 m/s or jump > 1 m), keep the poses up to 20 frames before it, restart Basalt from that frame on a trimmed input, map the new segment's first pose onto the last kept pose (SE3), repeat. Same `basalt_ref1` configuration.

**Result** on the six diverged B05 cells (ATE m sim3; B05 value; OpenVINS ov_ref005 at the same offset):

| Cell | B05 (no recovery) | B06 robust | restarts | OpenVINS |
|---|---|---|---|---|
| R_10 k=0 | 113 | **4.235** | 1 | 6.102 |
| R_07 k=0 | 65.3 | **1.255** | 1 | 3.203 |
| R_04 k=100 | 38.8 | 0.929 | 1 | 0.675 |
| R_08 k=100 | 49.7 | **0.963** | 1 | 1.964 |
| R_03 k=0 | 6.16 | 0.435 | 1 | 0.216 |
| R_12 k=100 | 54.7 | 13.24 (score 12.9) | 3 | 8.579 (score 5.9) |

Each needed exactly one restart; poses exist for every frame (the restart gap is carried forward like in the OpenVINS runner).

**Decision**: keep; the robust driver is Basalt's runner from here. B07 = robust Basalt on all 13 at two offsets for the proper comparison with ov_ref005 (2.83 m).

## B05: Basalt reference on all 13 controlled sequences, two offsets (2026-10-03, pc)

**Setup**: `configs/basalt_ref1` (noise x20, 4 pyramid levels, 10 keyframes), start offsets 0 and 100 (new `SKIP_FRAMES` support in the EuRoC-layout input), pinhole ASL input.

**Result** (ATE m sim3; OpenVINS ov_ref005 for comparison):

| Seq | OV k=0 | OV k=100 | Basalt k=0 | Basalt k=100 |
|---|---|---|---|---|
| R_01 | 0.289 | 0.176 | **0.151** | **0.156** |
| R_02 | 0.584 | 0.358 | **0.170** | **0.230** |
| R_03 | 0.216 | 0.195 | 6.160 (diverged) | 0.413 |
| R_04 | 1.480 | 0.675 | **0.788** | 38.8 (diverged) |
| R_05 | 1.307 | 1.715 | **1.139** | **1.159** |
| R_06 | 2.081 | 1.906 | **1.131** | **0.726** |
| R_07 | 3.203 | 1.974 | 65.3 (diverged) | **1.216** |
| R_08 | 1.484 | 1.964 | **1.001** | 49.7 (diverged) |
| R_09 | 3.843 | 6.696 | **2.726** | **2.420** |
| R_10 | 6.102 | 6.336 | 113 (diverged) | **4.026** |
| R_11 | 0.684 | 0.476 | 2.601 (score 73.2) | 2.051 (score 78.4) |
| R_12 | 9.211 | 8.579 | 12.68 (score 13.1) | 54.7 (diverged) |
| R_13 | 5.188 | 6.940 | **3.411 (score 44.8)** | **3.537 (score 44.3)** |

Two-offset means: OpenVINS 2.83 m, Basalt 14.2 m (dominated by the six divergences); Basalt better on 6 of 13 by mean, and on 18 of the 20 non-diverged cells it beats the OpenVINS run at the same offset. Basalt has no divergence detection or recovery, so one bad stretch costs the rest of the sequence.

**Decision**: continue. The accuracy when it holds is clearly better than tuned OpenVINS at a lower CPU cost; the missing piece is the robustness layer v1 built for OpenVINS. B06: script-level divergence detection + restart from just before the divergence + stitching (`scripts/basalt_segments.py`), then rerun these 26.

## C01: ORB-SLAM3 stereo-inertial out of the box, fisheye input (2026-10-03, pc, ORB_SLAM3 4452a3c + C++14, viewer off)

**Setup**: `scripts/run_orbslam3.sh` with `configs/orbslam3_default` (EuRoC/TUM-VI defaults: 1200 ORB features, 8 levels), KannalaBrandt8 from the fitted fisheye calibration (`data/training_fisheye`), IMU noise x1, loop closing on. The right raw frames are stamped 25 us after the left ones; alias links let the example load them by the left timestamp.

**Result**, R_01_easy: ATE sim3 **0.031 m** (scale 0.969), 2888 of 2898 images with a pose (10 before initialisation). Paper: ORB-SLAM3 0.03 m. The first attempt segfaulted 70 s in; the same command run under gdb completed normally (timing-dependent crash, a known ORB-SLAM3 trait), so the run script now retries up to three times.

R_04_medium: 0.794 m (scale 0.922) but poses for only 3923 of 5253 frames (tracking lost for a quarter of the sequence; those frames get carried-forward poses in the submission). R_11_5cp: 0.999 m, score 65.6, recall @ 1 m 53.5, 9528 of 9547 poses. R_08_hard: crashed three times right after the second inertial BA ("end VIBA 2"), 1.5 GB RSS; no result.

**Decision**: continue, with lower priority than A and B: superb when it holds (R_01), but it loses tracking (R_04) and crashes deterministically on R_08 as built. Next tries: pinhole input, IMU noise scaling, `IMU.InsertKFsWhenLost`, and a look at the crash site.

## B04: Basalt combinations (2026-10-03, pc)

**Change**: combinations of the B03 winners: noise x20 + 4 levels (n20l4); + 5 levels (n20l5); x30 + 4 levels (n30l4); x20 + 4 levels + 10 keyframes (n20l4k10). `configs/basalt_r4_*`. Four runs had to be repeated after a symlink race between concurrent Basalt runs (fixed with `ln -sfn`).

**Result** (ATE m sim3, offset 0; R_11 score 2D in brackets):

| Variant | R_01 | R_04 | R_08 | R_11 |
|---|---|---|---|---|
| B02 noise x10 | 0.338 | 1.549 | 3.837 | 1.614 (52) |
| B03 noise x20 | 0.367 | 1.009 | 1.307 | 1.028 (69.5) |
| B03 levels 4 | 0.138 | 1.010 | 1.347 | 1.376 (69.5) |
| x20 + levels 4 | 0.143 | 0.862 | 1.110 | 2.562 (74.1) |
| x20 + levels 5 | 0.285 | 0.806 | 1.652 | 2.449 (63.6) |
| x30 + levels 4 | 0.147 | 1.007 | 0.927 | 3.049 (69.9) |
| **x20 + levels 4 + 10 keyframes** | 0.152 | **0.775** | **1.006** | 2.595 (73.5) |
| OpenVINS ov_ref005 (k=0) | 0.289 | 1.480 | 1.484 | 0.684 (72) |

**Decision**: `configs/basalt_r4_n20l4k10` becomes the Basalt reference (B-ref1): ahead of tuned OpenVINS on R_01/R_04/R_08 and on the R_11 score, at about 2x realtime on fewer than 2 cores. R_11's ATE is unstable across Basalt variants (1.0 to 3.0) while its score stays 64 to 74; needs the two-offset view. Next: all 13 controlled at two offsets (B05), then Basalt's offline mapper (non-causal BA + loop closure) on top (B06), then the fisheye kb4 input (Basalt handles it natively).

## B03: Basalt single-knob round (2026-10-03, pc)

**Change** (one knob each from B02 = noise x10): noise x5 / x20; optical-flow detection grid 30 px (default 50); optical-flow pyramid levels 4 (default 3); max keyframes 10 (default 7). `configs/basalt_r3_*`.

**Result** (ATE m sim3, offset 0; R_11 also score 2D):

| Variant | R_01 | R_04 | R_08 | R_11 |
|---|---|---|---|---|
| B02 noise x10 | 0.338 | 1.549 | 3.837 | 1.614 (52.1) |
| noise x5 | 0.298 | 2.025 | 4.532 | 3.236 (33.0) |
| noise x20 | 0.367 | **1.009** | **1.307** | **1.028 (69.5)** |
| grid 30 px | 0.645 | 1.612 | 1.666 | 1.984 (52.2) |
| pyramid levels 4 | **0.138** | **1.010** | **1.347** | 1.376 (69.5) |
| keyframes 10 | 0.239 | 1.502 | 3.939 | 1.755 (48.6) |

OpenVINS ov_ref005 k=0: 0.289 / 1.480 / 1.484 / 0.684 (72).

**Decision**: noise x20 and 4 pyramid levels are each large gains on three of four sequences; combine them in B04 (x20 + 4 levels; with 5 levels; x30; plus 10 keyframes).

## B02: Basalt, IMU noise x10 (2026-10-03, pc)

**Change**: `NOISE_SCALE=10` on the white-noise densities (walks x1), as OpenVINS needed. `configs/basalt_n10`.

**Result** (ATE m sim3, offset 0; OpenVINS ov_ref005 k=0 for comparison):

| | R_01 | R_04 | R_08 | R_11 |
|---|---|---|---|---|
| Basalt default (B01) | 1.558 | - | - | - |
| Basalt noise x10 | 0.338 (0.997) | 1.549 (0.989) | 3.837 (0.963) | 1.614 (0.934), score 52.1 / recall@1m 16.3 |
| OpenVINS ov_ref005 | 0.289 | 1.480 | 1.484 | 0.684, score 72 |

Runtime: 102 / 165 / 344 / 269 s at 1.6 to 1.9 cores, i.e. about 2x realtime on fewer than 2 cores (OpenVINS ~1.4x realtime on one core). Basalt's sim3 scale is 0.99 to 1.00 on R_01/R_04 where OpenVINS shows 0.96 to 0.98, so the v1 scale offset is estimator-specific.

**Decision**: continue; the noise scaling was the big step (4.6x on R_01). Round B03: optical-flow grid 30 px, 4 pyramid levels, 10 keyframes, noise x5 and x20, one knob each.

## B01: Basalt out of the box (2026-10-03, pc, binary release 2026-03-22)

**Setup**: `scripts/run_basalt.sh` with `configs/basalt_default` (= Basalt's `euroc_config.json`), calibration from the LaMAria pinhole JSON (`make_basalt_calib.py`), IMU noise as in the JSON (x1), 4 threads, pinhole ASL input.

**Result**: R_01_easy ATE sim3 1.558 m (scale 0.964), a pose for all 2898 images, 66 s wall at 2.8 cores (about 2.2x realtime). OpenVINS reference on the same run: 0.19 to 0.29 m.

**Decision**: expected for defaults tuned to EuRoC (different camera, rate and noise); optimisation rounds start with the IMU noise scaling that OpenVINS needed (x10) and the optical-flow settings.

## Plan per candidate

1. Build and adapter (same inputs, same `trajectory.tum` output, same scoring).
2. Out-of-the-box run on the standard four (R_01, R_04, R_08, R_11), two offsets.
3. Optimisation rounds: calibration/model choice (pinhole vs native fisheye), noise and tracking parameters, keyframing, loop closure on/off, non-causal refinement if available. Each round recorded here.
4. Full comparison: 13 controlled sequences at two offsets plus the ten additional-set sequences.
5. Decision for v3: approach or combination.
