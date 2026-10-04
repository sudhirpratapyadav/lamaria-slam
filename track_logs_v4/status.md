# Status: v4, stereo quality gate and non-causal backend (opened 2026-10-05)

**Reference**: `configs/basalt_v3_ref` on the repeatable build (v3 F21): controlled two-offset mean 2.38 m, additional-set mean score 23.7; dark walks 20.6 / 56.9; long walks 3_17 / 3_18 scores 6.0 / 1.7 (ATE 47 / 56 m).

**Owner's goal**: "start v4, stereo quality gate as well as non causal backend, let's see how far we can go."

## Where the gap is, and what moves it (X01 to F05)

- The long walks never revisit a place: loop closure cannot help them. Their remaining error after v3 was a **steady heading drift of 2 to 3.5 degrees per minute**, same sign on all daytime walks (3_17, 3_18, 2_11, 2_12, R_12), absent on the dark walks, 1_19 / 1_20 and indoors.
- **It is visual, and it has two measured parts**: (1) a **camera-IMU time offset of 5 ms** (images later than their stamps; measured from the images on both devices and both cameras, `scripts/cam_imu_check.py`; Basalt ignores the calibration's offset field, so the input is shifted): +4.5 ms removes 40 % of 2_11's drift, +10 ms removes it (heading -57 to -5 degrees, ATE 21.5 to 6.8 m, score unchanged); (2) **running monocular on cam0** (the left-looking camera; cam1 enters only as a stereo partner and never matches on this pair): with cam1 as the primary camera the drift is gone, and landmarks in both cameras (`BASALT_MONO_CAMS=1`, F02) halve it (2_11 21.5 to 12.5 m, 3_18 56 to 34 m) and win indoors (R_04 0.70 to 0.55, R_08 1.03 to 0.75, R_12 13.9 to 11.0) at 2x cost; the dark walk is worse (1.8 to 5.3 m, but no restarts).
- **What does not work**: trusting the gyro (noise x2 instead of x20). It removes the drift on the daytime walks (2_11 2.9 m, 3_17 9 m) but breaks 1_19 (0.65 to 14 m), 1_20, the dark walks and every indoor sequence, because the gyro bias moves and vision must stay free to re-estimate it; a faster bias walk recovers those and gives the drift back on 3_18. Closed (F01 series). More baseline before a landmark (F04): no effect.
- Scale: with the heading fixed, the fitted sim3 scales sit at 0.93 to 0.97 on the walks; that is the stereo thread's target.

## Running

- F05b (`lamaria-v4-f05b`): offset sweep +7 / +15 ms on 2_11, +4.5 ms on 1_19 and 4_11 (must not hurt where there is no drift).
- F06 (`lamaria-v4-f06`): both visual fixes together (both-camera landmarks + offset 5 or 10 ms) on 2_11, 3_18, 4_11, R_08, R_04.

## Plan

1. Settle the causal visual fixes (F06): pick the offset (the measured 5 ms unless 10 ms is clearly better everywhere), decide on both-camera landmarks (cost 2x; the dark walk needs the second offset to judge), then the full sets on one snapshot to make the v4 causal reference.
2. Non-causal backend: global visual-inertial bundle adjustment over Basalt's keyframes (Ceres 2.0 is installed), fed by a dump of Basalt's landmark observations; stereo observations enter there with a quality gate judged against the converged solution.
3. Stereo quality gate (causal side): `BASALT_STEREO_INIT=1 BASALT_STEREO_CHECK=0.3` is the indoor option from v3 F19; the open problem is the dark walk, where wrong stereo matches agree with wrong temporal depths.
