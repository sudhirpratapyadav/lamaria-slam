# Experiments (v2: exploration of estimator classes)

One section per experiment, newest first, same fields as v1 (hypothesis, change, command, per-sequence result, cost, decision). Scoreboard at the top. The v1 reference (`configs/ov_ref005`, OpenVINS) is the baseline every candidate is compared against: controlled set two-offset mean ATE 2.83 m; additional set scores in v1 experiments 030 / 037.

## Scoreboard

| Candidate | Stage | Controlled set, 2-offset mean ATE (13 seq) | Additional set score 2D / recall @ 5 m (seq_1_19, 1_20, 2_11, 2_12) | Notes |
|---|---|---|---|---|
| v1 OpenVINS ov_ref005 | tuned (v1) | 2.83 m | see v1 037 | causal, ~1.4x realtime on one core |
| A OKVIS2 | - | | | |
| B Basalt | - | | | |
| C ORB-SLAM3 | - | | | |
| D OpenVINS + BA smoother | - | | | |

## Plan per candidate

1. Build and adapter (same inputs, same `trajectory.tum` output, same scoring).
2. Out-of-the-box run on the standard four (R_01, R_04, R_08, R_11), two offsets.
3. Optimisation rounds: calibration/model choice (pinhole vs native fisheye), noise and tracking parameters, keyframing, loop closure on/off, non-causal refinement if available. Each round recorded here.
4. Full comparison: 13 controlled sequences at two offsets plus the ten additional-set sequences.
5. Decision for v3: approach or combination.
