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
