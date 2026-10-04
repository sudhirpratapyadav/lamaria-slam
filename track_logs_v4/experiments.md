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

Indoors the second camera's landmarks pay off clearly (R_04 -21 %, R_08 -27 %, the best R_08 of any setting); on the dark walk the run is cleaner (no restart, recall 96 %) but the ATE is worse (5.3 against 1.8; the F21 figure sits in the 1.6 to 4.5 range of that walk's restart chaos, so the gap is smaller than it looks and needs the second offset). Cost 2x.

First reading of 2_11: the heading bias halves (-57 to -25 degrees) and the ATE with it, so the geometric explanation holds; but the control-point score and the 5 m recall fall (21 to 6, 49 to 11 %). The two metrics disagree because they align differently: the ATE is a sim3 fit over the whole trajectory, the score and recall are judged after the control-point alignment, and a trajectory with a smaller but differently shaped error can lose there. Not a candidate on its own; the question is what it does on top of the gyro at x2 (F03), where the heading is already mostly held and the extra observations should count for robustness and scale rather than heading.
