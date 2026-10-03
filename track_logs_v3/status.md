# Current status (v3: front end)

Last updated: 2026-10-03 18:41 IST. Edit in place.

## What v3 is

v2 showed that the long walks are lost to a few heading events (wrong features on the wearer's body, passers-by and reflections; too few features in dark, low-texture or overexposed stretches) and that reweighting cannot fix them. v3 builds a better front end on the Basalt back end and measures it by those events. Phase 2 (non-causal finishing: global BA, loop closure) is v4. Rule from the owner: improvements must stay as general as reasonably possible; every kept change records where it applies and where it fails.

## Plan

- Carrier: Basalt back end (source build, already patched). Add an interface that takes observations (tracks per frame) from outside, so any front end, classic, learned or mixed, can be run separately and plugged in; same back end, same scoring.
- Candidates, cheapest first:
  1. IMU-consistent rejection (geometry, no GPU): drop tracks whose motion disagrees with the gyro-predicted rotation beyond what parallax allows; plus an "untrustworthy image" rule (sharpness or feature count collapses: stop creating landmarks, let the IMU carry).
  2. Semantic masking (small GPU net): mask people and the wearer's body before tracking.
  3. Learned keypoints with classic tracking (SuperPoint / ALIKED to choose points, KLT patches to follow them).
  4. Learned trackers (CoTracker, DPVO-style); likely A100 territory at scale.
  5. Combinations: 1 and 2 remove liars, 3 and 4 find points where there are few.
- Measure: each candidate on the six event sequences (2_11, 3_18, 4_11, R_12, R_08, R_11) with the drift decomposition (`scripts/drift_analysis.py`, `scripts/sequence_timeline.py`) as the diagnostic (count and size of heading events), then the full two sets at two offsets. Applicability recorded per candidate from the start.
- Hosts: this PC (16 cores, 2 GB Quadro P620) for geometry and small nets; the A100 for heavier learned components when the owner moves there.

## Where things stand

- Survey done (`docs/v3_frontend_survey.md`). Found that Basalt never calls its own post-solve outlier filter.
- **F01 complete**: enabling that filter at 3 px is the first clear, general win of v3: dark walk 4_11 from 14.9 m / score 9.9 / recall 19 % to **3.8 / 37.9 / 99.1 %** (the level of v2's scene-specific near-feature cap), R_11 score 73 to 79, 2_11 and 3_18 ATE down by a quarter to a third, R_08 a near tie, R_12 slightly worse. The IMU-consistency gate alone is weaker and hurts R_08; combined with the filter it adds nothing. F06 (filter at 2 / 4 / 5 px, stricter minimum observations) running; F07 (3 px on all 13 x 2 offsets + the 10 additional) queued.
- F02 (person masks, YOLO11n-seg): small consistent gains where people walk through the view (2_11 30.9 to 24.3 m, score 20.7 to 26.0; R_11, R_12 slightly better), a loss indoors (R_08), split on 3_18. Kept as an option; F05 combines it with the gate.
- F03 (epipolar gate on new landmarks) and F04 (untrustworthy-image rule) running / queued.
- X05: a Basalt segfault (null pointer in the landmark-block QR) hits some runs deterministically (4_11 with masks at frame 8000; also behind v2's failed segments). First guard did not fix it; a debug-symbol build is in progress for a line-level backtrace. Crashed runs are re-run automatically once fixed.
- Diagnostics: 4_11 is the "too few usable features" failure (X02, X04), R_12 the "wrong features" failure (gate fires exactly on the shoe episode, image centre, so no static mask).

## Next

1. Finish F03 to F07; fix the segfault (X05).
2. If F07 holds on the full sets, the outlier filter becomes part of the v3 reference config; then combinations (filter + masks, filter + gate on new landmarks) and the learned-keypoint candidate (XFeat seeding) for the dark stretches.
3. The external-observation interface in Basalt stays on the list for the learned trackers.

## Blockers

None.
