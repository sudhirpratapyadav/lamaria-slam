# v4 plan: the non-causal finishing stage (draft, 2026-10-04, not yet opened)

Written at the close of v3 so the owner can decide with the evidence in one place. v4 opens only when the owner says so; `track_logs_v4/` does not exist yet.

## Starting point (v3 reference, one frozen binary)

- Causal Basalt (`configs/basalt_v3_ref`): controlled two-offset mean 2.42 m, additional-set mean score 21.5; dark walks 20.9 / 41.2; long walks 3_17 / 3_18 scores 1.8 / 1.6 (ATE 47 / 57 m over 2 km).
- Leaderboard (test set, score 2D short / medium / long): Aria's SLAM 90.7 / 78.5 / 70.9; AnonSLAM 75.3 / 61.1 / 59.9; OpenVINS+Maplab (open baseline) 27.7 / 23.4 / 12.8. Our local picture: short above the baseline and near rank 2, medium around the baseline, long far below.
- The benchmark does not enforce causality; ranks 1 and 5 are non-causal (`thoughts.md`).

## What the measurements say the long walks need

1. **Drift, not events, is what is left after v3.** v2 X01 found the long walks lost to a few heading events in degraded stretches; v3's filter and per-landmark rule removed most of those (2_11 31 to 21 m, 3_18 81 to 56 m, 4_11 16 to 1.6 m). What remains on 3_17 / 3_18 is the ordinary 0.1 to 2 m per 100 m drift of a causal filter over 2 km with no revisits.
2. **Global optimisation works on this data.** OKVIS2's final bundle adjustment (v2 A07) took R_01 from 0.14 to 0.02 m and R_12 from 12.9 to 4.5 m, at 5 to 10x Basalt's cost and with a scale drift of its own (fitted scale 0.81 to 0.96). Its live path was worse than Basalt everywhere.
3. **Loop closure helps only where there are revisits**: R_11 to R_13 and the city walks have some; the 2 km point-to-point walks (3_17, 3_18) have few. The gain there must come from global BA with good priors (IMU, the control-point-free sim3 is still fitted by the evaluator).
4. **Scale is now IMU-only** (X06d: no stereo observations on this pair). A non-causal stage can afford a careful stereo step (geometric quality gate: a stereo match is kept only if its depth agrees with the temporal triangulation a few frames later), which the causal filter could not.

## Candidates, cheapest first

1. **Basalt mapper on the v3 keyframes** (`scripts/run_basalt_mapper.sh`, patch already carries the mapper fixes from v2 B12/B14): non-linear factor recovery, loop detection (BoW) and global BA over the keyframe graph; output the optimised poses, then re-propagate the per-frame poses (`scripts/basalt_propagate_keyframes.py` exists). Cost: minutes per sequence. First test: the six event sequences plus 3_17, scored as usual.
2. **Pose-graph post-processing of the v3 trajectory**: a lightweight global BA / pose graph over the robust driver's output with IMU preintegration between keyframes and the few loop constraints available; keeps v3's front end untouched. Our own code, moderate effort.
3. **OKVIS2 final BA as a second opinion** (v2 A07 config): already measured; a per-sequence selector between Basalt and OKVIS2 final would reach 1.66 m on the controlled set (v2 oracle), but needs a selector signal (v2 M02 candidates: agreement, restarts, live-versus-final disagreement). Expensive (hours per long walk).
4. **Stereo with a geometric quality gate** in the non-causal pass (see 4 above); measured as a v3 follow-up if the owner prefers.
5. **Reinitialisation gaps**: the robust driver's restarts leave the segment joins stitched by the IMU; a global pass can align segments properly (R_04, 4_11 restarts).

## Method rules carried over from v3

- One frozen binary per experiment (`scripts/snapshot_basalt.sh`), deterministic reductions on; compare settings on the same binary only; repeat long walks once when a difference is below 10 %.
- Every kept change gets an applicability line (indoor, outdoor, tunnel, platform, this sensor, this benchmark).
- Full-set validation (13 x 2 offsets + 10 additional) before anything becomes the reference; the robust driver stays, since the recall metric rewards a pose per image.
- Submission only when the owner says so.

## Open questions for the owner

- v4 scope: Basalt mapper first (cheapest) or straight to our own pose-graph stage?
- Host: the mapper and pose graph fit this PC; OKVIS2 final BA on all sequences would be A100 work.
- Whether the stereo quality gate is a v3 follow-up or part of v4.
