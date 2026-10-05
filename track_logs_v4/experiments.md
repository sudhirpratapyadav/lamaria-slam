# v4 experiments: stereo quality gate and the non-causal backend (opened 2026-10-05)

Reference entering v4: `configs/basalt_v3_ref` on the repeatable build (v3 F21): controlled two-offset mean 2.38 m, additional-set mean score 23.7; long walks 3_17 / 3_18 ATE 47 / 56 m, scores 6.0 / 1.7. Owner's v4 goal (2026-10-05): "start v4, stereo quality gate as well as non causal backend, let's see how far we can go."

Method rules (from v3): one frozen binary per experiment (`scripts/snapshot_basalt.sh`), deterministic reductions on; compare only on the same binary; several sequences and both offsets before any decision; every kept change gets an applicability line (indoor / outdoor / tunnel / platform / this sensor / this benchmark).

## Scoreboard (ATE m on the controlled set, score on the additional set)

| Setting | Controlled two-offset mean | Additional mean score | Notes |
|---|---|---|---|
| v3 reference (F21) | 2.379 | 23.7 | entering v4 |
| F01: gyro noise x2 | running | running | 2_11 alone: 21.5 to 2.9 m, score 21 to 47 (X02) |

## X01: what the long walks actually lose (2026-10-05, pc, analysis)

**Question**: what error is left on the long walks after v3, and can a non-causal stage remove it? Loop closure needs revisits; smoothing needs the IMU to know better than the estimate.

**Method**: (1) revisit statistics from the pGT (a pose counts as a revisit when a pose more than 60 s away lies within 5 m); (2) `scripts/drift_analysis.py` (60 s sim3 windows: scale, heading, local residual) on the v3 reference; (3) new `scripts/gyro_yaw_check.py`: integrates the gyro with a constant bias fitted against the pGT, and reports the heading error about gravity of the gyro alone and of the estimate over the sequence. The pGT body frame is detected from the angular rates (Wahba): the controlled set's pGT is in the IMU frame, the additional set's is in the **left camera frame** (105.5 degrees from the IMU); the first pass of this analysis, which assumed the IMU frame, was wrong and is discarded. Outputs: `results/v4-X01-gyro-yaw/`.

**Result 1, revisits**: none on the long walks. 3_17, 3_18, 4_10, 4_11, 1_19: 0.0 % of poses revisit a place; 2_11 8.7 %, 2_12 1.3 %, 1_20 6.7 %, R_13 8.0 %, R_10 12.9 %; only R_01 / R_03 / R_05 (71 / 88 / 59 %) are loop-rich. Start-to-end distance on the long walks: 300 to 760 m. **Loop closure cannot help the long walks**; a place-recognition backend has nothing to recognise there.

**Result 2, what drifts**: local scale is fine (60 s window scales 0.91 to 1.03 on 3_17 / 3_18, median 0.985), local consistency is fine (window RMSE 0.17 to 0.19 m); the error is heading: 73 / 94 degrees of accumulated yaw over 3_17 / 3_18. A heading error growing linearly to 90 degrees over a 2 km walk is an arc of radius about 1.5 km; the sim3 fit absorbs part of it (fitted scales 0.92 / 1.07), leaving the 47 / 56 m ATE.

**Result 3, heading, estimate against gyro alone** (yaw error about gravity at the end of the sequence, degrees; drift rate in degrees per minute; the gyro alone with one constant bias fitted against the pGT):

| Seq | duration | estimate end / rate | gyro alone end / rate | pGT body frame |
|---|---|---|---|---|
| sequence_3_17 | 30 min | **-78.5 / -2.5** | -20.2 / -0.7 | cam0 |
| sequence_3_18 | 28 min | **-95.2 / -3.4** | -31.0 / -1.1 | cam0 |
| sequence_2_11 | 20 min | **-57.4 / -2.8** | -27.8 / -1.5 | cam0 |
| sequence_2_12 | 28 min | **-49.5 / -1.7** | -17.2 / -0.7 | cam0 |
| R_12_10cp | 17 min | **-28.7 / -1.7** | -22.0 / -1.3 | IMU |
| sequence_4_11 (dark) | 19 min | +1.3 / 0 | +21.4 | cam0 |
| sequence_4_10 (dark) | 24 min | -0.9 / 0 | -22.3 | cam0 |
| sequence_1_19 | 15 min | +5.1 / +0.3 | +15.5 | cam0 |
| sequence_1_20 | 17 min | +5.2 / +0.3 | +12.2 | cam0 |
| R_08_hard | 10 min | +2.0 / +0.2 | -15.6 | IMU |

The per-minute heading drift of the estimate on the daytime walks is **steady** (3_17: mean -2.54, std 1.22 degrees per minute over 29 minutes; 3_18: -3.36 +/- 1.43; 2_11: -2.79 +/- 2.34), uncorrelated with distance walked (r = 0.06 / -0.06 / -0.45) or turning (r = -0.21 / -0.11 / 0.07), and always of the same sign. It is 2 to 4 times the gyro's own residual drift. On the dark walks and on 1_19 / 1_20 the estimate holds heading to within 5 degrees while the gyro alone would lose 12 to 22, so there vision corrects the gyro as it should. Rotation scale (estimate's rotation per pGT rotation, all axes, intervals above 3 degrees) is 1.0030 on the daytime walks against 1.0006 to 1.0012 for the gyro, but also 1.0023 on 4_11 which does not drift, so a rotation-scale error is not the mechanism. The gyro's per-axis scale against the pGT repeats across the additional-set device (x +0.12 to +0.21 %, y -0.16 to -0.24 %), i.e. the factory gyro rectification that the ASL export omits (v1 031 found the same magnitudes in the .vrs) is visible here; its effect on heading is second order.

**Reading**: after v3 the long walks lose to one thing: a slow, steady, same-signed heading drift of 2 to 3.5 degrees per minute that appears only on daytime outdoor walks, where vision is rich, and not in the dark or indoors, so it is a visual bias and not a weakness of the IMU. Removing it would take 3_17 / 3_18 from 47 / 56 m to the few-metre range; no other single item in the project is worth as much. **X02** looks for the mechanism with three runs on 2_11 (gyro trusted more, gyro bias walk tightened, time-reversed input); the backend design waits for that answer, since a global bundle adjustment that includes the same visual bias would reproduce it.

**Applicability**: diagnostic. The body-frame detection in `gyro_yaw_check.py` is general (any pGT given in some fixed body frame); the no-revisit finding is about these sequences, but the method (check for revisits before building a loop-closure stage) is general.

## X02: what drives the heading drift (2026-10-05, pc)

**Change**: three arms on sequence_2_11 (the shortest daytime walk), F21 snapshot binary, v3 reference settings; reference = F21's own 2_11 run (ATE 21.1 m, heading -57 degrees). (a) `configs/v4_gyro_n2`: gyro noise x2 instead of x20 (accelerometer stays x20; new `GYRO_NOISE_SCALE` option in `make_basalt_calib.py` / `run_basalt_robust.sh`); (b) `configs/v4_gyro_w01`: gyro bias random walk x0.1 (`GYRO_WALK_SCALE`); (c) the v3 reference on a time-reversed 2_11 (`scripts/make_reversed_input.py` over the whole sequence, `data/derived/sequence_2_11_rev`): if the drift keeps its sign in the camera frame the bias is image-fixed (tracker, calibration); if it flips it is motion-dependent.

**Command**: `results/v4-X02-heading-cause/batch.sh` (systemd unit `lamaria-v4-x02`).

**Result** (sequence_2_11, ATE m; score; recall @ 5 m; heading error at the end against the pGT; one segment, no restarts in every arm):

| Arm | ATE | score | recall 5 m | heading end | heading drift per minute |
|---|---|---|---|---|---|
| reference (F21, gyro x20) | 21.51 | 21.1 | 48.5 % | -57.4 deg | -2.8 |
| (a) gyro noise x2 | **2.92** | **46.7** | **90.2 %** | **-6.6 deg** | 60 s windows: median 0.6, max 2.8, total 1.0 deg |
| (b) gyro bias walk x0.1 | 21.59 | 20.0 | 44.7 % | -57.0 deg | -2.8 |
| (c) time-reversed input | void: `make_reversed_input.py` keeps the original image timestamps, so the submission step matched no pose; not repeated, the question is answered by (a) | | | | |
| (d) cameras swapped (cam1 primary, gyro x20) | 8.22 | 19.2 | 43.2 % | +0.2 deg (max 11, rms 5.5) | no steady drift (worst minutes +5.0 / -4.7) |

