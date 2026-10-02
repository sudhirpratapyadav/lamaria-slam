# Experiments

Timestamped but editable. This is the single record of what was tried: a scoreboard at the top, then one section per experiment with hypothesis, change, exact command, per-sequence numbers, cost, decision, and insights. Raw outputs live in `results/<exp>/` (git-ignored); each run folder has `run_info.txt` with the commit, host and command, plus the exact yaml used.

## Scoreboard

ATE = RMSE in metres after sim3 Umeyama against the controlled-set pseudo-GT (official `evaluate_wrt_mps`). "Start-offset spread" = min to max over 6 start frames (0, 20, 50, 100, 200, 400). Published stereo+IMU numbers for the same metric are in `docs/benchmark_notes.md` (paper Table 2): OpenVINS+Maplab 0.65 / 1.05 / 3.97, OKVIS2 0.02 / 1.36 / 6.81 on R_01 / R_04 / R_08.

| # | Date | Host | Config | R_01_easy | R_04_medium | R_08_hard | Notes |
|---|---|---|---|---|---|---|---|
| 001 | 2026-10-02 | pc | `ov_ref001`: OpenVINS stereo+IMU, pinhole ASL, dynamic init, time offset fixed, IMU noise densities x10 | 0.301 | 0.739 | 4.49 | reference; datasheet-noise first attempt: 0.169 / diverged / 10.59 |
| 002 | 2026-10-02 | pc | same, 6 start offsets each | 0.17 to 0.34 (mean 0.25) | 0.74 to 1.08 (mean 0.90) | 3.3 to 7.4 (mean 4.85) | no divergence in 18 runs; this spread is the noise floor |

Leaderboard-metric sequences (the main-set metrics, computed locally with the official evaluators):

| # | Config | Sequence | score 2D | CP recall @ 1 m | pose recall @ 5 m | pose recall @ 1 m | ATE sim3 (paper: OpenVINS / OV+Maplab / OKVIS2) |
|---|---|---|---|---|---|---|---|
| 003 | `ov_ref001` | R_11_5cp (477 s, 5 CPs, 1627 pGT keyframes) | 58.9 | 40.0 | 100.0 | 35.8 | 1.36 (1.04 / 1.62 / 1.85) |

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
