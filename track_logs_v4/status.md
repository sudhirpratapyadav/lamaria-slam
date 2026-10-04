# Status: v4, stereo quality gate and non-causal backend (opened 2026-10-05)

**Reference**: `configs/basalt_v3_ref` on the repeatable build (v3 F21): controlled two-offset mean 2.38 m, additional-set mean score 23.7; dark walks 20.6 / 56.9; long walks 3_17 / 3_18 scores 6.0 / 1.7 (ATE 47 / 56 m).

**Owner's goal**: "start v4, stereo quality gate as well as non causal backend, let's see how far we can go."

## Where the gap is (X01)

- The long walks never revisit a place: loop closure cannot help them. Place recognition would matter only on R_01 / R_03 / R_05 and a little on R_10, R_13, 1_20, 2_11.
- Their error is a **steady heading drift of 2 to 3.5 degrees per minute**, same sign on all daytime walks (3_17, 3_18, 2_11, 2_12, R_12), absent on the dark walks and on 1_19 / 1_20, 2 to 4 times what the gyro alone drifts. Local scale and local consistency are fine.
- **Cause found (X02)**: the x20 IMU noise inflation inherited from v1 was applied to the gyro as well as the accelerometer; at x20 the gyro no longer holds the heading against a slow visual yaw bias. With the gyro at x2, 2_11 goes from 21.5 to 2.9 m ATE and from score 21 to 47, heading error 57 to 7 degrees. Validation on the full sets is running (F01).

## Running

- F01 (`lamaria-v4-f01`): gyro x2 on the full sets; F01b (`lamaria-v4-f01b`): gyro x1 / x5 on seven event sequences; X02 (d): cameras swapped on 2_11.

## Plan

1. Settle the gyro weight (F01 / F01b), make it the v4 reference if the full sets agree; then look at the residual visual yaw bias (swap arm, far-landmark handling, independent cam1 landmarks).
2. Non-causal backend: global visual-inertial bundle adjustment over Basalt's keyframes (Ceres 2.0 is installed), fed by a dump of Basalt's landmark observations; stereo observations enter there with a quality gate judged against the converged solution.
3. Stereo quality gate (causal side): `BASALT_STEREO_INIT=1 BASALT_STEREO_CHECK=0.3` is the indoor option from v3 F19; the open problem is the dark walk, where wrong stereo matches agree with wrong temporal depths.