**Reading**: the heading drift was the estimator's weighting, not the data or the tracker. Since v1 the IMU noise densities are inflated x20 (needed for the accelerometer: OpenVINS, OKVIS2 and Basalt all failed on the hard sequences at the datasheet values), and the same factor was applied to the gyro. At x20 the gyro's rotation constraint is weak enough that a slow visual yaw bias (whatever its source: far landmarks initialised too far, moving objects, the sideways-looking monocular geometry) wins, and the gyro bias state absorbs the difference. At x2 the gyro holds the heading: 2_11 goes from 21.5 to 2.9 m, the heading error from 57 to 7 degrees, the control-point score from 21 to 47. The bias random walk (b) is irrelevant: the drift is not a bias-tracking problem. The visual bias is still there (the x2 run's remaining 7 degrees, and the fitted scale 0.95) and is the next thing to look at once the gyro weight is settled. **Arm (d)** answers where it comes from: with cam1 as the primary (and effectively only) camera, same binary and same x20 gyro, the steady drift is gone (heading error wanders within +/-11 degrees and ends at 0.2; ATE 8.2 m against 21.5), so the -2.8 degrees per minute is tied to running monocular on cam0, the camera that looks left of the walking direction (far landmarks initialised from forward motion, whose translational flow in a sideways-looking camera is one-signed). That also says what the front-end fix is, independent of the gyro weight: landmarks detected and tracked in **both** cameras (Basalt creates landmarks for cam0 tracks only; cam1 enters only as a stereo partner, and on this pair it never matched), which symmetrises the geometry and adds observations where cam0 has none. Candidate F02. (The swapped run's control-point score is lower than its ATE suggests, 19 against 21; the score depends on which control points the primary camera sees, so arms (a) and (d) are not comparable on score.)

**Decision**: `GYRO_NOISE_SCALE=2` becomes the v4 candidate; **F01** runs it on the full sets (F21 binary), **F01b** sweeps x1 and x5 on the event sequences. Indoors the inflation might have been protecting something (v1 005 / 008 were about both sensors at once), so the full controlled set decides, not 2_11.

**Applicability**: general and sensor-specific at once: the right gyro weight is a property of the IMU (the Aria gyro is quiet enough to be trusted near its datasheet), and on the robot's ICM-42688-P the factor must be re-derived the same way (heading of the estimate against a reference, or against the gyro alone). The lesson is general: never scale gyro and accelerometer noise together; the gyro is the heading sensor, and inflating it hands the heading to vision, which drifts.

## F01: gyro noise x2 on the full sets; F01b: gyro factor sweep (2026-10-05, pc)

**Hypothesis** (X02): the gyro trusted near its datasheet noise removes the heading drift on every daytime walk and costs nothing elsewhere.

**Change**: `configs/v4_gyro_n2` (= `basalt_v3_ref` + `GYRO_NOISE_SCALE=2`; accelerometer x20, walks x1); F01b: `configs/v4_gyro_n1`, `configs/v4_gyro_n5`. F21 snapshot binary (md5 4542b534a81f), v3 reference settings otherwise.

**Command**: `results/v4-F01-gyro-n2-full/batch.sh` (13 x 2 offsets + 10 additional; unit `lamaria-v4-f01`), `results/v4-F01b-gyro-sweep/batch.sh` (x1 and x5 on 2_11, 4_11, 3_18, R_04, R_08, R_12, R_11; unit `lamaria-v4-f01b`).

**Result so far** (ATE m; score; recall @ 5 m; F21 reference in brackets):

| Seq | gyro x1 | gyro x2 | gyro x5 | heading with x2 |
|---|---|---|---|---|
| sequence_2_11 | 5.25, 25.4, 61 % | **2.92, 46.7, 90 %** (21.5, 21.1, 49 %) | 12.09, 7.1, 11 % | ends at -7 deg, no steady drift |
| sequence_3_17 | | **9.01, 21.8, 42 %** (46.9, 6.0, 6 %) | | wanders within +/-14 deg (minutes 4 to 10: -3 to -4.5; minutes 20 to 29: +6 to +13) |
| sequence_3_18 | | **22.42, 10.2, 12 %** (56.1, 1.7, 5 %) | | **still a steady drift**: -1.5 deg per minute, -43 deg at the end (was -3.4 per minute, -95) |

| sequence_2_12 | | **6.21, 22.7, 62 %** (27.3 in v2; F21: 2_12 score 3.7) | | scale 0.925 |
| sequence_4_11 (dark) | 8.19, 27.1, 70 % (1 restart) | F01 pending | 6.27, 32.1, 73 % (1 restart) | F21: **1.77, 56.9**, 3 restarts |

**The dark walk goes the other way**: 4_11 is best with the loose gyro (x20: 1.8 m; x5: 6.3; x1: 8.2). In the dark the few landmarks cannot correct a gyro that is trusted too much against its own bias drift (the gyro alone loses 21 degrees on 4_11), while on the daytime walks the same trust is what stops the visual bias. The two cases pull the IMU weighting in opposite directions, which is the usual sign that the fixed noise factor is the wrong knob: the gyro bias walk (how fast vision may re-estimate the bias) is the parameter that separates them, so **F01c** runs gyro x2 with a 5x bias walk, and, since the fitted scales got worse with the gyro trusted (2_11 0.95, 2_12 0.925, 4_11 0.93; the accelerometer still sits at x20), the accelerometer at x5 and x10 with the gyro at x2 (`configs/v4_g2_a5`, `v4_g2_a10`, `v4_g2_w5`; `results/v4-F01c-imu-weights/`, unit `lamaria-v4-f01c`).

| sequence_1_19 | | **13.98, 3.5, 5.5 %** (F21: 0.65, 74.8) | | **a new steady drift of +3 deg per minute** (F21: within 5 deg); scale 0.914 |
| sequence_4_11 (dark) | 8.19, 27.1, 70 % | 7.21, 26.9, 71 % (1 restart) | 6.27, 32.1, 73 % | F21: 1.77, 56.9 |
| sequence_3_18 | 15.75, 13.9, 20 % | 22.42, 10.2, 12 % | 41.03, 3.2, 8 % | F21: 56.1, 1.7 |

**1_19 explains the trade**: with the gyro trusted, 1_19 acquires a steady +3 degrees per minute heading drift that it did not have (0 to 50 degrees over 15 minutes, monotonic), the sign of its gyro's own drift (gyro alone: +15 degrees with a constant bias), and larger than that: the gyro bias is *time-varying* (warm-up), and with the gyro noise at x2 and the bias random walk at its datasheet value vision is no longer allowed to re-estimate the bias fast enough, so the estimate follows the gyro's bias drift instead of vision's. At x20 the opposite happens: vision's own yaw bias wins on the daytime walks. So neither fixed factor is right; what the daytime walks need is the gyro's *short-term* precision (noise), what 1_19 and the dark walk need is freedom for the bias (walk). **F01c** (walk x5 with gyro x2) and **F01d** (walk x20, x100 on 1_19, 4_11, 3_18; `results/v4-F01d-gyro-walk/`) test exactly that split. In parallel, **F04** tests the visual side of the bias with the gyro at x20: a landmark is created only after 0.2 / 0.5 m of baseline instead of 0.05 (`vio_min_triangulation_dist`; far landmarks initialised from forward motion in a sideways-looking camera are the suspected source), 2_11, `results/v4-F04-min-triang/`.

**F01 further** (gyro x2, walk x1): sequence_1_20 **37.5 m** (F21 score 41), sequence_4_10 11.2 m, score 4.9 (F21 20.6), sequence_5_11 score 13.8 (F21 8.2). **F01b indoor** (ATE m; F21 in brackets): R_04 x1 2.74 / x5 4.37 (0.70); R_08 5.05 / 2.54 (1.03); R_11 2.99, score 38 / 1.42, 65 (2.17, 76.5); R_12 5.21, 22 / 9.87, 12 (13.9, 9.6). **F01d** (gyro x2, bias walk faster): 1_19 walk x5 10.65 / x20 2.40, score 42 / **x100 1.08, score 67.8** (F21 0.65, 74.8), so a fast bias walk gives 1_19 back; but 3_18 with walk x20 is **53.1 m**, the whole daytime gain gone, and 4_11 walk x20 6.06, score 40.7. **F04** (gyro x20, more baseline before a landmark): 2_11 at 0.2 m 20.3, score 26.4; at 0.5 m 21.9, 22.2 (21.5, 21.1): no effect on the drift, so far-landmark triangulation is not the source.

