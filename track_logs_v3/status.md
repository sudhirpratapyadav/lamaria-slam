# Current status (v3: front end)

Last updated: 2026-10-04 12:00 IST. **v3 closed** (owner, 2026-10-04); F17 / F18 tail runs are appended to experiments.md as they land. Edit in place.

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

## v3 result

**Reference**: `configs/basalt_v3_ref` = Basalt `basalt_ref1` + robust driver + `BASALT_OUTLIER_PX=3` + `BASALT_OUTLIER_LM_RULE=1` (+ `BASALT_DETERMINISTIC=1`), patched Basalt in `docs/patches/basalt-0f3b2b5.patch`. Full sets, repeatable build (F21; bit-reproducible, `results/v3-F21-ref-repeatable/bin`):

| | v3 reference | v2 reference (Basalt ref1) | v1 reference (OpenVINS) |
|---|---|---|---|
| Controlled set, 13 seq x 2 offsets, mean ATE sim3 | **2.38 m** (F21, repeatable build; F16 2.42) | 2.43 m | 2.83 m |
| Additional set, 10 seq, mean score 2D | **23.7** (F21; F16 21.5) | 16.9 | 22.0 |
| Dark walks 4_10 / 4_11, score | **20.6 / 56.9** (F21) | 8.4 / 9.9 | 0.9 / 30.2 |

Leaderboard, rough (local training numbers against published test scores): short walks above the open baseline and near rank 2, medium around the baseline, long walks far below (drift; v4), moving platform weak.

## What v3 established (details and applicability in experiments.md)

- Basalt's own post-solve outlier filter, never called upstream, plus a per-landmark rule for which observations to remove: the two general changes that carried v3. Every other filter variant and every pre-solve rejection (IMU gate, epipolar gate, masks, burst skip, warm-up, adaptive threshold, keep-host, newest-frames) measured; kept as options with applicability notes, none as default.
- Basalt had zero stereo observations on the Aria pair (75 degrees apart); calibration-initialised stereo exists in the patch, helps indoors, poisons the dark walk without a quality gate; parked here, right default for the robot's parallel pair.
- Learned front ends (XFeat seeding, XFeat matching, KLT + descriptor re-association) all below Basalt's patch tracker; the external-tracks interface and the scripts stay.
- Crash root-caused and fixed; run-to-run and cross-build chaos understood, deterministic reductions and per-experiment binary snapshots in place.
- Tooling: systemd batches, dev build tree, atomic install, snapshots, residual dump, summariser.

## Next (owner's call; draft plan in `docs/v4_plan.md`)

v4: the non-causal finishing stage (global BA, loop closure) for the long walks, where the leaderboard gap is; or a v3 follow-up on the stereo quality gate and in-tracker re-association. Tail runs still going: F17 (stereo photometric gate) and F18's last bound (3 px), appended when they land.

## Blockers

None.
