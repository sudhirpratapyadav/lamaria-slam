# Current status (v2: exploration)

Last updated: 2026-10-03 06:16 IST. Edit in place.

## What v2 is

v1 took OpenVINS (filter-based VIO) as far as config tuning goes: two-offset mean ATE 2.83 m on the 13 controlled sequences, open-baseline level on the test-like additional set, far from the top two leaderboard entries (AnonSLAM 75 / 61 / 60, Aria's SLAM 91 / 79 / 71). v2 explores different estimator classes that could reach first place if optimised. Each candidate gets: build, harness adapter (same inputs, same scoring, same tracking), an out-of-the-box run on the standard set, then a few optimisation rounds (not just defaults), then the full controlled set at two offsets and the additional set. At the end v2 decides which approach, or combination, v3 takes up.

Rules carried over: owner decides on submissions (only when top 3 and confident), hosts (this PC first), downloads beyond the training set. Numbers are reported in the leaderboard's metrics per set. Logs stay in this folder; v1 is archived read-only in `track_logs_v1/` except for the two experiments that were still running at closure (034, 037), which append there.

## Candidates (proposed order)

| # | Approach | Why it could win | Risk | Status |
|---|---|---|---|---|
| A | OKVIS2 (keyframe stereo-inertial, BA + loop closure, BSD) | best published open numbers on several long controlled sequences (paper Table 2); native fisheye models; real-time capable | fails one sequence in the paper; heavy build (Ceres, DBoW) | A02 noise x10: R_01 final **0.033 m**, R_04 0.69, R_08 5.0, R_11 1.6 (score 67); slowest candidate. A03 (x20, no loop closure) diverged; A04 (10 keyframes) and A05 (fisheye) running |
| B | Basalt (VIO with marginalisation + mapping/BA stage, BSD) | very light on CPU (Nano-friendly), KB fisheye native, strong on EuRoC/TUM-VI | no published LaMAria numbers; mapping stage is offline | B07 robust Basalt **2.43 m** on the 13 controlled (OpenVINS 2.83); B08 additional set mean score 16.9 vs 22.0 (wins 1_19/2_11/4_10, loses the 2 km walks: structural drift, B09 knobs no help); B10/B11 native fisheye better on 3 of 4 (R_01 0.12, R_11 score 77-78), worse on R_08; offline mapper (B12/B14) parked: it degrades the VIO on loop-free walks |
| C | ORB-SLAM3 stereo-inertial (GPL) | highest accuracy where it works (0.03 m on R_01, 0.43 on R_02 in the paper), loop closing and multi-map | brittle (fails / jumps on hard sequences), heavy CPU | C01/C02 fisheye: R_01 **0.031 m**, R_04 0.79-0.83 with 25 % of frames lost, R_11 1.00 (score 65.6), R_08 crashes deterministically. Parked pending a code-level fix |
| D | OpenVINS (v1 reference) + further tracker work and a non-causal keyframe BA smoother | reuses everything from v1; v1 034 found a 21 px KLT window lifts the blurry test-like sequences (recall@5m 37 to 94 %) | smoother is engineering from scratch | D01-D03 (fixed / adaptive KLT windows): sequence-dependent, no broad win; parked at ov_ref005 (2.83 m) |
| E | VINS-Fusion (stereo+IMU, optimisation-based, loop closure) | classic, robust, cheap | older code base; pinhole only | optional |

Learned/dense methods (DPVO, DPV-SLAM, MASt3R-style) scored badly in the paper on this data and need the GPU: deferred to the A100 stage, owner's call.

## Harness (unchanged from v1)

`scripts/run_sequence.sh` runs one sequence end to end for OpenVINS; v2 adds one adapter per candidate that produces the same `trajectory.tum` (IMU pose, image timestamps) so `tum_to_submission.py` and `evaluate.py` apply unchanged. Data: all 23 training sequences in ASL/pinhole form (`data/training/*/runner_input`), raw fisheye for R_01/R_04/R_08/R_11 (`data/training_fisheye/`), `.vrs` for those four. Disk: 26 GB free.

## Numbers to beat (v1 reference ov_ref005)

Controlled set, two-offset mean ATE: 2.83 m. Additional set (ov_ref004, offset 0): score 2D 41 / 14 / 15 / 21, recall @ 5 m 100 / 37 / 24 / 49 % on sequence_1_19 / 1_20 / 2_11 / 2_12; ov_ref005 on all ten pending (v1 experiment 037).

## Where the candidates stand (all numbers single runs unless stated; details in experiments.md)

- Basalt (robust driver): controlled two-offset mean **2.43 m** (OpenVINS 2.83); additional-set mean score 16.9 (OpenVINS 22.0): wins short/medium and dark walks, loses the 2 km walks (structural drift, knobs do not help). Fisheye input helps 3 of 4 standard sequences. Cheap (~2x realtime, <2 cores).
- OKVIS2 (x10, 10 keyframes, final BA): R_01 0.022, R_04 0.68, R_08 2.09, R_11 1.94 (score 56.7); live path fragile (R_11 diverged live, recovered by the final BA); 15 keyframes worse on R_08; fisheye helps only R_01; ~10x Basalt's CPU. 13-sequence batch running detached.
- ORB-SLAM3: R_01 0.031 m, but loses a quarter of R_04's frames and crashes deterministically on R_08; parked pending a code-level fix.
- OpenVINS line: window variants parked; ov_ref005 stands (2.83 m / score 22.0).
- Drift analysis (X01): on the 2 km walks both Basalt and OpenVINS are locally consistent (0.15 to 0.5 m per minute) and lose everything to a handful of heading events (5 to 28 degrees in a minute) inside low-feature stretches: dark (4_11), low texture (2_11, 2_12), overexposed or reflective street scenes (3_18). Not scale, not restarts. The lever is the front end in degraded input.
- Mix-and-match (M01): a per-sequence choice between Basalt and OpenVINS would give 1.97 m and mean score 25.9 (oracle); a duration rule 24.2. Selector design is a v3 candidate.

## Next

1. OKVIS2: 13-sequence batch (k=0, final BA) running detached two at a time; judge on the controlled set and cost.
2. Basalt: B16 CLAHE at load time (source build) running on the standard four and three long walks; B15 tighter restart thresholds negative (2_12 pending). Then the same CLAHE step for OKVIS2.
3. Ensemble: a selector between Basalt and OpenVINS runs (restart counts, consistency, agreement).
4. ORB-SLAM3: one debugging round on the R_08 crash if time allows.

## Blockers

None.