**F01 controlled set (gyro x2, both offsets, F21 in brackets)**: R_01 0.198 / 0.201 (0.132 / 0.137), R_02 0.534 / 0.435 (0.210 / 0.262), R_03 0.385 / 0.390 (0.345 / 0.298), R_04 5.58 with 2 restarts (0.697): worse on every controlled sequence. F01c: 4_11 with accelerometer x10 and gyro x2: 32.9 m, 11 restarts; 4_11 with gyro x2 and walk x5: 8.81, score 27. F01d on 3_18: walk x5 46.0, x20 53.1, x100 59.7 (reference 56.1): every faster walk gives the drift back. The F01 / F01c / F01d batches were stopped at this point (02:50), their remaining runs cancelled; the verdict did not need them.

**Decision on the IMU weights**: a fixed gyro factor is not a setting we can keep. The daytime walks want the gyro's short-term precision against a visual yaw bias; 1_19, 1_20, the dark walks and every indoor sequence want vision free to re-estimate a bias that moves (and the x20 noise evidently also covers model errors the estimator does not have: time offset, extrinsics, gyro scale), and any bias walk fast enough for them hands the heading back to vision on 3_18. **Not kept**; `GYRO_NOISE_SCALE` / `GYRO_WALK_SCALE` stay as options. The gain on the daytime walks (2_11 2.9 m, 3_17 9 m, 2_12 6 m) stands as the measure of what removing the visual yaw bias is worth; the bias itself has to be fixed on the visual side.

The gyro at x2 removes most of the drift but not all of it on 3_18: the visual yaw bias is reduced by the stronger gyro, not gone, which is what X02 (d) predicts (the bias is in the cam0-monocular geometry). Scale after the fix: 0.99 on both long walks (was 0.92 / 1.07), but the 60 s window scales still span 0.89 to 1.05, and on 2_11 the fitted scale is 0.95: with the heading fixed, scale is the next visible error, which is the stereo thread's job.

## F02: landmarks in both cameras (2026-10-05, pc)

**Hypothesis** (X02 d): the residual heading bias comes from running monocular on the left-looking cam0; detecting and tracking points in cam1 as well, with landmarks hosted in either camera, symmetrises the geometry and adds observations where cam0 has none.

**Change**: `BASALT_MONO_CAMS=1`: `frame_to_frame_optical_flow.h` `addPoints()` detects new points in every camera with the grid occupancy rule (fresh ids, tracked frame to frame in their own camera); `sqrt_keypoint_vio.cpp` creates landmarks from unconnected tracks of every camera, hosted in that camera (upstream: cam0 only). Stereo matching unchanged. v3 reference settings (gyro x20, to isolate the camera effect), own snapshot (build 17, md5 in `results/v4-F02-mono-cams/bin`); controls with the option off on 2_11 and 4_11.

**Command**: `results/v4-F02-mono-cams/batch.sh` (unit `lamaria-v4-f02`).

**X03 check (150 s single-process runs on 2_11, residual dump)**: with the option, cam1 holds 300 to 670 observations per frame against 400 to 1200 in total (control: 150 to 625, all cam0), landmarks 128 to 230 against 50 to 112; residual medians unchanged (0.15 to 0.25 px). Speed halves (3100 against 6200 frames in 150 s at 3 threads): twice the landmarks, twice the cost. Mechanically it does what it should.

**Result so far** (ATE m; score; recall @ 5 m; heading at the end):

| Seq | control (same snapshot) | both cameras |
|---|---|---|
| sequence_2_11 | 21.51, 21.1, 48.5 % (bit-identical to F21), heading -57 deg, 523 s | **12.54**, 5.8, 11.1 %, heading **-25 deg**, 917 s |

| sequence_4_11 (dark) | 1.77, 56.9, 99.6 % (3 restarts; F21's number) | 5.27, 35.2, 96.4 %, **no restart** |
| R_04_medium | 0.697 (F21) | **0.550** |
| R_08_hard | 1.031 (F21) | **0.748** |
| R_11_5cp | 2.174, 76.7 (F21) | 2.594, 76.3 |
| R_12_10cp | 13.88, 9.6 (F21) | **11.04, 9.7** |
| sequence_3_18 | 56.12, 1.7 (F21) | **34.39, 6.1** |

Indoors the second camera's landmarks pay off clearly (R_04 -21 %, R_08 -27 %, the best R_08 of any setting); on the dark walk the run is cleaner (no restart, recall 96 %) but the ATE is worse (5.3 against 1.8; the F21 figure sits in the 1.6 to 4.5 range of that walk's restart chaos, so the gap is smaller than it looks and needs the second offset). Cost 2x.

First reading of 2_11: the heading bias halves (-57 to -25 degrees) and the ATE with it, so the geometric explanation holds; but the control-point score and the 5 m recall fall (21 to 6, 49 to 11 %). The two metrics disagree because they align differently: the ATE is a sim3 fit over the whole trajectory, the score and recall are judged after the control-point alignment, and a trajectory with a smaller but differently shaped error can lose there. Not a candidate on its own; the question is what it does on top of the gyro at x2 (F03), where the heading is already mostly held and the extra observations should count for robustness and scale rather than heading.

## X04: camera-IMU consistency from the images (2026-10-05, pc, analysis)

**Method**: new `scripts/cam_imu_check.py` (OpenCV, system Python): frame-to-frame rotation of one camera from KLT tracks with a rotation-only RANSAC fit on bearings (consecutive frames have a few cm of baseline, so the essential matrix is degenerate), compared with the gyro integrated over the same interval and rotated into the camera frame with the calibration. Outputs: the time offset that minimises the median rotation residual (1 ms grid), the extrinsic rotation implied by the data against the calibration (Wahba), per-axis rotation scale. The mean rotation-rate difference it also prints is contaminated by translation parallax of near features (one-signed while walking) and is not usable as a measure of the estimator's visual bias.

**Result** (3000 frames each, `results/v4-X04-cam-imu-check/`):

| Sequence, camera | time offset (images later than stamped) | extrinsic rotation, data vs calibration | inliers per pair |
|---|---|---|---|
| 2_11 cam0 | **5 ms** | 4.2 deg over 3000 frames (0.3 deg over 400: the long-stretch figure drifts with the uncorrected gyro bias; the short one is the trustworthy number) | 155 |
| 2_11 cam1 | **5 ms** | 1.1 deg over 400 frames | 154 |
| 1_19 cam0 | **4 ms** | | 240 |
| R_08 cam0 | **4 ms** | | 285 |

Refined with a 0.5 ms residual curve and a parabola through its minimum (`*_fine.json`): 2_11 cam0 **5.1 ms**, 2_11 cam1 **4.9 ms**, 3_18 cam0 **4.75 ms**; the minimum is sharp (median residual 0.215 deg per frame at 5 ms against 0.245 at 0 and 0.250 at 10 ms). Both devices and both cameras agree on a camera-IMU time offset of 4 to 5 ms (v1 010 had found 4.3 ms for OpenVINS and discarded it as a setting; nobody checked its effect on heading). Basalt's VIO ignores `cam_time_offset_ns` (the line is commented out upstream), so the offset is applied to the input instead (`scripts/make_timeshift_input.py`: IMU stamps shifted).

**Applicability**: general, and the kind of check to run first on any new sensor (lesson 6 of AGENTS.md); the robot's camera-IMU offset must be measured the same way.

## F05: camera-IMU time offset (2026-10-05, pc)

**Hypothesis** (X04): the 4 to 5 ms offset, unmodelled, is part of the daytime heading drift (the IMU rotation between two frames is matched against image content from 5 ms later; with head motion coupled to the stride this does not average out).

**Change**: IMU timestamps shifted so that the images count as 4.5 ms later (`dtp45`) or earlier (`dtm45`) relative to the IMU, `data/derived/sequence_2_11_dt*`; v3 reference settings (gyro x20), F21 binary. F05b sweeps +7, +10, +15 ms on 2_11 and applies +4.5 ms to 1_19 and 4_11 (no drift there: a correct offset must not hurt them). `results/v4-F05-time-offset/`, `results/v4-F05b-time-offset-sweep/`.

**Result** (sequence_2_11; ATE m; score; recall @ 5 m; heading error at the end):

| Offset | ATE | score | recall 5 m | heading end |
|---|---|---|---|---|
| -4.5 ms | 29.70 | 25.9 | 51 % | -78.9 deg |
| 0 (reference) | 21.51 | 21.1 | 49 % | -57.4 deg |
| **+4.5 ms** | **14.32** | 5.7 | 11 % | **-34.9 deg** |
| **+10 ms** | **6.81** | 19.8 | 47 % | **-4.7 deg** (max 12, rms 4) |
| +7 ms | 10.53 | 11.0 | 15 % | **-19.9 deg (max 20, rms 8.4)** (the first +7 arm had been built with a 70 ms shift by mistake: 91 m, 12 restarts, void; this is the rerun) |
| +15 ms | 4.15 | 28.4 | 81 % | **+19.0 deg** (rms 8.5): overshoot, the drift changes sign |

