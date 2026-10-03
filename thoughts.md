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

## 2026-10-03: how the methods work (front end discussion)

- Pipeline shared by all four systems (OpenVINS, Basalt, OKVIS2, ORB-SLAM3)
  - Front end finds and follows points; IMU preintegration sums gyro and accelerometer between images; back end fuses them; marginalisation keeps the problem small; extras are loop closure, global map, final bundle adjustment.
  - Vocabulary: state (poses, velocity, biases, landmarks), measurements (pixels, IMU readings), model (projection, IMU kinematics, calibration), residual (prediction minus measurement). Noise parameters say how much each measurement is believed.
- Filter vs optimiser
  - Both are Bayesian; the difference is how many states are re-estimated together and whether the solve iterates. A filter nudges one belief once per measurement and never looks back; an optimiser re-solves a window of states and can undo a wrong step while it is still in the window.
  - "Filter" is the Wiener/Kalman sense: an adaptive low-pass on the measurement stream. Filtering uses data up to now; smoothing uses later data too.
  - An event pulls both wrong; the optimiser can recover if good features return inside the window. Marginalisation turns the oldest state back into a filter prior.
- Front ends
  - Tracking (KLT, optical flow): slide a remembered patch to where it overlaps best in the next frame. Sub-pixel precise, degrades gracefully in blur and dark, needs small motion, creeps and latches onto look-alikes when the point is lost.
  - Descriptor matching (ORB, BRISK): summarise each corner as a bit string and find the closest one anywhere in the image or the map. Re-finds lost points, handles big jumps, coarser position, falls apart in blur and dark.
  - Map points in ORB-SLAM3 and OKVIS2 keep all their observations and descriptors; only the matching is collapsed to one representative. Learned trackers keep the whole track as memory.
  - Basalt wins despite no IMU-guided search because measurement quality (0.1 px) and graceful degradation matter more than how features are found at 20 Hz.
  - Back-end-to-front-end feedback exists as IMU-guided search (ORB-SLAM3, OKVIS2) and outlier gating (all). Nobody uses the IMU to decide which features are lying; a feature on the wearer's shoe or a passer-by moves inconsistently with the gyro.
- Target front end
  - Precision from patch tracking, re-finding from descriptors, plus a third piece for bad images: a learned front end that sees in the dark and knows people and body parts, or a rule that says the image is untrustworthy now, lean on the IMU, invent no features.
  - Learned options: detectors and descriptors (SuperPoint, ALIKED), matchers (LightGlue), trackers (CoTracker, RAFT, DPVO). Cautions: DPVO/DPV-SLAM scored badly in the benchmark paper; GPU needed (fine on the Orin, not on the old Nano).
