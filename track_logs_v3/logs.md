# Logs (v3: front end)

Append-only, timestamped. Add with `scripts/log.sh "..."`.

- **2026-10-03 15:24** v3 opened by the owner after the v2 discussion (see `thoughts.md`). Scope: a better front end on the Basalt back end, measured by the heading events; the non-causal finishing stage is v4. Research agent launched to survey masking, IMU-aided rejection, learned keypoints and learned trackers.
- **2026-10-03 15:30** Survey saved (docs/v3_frontend_survey.md). Found that Basalt never calls filterOutliers. F01 launched: IMU-consistency gate (pre-solve) and the post-solve outlier filter, env-gated, on the six event sequences.
