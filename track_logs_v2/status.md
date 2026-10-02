# Current status (v2: exploration)

Last updated: 2026-10-03 02:14 IST. Edit in place.

## What v2 is

v1 took OpenVINS (filter-based VIO) as far as config tuning goes: two-offset mean ATE 2.83 m on the 13 controlled sequences, open-baseline level on the test-like additional set, far from the top two leaderboard entries (AnonSLAM 75 / 61 / 60, Aria's SLAM 91 / 79 / 71). v2 explores different estimator classes that could reach first place if optimised. Each candidate gets: build, harness adapter (same inputs, same scoring, same tracking), an out-of-the-box run on the standard set, then a few optimisation rounds (not just defaults), then the full controlled set at two offsets and the additional set. At the end v2 decides which approach, or combination, v3 takes up.

Rules carried over: owner decides on submissions (only when top 3 and confident), hosts (this PC first), downloads beyond the training set. Numbers are reported in the leaderboard's metrics per set. Logs stay in this folder; v1 is archived read-only in `track_logs_v1/` except for the two experiments that were still running at closure (034, 037), which append there.

## Candidates (proposed order)

| # | Approach | Why it could win | Risk | Status |
|---|---|---|---|---|
| A | OKVIS2 (keyframe stereo-inertial, BA + loop closure, BSD) | best published open numbers on several long controlled sequences (paper Table 2); native fisheye models; real-time capable | fails one sequence in the paper; heavy build (Ceres, DBoW) | A01 defaults: R_01 live 0.237 / final-BA **0.043 m**; R_04 1.56/1.44 (scale 0.89); R_08, R_11 diverge; 6 GB RSS, 1 h+ per long sequence under load. A02 noise x10 running |
| B | Basalt (VIO with marginalisation + mapping/BA stage, BSD) | very light on CPU (Nano-friendly), KB fisheye native, strong on EuRoC/TUM-VI | no published LaMAria numbers; mapping stage is offline | basalt_ref1 + robust driver (B06): beats OpenVINS on most cells when it holds, and every divergence is rescued by one restart (R_10 4.2 m vs OV 6.1). B07 = robust on 13 x 2 running |
| C | ORB-SLAM3 stereo-inertial (GPL) | highest accuracy where it works (0.03 m on R_01, 0.43 on R_02 in the paper), loop closing and multi-map | brittle (fails / jumps on hard sequences), heavy CPU | C01 fisheye: R_01 **0.031 m**, R_04 0.79 with 25 % of frames lost, R_11 1.00 (score 65.6), R_08 crashes 3/3. Brittle |
| D | OpenVINS (v1 reference) + further tracker work and a non-causal keyframe BA smoother | reuses everything from v1; v1 034 found a 21 px KLT window lifts the blurry test-like sequences (recall@5m 37 to 94 %) | smoother is engineering from scratch | D01 window 21: worse on sharp sequences (2.72 vs 1.99 over 11); D02 blur-adaptive window (wide only when Laplacian variance < 15) running |
| E | VINS-Fusion (stereo+IMU, optimisation-based, loop closure) | classic, robust, cheap | older code base; pinhole only | optional |

Learned/dense methods (DPVO, DPV-SLAM, MASt3R-style) scored badly in the paper on this data and need the GPU: deferred to the A100 stage, owner's call.

## Harness (unchanged from v1)

`scripts/run_sequence.sh` runs one sequence end to end for OpenVINS; v2 adds one adapter per candidate that produces the same `trajectory.tum` (IMU pose, image timestamps) so `tum_to_submission.py` and `evaluate.py` apply unchanged. Data: all 23 training sequences in ASL/pinhole form (`data/training/*/runner_input`), raw fisheye for R_01/R_04/R_08/R_11 (`data/training_fisheye/`), `.vrs` for those four. Disk: 26 GB free.

## Numbers to beat (v1 reference ov_ref005)

Controlled set, two-offset mean ATE: 2.83 m. Additional set (ov_ref004, offset 0): score 2D 41 / 14 / 15 / 21, recall @ 5 m 100 / 37 / 24 / 49 % on sequence_1_19 / 1_20 / 2_11 / 2_12; ov_ref005 on all ten pending (v1 experiment 037).

## Next

1. A: build OKVIS2 on this PC, write the adapter (ASL pinhole input and the raw fisheye input), out-of-the-box run on R_01 / R_04 / R_08 / R_11.
2. B: same for Basalt.
3. Then the optimisation rounds per candidate, then the full comparison.

## Blockers

None.
