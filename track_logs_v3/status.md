# Current status (v3: front end)

Last updated: 2026-10-04 02:45 IST. Edit in place.

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
- **The filter (F01/F06/F07)**: 3 px post-solve reprojection filter, the first clear general win: dark walk 4_11 from 14.9 m / score 9.9 / recall 19 % to **3.8 / 37.9 / 99.1 %**; additional set mean score **21.2** (reference 16.9, 8 of 10 up); controlled two-offset mean 2.50 against 2.43 (loses the medium set and the long control-point walks). Threshold curve flat 2 to 5 px on the walks, indoor tax grows with tightness.
- **Filter + epipolar gate (F03/F09)**: the gate on new landmarks (0.005) combined with the filter is best or tied-best on five of six event sequences (R_12 back to the reference, 2_11 20.1 m, 4_11 3.5 m / recall 99.9 %). **Candidate reference pair.**
- **Why the medium set loses (X06/X07/F08)**: residuals are tiny everywhere (median 0.22 px); R_04 diverges at one frame in a burst where the pose, not the points, is wrong, and the filter removes the constraints that would fix it. Warm-up: not kept (costs the dark walk). MAD-adaptive threshold: just a tighter fixed threshold, closed. Keep-host (do not delete a landmark on its host residual): R_04 **0.56 / 0.53** at the two offsets, better than the reference, but 4_11 7.1 m, so the host rule is what cleans the dark walk. **F08d** (burst skip: no filtering in a frame where more than 2 % of observations exceed the threshold; per-landmark rule) running, with the host rule on. Runs repeat to 0.5 % (X07).
- **Learned candidates**: XFeat keypoints seeding KLT (F10, three modes plus a FAST-threshold ablation): negative whenever they supply a large share of the points, neutral when a few percent; parked, with the finding that the weak FAST corners carry the dark walk and a learned detector's points are less trackable by KLT. XFeat descriptor-matching front end through the new external-tracks interface (F11): first run 15.3 m on 4_11 (filter alone 3.8); the matcher needs sub-pixel refinement and a longer temporal window before it is a fair test. Person masks (F02/F05): small gains where people walk through the view, a tax indoors; option.
- **Crash (X05) solved**: self-pair triangulation in float after a divergence; fixed in the patch. Crashed runs re-run.
- Infrastructure: batches as systemd units; a second build tree (`build/dev`) and an atomic install dir (`third_party/basalt/install`) so rebuilds never race a starting run; vcpkg packages restored from the binary cache.

## Next

1. F08d result; then the full-set validation (13 x 2 offsets + 10 additional) of filter 3 px + epipolar gate 0.005 (+ burst rule if it holds) as the v3 reference candidate.
2. F11 iteration: KLT refinement step from the matched position, two-frame temporal consistency; R_08 runs.
3. Then the remaining list: learned trackers via the interface (A100 territory), mixed re-association of lost tracks by descriptor.

## Blockers

None.
