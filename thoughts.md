# Thoughts

## 2026-10-03: issues observed in v1/v2

- Main chain: events, not general tracking error. The systems work about as well as the open baseline; a few specific events derail a whole run.
  - Events: sustained low lighting, low texture, overexposure; dynamic objects (people, the wearer's own arm and shoe); reflections.
  - They give too few or wrong features (a front-end problem).
  - The IMU (6-DoF) fixes roll and pitch through gravity but cannot correct yaw, so the wrong features corrupt the heading, and heading error grows with distance walked.
  - Giving the IMU more weight over vision did not fix it (trades ATE against control-point score).
- Secondary issues
  - Scale: raw Aria accelerometer gives a 2 to 4 % metric scale error (forgiven by the Sim3 metric, matters for the robot); OKVIS2 drifts further in scale.
  - Initialisation gaps: no poses for 30 to 60 s before inertial init (ORB-SLAM3), early restarts (Basalt); missing poses count as misses.
  - Restart stitching: a heading error present at the cut is carried into the rest of the run.
  - Moving platform (5_11, 5_12): IMU says moving, the cabin in view says still; every system scores under 13.
  - Loop closure never exercised: no training walk revisits a place; the test set might reward it.
  - Cost: OKVIS2 5 to 10x Basalt, ORB-SLAM3 two cores; only Basalt and OpenVINS fit the robot budget as they are.

## 2026-10-03: the gap that remains after the events and small issues are fixed

- Where we stand on clean sequences: ahead of the open baselines on 12 of 13 controlled sequences; on the clean 1 km walk (like the Short challenge) we score 64 to 72 against 75 (AnonSLAM) and 91 (Aria's SLAM). The leaders' per-sequence numbers are not public, only three aggregate scores on the hidden test set.
- Likely sources of the remaining gap, in order
  - Ordinary slow drift (about 0.1 % of distance, 0.7 to 1 m on 1 km): only a global, non-causal optimisation over the whole run removes it (OKVIS2's final BA: R_01 0.14 to 0.02 m).
  - Loop closure: test walks probably revisit places (training ones do not); never exercised.
  - Local accuracy at the control points (pose jitter, camera-IMU extrinsics, time offset, raw-IMU scale): a few points.
  - Missing poses (init gaps, restarts): cheap, a few points of recall.
- Causal vs non-causal: the benchmark does not enforce causality. Rank 1 (Aria's SLAM, Meta's offline MPS) and rank 5 (OpenVINS + Maplab) are non-causal; rank 2 (AnonSLAM) is unknown, probably non-causal; ranks 3 and 4 not checked.
- Shape of the solution: fix the events causally in the front end, then a non-causal finishing stage (global BA plus loop closure) to go from good to top.
