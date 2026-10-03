# Current status (v2: exploration)

Last updated: 2026-10-03 13:13 IST. **All runs finished; v2 paused for the owner's discussion on how to take it further.** Edit in place.

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

## Where the candidates stand (single runs unless stated; details in experiments.md)

Reference numbers: controlled set two-offset mean ATE; additional set mean score 2D over the 10 sequences (leaders: AnonSLAM 75 / Aria 91 on the main set).

| System | Controlled | Additional | Cost | Notes |
|---|---|---|---|---|
| OpenVINS ov_ref005 (v1) | 2.83 | 21.8 | 1.4x realtime, 1 core | causal; CLAHE + 400 features + 8x8 grid |
| Basalt basalt_ref1 (B07) | **2.43** | 16.9 | 2x realtime, <2 cores | robust driver with restarts |
| Basalt Huber 0.5 (B18) | 2.61 (better on 20/26, loses R_12/R_13) | 19.7 | same | dark walk 4_11: 9.9 to 37.1 |
| Basalt 1.5 m near cap (B20/B22) | not run (ruins indoor: R_08 1.0 to 4.9) | 21.6 (best on 6/10; 5_12 fails) | same | 4_11: 42.1, recall 99.6 % |
| OKVIS2 final BA (A07) | 2.15 at offset 0 (Basalt 2.46 at offset 0) | not run | 5-10x Basalt, up to 8 GB | non-causal; wins easy + R_12; CLAHE: R_11 0.91 / 75.6, R_08 2x worse |
| ORB-SLAM3 fisheye (C02/C03) | 4 sequences only (R_01 0.031, R_04 0.8, R_08 1.38, R_11 1.00) | | 1.2x realtime, 2 cores | needs raw fisheye; poses missing before IMU init; pinhole path fails |
| Oracle, per sequence | 1.56 (three systems, offset 0) | 28.8 (Basalt settings + OpenVINS) | | upper bound for a selector |

What v2 established:

- **Where the error is (X01)**: on the long walks every system is locally consistent and loses the sequence to a few heading events of 5 to 28 degrees inside a minute, in low-feature stretches (dark, low texture, overexposed) and, as shown on R_12, from features on the wearer's own body and on near moving objects. Not scale, not restarts, not the back end.
- **Weighting cannot fix it**: adaptive pixel noise (D04), Basalt obs-std and Huber (B17-B19) all trade ATE against control-point score.
- **Rejecting the cause works but is scene-dependent**: Basalt's 1.5 m near-feature cap gives the best 4_11 of any system and lifts six of ten additional sequences, and ruins indoor sequences; a relative rule (B21) does not fix that. CLAHE helps OKVIS2 enormously on R_11 and hurts it on R_08; it does nothing for Basalt.
- **Complementarity is large**: per-sequence oracles are 1.56 m (controlled) and 28.8 (additional) against 2.15 / 21.8 for the best single setting. A selector with an observable signal (M02 reached 24.4 against an oracle of 25.9 with two systems) is the cheapest route to a big step.
- ORB-SLAM3 is viable only on raw fisheye input (its crash was a bug in the example, fixed); covering all sequences needs the other nine `.vrs` files (owner's call, 49 GB free now).

## Next

Paused at the owner's request for a discussion on direction. Candidate directions for v3, in my order: (1) a per-sequence selector over a small set of runs (Basalt plain / Basalt near-cap / OKVIS2 final / OpenVINS) using observable signals (indoor-outdoor, restart counts, live-final agreement, cross-system agreement); (2) a front end that rejects body and near moving features with a scene-aware trigger, built into Basalt; (3) OKVIS2's final BA as the non-causal finishing stage where its cost is acceptable.

## Blockers

None.
