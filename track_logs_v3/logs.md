# Logs (v3: front end)

Append-only, timestamped. Add with `scripts/log.sh "..."`.

- **2026-10-03 15:24** v3 opened by the owner after the v2 discussion (see `thoughts.md`). Scope: a better front end on the Basalt back end, measured by the heading events; the non-causal finishing stage is v4. Research agent launched to survey masking, IMU-aided rejection, learned keypoints and learned trackers.
- **2026-10-03 15:30** Survey saved (docs/v3_frontend_survey.md). Found that Basalt never calls filterOutliers. F01 launched: IMU-consistency gate (pre-solve) and the post-solve outlier filter, env-gated, on the six event sequences.
- **2026-10-03 15:52** X03: YOLO11n-seg finds pedestrians and the wearer's shoe when the frame is rotated upright. F02 launched: person masks precomputed per frame, consumed by Basalt's optical flow (no detection inside, tracks entering are dropped); mask generation at 1100 frames/min after a threading fix.
- **2026-10-03 16:33** F02 first pass void: low-confidence whole-image person boxes starved the tracker (R_12 18.7 m). Masks regenerated at conf 0.4, oversized masks ignored in Basalt; F02 relaunched.
- **2026-10-03 18:07** X05: Basalt segfault root-caused (landmark without observations -> empty QR block); guard added; crashed runs will be re-run.
- **2026-10-03 18:40** F01 complete: enabling Basalt's dormant post-solve outlier filter at 3 px lifts the dark walk 4_11 from 14.9 m / score 9.9 / recall 19 % to 3.8 / 37.9 / 99.1 %, R_11 73 to 79, cuts 2_11 and 3_18 ATE by a quarter to a third; the IMU gate alone is weaker. F06 (filter variants) launched, F07 (3 px on the full sets) queued.
- **2026-10-03 19:38** Memory-pressure guard killed my waiters, the debug build and (with SIGTERM) 27 of the F03/F06 runs; F04's untrusted-image rule is catastrophic (R_08 142 m) and was stopped. Killed runs re-launched under a systemd user unit (own cgroup).
