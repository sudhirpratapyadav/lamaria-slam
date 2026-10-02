# Experiments (v2: exploration of estimator classes)

One section per experiment, newest first, same fields as v1 (hypothesis, change, command, per-sequence result, cost, decision). Scoreboard at the top. The v1 reference (`configs/ov_ref005`, OpenVINS) is the baseline every candidate is compared against: controlled set two-offset mean ATE 2.83 m; additional set scores in v1 experiments 030 / 037.

## Scoreboard

| Candidate | Stage | Controlled set, 2-offset mean ATE (13 seq) | Additional set score 2D / recall @ 5 m (seq_1_19, 1_20, 2_11, 2_12) | Notes |
|---|---|---|---|---|
| v1 OpenVINS ov_ref005 | tuned (v1) | 2.83 m | 40.0/99.9, 46.3/99.9, 11.6/15.7, 29.0/60.4; 3_17 9.9/21.6, 3_18 13.1/33.0, 4_10 0.9/0, 4_11 30.2/66.2 (v1 037) | causal, ~1.4x realtime on one core |
| A OKVIS2 | A02 noise x10 | R_01 0.145 live / **0.033 final**; R_04 0.84 / **0.69**; R_08, R_11 running | | very slow under load (0.1x realtime), final BA non-causal |
| B Basalt | B06 robust driver | all 5 tested divergences rescued with one restart (R_10 4.2 vs OV 6.1, R_07 1.3 vs 3.2) | | B07 = robust on 13 x 2 running |
| C ORB-SLAM3 | C01 defaults, fisheye | R_01 **0.031**; R_04 0.79 (25 % frames lost); R_11 1.00 (score 65.6); R_08 crashes | | brittle: loses tracking, crashes |
| D OpenVINS line | D01 ov_ref005 + window 21 | 3.44 vs 2.83 over 13 | mean score 22.3 vs 22.0 (2_11 up to 27.3 / 68.5 %) | D02 blur-adaptive window running |

## A01: OKVIS2 out of the box (2026-10-03, pc, okvis2 a2ea006, USE_NN=OFF)

**Setup**: `scripts/run_okvis2.sh` with `configs/okvis2_default` (OKVIS2 defaults: loop closures on, final bundle adjustment on, realtime limit off, CNN off), calibration from the LaMAria pinhole JSON (radialtangential with zero coefficients), IMU noise as in the JSON (x1), pinhole ASL input. Two outputs: the live estimate (causal) and the trajectory after the final full BA (non-causal).

**Result**, R_01_easy: live ATE sim3 0.237 m (scale 0.958); final-BA ATE 0.043 m (scale 0.976); poses for all 2898 images. Paper: OKVIS2 0.02 m, OpenVINS 0.66 m; our OpenVINS ov_ref005 0.19 / 0.29 m. Cost: 1466 s wall (10x slower than realtime) at 0.83 cores average under a heavily loaded machine (15 other estimators running), 564 MB RSS. A clean timing is owed.

R_04_medium (defaults): live 1.555 m (scale 0.894), final BA 1.441 m (scale 0.898), all 5253 poses, 1988 s wall under load. Basalt 0.79, ORB-SLAM3 0.79 (with gaps), OpenVINS 1.48 on the same run. The low scale says the datasheet IMU noise makes OKVIS2 over-trust the IMU; noise scaling (A02) is the next round. R_08_hard and R_11_5cp (defaults): diverged (ATE 95 / 42 m, sim3 scale 0: the estimate runs off to kilometres), 87 / 65 min wall and 6.5 / 6.1 GB RSS under load. So the datasheet noise makes OKVIS2 fail on the hard sequences exactly as it did OpenVINS and Basalt before their noise scaling.

**Decision**: continue with high priority. The final-BA trajectory is the non-causal, benchmark-eligible path; the live one is the causal (robot) path. Next: A02 noise x10 on R_01/R_04, then keyframing and the fisheye input (OKVIS2 has a native equidistant model).

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

**Decision**: continue; noise x10 is OKVIS2's working point so far. Next: R_08 and R_11 (diverged at x1), then x20, keyframing, realtime budget vs accuracy, fisheye input.

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
