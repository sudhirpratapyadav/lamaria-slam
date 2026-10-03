# Current status (v3: front end)

Last updated: 2026-10-03 16:45 IST. Edit in place.

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

- Survey done (`docs/v3_frontend_survey.md`). Found that Basalt never calls its own outlier filter.
- F01 (IMU-consistency gate on existing landmarks + post-solve filter): gate 5 px on the six event sequences: 4_11 14.9 to 8.0 m (score 9.9 to 16.0), R_11 2.61 to 2.15 (score 73 to 78.5), 2_11 30.9 to 25.1 (score 20.7 to 26.7), R_08 worse (1.01 to 1.33), R_12 about the same; other variants running.
- F02 (person masks from YOLO11n-seg in the optical flow): first pass void (low-confidence whole-image boxes starved the tracker); masks regenerating at confidence 0.4 with an oversized-mask guard.
- F03 (temporal epipolar gate on new landmarks): queued behind F01.
- X02/X04 diagnostics: the dark walk 4_11 is the "too few usable features" failure (XFeat finds no more there either; the gate fires uniformly), R_12 is the "wrong features" failure (gate fires exactly on the shoe episode, in the image centre, so no static mask is possible).

## Next

1. Read the survey, pick concrete tools per candidate.
2. Build the external-observation interface in Basalt and a track-file format; verify it reproduces `basalt_ref1` when fed Basalt's own tracks.
3. Candidate 1 first (cheap, general, tells how much damage is liars versus too few features).

## Blockers

None.
