# Experiments (v3: front end)

One section per experiment, newest first, same fields as before (hypothesis, change, exact command, per-sequence result, cost, decision) plus an **applicability** line for every kept change: where it applies (indoor, outdoor, tunnel, platform, this sensor, this benchmark), how general it is, where it can fail. Scoreboard at the top. Reference: Basalt `basalt_ref1` with the robust driver (v2 B07/B08): controlled two-offset mean 2.43 m, additional-set mean score 16.9; Huber 0.5 and the 1.5 m near cap as per-sequence options (19.7 / 21.6).

## Scoreboard

| Candidate | Stage | Event sequences (2_11, 3_18, 4_11, R_12, R_08, R_11) | Controlled 2-offset | Additional mean score | Applicability | Notes |
|---|---|---|---|---|---|---|
| Basalt ref1 (v2) | reference | 30.9 / 81.0 / 14.9 / 12.9 / 1.01 / 2.61 m | 2.43 | 16.9 | general | |

## F01: IMU-consistency gate and the dormant outlier filter in Basalt (2026-10-03, pc)

**Finding first**: Basalt's VIO never calls its own `filterOutliers` (a `TODO` in `sqrt_keypoint_vio.cpp`), so in all v2 runs no observation was ever rejected after the solve; only the Huber loss damped them. That is why the Huber threshold was the one knob that moved things in v2.

**Hypothesis**: features on moving objects (people, the wearer's arm and shoe, reflections) disagree with the IMU-predicted ego-motion. Checking each observation of an existing landmark against its reprojection from the IMU-predicted pose, before the solve, removes them where they appear; the post-solve reprojection filter removes what slips through.

**Change** (`sqrt_keypoint_vio.cpp`, env-gated, in `docs/patches/basalt-0f3b2b5.patch`): `BASALT_IMU_GATE_PX` drops an observation whose reprojection residual from the IMU-predicted state exceeds the threshold (announced once, counts every 500 frames); `BASALT_OUTLIER_PX` calls `filterOutliers` after each optimisation with that reprojection threshold (`BASALT_OUTLIER_MIN_OBS`, default 2). `basalt_ref1` otherwise, robust driver, offset 0.

**Command**: `results/v3-F01-imu-gate/batch.sh`: gate 5 px, gate 10 px, filter 3 px, gate 5 + filter 3, each on R_08, R_11, R_12, sequence_2_11, 3_18, 4_11. First log line on R_08 with gate 5: 128 of 24656 observations dropped in the first 500 frames (0.5 %).

**Result**: pending.

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

**Result**: pending.

**Applicability**: general wherever people or the robot's own body enter the view (homes, streets); costs a segmentation per frame (about 25 ms on an Orin for the detection-only model, more for masks); fails on reflections and on body parts the detector does not recognise; no help in dark or low-texture stretches.
