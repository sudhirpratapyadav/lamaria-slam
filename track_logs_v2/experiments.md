# Experiments (v2: exploration of estimator classes)

One section per experiment, newest first, same fields as v1 (hypothesis, change, command, per-sequence result, cost, decision). Scoreboard at the top. The v1 reference (`configs/ov_ref005`, OpenVINS) is the baseline every candidate is compared against: controlled set two-offset mean ATE 2.83 m; additional set scores in v1 experiments 030 / 037.

## Scoreboard

| Candidate | Stage | Controlled set, 2-offset mean ATE (13 seq) | Additional set score 2D / recall @ 5 m (seq_1_19, 1_20, 2_11, 2_12) | Notes |
|---|---|---|---|---|
| v1 OpenVINS ov_ref005 | tuned (v1) | 2.83 m | see v1 037 | causal, ~1.4x realtime on one core |
| A OKVIS2 | A01 defaults, R_01 only | R_01: 0.237 live / **0.043 final BA** | | non-causal final BA; slow under load |
| B Basalt | B02 noise x10, 4 seqs | R_01 0.34, R_04 1.55, R_08 3.84, R_11 1.61 | R_11 score 52 | ~2x realtime on <2 cores |
| C ORB-SLAM3 | - | | | |
| D OpenVINS + BA smoother | - | | | |

## A01: OKVIS2 out of the box (2026-10-03, pc, okvis2 a2ea006, USE_NN=OFF)

**Setup**: `scripts/run_okvis2.sh` with `configs/okvis2_default` (OKVIS2 defaults: loop closures on, final bundle adjustment on, realtime limit off, CNN off), calibration from the LaMAria pinhole JSON (radialtangential with zero coefficients), IMU noise as in the JSON (x1), pinhole ASL input. Two outputs: the live estimate (causal) and the trajectory after the final full BA (non-causal).

**Result**, R_01_easy: live ATE sim3 0.237 m (scale 0.958); final-BA ATE 0.043 m (scale 0.976); poses for all 2898 images. Paper: OKVIS2 0.02 m, OpenVINS 0.66 m; our OpenVINS ov_ref005 0.19 / 0.29 m. Cost: 1466 s wall (10x slower than realtime) at 0.83 cores average under a heavily loaded machine (15 other estimators running), 564 MB RSS. A clean timing is owed.

**Decision**: continue with high priority. The final-BA trajectory is the non-causal, benchmark-eligible path; the live one is the causal (robot) path, already as good as tuned OpenVINS. Next: R_04, R_08, R_11 with defaults, then noise scaling (OKVIS2 has its own IMU priors), keyframing, and the fisheye input (OKVIS2 has a native equidistant model).

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
