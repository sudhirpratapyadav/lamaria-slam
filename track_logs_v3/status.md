# Current status (v3: front end)

Last updated: 2026-10-04 08:00 IST. Edit in place.

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

- **The filter (F01/F06/F07)**: Basalt never called its own post-solve reprojection filter; at 3 px it is the first clear general win (dark walk 4_11 14.9 m to 3.8 m; additional-set mean score 16.9 to 21.2; controlled two-offset mean 2.50 against 2.43, losing the medium set).
- **Per-landmark rule (F08d, X08)**: an observation above 3 px is removed only if its landmark is otherwise well fitted; the dark walk goes to **1.66 m / score 56.7 / recall 99.6 %** (reproduced across builds: 2.26 then 1.66 with the same divergence structure), R_12, R_08, 2_11 at or better than the reference. **Candidate reference: filter 3 px + per-landmark rule.** The epipolar gate (F03/F09) helped on its own but gate + rule together break the dark walk on every build (16 to 23 m): a real interaction on sparse maps, so no gate in the candidate.
- **Method finding (X07/X08)**: runs repeat to 0.5 % on one binary, but builds of identical logic differ on sequences with divergences (floating-point contraction), so cross-build comparisons on 4_11 / R_04 are unreliable. Binaries are now frozen per experiment (`scripts/snapshot_basalt.sh`). **F15** (running next) re-measures reference, flat filter, rule, gate, gate + rule and stereo-as-constraint on one snapshot over the six event sequences; **F16** validates the candidate on the full sets on the same snapshot. These two decide v3's reference.
- **Stereo (X06d/F14)**: Basalt had **zero** stereo observations on this sensor (cameras 75 degrees apart; the same-pixel search never converges), so every Basalt result so far is monocular + IMU. Starting the stereo search from the calibration gives real stereo observations; they help R_08 (0.95) and 3_18, but on the dark walk most matches are wrong and the map collapses (14.8 m as initialiser, 102 m as constraint). Parked for this sensor pending a match-quality gate; right default for a parallel pair like the robot's camera.
- **Filter variants not kept** (all measured): warm-up, MAD-adaptive threshold, keep-host, burst skip (indoor win, outdoor loss), median-gated burst skip, newest-frames rule. R_04's divergence at frame 393 with any filter stays the one known cost.
- **Learned candidates, all parked with reasons**: XFeat seeding of KLT (F10: negative when dominant, neutral when sparse; weak FAST corners carry the dark walk), XFeat descriptor-matching front end (F11: 152 m), hybrid KLT + descriptor re-association (F13: worse than its own KLT ablation, and the external cv2 KLT is far below Basalt's patch tracker). Person masks (F02/F05): option for people-heavy scenes. The external-tracks interface stays for later learned trackers.
- X05 crash solved (self-pair triangulation in float after a divergence). Infrastructure: systemd units, dev build tree, atomic install, per-experiment snapshots.

## Next

1. F15 (same-binary comparison) then F16 (full sets with filter + rule): set the v3 reference from those two.
2. If F16 holds: the additional-set mean and controlled mean become the v3 numbers; then decide with the owner between finishing v3 and opening v4 (non-causal).
3. Open ideas with evidence behind them: a stereo match-quality gate (depth consistency over two frames) to switch stereo on; re-association inside Basalt's tracker rather than outside.

## Blockers

None.