Sequences without the drift at +4.5 ms (must not be hurt; F21 reference in brackets):

| Sequence | ATE | score | recall 5 m | heading |
|---|---|---|---|---|
| sequence_1_19 | 1.26 (0.65) | 64.4 (74.8; the reference's other start offset gives 64.1) | 100 % | rms 1.1, end -0.2 deg (F21: rms 2.9, end +5.1) |
| sequence_4_11 (dark) | 4.38, 2 restarts (1.77, 3 restarts) | 33.2 (56.9; other offsets 41 / 10) | 74 % | rms 7.6, max 23 (F21: rms 2.2) |


The drift responds to the offset in the predicted direction and almost linearly (-79, -57, -35 degrees for -4.5, 0, +4.5 ms), so the time offset is a real part of the mechanism; +4.5 ms removes about 40 % of it. The control-point score falls again while the ATE improves (same pattern as F02: the score is judged after the control-point alignment and does not reward a smaller but reshaped error the same way). F05b tells whether a larger offset removes the rest or whether the remainder is the cam0 geometry (X02 d).

**F05b reading**: on 2_11 with cam0-only landmarks the end heading is linear in the offset over the whole range, about **5 degrees per millisecond** (-79, -57, -35, -20, -5, +19 for -4.5, 0, +4.5, +7, +10, +15 ms), with the zero crossing near +11 ms, i.e. twice the offset measured from the images (X04, 5 ms, sharp minimum on both devices). The IMU shift therefore does more than correct the timing: on this one-sided geometry a timing error and a heading bias are nearly interchangeable, so the "best" offset on 2_11 absorbs whatever else biases the heading. Only the measured 5 ms is a sensor constant we may keep; +10 ms would be a 2_11 fit. On 1_19 the heading is as good or better than the reference (rms 2.9 to 1.1 degrees) but the ATE doubles (0.65 to 1.26) and the score drops within its usual spread (64 to 75 across offsets); the dark walk 4_11 is worse (4.4 vs 1.8) but its runs are chaotic (restarts in 3 of 4 arms; F07 shows why). Verdict on the offset waits for F06 (both cameras) and F07 (restarts).

**Applicability**: a sensor property (Aria image stamps against the IMU clock), not a benchmark fit; the robot's offset is to be measured, not copied.

## F06: both visual fixes together, offset + landmarks in both cameras (2026-10-05, pc)

**Hypothesis**: the time offset (F05) and the cam0-only geometry (F02) are two independent parts of the daytime heading bias; together they should remove most of it without touching the IMU weights, and F02's indoor gains should carry.

**Change**: `BASALT_MONO_CAMS=1` on the F02 snapshot (build 17) with the IMU shifted by +5 ms (the measured offset) or +10 ms (2_11's optimum in F05b), v3 reference settings; 2_11, 3_18, 4_11, R_08, R_04. The +5 ms arm is the general one (a measured sensor constant); +10 ms is kept only to see whether the second 5 ms still buys anything once the geometry is symmetrised.

**Command**: `results/v4-F06-offset-monocams/batch.sh` (unit `lamaria-v4-f06`).

**Result so far** (ATE m; score; recall; restarts; F02 alone and F05 alone in brackets):

| Sequence | both cams, +5 ms | both cams, +10 ms | both cams only (F02) | cam0 only, +10 ms (F05) |
|---|---|---|---|---|
| sequence_2_11 | 27.5, 18.0, 46 %, **5 restarts** (39 numerical failures) | 11.8, 8.8, 11 %, heading **-19.5 deg** (rms 9.3) | 12.5, 5.8, 11 %, heading -25 | 6.8, 19.8, 47 %, heading -4.7 |
| sequence_4_11 (dark) | 130.6, 0, 0 %, 4 restarts (106 failures) | 24.7, 9.5, 22 %, 0 restarts | 5.27, 35.2 | (F21: 1.77, 56.9) |
| R_08_hard | 138 m, **12 restarts in the first 43 s** | **0.340** (F21 1.03, F02 0.75) | 0.75 | |
| R_04_medium | 0.775, 1 restart (scale 0.938) | **0.523**, 1 restart (F21 0.70, F02 0.55) | 0.55 | |
| sequence_3_18 | **19.9**, 3.5, 4 %, no restart, heading **+33.5** (rms 13.7) | 31.9, 7.1, 16 %, heading -54.6 | 34, heading about -60 | (F21: 56.1, 1.7, heading -95) |

**Complete reading**: the combination is strong where it holds (3_18 56 to 20 m with the measured 5 ms, the heading's sign flips; R_08 1.03 to 0.34 and R_04 0.70 to 0.52 with 10 ms) and unstable elsewhere: the same 5 ms arm that wins 3_18 loses 2_11 to five mid-sequence restarts and R_08 / 4_11 to initialisation blow-ups, and 3_18 at 10 ms is worse than at 5 ms while 2_11 is the opposite. Two conclusions: (1) with both cameras the offset no longer acts as a heading knob, so there is no reason to go beyond the measured 5 ms; (2) nothing here can be judged before the initialisation is robust (F11), after which F12 (both cameras, no shift, full sets) and a +5 ms arm on the walks decide the v4 causal reference.

**First reading**: the two fixes are **not independent**. With landmarks in both cameras the heading's sensitivity to the offset falls from 5 to about 0.5 degrees per millisecond (-25 at 0 ms, -19.5 at +10 ms), so most of what the IMU shift removed on cam0-only geometry was the one-sided geometry itself, and the residual -20 to -25 degrees on 2_11 is a third thing, not timing. The +5 ms arms are wrecked by restarts that come from a solver numerical failure (NaN landmark increments applied to the state, see F07), which also hit the F02 and reference runs at random: F06 has to be read again on the F07 binary.

## F07: non-finite landmark increments are no longer applied (2026-10-05, pc)

**Observation**: every chaotic restart cluster examined (4_11 reference: 31 "Numerical failure in backsubstitution" lines and 3 restarts; F06 2_11 +5 ms: 39 and 5; 4_11 +5 ms: 106 and 4; R_08 +5 ms: 650; also R_03, R_07, R_10 skip 0 and R_04 skip 100 in the reference set, 6 of the 13 reference runs that restart) logs the sqrt solver's backsubstitution warning first. In `landmark_block_abs_dynamic.hpp` `backSubstitute()` Basalt computes the landmark increment from the landmark's 3x3 R block; when that block is singular (degenerate landmark: no baseline, direction at the parametrisation's pole) the increment is non-finite, upstream only prints the warning and **adds it anyway**, so the landmark's direction becomes NaN, its residuals poison every later linearisation of the window and the estimate diverges a few frames later.

**Change**: a non-finite increment is skipped (the landmark stays where it was; the outlier filter / marginalisation remove it later), counted and logged ("Non-finite landmark increment skipped"). Nothing else touched; snapshot `results/v4-F07-nan-landmark/bin` (libbasalt md5 4e16d4a73f24; `snapshot_basalt.sh` now hashes libbasalt.so too, the executable alone does not change with estimator code).

**Command**: `results/v4-F07-nan-landmark/batch.sh` (unit `lamaria-v4-f07`): v3 reference settings on the reference runs that logged the failure (4_11, R_03, R_10, R_07 at skip 0; R_04 at skip 100; 1_20 at skip 0, which logged 6 failures without a restart) plus R_01 skip 0 and R_04 skip 0 as no-failure controls (must be bit-identical to F21).

**Result** (ATE m; reference in brackets): R_01 0.132 (0.132), R_03 0.345 (0.345, restart at 1.6 s in both), R_04 0.697 / 0.665 (0.697 / 0.665), R_07 1.201 (1.201), R_10 4.371 (4.371), 1_20 2.77, score 41.1 (41.0), 4_11 1.770, 3 restarts at 3 / 5 / 7 s (identical): **bit-identical to the reference on every run**, although 10 to 30 non-finite increments were skipped in each. Basalt's `use_valid_projections_only` already drops the observations of a NaN landmark at the next linearisation, so the applied NaN was in effect a removal; the guard only makes that explicit. F07b (the F06 +5 ms arms, both-camera landmarks): 2_11 **14.7 m**, 3 restarts at 87 / 1094 / 1106 s (F06: 27.5, 5 restarts at 87 / 527 / 528 / 552 / 801), i.e. a different branch of the same chaos, not a cure; 4_11 +5 ms: 153 m, 4 restarts at 5 / 17 / 22 / 27 s (F06: 131 m, the same four restart times), the initialisation blow-up again.

**Decision**: kept as a harmless guard (no run changes unless a NaN would have been applied), **not** a fix for the restarts. The restarts of the reference set are initialisation blow-ups: in 4_11 and R_03 the speed ramps from 0 to 6 to 8 m/s within the first 3 s of a segment (monocular front end without scale, velocity started at zero while the wearer is already walking); the driver's restart absorbs them at the cost of a few poses and of the chaotic branch. A proper visual-inertial initialisation (velocity and gravity from the first second, or stereo depth at start) is the general fix; listed as a v4 item.

**X07, self-occlusion checked and dropped** (`scripts/occluder_check.py`, `results/v4-X07-occluder/`): one 2_11 frame showed the wearer's hair over most of cam0, so an attached textured occluder (device A's wearer, cam0 side, invisible in the dark) was a candidate for the drift. Measured over the sequences (fraction of pixels with almost no temporal change while the image moves), cam0 of device A carries 3 to 9 % of such pixels against 1 % on device B, but the per-minute drift does not follow it: 2_11 drifts -3.1 deg/min in minutes with under 2 % occluder and -1.5 with over 5 %; 2_12 and R_12 likewise. Not the mechanism.

**Applicability**: general (any sequence, platform or sensor: a solver robustness fix, nothing benchmark-specific). It only acts where a degenerate landmark would have been applied; runs without the warning are unchanged.

## X05: does the heading drift follow the device or the light? (2026-10-05, pc)

**Observation**: the training set comes from two devices (md5 of `aria_calibrations/*.json`): device A (`cc5c2f57`): 2_11, 2_12, 3_17, 3_18, 4_10, 4_11, 5_11, 5_12 and all controlled sequences except R_08; device B (`5f4f20ee`): 1_19, 1_20, R_08. Every walk with the steady heading drift is device A; both device-B walks (1_19, 1_20; daytime, 15 to 17 minutes) and R_08 are clean; the two device-A walks without drift (4_10, 4_11) are the dark ones. Heading error of the reference runs on the whole controlled set (`gyro_yaw_check.py`, pGT frame detected per sequence: R_01 to R_10 are given in the IMU frame, R_11 to R_13 in the cam0 frame like the additional set):

| Sequence | duration | heading end | rms | worst minutes (deg/min) |
|---|---|---|---|---|
| R_01 / R_02 / R_03 | 2.5 min | -1.2 / -3.6 / +1.9 | 0.9 / 2.8 / 1.3 | |
| R_04 / R_05 / R_06 / R_07 | 4 to 7 min | +6.0 / -9.2 / -1.3 / -0.4 | 3.9 / 7.0 / 2.5 / 1.0 | R_05: -3.1 in the first minute |
| R_08 (device B) | 10 min | +2.0 | 4.4 | |
| R_09 / R_10 | 13 / 16 min | +15.7 (max 41) / +9.5 | 17.3 / 5.1 | R_09 excursion, not steady |
| R_11 / R_13 | 8 / 23 min | -7.7 / -6.3 | 4.8 / 2.9 | |
| **R_12** | 17 min | **-28.7** | 18.3 | **-4.5, -3.8, -2.7**: the walks' steady drift, same sign |

So the drift is not an outdoor-only effect: R_12 (device A, controlled set) drifts exactly like 2_11, and R_12 is the controlled set's largest error (13.9 m of the 2.38 m mean). What distinguishes the devices: intrinsics and extrinsics (different factory values), and the factory IMU terms the ASL export omits: gyro misalignment 0.26 deg (A) vs 0.22 deg (B), similar; accelerometer bias 0.25 / 0.21 / 0.39 m/s^2 (A) against about 0 (B), very different (v1 031 had found this in the .vrs). The light explanation (fast daytime walks) and the device explanation are confounded on this data except through R_12 and the dark walks; a device-B dark walk or a device-A short indoor walk with drift would separate them, and the training set has neither.

**Applicability**: diagnosis only. If the device is the cause, the fix is calibration (self-calibration in the backend, or the full factory IMU model), which carries to any sensor; if it is the light, it is the front end.

## F08: factory IMU rectification applied to the raw IMU (2026-10-05, pc)

**Hypothesis** (X05): the ASL export's IMU is raw; the omitted factory model (per-axis scale, 0.26 deg of gyro misalignment, 0.25 to 0.39 m/s^2 of accelerometer bias on device A) is part of what the estimator absorbs as heading drift on device A.

**Change**: the factory model `raw = M @ rectified + bias` for both devices, recovered exactly (residual 5e-9) from v1's rectified IMU files (`data/training_rect`, built from the .vrs that was deleted afterwards), stored in `configs/aria_factory_imu/<device>.json`; `scripts/make_rectified_input.py` builds `data/derived/<seq>_rect` (rectified gyro and accelerometer, bias removed; everything else linked). v3 reference settings, F21 binary, on 2_11, 3_18, R_12 (device A, drifting), 4_11 (device A, dark) and 1_19 (device B, control). `results/v4-F08-imu-rectified/`, unit `lamaria-v4-f08`.

**Result** (ATE m; score; recall 5 m; heading at the end; F21 reference in brackets):

| Sequence | rectified IMU | reference |
|---|---|---|
| sequence_2_11 | 21.98, 30.8, 53.6 %, heading **-55.7** | 21.51, 21.1, 48.5 %, -57.4 |
| sequence_3_18 | 58.1, 1.3, 4.4 %, heading -98.2 | 56.1, 1.7, heading -95.2 |
| R_12_10cp | 12.03, 10.4, 18.7 %, heading -24.6 | 13.9 / 13.95, 9.6, heading -28.7 |
| sequence_4_11 (dark) | 7.53, 17.4, 20.5 %, no restart, heading -14.8 | 1.77, 56.9 (3 restarts), heading +1.3 |
| sequence_1_19 (device B) | 0.707, 72.6, 100 %, heading +5.4 | 0.65, 74.8, +5.1 |

**Decision**: not kept. The factory IMU model changes the drift by a few degrees at most on 2_11 and 3_18 (within the per-run spread), helps R_12 a little, and the dark walk ends on another branch of its restart chaos (worse here). The gyro's omitted misalignment (0.26 deg) and scale, and device A's accelerometer bias, are not the heading mechanism; the estimator absorbs them in its bias states as designed. `make_rectified_input.py` and the recovered factory models stay available (they are the right input for any estimator that cannot estimate the bias quickly, e.g. at initialisation).

**Applicability**: general in principle (use the sensor's full factory model), specific to Aria in the numbers; on the robot the IMU intrinsics come from its own calibration.

## X06: the time-reversed run, mapped back to forward time (2026-10-05, pc)

**Question**: is the heading drift anti-symmetric under time reversal (then a forward/backward fusion cancels it) or not? X02's reversed arm had run to completion (23748 poses, no restart, F21 binary, v3 reference settings) but its submission file was empty because the trajectory was in reversed time; here it is mapped back (`t = pivot - t'`), converted and scored. `results/v4-X06-reverse-fusion/sequence_2_11_rev2fwd/`.

**Result** (sequence_2_11; forward reference in brackets): ATE **9.73 m** (21.51), score 17.6 (21.1), recall 5 m 44.9 % (48.5), scale 0.986, heading error at the forward end **-28.7 deg** (-57.4), rms 10.9 (22.8). In its own running time the backward estimator drifts at about +1.4 deg/min, i.e. the opposite sign and half the rate of the forward run's -2.9 deg/min.

**Reading**: not anti-symmetric and not symmetric: the drift has a part that flips with the direction of travel and a part that does not (a 5 ms time offset flips sign under reversal; one-sided camera geometry relative to the direction of walking flips too; whatever does not flip is neither). A plain fusion of the two passes would end around -40 deg on 2_11, so it cannot be the whole answer, but the backward pass alone is 2x better and a time-weighted fusion also removes initialisation transients at both ends: worth having as the first (cheap, general) non-causal tool, `scripts/fuse_bidirectional.py`.

**Fusion tried** (`scripts/fuse_bidirectional.py`: backward pass aligned to the forward one over the first 60 s by yaw and translation, then per-pose blend with a weight running linearly from forward at the start to backward at the end, slerp for the orientation): 2_11 ATE **10.06 m**, score 15.5, recall 25.9 %, heading end -28.4 (rms 12.7). Not better than the backward pass alone (9.73): the two passes disagree by 85 m at the end after the start alignment, and the blend simply follows the better pass. Parked; the two-pass idea only pays once the drift itself is anti-symmetric or small.

**Applicability**: any offline/non-causal use (the benchmark, map building on the robot); not for live navigation.

## F09: cam0 extrinsic-rotation probe (2026-10-05, pc)

**Hypothesis** (X02 d, X05): landmarks hosted in cam0 drift on device A while cam1-hosted ones do not (X02 swap) and device B's cam0 does not either, so device A's cam0 calibration (extrinsic rotation first) is suspect. A time offset and a heading bias were interchangeable at 5 deg/ms (F05b), so a small extrinsic rotation may be too.

**Change**: `make_basalt_calib.py --cam0-rot-deg RX RY RZ` (camera frame rotated about its own axes, `T_i_c0 * Exp(r)`), driver env `CAM0_ROT_DEG` / `CAM1_ROT_DEG`; +-0.3 deg about each cam0 axis on 2_11, v3 reference settings, F21 binary. `results/v4-F09-cam0-extrinsic-probe/`, unit `lamaria-v4-f09`. If one axis moves the heading linearly, the zero crossing is a candidate correction to be validated on the other device-A sequences (3_18, R_12, 2_12, 3_17; 4_11 and device B must not move).

**Result** (sequence_2_11; ATE m; score; heading at the end; reference 21.51, 21.1, -57.4):

| cam0 rotation | ATE | score | heading |
|---|---|---|---|
| +0.3 deg x | 24.5 | 17.7 | -63.1 |
| +0.3 deg y | 22.7 | 21.2 | -58.8 |
| -0.3 deg y | 20.4 | 20.6 | -55.4 |
| +0.3 deg z | 20.5 | 20.4 | -53.9 |
| -0.3 deg z | 22.4 | 23.1 | -59.2 |
| -0.3 deg x | (run void: input race with another batch; not needed) | | |

**Decision**: closed. The heading moves 10 to 20 degrees per degree of cam0 rotation, so a calibration error of 3 to 5 degrees would be needed to explain the drift; factory extrinsics are not off by that much, and the probes at 0.3 deg stay within the per-run spread in ATE. The cam0 extrinsic rotation is not the mechanism.

**Applicability**: a device calibration refinement (sensor-specific numbers, general procedure); the robot gets its own calibration, so what carries is the method (and, later, its automation in the backend).

## F11: initialisation window, gravity from the mean accelerometer (2026-10-05, pc)

**Hypothesis** (F07 reading): the reference restarts are initialisation blow-ups. Upstream Basalt creates the first state from a single accelerometer sample at the first frame (attitude from that one sample, velocity zero). On a wearer who is already walking the sample carries up to 3 m/s^2 of stride acceleration, i.e. an attitude error of up to 17 degrees, and the first seconds run away (4_11: 0 to 6 m/s within 3.5 s, 8 m of travel; R_03: 8.5 m/s at 3 s). F06's R_08 +5 ms arm with both-camera landmarks restarted twelve times in its first 43 s for the same reason (138 m).

**Change**: `BASALT_INIT_WINDOW_S=w` (`sqrt_keypoint_vio.cpp`, first-state block): frames are consumed without a state for the first w seconds while the accelerometer is averaged; the first state is created at the first frame after the window with gravity from the mean. Off by default (w = 0 reproduces upstream bit for bit). w = 1 here. Velocity still starts at zero (it is unobservable from the IMU alone; the optimiser recovers it from the first landmarks). Snapshot `results/v4-F11-init-window/bin` (libbasalt 90095f3d98b0).

**Command**: `results/v4-F11-init-window/batch.sh` (unit `lamaria-v4-f11`): v3 reference settings on the reference runs that restart (4_11, R_03, R_04 at both offsets, R_07, R_10, R_08 skip 100, R_12 skip 100) plus R_01 skip 0 and R_02 skip 100 as controls.

**Result** (ATE m; restarts with their times in the segment; reference in brackets):

| Run | F11 (window 1 s) | reference |
|---|---|---|
| R_03 skip 0 | **0.343, 0 restarts** | 0.345, 1 (1.6 s) |
| R_07 skip 0 | **1.195, 0** | 1.201, 1 |
| R_10 skip 0 | **4.433, 0** | 4.469, 1 |
| R_08 skip 100 | 1.049, 0 | 0.806, 1 (0.1 s) |
| R_04 skip 0 / 100 | 0.748, 1 (17.5 s) / 0.732, 2 (2.0, 12.5 s) | 0.697, 1 (18.6 s) / 0.665, 3 (1.2, 3.1, 13.6 s) |
| R_12 skip 100 | 13.96, 1 (0.0 s) | 13.95, 1 |
| R_02 skip 100 | 0.231, **1 (0.0 s)** | 0.262, 0 |
| sequence_4_11 | 3.09, score 44.6, 2 (4.7, 8.6 s) | 1.77, 56.9, 3 (2.6, 4.7, 6.8 s) |
| R_01 skip 0 (control) | 0.136, 0 | 0.132, 0 |

**Reading**: three initialisation restarts gone (R_03, R_07, R_10), one new (R_02 skip 100), the rest moved; ATE neutral within the spread. The segments that still diverge show the same signature as before, the speed ramping to 6 to 27 m/s within 4 s of the first state, now with an attitude from the 1 s mean: so the attitude was only part of it. Two things remain wrong at the first state: the mean was taken in the body frame while the head turns during the window (fixed in **F11b**: samples rotated through the integrated gyro into the end-of-window frame), and the velocity still starts at zero while the wearer walks at about 1.4 m/s (a velocity estimate from the first visual tracks is the next step if F11b is not enough).

**F11b** (`results/v4-F11b-init-window-rot/`, libbasalt 3b65326f17a8, unit `lamaria-v4-f11b`): same runs, the window's accelerometer mean rotated through the integrated gyro into the end-of-window frame. Result (ATE; restarts): R_01 0.137 (0); R_02 skip 100 0.257 (1, at 0 s); R_03 0.343 (0); R_04 0 / 100: 3.28 (2: 17.5 s, 24.8 s) / 1.14 (2: 0.3 s, 12.6 s); R_07 1.187 (0); R_08 skip 100 1.032 (0); R_10 4.255 (0); R_12 skip 100 **13.95 (0)**; 4_11 3.11, score 37.4 (1, at 4.2 s). Six restarts over the ten runs against seven (F11) and ten (reference).

**F11c, weaker prior on the first pose** (`configs/v4_initpw1e4`, `v4_initpw1e2`: `vio_init_pose_weight` 1e4 / 1e2 instead of 1e8, with the F11b window; `results/v4-F11c-init-pose-weight/`, unit `lamaria-v4-f11c`). The first pose is otherwise locked, so a wrong initial attitude cannot be corrected by the optimiser and is pushed into velocity and bias instead. Result (ATE; restarts): weight 1e2: R_02 skip 100 **0.252, 0**; R_04 skip 100 **0.715, 0** (reference 0.665 with 3 restarts); R_12 skip 100 14.31, 0; 4_11 3.98, score 45.3, 1 restart (7.2 s). Weight 1e4: R_02 0.300, 1; R_04 skip 100 2.12, 1; R_12 14.21, 0; 4_11 7.00, 1. **One restart in four runs at 1e2** against seven in the reference: the weak prior is the most effective single change so far (the window gives a reasonable attitude, the free first pose lets vision and the IMU finish the job). It needs the no-restart controls before it is kept (a free first pose could cost accuracy where the start was fine); F15 combines it with F14.

**Attitude at the first state measured against the pGT gravity direction** (pGT frame handled per sequence): R_12 skip 100: 17.4 deg with the plain mean (F11, restart) against **2.6 deg** rotated (F11b, no restart); R_04 skip 0: 3.4 (reference) / 2.5 (F11b); R_02 skip 100: 9.5 (reference) / 10.1 (F11) and still a restart in F11b; 4_11 skip 0: 11 to 12 deg in every variant (sustained acceleration in the first second; the successful second segment starts at 0.9 deg). So the rotated mean is right where the head turns, and what remains are starts with a sustained acceleration, which no accelerometer average can separate from gravity: that needs the velocity (F14).

**Applicability**: general (any platform that may start while moving: a robot pushed, a handheld device, glasses); it costs w seconds of poses at the start of a run (the submission fills them from the first estimate); on a stationary start it is a no-op in effect.

## F10: cam0 intrinsics probe, focal length (2026-10-05, pc)

**Hypothesis** (X05): device A's cam0 undistorted-pinhole model is off; a focal error would bias bearings and could give both the heading drift and the 1 to 3 % scale deficit seen on every device-A sequence.

**Change**: `CAM0_FOCAL_SCALE` (env, `make_basalt_calib.py --cam0-focal-scale`): cam0 fx, fy scaled by 0.98 / 0.99 / 1.01 / 1.02 on 2_11, v3 reference settings, F21 binary. `results/v4-F10-cam0-focal-probe/`.

**Result** (sequence_2_11; reference 21.51, score 21.1, heading -57.4, scale 0.993):

| cam0 focal | ATE | score | recall 5 m | heading | sim3 scale |
|---|---|---|---|---|---|
| x0.98 | 23.5 | 6.0 | 13 % | -52.6 | 1.002 |
| x0.99 | 22.5 | 30.0 | 57 % | -54.7 | 0.997 |
| x1.01 | 20.4 | 30.3 | 57 % | -58.1 | 0.984 |
| x1.02 | 18.7 | 26.9 | 52 % | -58.5 | 0.979 |

**Decision**: closed. Two percent of focal length moves the heading by 3 degrees and the sim3 scale by 1 % (as expected: the focal sets the visual scale against the IMU's), so no plausible intrinsic error produces a 57-degree drift. The score's jump from 21 to 30 at +-1 % is the control-point alignment's usual sensitivity, not a signal. **The mechanism hunt stops here** (X01 to X07, F01, F04, F05, F08, F09, F10): the drift is specific to device A's cam0-hosted landmarks and is not explained by any calibration or timing term we can probe; what we keep is the general defence, landmarks in both cameras (F02), plus per-sequence self-calibration in the backend later.

## F13: the time-reversed pass on more sequences (2026-10-05, pc)

**Question** (X06): the backward pass of 2_11 scored 9.7 m against 21.5 forward. Is the backward pass generally better (a cheap non-causal gain, and a clue about the mechanism), or was that 2_11 alone?

**Change**: whole-sequence reversed inputs (`make_reversed_input.py --window 100000`: images in reverse order, gyro negated, accelerometer unchanged) for 3_18, 2_12, R_12 (device A, drifting), 1_19 (device B) and 4_11 (dark); v3 reference settings, F21 binary; scored in forward time by the new `scripts/eval_reversed_run.sh`. `results/v4-F13-reversed/`, unit `lamaria-v4-f13`.

**Result** (ATE m; score; recall 5 m; heading at the forward end; forward reference / backward pass / linear fusion of the two):

| Sequence | forward (F21) | backward pass | fused |
|---|---|---|---|
| sequence_2_11 (X06) | 21.5, 21.1, 49 %, -57 | **9.7**, 17.6, 45 %, -29 | 10.1, 15.5, 26 % |
| sequence_3_18 | 56.1, 1.7, 5 %, -95 | **39.5**, 3.4, 5 %, -71 | 35.5, 11.0, 18 % |
| sequence_2_12 | 31.7, 3.7, 8 %, -50 | **10.0**, 10.2, 9 %, -16 | 14.1, 9.7, 24 % |
| R_12_10cp | 14.0, 9.6, 18 %, -29 | **4.1**, 32.2, 85 %, -4 | 5.6, 18.9, 40 % |
| sequence_1_19 (device B) | **0.65**, 74.8, 100 %, +5 | 3.3, 38.0, 88 %, +10 | 3.4, 37.2, 88 % |
| sequence_4_11 (dark) | **1.77**, 56.9, 99.6 %, +1 | 7.4, 28.0, 46 %, +16 | 6.0, 37.1, 86 % |

**Reading**: the backward pass is **2 to 3.5x better on every drifting device-A sequence** (its heading drift is 2 to 7x smaller) and 2 to 5x worse on the clean ones (1_19, 4_11), where the reversal costs the usual initialisation and bias convergence at what is now the start. The linear fusion lands near the backward pass each time (it cannot do better than the two inputs' heading errors allow), so as a blind procedure neither the backward pass nor the fusion is a gain over the whole set. What it does establish: the drift depends on the direction of travel relative to the camera (forward -2.9, backward +1.4 deg/min in running time on 2_11), which is a strong constraint on the mechanism and the reason a one-sided camera geometry fix (both cameras, F02) halves it.

**Decision**: no blind use. Kept as an analysis tool and as the basis for a later non-causal estimator that models a direction-dependent heading-rate bias (the two passes then give two equations for one trajectory).

**Applicability**: offline use only (benchmark, map building); the robot's live estimate is causal.

## F14: linear visual-inertial initialisation (2026-10-05, pc)

**Hypothesis** (F11, F11b): the starts that still blow up have a sustained acceleration in the first second (R_02 skip 100 and 4_11 start 10 to 12 degrees off), so gravity and the initial velocity must be solved together from vision and IMU.

**Change**: `BASALT_INIT_VEL=1` (`sqrt_keypoint_vio.cpp`, `viInitLinear`): over the 1 s window the cam0 tracks are buffered as bearings, the gyro gives the rotation between frames, the accelerometer its single and double integrals in the first frame's body frame; the unknowns, velocity v0, gravity g (both in that frame) and one depth per feature seen in the first frame, enter linearly through f_ij x q_ij = 0 for every later observation (q_ij the feature in camera j), and are solved by least squares (features with at least 5 later observations). Accepted when |g| is 8 to 11.5 m/s^2, |v0| < 6 m/s and most depths are positive; otherwise the F11b fallback. The first state is then created at the end of the window with the gyro-propagated attitude, the propagated velocity and position. Snapshot `results/v4-F14-vi-init/bin` (libbasalt 2256ce3c85b2).

**Command**: `results/v4-F14-vi-init/batch.sh` (unit `lamaria-v4-f14`): the F11 runs.

**Result, F14 (joint solve, window 1 s, default prior)**: the solver accepts its solution (|g| 9.6 to 9.9, |v| 0.4 to 0.6 m/s, 24 to 32 features) but one second of walking does not separate gravity from velocity: on R_02 skip 100 its gravity direction is 19 deg off the pGT against 2 deg for the rotated accelerometer mean, and the run still restarts; R_03 0.408 (F11b 0.343), R_04 1.13 / 1.04 with 2 restarts each, 4_11 2.65, score 41.4, 2 restarts. Not kept as such.

**F14b, gravity fixed from the rotated mean, velocity and depths solved, with the weak gauge prior (1e2)** (`results/v4-F14b-vi-init-gfixed/`, libbasalt 69b47db6a12d): **no restart on 7 of 8 runs** (R_01, R_02 skip 100, R_03, R_04 skip 100, R_05, R_08, R_12 skip 100), 4_11 one at 7.2 s; velocities 0.06 (R_03, standing) to 1.42 m/s (R_02), plausible. ATE (reference in brackets): R_01 0.183 (0.132), R_02 0.260 (0.262), R_03 0.351 (0.345), R_04 skip 100 0.690 (0.665, 3 restarts), R_05 1.467 (1.361), R_08 1.118 (1.031), R_12 14.27 (13.95), 4_11 4.21 (1.77). Robustness won, accuracy slightly lost on the short sequences (R_01 +0.05 m, R_05 +0.1): the first second has no poses and the gauge prior at 1e2 lets the start settle differently. On the skip-0 runs the solver found **no features in the first frame** (recordings start over-exposed) and fell back to the window mean; F14c moves the reference frame to the first frame with features.

Note on the prior: Basalt's `vio_init_pose_weight` acts on position and yaw only (roll and pitch are free from the start), so the 1e2 setting loosens the gauge, not the attitude; why that removes restarts is not understood (a stiff gauge on a first pose that the first optimisations want to move?), and it is kept on evidence only.

**F14c** (`results/v4-F14c-vi-init-rebase/`, libbasalt cad41a67d91f, unit `lamaria-v4-f14c`): F14b with the reference frame moved past an over-exposed start; the skip-0 runs plus two repeats. Result (ATE; restarts): R_01 0.183 (0), R_02 skip 100 0.260 (0), **R_04 skip 0 0.762 (0; reference 0.697 with a restart at 18.6 s)**, R_05 1.467 (0), R_08 1.118 (0), 4_11 4.21 (1 at 7.2 s). The skip-0 runs still fell back to the mean (no features): the tracker re-seeds its keypoint ids twice in the first five frames of a recording (24, 87, 143 features with none shared), so frame 0's ids never reach five later observations. **F14d** (libbasalt 32abc56db776): the reference frame is the earliest with 15 tracks surviving five frames, and a stationary start (|v| < 0.2 m/s) is accepted without the depth-sign test; on R_01 the solve then succeeds (+0.2 s, 62 features, v 0.05 m/s). F14d is the initialiser used by the F15 full-set candidate.

**Decision (initialisation thread)**: kept for the candidate: `BASALT_INIT_WINDOW_S=1` + `BASALT_INIT_VEL=2` + `configs/v4_initpw1e2`. Over the F11 runs the restarts go from 10 (reference) to 1, at an ATE cost of 0 to 0.1 m on the short sequences (R_01 0.13 to 0.18) which the full-set comparison (F15 against F12 / reference) has to weigh.

**Applicability**: general (any platform that starts while moving); the classic closed-form VI initialisation, here with Basalt's own tracks; it needs a few hundred milliseconds of accelerometer excitation to separate scale from gravity, which walking provides.

## G01: non-causal backend, first build (2026-10-05, pc)

**Hypothesis**: a global visual-inertial bundle adjustment over the whole sequence, with the per-sequence calibration (camera time offset, camera-IMU rotation, intrinsics) free, can remove part of what the sliding-window filter leaves: the filter cannot estimate a time offset or a calibration bias, and the backward pass (F13) showed that the forward estimate is not the best the data supports. Basalt's own mapper is parked (v2 B12/B14: wrong loop matches; no gain from its BA alone).

**Change** (all new, no behaviour change for existing runs):
- Basalt: `BASALT_OBS_DUMP=<dir>` in `frame_to_frame_optical_flow.h` writes every frame's tracks (int32 id, int32 cam, float x, y per record, `<t_ns>.bin`, the external-track format of v3 F11) after the tracker's own filtering. The driver (`basalt_segments.py`) sets it per segment when `OBS_DUMP=1`. Snapshot `results/v4-G01-vi-ba/bin` (basalt_vio 196d977bf0fc, libbasalt 4c1a3b7f8590); R_01 with the dump on reproduces F15's R_01 exactly (0.166 m).
- `tools/vi_ba/` (C++17, Ceres 2.0, Sophus and basalt-headers from Basalt's vcpkg tree; `cmake -G Ninja` in `tools/vi_ba/build`): states per keyframe pose, velocity, gyro and accelerometer bias; landmarks as inverse depth along the bearing of their first observation (host keyframe and camera); one calibration block (T_i_c0, T_i_c1, intrinsics of both cameras, one common time offset) constant unless freed by the config. Residuals: pinhole reprojection (Huber 1 px), Basalt's preintegrated IMU between consecutive keyframes with first-order bias correction (re-preintegrated at the current biases every round), bias random walk, weak bias prior on the first keyframe; first keyframe pose fixed; sparse Schur. Rounds: initial gate at 20 px on the VIO state, solve, gate 5 px, solve, gate 3 px, solve. The time offset enters as the pixel-velocity correction `z(t) = z_obs - v_px * td` (velocity from the neighbouring frames of the track), so `td > 0` means the images are exposed later than their stamps relative to the IMU, the convention of `make_timeshift_input.py`. Cross-camera observations are counted and gated separately (the stereo gate of the v4 goal lives here).
- `scripts/vi_ba_prepare.py RUN_DIR SEQ_DIR CONFIG OUT` (keyframes every `kf_interval_s` = 0.5 s from the frames with a kept VIO pose, first and last of every segment; ids made unique per restart segment; pixel velocities; IMU to ns; cameras from the run's `calib.json`), `scripts/run_vi_ba.sh RUN_DIR SEQ_DIR OUT_DIR [CONFIG_DIR]` (prepare, solve, propagate the keyframe corrections to every frame with `basalt_propagate_keyframes.py`, score with `finish_basalt_run.sh`). Configs `configs/vi_ba_base` (calibration fixed), `vi_ba_td` (time offset free), `vi_ba_extr` (camera-IMU rotations free), `vi_ba_full` (rotations, intrinsics, time offset).

**Command**: `scripts/run_vi_ba.sh results/v4-G01-vi-ba/vio/R_01_easy_skip0 data/training/R_01_easy results/v4-G01-vi-ba/ba_<cfg>_R_01_easy_skip0 configs/vi_ba_<cfg>`; the VIO run is F15's setting with `OBS_DUMP=1` (`results/v4-G01-vi-ba/run_vio.sh`).

**Result, R_01_easy skip 0** (one run; VIO = F15 setting, 288 keyframes, 109 k observations on them, 16.3 k landmarks after the gates, 48 k reprojection residuals, 287 IMU factors; solve 19 to 39 s on 8 threads, 85 MB):

| Backend | ATE | sim3 scale | estimated calibration |
|---|---|---|---|
| none (VIO, F15) | 0.166 | 0.999 | |
| calibration fixed | 0.151 | 0.995 | |
| time offset free | **0.090** | 0.999 | td = **+3.36 ms** |
| rotations free | 0.106 | 0.996 | cam0 0.81 deg, cam1 0.73 deg |
| rotations, intrinsics, time offset free | 0.092 | 0.998 | td +3.20 ms, cam0 0.66 deg, cam1 0.63 deg, principal points -0.4 to -0.6 px |

Final reprojection residuals: median 0.46 px, rms 0.82 px in every arm. No cross-camera observations exist in this run: on Aria's pair (75 degrees apart) Basalt's cam0-to-cam1 stereo tracking of new points almost never succeeds with the pinhole input, and `BASALT_MONO_CAMS=1` adds cam1-born tracks with their own ids; the "stereo" of this benchmark is two monocular cameras sharing an IMU. A control run without `BASALT_MONO_CAMS` (`vio_stereo/`) is dumped to count the stereo matches that do exist.

**Time offset sign check**: with the problem's IMU stamps moved +4.5 ms (the images then count as 4.5 ms earlier) the estimated td moves from +3.36 to +0.54 ms: the right direction, and the direction of X04's image-based 5 ms and of F05's winning `dtp45` arm (images later), but 2.8 ms of response to a 4.5 ms shift, so the first-order pixel-velocity model under-reacts by about 40 % here; the absolute value is a lower bound until that is understood (candidate: the IMU-side shift also moves the preintegration windows, which the pixel model does not see).

**Reading so far**: the backend reproduces the VIO when the calibration is fixed (0.151 vs 0.166) and nearly halves the error of this easy sequence when the time offset is free. Whether it touches the heading drift of device A is the real question: R_12 and 2_11 are being dumped (`lamaria-v4-g01-r12`, `lamaria-v4-g01-211`).

**Applicability**: general: any VIO run with per-frame tracks and raw IMU; nothing in it is Aria- or benchmark-specific (pinhole model only, for now; the kb4 fisheye model is a small addition). The self-calibration is the part that transfers most directly to the robot (the HJY1A camera and ICM-42688-P will have their own time offset). Where it can fail: sequences with restarts (the segments are linked by IMU only), long sequences (memory and time scale with observations; untested beyond 2.5 min so far), and an under-modelled time offset (above).

**G01b, time offset sweep on R_01** (backend with the offset fixed at each value, calibration otherwise fixed; ATE m, final Ceres cost):

| td fixed (ms) | 0 | 2 | 3.36 | 5 | 6.5 | 8 |
|---|---|---|---|---|---|---|
| ATE | 0.151 | 0.109 | 0.090 | **0.087** | 0.097 | 0.154 |
| cost | 15138 | 14671 | **14557** | 14698 | 15042 | 15630 |

The cost minimum (3.4 ms, what the free parameter finds) and the ATE minimum (about 5 ms, X04's image-based value) differ by 1.5 ms inside a flat valley (0.087 to 0.090); the fixed-td runs on the +4.5 ms-shifted problem put the cost minimum at +0.5 ms, so the under-response of G01's shift test is a property of the pixel-velocity model (cost), not of the solver. For the ATE the difference does not matter here; the free estimate is kept as the general option, the measured 5 ms as the sensor constant to compare against.

**Front-end stereo, measured from the dumps**: the cam0-only front end (the v3 reference setting) produces **no cam1 observation at all** on R_01 (0 of 55 k ids in a 1-in-10 frame sample): Basalt's cam0-to-cam1 patch tracking of new points fails on Aria's 75-degree pair with the pinhole input, so the "stereo" system of v1 to v3 was monocular-inertial on cam0, and `BASALT_MONO_CAMS=1` (F02) is what makes cam1 contribute at all (as a second monocular camera on the same IMU). Stereo matches exist only with `BASALT_STEREO_INIT=1` (v3 F19, cam1 search started at the rotated bearing); the stereo gate of the v4 goal therefore needs that option on, and its first measurement is the backend's cross-camera residual statistics (G01c, dumps with `BASALT_STEREO_INIT=1 BASALT_MONO_CAMS=1` on R_01 and the dark walk 4_11).
