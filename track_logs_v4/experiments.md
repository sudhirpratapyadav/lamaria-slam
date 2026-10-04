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

**Result**: running.
