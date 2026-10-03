# Current status (v3: front end)

Last updated: 2026-10-03 22:05 IST. Edit in place.

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
- **F01 complete**: enabling that filter at 3 px is the first clear, general win on the event set: dark walk 4_11 from 14.9 m / score 9.9 / recall 19 % to **3.8 / 37.9 / 99.1 %**, R_11 score 73 to 79, 2_11 and 3_18 ATE down by a quarter to a third, R_08 a near tie, R_12 slightly worse.
- **F06** (threshold 2 / 4 / 5 px, min 3 obs): flat between 2 and 4 px on the walks; the indoor cost grows with tightness (R_08 1.04 at 4 px, 1.28 at 2). 3 px stays, 4 px is the fallback.
- **F07** (3 px on the full sets, one run left): controlled two-offset mean **2.50 against 2.43**: wins easy, hard, R_11 and the additional set (1_19 74 against 64, 1_20 44 against 40), loses every medium sequence by 10 to 15 % and R_12 / R_13 (the same two that punished Huber 0.5 in v2). R_04's extra restarts all sit within 240 frames of an initialisation: the filter removes good observations before the solve has converged. **F08** (warm-up of 100 / 300 frames before filtering) is queued to test that.
- **F03** (epipolar gate on new landmarks, 0.005): the surprise of the day: best 2_11 score of any single change (30.3, ATE 21 m), best 3_18 score (4.7), 4_11 down by a third; 14 % cost on R_08. Four runs still re-running. Combination with the filter (F09) is next.
- **F02 / F05** (person masks, gate + masks): small gains where people walk through the view; gate 5 + masks gets 4_11 to 3.3 m and 2_11 to score 31.5 but taxes R_08 / R_12 by 15 to 30 %. Options, not defaults.
- **F04** (untrustworthy-image rule): catastrophic (R_08 142 m), discarded.
- **X05 root-caused** (gdb, line-level): the segfault is a landmark with a **single observation** (its host only, inverse distance 5e-7) reaching the QR; a 5-row block's third Householder step runs on zero rows. Fix: the pre-solve guard now also drops landmarks with fewer than two observations and prints where they came from (instrumented; the creation path adds at least two, so a removal path must be leaving one). Rebuild and the crash check (4_11, gate 10) are running; all runs with "failed" segments (F01 gate10 4_11, F02 masks 4_11, F03 4_11 and 2_11) get re-run after it.
- Infrastructure: the memory-pressure guard of the session killed 27 runs and the debug build; every batch now runs as a systemd user unit (`lamaria-*`). The Basalt build tree had lost its vcpkg packages to an aborted reinstall (CMake 4.4 in the venv changed the ABI hash); restored from vcpkg's binary cache and configured with `VCPKG_MANIFEST_INSTALL=OFF`, so `ninja basalt_vio` works again without touching vcpkg.
- Diagnostics: 4_11 is the "too few usable features" failure (X02, X04), R_12 the "wrong features" failure (gate fires exactly on the shoe episode, image centre, so no static mask).

## Next

1. X05 check, then re-run every crashed run; F07 last run; F08 (filter warm-up); F09 (filter + epipolar gate 0.005).
2. Pick the v3 reference config from F07 / F08 / F09 on the full sets (two offsets).
3. Then the learned-keypoint candidate (XFeat seeding) for the dark stretches, and the external-observation interface for learned trackers.

## Blockers

None.
