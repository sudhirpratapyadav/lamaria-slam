# Experiments (v3: front end)

One section per experiment, newest first, same fields as before (hypothesis, change, exact command, per-sequence result, cost, decision) plus an **applicability** line for every kept change: where it applies (indoor, outdoor, tunnel, platform, this sensor, this benchmark), how general it is, where it can fail. Scoreboard at the top. Reference: Basalt `basalt_ref1` with the robust driver (v2 B07/B08): controlled two-offset mean 2.43 m, additional-set mean score 16.9; Huber 0.5 and the 1.5 m near cap as per-sequence options (19.7 / 21.6).

## Scoreboard

| Candidate | Stage | Event sequences (2_11, 3_18, 4_11, R_12, R_08, R_11) | Controlled 2-offset | Additional mean score | Applicability | Notes |
|---|---|---|---|---|---|---|
| Basalt ref1 (v2) | reference | 30.9 / 81.0 / 14.9 / 12.9 / 1.01 / 2.61 m | 2.43 | 16.9 | general | |
| F01/F07 outlier filter 3 px | full sets done | 22.8 / 54.4 / 3.8 / 14.2 / 1.07 / 2.05 m | 2.50 (wins easy, hard, R_11; loses medium, R_12, R_13) | **21.2** (8 of 10 up; moving platform down) | general; restarts right after init (F08), vehicle interiors | candidate reference |
| F03 epipolar gate 0.005 | event set, 4 re-running | 21.1 / 57.4 / 10.5 / ? / 1.14 / ? m; best 2_11 (30.3) and 3_18 (4.7) scores | | | general, IMU-prediction dependent, indoor tax | combine with filter (F09) |
| F05 gate 5 + masks | event set done | 24.2 / 52.7 / 3.3 / 14.6 / 1.29 / 2.10 m | | | people and own body; 15-30 % tax where nothing to remove | option |
| F04 untrusted-image rule | stopped | R_08 142 m | | | | discarded |

## F01: IMU-consistency gate and the dormant outlier filter in Basalt (2026-10-03, pc)

**Finding first**: Basalt's VIO never calls its own `filterOutliers` (a `TODO` in `sqrt_keypoint_vio.cpp`), so in all v2 runs no observation was ever rejected after the solve; only the Huber loss damped them. That is why the Huber threshold was the one knob that moved things in v2.

