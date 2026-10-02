# Decision log v2 (append only)

Timestamped decisions, real clock (IST), written through `scripts/log.sh` (now pointing at v2).

- **2026-10-02 23:50** Owner closed v1 and opened v2. Standing rules: no leaderboard submission until top 3 and confident (owner decides); v2 explores different estimator classes, optimises each for a few rounds (not out-of-the-box only), then decides which approach or combination v3 takes up. v1 logs archived in `track_logs_v1/`; its two still-running experiments (034 KLT window/pyramid, 037 ov_ref005 on the additional set) append their results there.
- **2026-10-02 23:55** Candidate list set (see status.md): A OKVIS2, B Basalt, C ORB-SLAM3 stereo-inertial, D OpenVINS + non-causal keyframe BA smoother, E VINS-Fusion optional; learned/dense methods deferred to the A100 stage. Order of attack: A, B, then C/D. Each candidate: build on this PC, adapter to the v1 harness, out-of-the-box on the standard four at two offsets, optimisation rounds, full comparison.