**Hypothesis**: features on moving objects (people, the wearer's arm and shoe, reflections) disagree with the IMU-predicted ego-motion. Checking each observation of an existing landmark against its reprojection from the IMU-predicted pose, before the solve, removes them where they appear; the post-solve reprojection filter removes what slips through.

**Change** (`sqrt_keypoint_vio.cpp`, env-gated, in `docs/patches/basalt-0f3b2b5.patch`): `BASALT_IMU_GATE_PX` drops an observation whose reprojection residual from the IMU-predicted state exceeds the threshold (announced once, counts every 500 frames); `BASALT_OUTLIER_PX` calls `filterOutliers` after each optimisation with that reprojection threshold (`BASALT_OUTLIER_MIN_OBS`, default 2). `basalt_ref1` otherwise, robust driver, offset 0.

**Command**: `results/v3-F01-imu-gate/batch.sh`: gate 5 px, gate 10 px, filter 3 px, gate 5 + filter 3, each on R_08, R_11, R_12, sequence_2_11, 3_18, 4_11. The gate drops 0.3 to 0.7 % of observations.

**Result** (ATE m; score 2D / recall @ 5 m; reference basalt_ref1 first):

| Seq | reference | gate 5 px | gate 10 px | filter 3 px | gate 5 + filter 3 |
|---|---|---|---|---|---|
| R_08 | **1.006** | 1.327 | 1.299 | 1.072 | 1.129 |
| R_11 | 2.605, 73.3 / 96.5 | 2.150, 78.5 / 97.3 | 2.394, 74.8 / 96.9 | **2.051, 78.7 / 97.7** | 2.077, 78.3 / 97.6 |
| R_12 | **12.86, 12.0 / 18.1** | 13.97, 11.2 / 17.6 (1 restart) | 15.44, 9.3 / 11.1 | 14.17, 10.4 / 17.9 | 14.06, 10.3 / 17.9 |
| sequence_2_11 | 30.92, 20.7 / 45.9 | 25.09, **26.7 / 52.8** | 31.85, 20.9 / 42.4 | **22.75**, 21.2 / 44.7 | 22.18, 23.4 / 49.8 |
| sequence_3_18 | 81.04, **2.4** / 4.2 | 55.42, 1.9 / 5.2 | 55.83, 1.2 / 1.4 | **54.41**, 1.3 / 2.6 | 55.07, 2.1 / 4.8 |
| sequence_4_11 | 14.89, 9.9 / 18.9 | 7.96, 16.0 / 32.9 | 5.45, 25.9 / 63.0 (after the X05 fix, 2 restarts; crashed run was 4.72 / 26.6 / 60.8) | **3.79, 37.9 / 99.1** | 4.11, 29.7 / 83.9 |

Enabling the post-solve outlier filter at 3 px (upstream's own function, never called) is the clear winner: the dark walk goes from 14.9 m / score 9.9 / recall 19 % to 3.8 / 37.9 / 99.1 %, the same level as v2's scene-specific near-feature cap but by a general mechanism; R_11 improves, 2_11 and 3_18 lose a quarter to a third of their ATE, R_08 is a near tie, R_12 loses a little. The IMU gate alone is weaker and hurts R_08; adding it to the filter adds nothing. So on these sequences the damage is done by features whose reprojection error is large *after* the solve (the Huber loss only damped them), more than by features inconsistent with the IMU prediction before it.

**Decision**: iterate the filter (F06: 2, 4, 5 px and a stricter minimum-observation rule) and validate 3 px on the full sets (F07). The IMU gate stays available (off by default).

**Applicability**: general (reprojection outlier rejection is standard practice; the threshold scales with resolution and noise), fails if the threshold is set below the honest noise level (drops good points) or if the solve itself is already wrong when the filter runs.

**Applicability**: general (any VIO with an IMU prediction); can fail when the IMU prediction itself is poor (bad biases right after initialisation, wrong noise parameters) by rejecting good features; thresholds are in pixels, so they depend on resolution and lens.

## X02: do learned detectors find points where FAST finds none? (2026-10-03, pc, analysis only)

**Method**: `scripts/keypoint_density.py` (run with `.venv-ml`, CPU torch): one frame every 4 s, FAST per 50 px grid cell with Basalt's adaptive threshold (40 down to 5) against XFeat (CPU, score > 0.1), averaged per 60 s window, next to image brightness.

**Result, sequence_4_11 (dark walk)**: FAST fills 80 to 142 of 165 cells throughout; XFeat finds 180 to 645 points. The bad window (450 s, where v2 saw the 20-degree swings) is the minimum of both: 82 cells, 179 XFeat points, brightness 17. The darkest window (750 s, brightness 13) has 79 cells but 455 XFeat points. So the adaptive FAST threshold always finds *something* (noise corners in the dark); the learned detector finds more in most dark windows but not in the worst one. The limiting factor at 450 s is not the count of detectable points but what they are worth for tracking: this diagnostic cannot see that, the tracking experiments (F-series) will.

**Applicability of the tool**: general diagnostic. XFeat ran at about 0.3 s per frame on the CPU here (unoptimised), fine offline. Other event walks (3_18, 2_11, R_12) running.

## X03: can an off-the-shelf person segmenter see the wearer's body and passers-by? (2026-10-03, pc)

**Method**: YOLO11n-seg (Ultralytics, AGPL, 6 MB weights) on the twelve event frames extracted in v2 X01 (`results/v2-X01-drift-analysis/frames/`), CPU. The Aria cameras are mounted sideways; the frames were tested as is and rotated 90 degrees both ways.

**Result**: as is, the detector finds the shoe on R_12 (as "person", clean mask, 11 % of the image) but misses the four pedestrians on 2_11 at 1110 s. Rotated clockwise (upright), it finds them (4 persons plus a handbag), the people on 2_11 at 630 s, R_12 at 530 s and 3_18 at 870 s, and still the shoe; counter-clockwise finds almost nothing. Misses: the people in shop-window reflections on 3_18 at 1170 s, and the arm on 2_11 at 1110 s (people found, arm not). About 130 ms per frame on one CPU core. Outputs in `results/v3-X03-person-masks/`.

**Decision**: good enough to try as a mask (F02). **Applicability**: general for people; body parts are hit and miss (COCO "person" is a whole body); reflections are not covered; the clockwise rotation is Aria-specific (any sideways-mounted camera needs the same).

## F02: person and body masks in Basalt's optical flow (2026-10-03, pc)

**Hypothesis** (X01, B18's R_12 analysis): features on people and on the wearer's own body cause the heading events; removing them before tracking removes the events without touching the rest.

**Change**: `scripts/make_person_masks.py` precomputes per-frame masks for cam0 (YOLO11n-seg, frames rotated upright, masks rotated back, dilated 12 px, stored as `data/training/<seq>/masks_person/cam0/<stamp>.png` with a stats csv; 12 CPU workers at one thread each, about 1100 frames per minute after fixing a thread-oversubscription bug that had it at 55). Basalt `frame_to_frame_optical_flow.h` (env `BASALT_MASK_DIR`, in the patch file): no corners are detected inside the mask and tracks that enter it are dropped from both cameras; a frame without a mask keeps the previous one; counts every 1000 frames. `basalt_ref1` otherwise, robust driver, offset 0.

**Command**: `results/v3-F02-person-masks/masks.sh` (masks for R_12, 4_11, 2_11, 3_18, R_08, R_11), then `batch.sh` (one run per sequence as soon as its masks exist).

**First pass (confidence 0.25), void**: R_12 came out at 18.7 m, score 5.5 (reference 12.9 / 12.0) with the heading swing at 450 to 510 s grown to -25 / +35 degrees. Cause: in 22 % of the frames the mask covered more than 10 % of the image and in 3 % more than 90 %. Looking down at the pavement, the detector returns a confident mask on the feet (0.54) plus a low-confidence "person" box (0.29) spanning the whole image; the union starved the tracker exactly in the stretch that matters. Fixes: masks regenerated at confidence 0.4, and Basalt now ignores any mask covering more than `BASALT_MASK_MAX_FRAC` (0.4) of the image.

**Result** (second pass, confidence 0.4, oversized masks ignored; ATE m, score 2D / recall @ 5 m; reference basalt_ref1 in brackets):

| Seq | masks | reference | tracked points dropped |
|---|---|---|---|
| R_08 | 1.157 | **1.006** | 1019 |
| R_11 | **2.422, 75.1 / 96.8** | 2.605, 73.3 / 96.5 | 2402 |
| R_12 | **12.61, 13.3 / 18.2** | 12.86, 12.0 / 18.1 | 4630 |
| sequence_2_11 | **24.29, 26.0 / 48.2** | 30.92, 20.7 / 45.9 | 13182 |
| sequence_3_18 | 73.77, 0.4 / 0.2 | 81.04, **2.4 / 4.2** | 8202 |
| sequence_4_11 | re-running (first run crashed, X05) | 14.89, 9.9 / 18.9 | |

Small, consistent gains where people walk through the view (2_11 by a fifth in ATE and five score points, R_11, R_12), a loss on R_08 (indoor, few people: the masks only remove good points) and a split on 3_18. The shoe episode on R_12 improves only slightly: the mask covers the feet in the looking-down frames, but the heading swing there is already partly caused by the near pavement filling the view. **Decision**: keep as an option; combine with the IMU gate (F05) and test the combination on the full sets.

**Applicability**: general wherever people or the robot's own body enter the view (homes, streets); costs a segmentation per frame (about 25 ms on an Orin for the detection-only model, more for masks); fails on reflections and on body parts the detector does not recognise; no help in dark or low-texture stretches.

## F03: temporal epipolar gate on new landmarks (2026-10-03, pc)

**Hypothesis**: F01's gate only checks observations of landmarks that already exist. A new track is triangulated from two frames whose relative pose comes from the IMU prediction; if its two observations violate the epipolar constraint of that pose, the point moved on its own and should never become a landmark.

**Change**: `sqrt_keypoint_vio.cpp`, in the triangulation of new landmarks: `BASALT_EPI_GATE` (same units as Basalt's stereo `optical_flow_epipolar_error`, default there 0.005; 0 = off) rejects candidate pairs with `|p0^T E p1|` above it, counts reported every 500 frames. `basalt_ref1` otherwise, robust driver, offset 0.

**Command**: `results/v3-F03-epi-gate/batch.sh` (0.005 and 0.002 on the six event sequences). The first batch lost 7 of 12 runs to the memory reaper (SIGTERM, see logs 21:xx); they were re-run under a systemd unit, four of them are still running.

**Result** (ATE m; score 2D / recall @ 5 m; reference basalt_ref1 first; "failed" = X05 crash segments restarted by the driver, those runs are being re-run with the fix):

| Seq | reference | epi 0.005 | epi 0.002 |
|---|---|---|---|
| R_08 | **1.006** | 1.142 | 1.204 |
| R_11 | 2.605, 73.3 / 96.5 | **2.422, 74.3 / 96.9** | 2.493, 75.8 / 96.7 |
| R_12 | **12.86, 12.0 / 18.1** | 15.09, 8.6 / 13.6 (1 restart) | 15.24, 10.6 / 17.2 |
| sequence_2_11 | 30.92, 20.7 / 45.9 | 21.06, **30.3** / 49.5 (1 failed) | **20.64**, 28.9 / **61.9** |
| sequence_3_18 | 81.04, 2.4 / 4.2 | 57.42, **4.7 / 9.9** | **55.24**, 3.2 / 9.5 |
| sequence_4_11 | 14.89, 9.9 / 18.9 | **10.46, 10.3 / 22.5** (2 failed) | 21.79, 8.7 / 15.4 (5 failed) |

Both thresholds help every long walk with people (2_11 to 21 m with the best control-point scores of any single change, 29 to 30, and recall up to 62 %; 3_18 to 55 to 57 m with the best score on that walk), 0.005 also helps 4_11 by a third, and both cost 14 to 20 % on R_08 and R_12, the two sequences where there is little to reject (the same signature as the IMU gate, F01/F05). The 4_11 runs crashed (X05) and are being re-run. **Decision**: 0.005 is a candidate for the walks; combined with the outlier filter in F09.

## X04: where and when the IMU gate fires (2026-10-03, pc, analysis)

**Method**: F01's gate at 5 px with `BASALT_GATE_DUMP` on R_12 and sequence_4_11; `scripts/gate_map.py` bins the dropped cam0 observations on a 6x4 image grid and per 60 s window.

**Result**: R_12: 7814 drops, 2441 of them (31 %) in the 450 s window where the wearer looks down at their shoes (X01/B18), the rest spread thinly; in the image they sit in the centre rows (rows 2 and 3, columns 3 to 5), not in a corner. sequence_4_11: 2479 drops spread evenly over time (48 in the 450 s window where the heading swings happen), also centred.

**Reading**: on R_12 the gate finds the liars where and when they are, so the mechanism works as intended there. On the dark walk the swings are not caused by inconsistent features; the gate fires uniformly on noise, and 4_11 is the "too few usable features" failure type, not the "wrong features" type (consistent with X02). A static body-region prior is not viable: the wearer's body appears in the image centre whenever they look down, not in a fixed corner. **Applicability**: diagnostic only.

## F04: untrustworthy-image rule (2026-10-03, pc)

**Hypothesis** (X02/X04): on the dark walk the damage comes from frames with very few usable tracks, where the few noisy ones pull the heading. If such a frame contributes no visual observations and spawns no landmarks, the IMU carries the state through the stretch at a known, bounded drift instead.

**Change**: `sqrt_keypoint_vio.cpp`: `BASALT_MIN_OBS_FRAME` (0 = off): when fewer tracked landmarks than this reach the frame in cam0, no observations are added for the frame and it cannot become a keyframe; count reported every 100 untrusted frames. `basalt_ref1` otherwise, robust driver, offset 0.

**Command**: `results/v3-F04-untrusted-frame/batch.sh` (15 and 30 landmarks on 4_11, R_08, 2_11, R_11; queued behind F03).

**Result**: pending.

**Applicability**: general in principle (tunnels, dark rooms, lens occlusion); the threshold depends on the feature budget of the config; risk of long IMU-only stretches drifting if the threshold is too high.

## X05: the Basalt segfault (2026-10-03, pc)

**Symptom**: `basalt_vio` dies with a null-pointer segfault in `Eigen::makeHouseholder` (float QR) inside `LandmarkBlockAbsDynamic::performQR`, called from `optimize()`. Seen twice on sequence_4_11 with masks (F02, at about frame 8000 both times, so deterministic) and, in hindsight, in v2's B21/B22 runs with failed segments (4_11, 5_12). The robust driver hides it as a "failed" segment and restarts 100 frames later, which costs 100 poses and a stitch.

**Cause**: a landmark left without any observation (its tracks dropped by the mask, the gates, `filterOutliers` or marginalisation) still gets a landmark block; with zero rows the QR dereferences null. Upstream never removes observations outside marginalisation, so it only hits this rarely.

**First attempt (did not fix it)**: removing, before `optimize()`, landmarks with no observations in active frames or with an inactive host. The guard never fires on the crashing case (sequence_4_11 with masks still dies at about frame 8000), so the empty block comes from somewhere else. Next: a build with debug symbols (`-O3 -g`) and a backtrace with line numbers; a debug switch `BASALT_MASK_NO_DROP` isolates the track-dropping half of the mask. The guard stays (harmless). The crash also reproduces on sequence_4_11 with the IMU gate at 10 px and no mask, so it is tied to observation removal in general, not to the mask. The debug build was first attempted at three jobs and had to be stopped (seven compilers, memory pressure); it is being redone at one job. Runs with a "failed" segment are re-run once the cause is fixed.

**Root cause (gdb on a `-g` build of the three relevant translation units, then instrumentation)**: the crashing block has `num_rows = 5`, i.e. the landmark has **one** observation, its own host frame, with inverse distance 2e-7 to 5e-7 (a point "at infinity"). Such landmarks are *created* in the keyframe step: for a keypoint seen in no other frame, the candidate list holds only the keypoint itself, and the pair (frame, frame) is supposed to be rejected by the 5 cm baseline check. In float arithmetic, once the state has diverged far from the origin, the relative pose of a frame with itself is no longer identity: the instrumented run shows the self pair at a baseline of exactly 0.0625 m, one float ulp at a position of about a million metres. So the estimate had already diverged (the robust driver later discards that part), the self pair passed, the degenerate landmark was triangulated from two identical rays, and the third Householder step of its 5-row block ran on zero rows. Upstream has the same latent bug; it only shows after a hard divergence, which is why v2 saw it on the lost walks (4_11, 5_12) and v3 whenever a rejection setting made a run diverge harder.

**Fix** (in the patch): the keyframe step never pairs a keypoint with itself; and the pre-solve guard drops any landmark with fewer than two observations and reports it (should now never fire). **Check**: 4_11 with the IMU gate at 10 px (`results/v3-X05-crash/fix_gate10`, guard-only build) runs through: 0 failed segments, 2 divergence restarts, 5.45 m / score 25.9 / recall 63 %. The guard fired twice per segment, each time right after a divergence. The re-runs of every run with a "failed" segment (F01, F02, F03) use the full fix.

**Applicability**: a bug fix, general; also a reminder that this float build loses geometry once the position exceeds some 1e5 m, i.e. only after a divergence that the driver discards anyway.

## F05: IMU gate plus person masks (2026-10-03, pc)

**Hypothesis**: F01's gate and F02's masks remove different liars (inconsistent motion versus known people); together they should cover more of the events than either.

**Change**: no new code; `BASALT_IMU_GATE_PX` 5 or 10 with `BASALT_MASK_DIR` (confidence 0.4 masks, `BASALT_MASK_MAX_FRAC` 0.4), `basalt_ref1` otherwise, robust driver, offset 0.

**Command**: `results/v3-F05-gate-mask/batch.sh` (systemd unit `lamaria-f05`).

**Result** (ATE m; score 2D / recall @ 5 m; gate 5 alone and masks alone from F01 / F02):

| Seq | reference | gate 5 | masks | gate 5 + masks | gate 10 + masks |
|---|---|---|---|---|---|
| R_08 | **1.006** | 1.327 | 1.157 | 1.288 | 1.318 |
| R_11 | 2.605, 73.3 / 96.5 | 2.150, 78.5 / 97.3 | 2.422, 75.1 / 96.8 | **2.100, 78.6 / 97.4** | 2.316, 75.7 / 97.0 |
| R_12 | 12.86, 12.0 / 18.1 | 13.97, 11.2 / 17.6 | **12.61, 13.3 / 18.2** | 14.57, 9.5 / 17.4 (1 restart) | 15.86, 8.5 / 10.8 |
| sequence_2_11 | 30.92, 20.7 / 45.9 | 25.09, 26.7 / 52.8 | 24.29, 26.0 / 48.2 | **24.15, 31.5 / 56.7** | 24.45, 2.8 / 2.1 |
| sequence_3_18 | 81.04, 2.4 / 4.2 | 55.42, 1.9 / 5.2 | 73.77, 0.4 / 0.2 | **52.73, 1.8 / 5.5** | 53.02, 1.8 / 5.4 |
| sequence_4_11 | 14.89, 9.9 / 18.9 | 7.96, 16.0 / 32.9 | (crashed) | **3.29, 36.1 / 92.3** | 9.08, 16.9 / 38.5 |

The combination at 5 px is better than either part on the three walks with people (2_11 score 31.5, 3_18, R_11) and transforms 4_11 (3.3 m, where gate alone gave 8.0; the masks remove the wearer's body in the dark stretch, the gate the rest), but it is the worst setting on R_08 and R_12, the two sequences where there is little to remove. The 10 px gate is worse everywhere. The whole gate family keeps the same signature: good where liars exist, a 15 to 30 % tax indoors. **Decision**: gate 5 + masks stays a candidate for the people-heavy walks; it does not replace the filter (F01/F06), which gets 4_11 to the same place without the indoor tax.

**Applicability**: as F01 and F02 (any VIO with IMU prediction; people and own body; sideways camera needs the rotation); the tax on clean indoor sequences is the known failure mode of every pre-solve rejection tried so far.

## F06: outlier filter threshold and minimum observations (2026-10-03, pc)

**Hypothesis**: F01's 3 px is one point on a curve; a tighter threshold removes more liars but also good points on the noisy indoor sequences, a looser one the reverse; requiring three observations before a landmark survives the filter should protect the noisy ones.

**Change**: `BASALT_OUTLIER_PX` 2, 4, 5 and 3 with `BASALT_OUTLIER_MIN_OBS` 3; `basalt_ref1` otherwise, robust driver, offset 0.

**Command**: `results/v3-F06-filter-variants/batch.sh`, then `rerun_killed.sh` and `rerun_killed2.sh` for the 16 runs the memory reaper killed (the first re-run script read the sequence name from a file the killed runs had never written, so 11 of them started with an empty path and exited; second pass running).

**Result** (ATE m; score 2D / recall @ 5 m; 3 px from F01):

| Seq | reference | 2 px | 3 px | 3 px, min 3 obs | 4 px | 5 px |
|---|---|---|---|---|---|---|
| R_08 | **1.006** | 1.275 | 1.072 | 1.084 | 1.039 | 1.078 |
| R_11 | 2.605, 73.3 / 96.5 | 2.166, 76.7 / 97.5 | **2.051, 78.7 / 97.7** | 2.087, 77.6 / 97.6 | 2.021, 77.2 / 97.7 | 1.378, 76.8 / 98.5 (2 failed segments, re-run pending) |
| R_12 | **12.86, 12.0 / 18.1** | 13.21, 10.4 / 18.1 | 14.17, 10.4 / 17.9 | 14.08, 10.0 / 17.9 | 14.07, 10.1 / 17.8 | 16.53, 7.6 / 10.3 (1 restart) |
| sequence_2_11 | 30.92, 20.7 / 45.9 | **22.60, 32.8 / 52.4** | 22.75, 21.2 / 44.7 | 22.32, 23.6 / 51.3 | 23.46, 31.5 / 56.0 | 23.86, 19.4 / 40.0 |
| sequence_3_18 | 81.04, **2.4** / 4.2 | **52.95**, 1.8 / 4.2 | 54.41, 1.3 / 2.6 | 54.66, 1.1 / 3.5 | 53.65, 1.5 / 4.5 | 54.40, 1.1 / 3.4 |
| sequence_4_11 | 14.89, 9.9 / 18.9 | **3.51, 41.7 / 98.6** | 3.79, 37.9 / 99.1 | 3.48, 40.5 / 92.0 | 3.63, 34.3 / 78.0 | 3.40, 35.9 / 89.4 (1 restart) |

The curve is flat between 2 and 5 px on the walks (2_11 22.3 to 23.9 m, 3_18 53 to 55 m, 4_11 3.4 to 3.8 m); the indoor cost grows with tightness (R_08 1.04 at 4 px, 1.07 at 3 and 5, 1.28 at 2) and R_12 degrades towards 5 px. The minimum-observation rule changes nothing. The control-point score on 2_11 swings between 19 and 33 for runs whose ATE differs by a metre, so on that walk the score is not a reliable discriminator between close settings (noted for the metric). **Decision**: 3 px stays the setting of record pending F08; 4 px is the fallback if the indoor tax matters more than the walks.

**Applicability**: as F01 (general reprojection outlier rejection); the threshold scales with resolution and the image noise level; the 2 px setting is already into the honest noise of these 640x480 fisheye images on the indoor sequences.

## F07: outlier filter 3 px on the full sets (2026-10-03, pc)

**Hypothesis**: the F01 gain holds across all 13 controlled sequences at two offsets and the 10 additional sequences, so the filter can join the reference config.

**Change**: `BASALT_OUTLIER_PX=3`, `basalt_ref1` otherwise, robust driver; offsets 0 and 100 on the controlled set, offset 0 on the additional set.

**Command**: `results/v3-F07-filt3-full/batch.sh` (systemd unit `lamaria-f07`).

**Result so far**, controlled set (ATE sim3 m, offsets 0 / 100; restarts of the robust driver in brackets where they differ from the reference; reference basalt_ref1 from v2 B07):

| Seq | filter 3 px | reference |
|---|---|---|
| R_01 | **0.119 / 0.124** | 0.151 / 0.156 |
| R_02 | 0.190 / 0.233 (0 restarts) | **0.173 / 0.215** (3 restarts at offset 100) |
| R_03 | **0.247 / 0.207** | 0.434 / 0.415 |
| R_04 | 1.220 / 2.952 (2 / 3 restarts, all within the first 240 frames of a segment) | **0.781 / 0.935** (0 / 1) |
| R_05 | 1.291 / 1.328 | **1.139 / 1.153** |
| R_06 | 1.245 / 0.935 | **1.124 / 0.764** |
| R_07 | 1.356 / 1.362 | **1.236 / 1.220** |
| R_08 | 1.067 / **0.947** | **1.006** / 1.368 |
| R_09 | **1.957 / 1.640** (1 restart) | 2.762 / 2.414 |
| R_10 | **3.098 / 3.128** | 4.412 / 3.877 |
| R_11 | **2.053 / 1.638 (score 78.6 / 81.3)** | 2.605 / 2.078 (73.3 / 77.0) |
| R_12 | 13.96 / 15.66 (10.3 / 7.7) | **12.86 / 12.94 (12.0 / 14.0)** |
| R_13 | 3.584 / 3.449 (39.1 / 40.3) | **3.349 / 3.544 (45.2 / 44.3)** |
| **two-offset mean** | 2.50 | **2.43** |

Additional set (score 2D, reference B08 in brackets; restarts where they differ): 1_19 **74.1** (64.1), 1_20 **44.3** (39.6), 2_11 **21.0** (20.7), 2_12 **8.2** (5.3), 3_17 **5.7** (4.3), 3_18 2.0 (2.4), 4_10 **12.1** (8.4; 0 restarts against 2), 4_11 **34.2** / recall 97.9 % (9.9 / 18.9 %; 0 restarts against 1), 5_11 5.7 (6.9), 5_12 4.5 (7.6): mean score **21.2** (reference 16.9, Huber 0.5 19.7, 1.5 m near cap 21.6, OpenVINS 22.0). Eight of ten up, the two moving-platform sequences down by a fifth to a third: inside a vehicle the near structure gives large honest residuals that the filter removes.

Reading: the filter wins the easy and hard sequences, R_11 and the additional set, and loses every medium sequence by 10 to 15 % and the two long control-point walks (R_12 by 1 to 3 m and 2 to 6 score points, R_13 by 5 points), the same two that punished Huber 0.5 in v2. R_04 is the clearest signal of a mechanism: the three restarts at offset 100 all happen within the first 240 frames of a segment, i.e. right after an initialisation, where the solve has not converged yet and a 3 px filter removes good observations and starves the problem. That suggests a warm-up (no filtering for the first seconds after any initialisation) as the next iteration (F08), not a different threshold.

**Decision**: the filter is the best single Basalt setting on the additional set (21.2, the first Basalt setting to match OpenVINS there without a scene-specific trick) and a wash on the controlled set (2.50 against 2.43, lost on the medium set and the long control-point walks). Not yet the reference as a flat 3 px: F08 tests the warm-up on the losers, and the moving-platform loss is noted as its known failure case.

**Applicability**: as F01; the warm-up finding is general (any post-solve rejection must wait for the solve to be trustworthy).

## F08: outlier filter with a warm-up after initialisation (2026-10-03, pc)

**Hypothesis** (F07): the filter's extra restarts on R_04 (and the medium-set loss) come from filtering before the solve has converged; skipping the filter for the first frames after initialisation keeps the gain without the restarts.

**Change**: `BASALT_OUTLIER_WARMUP` (frames after initialisation during which `filterOutliers` is not called; one initialisation per process, the robust driver restarts the process). 100 and 300 frames (5 and 15 s) with 3 px, `basalt_ref1` otherwise.

**Command**: `results/v3-F08-filter-warmup/batch.sh` (R_04 at both offsets, R_12 at both, R_13, R_09, R_08, 4_11 at offset 0; queued behind the X05 re-runs).

**Result**: pending.

**Applicability**: general (any post-solve rejection needs a trustworthy solve first); the warm-up length is a time, so it depends on how fast the estimator converges (IMU noise, motion), not on the scene.

## F09: outlier filter plus epipolar gate (2026-10-03, pc)

**Hypothesis**: F03's gate removes liars before they become landmarks, F01's filter removes those that slipped through after the solve; the two should add up on the walks with people.

**Change**: `BASALT_OUTLIER_PX=3` with `BASALT_EPI_GATE=0.005`, `basalt_ref1` otherwise, robust driver, offset 0.

**Command**: `results/v3-F09-filter-epi/batch.sh` (six event sequences; queued behind F08).

**Result**: pending.

## F10: learned keypoints seeding the tracker (2026-10-03, pc)

**Hypothesis** (X02): in the dark and low-texture stretches FAST, with its threshold falling to 5, picks noise corners; a learned detector (XFeat) finds repeatable points there. Seeding Basalt's KLT with those points, one per empty grid cell, keeps the precision of patch tracking and borrows the detector's robustness.

**Change**: `scripts/make_learned_keypoints.py` (XFeat on CPU, top 500 per cam0 frame, about 20 frames/s with six workers, stored as float32 x / y / score per frame under `data/training/<seq>/kp_xfeat/cam0/`). Basalt `frame_to_frame_optical_flow.h`: `BASALT_KP_DIR` loads the frame's points, the best one per empty 50 px cell (score at least `BASALT_KP_MIN_SCORE`) becomes a new track; `BASALT_KP_MODE=union` (FAST fills the cells still empty) or `replace` (external points only). With the outlier filter 3 px, `basalt_ref1` otherwise.

**Command**: `results/v3-F10-learned-seed/keypoints.sh` then `batch.sh` (union and replace at min score 0.1), `batch_fill.sh` (fill mode: FAST first, XFeat only in the cells FAST leaves empty), `batch_fill20.sh` (F10c: FAST stops at threshold 20 instead of 5, alone and with XFeat filling the cells it leaves).

**Result** (first runs, ATE m; score / recall; filter 3 px alone from F01/F07 in brackets):

| Seq | union 0.1 (XFeat first, FAST fills) | replace (XFeat only) | fill (FAST first, XFeat fills) |
|---|---|---|---|
| sequence_4_11 | 14.46, 2.2 / 99.1, scale **0.82**, 1 restart (3.79, 37.9 / 99.1) | running | running |
| R_08 | (stopped) | 6.58, scale 0.95 (1.072) | 1.0725 (1.072): XFeat adds 2 % of the points, FAST fills every cell |

First lesson: XFeat points as the *main* seeds are bad for KLT (R_08 with XFeat points only: 6.6 m against 1.07, no restart, just a steadily worse estimate). With XFeat first, the dark walk goes from 3.8 m back to 14.5 m with a scale of 0.82 (reference scales are 0.97 to 0.99): the points a learned detector likes (blobs, edges, texture) are not the points a patch tracker can follow and stereo-match, so the stereo depths and the scale go wrong. FAST corners are chosen for exactly that. Second lesson: in fill mode the learned points almost never get a chance, because Basalt's adaptive FAST (threshold down to 5) always finds *something* in a cell, noise corners included. F10c makes FAST stop at 20 so the weak cells stay empty, as an ablation on its own (fewer noise corners may help or hurt) and with XFeat filling them.

**Applicability**: general in principle (any detector that beats FAST in the dark); costs a network pass per frame (XFeat is small: about 50 ms per frame on one CPU core here, far less on a GPU); fails where the detector itself finds nothing (X02's worst window) and adds nothing where FAST already finds good points.

## F11: descriptor-matching front end through the external-tracks interface (2026-10-03, pc)

**Hypothesis** (owner, thoughts.md): descriptor matching is more robust than patch tracking across appearance change and large motion; a matching front end feeding the same back end tells how much of the remaining error is the tracker. It also opens the back end to any learned tracker.

**Change**: Basalt `frame_to_frame_optical_flow.h`: `BASALT_TRACKS_DIR/<t_ns>.bin` (records of track id, cam, x, y) replaces the KLT output for the frame (`BASALT_TRACKS_MODE=replace`) or is added next to it with offset ids (`augment`). `scripts/make_xfeat_tracks.py`: XFeat keypoints (top 1000) per frame, mutual-nearest-neighbour descriptor matches to the previous frame chained into track ids (flow at most 80 px), stereo matches cam0 to cam1 per frame, written as those records. Smoke test on 30 frames of 4_11: 570 to 720 of 1000 points chained frame to frame, about 100 stereo matches, 0.5 s per frame on two cores.

**Command**: `results/v3-F11-xfeat-tracks/tracks.sh` (4_11 and R_08, about 3 h each, sequential by nature), then `batch.sh` (replace and augment, with the filter 3 px).

**Result**: pending.

**Applicability**: the interface is general (any front end, offline here, online later); the XFeat matcher as used is a baseline, not a tuned tracker: no sub-pixel refinement, no temporal window beyond one frame, so its precision is bounded by the detector's localisation; the stereo match count is low (the undistorted Aria pair has a wide baseline and viewpoint change) and may need a looser threshold.
