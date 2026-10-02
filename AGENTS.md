# AGENTS.md — lamaria-slam

Read this first. It is the full context for any agent (or person) starting work in this folder.

## Mission

Climb the **LaMAria benchmark, Stereo + IMU track** (https://lamaria.ethz.ch/leaderboard) with our own visual-inertial SLAM. Work loop: try a change, measure on the training sequences, keep it if it helps, record it, repeat. Details of the benchmark, targets and plan are in `README.md`, `purpose.md` and `docs/benchmark_notes.md`; do not duplicate them here, read them. Current state and numbers: `track_logs_v2/status.md` (v1 archive: `track_logs_v1/`).

Hosts, in order: **this PC first**, then the A100 server, then the Jetson Nano. The owner (Harish, user of this machine; the git author is Sudhir Pratap Yadav) decides when to move to the next host. Do not start on another host unprompted.

## Why this project exists (the bigger picture)

The owner is building a Matic-like home robot: full SLAM + navigation + computer vision + UI, on Jetson Orin Nano and RK3588 boards with an HJY1A-G8-SM stereo camera (AR0234 global-shutter pair, 60 mm baseline, wide fisheye, ICM-42688-P IMU). That hardware takes about a month to arrive, so in the meantime the SLAM stack is developed and measured on LaMAria (Aria glasses: stereo global-shutter fisheye 640x480 at 20 Hz plus IMU, the same kind of sensor suite). The result should transfer: accuracy per CPU cost matters, not accuracy at any cost. GPL licences are acceptable. Stereo is fine, monocular is not needed.

Priorities, as stated by the owner: accurate, fast, optimised, "as best as we can on our hardware", and robust (never losing track).

## The sibling project: `~/sudhir/slam` (read-only reference, do not edit from here)

That repo holds the Jetson/P3-DX web app and a month of OpenVINS work. Reusable pieces:

- **OpenVINS** source and builds: `~/sudhir/slam/sources/open_vins`, builds in `~/sudhir/slam/build/open_vins` (and `runner`, `runner_kimera`, `webapp_native`). The offline stereo runner is `~/sudhir/slam/runner/stereo_offline.cpp`; the Python wrapper is `webapp/backend/slam_native.py`; `scripts/replay_benchmark.py` replays a recording through it. Prefer copying what you need into this repo (or referencing by path in a script) over editing the sibling.
- **`~/sudhir/slam/slambench/`**: a benchmark harness with metrics (ATE yaw/se3/sim3 with scale, KITTI-style drift per distance, loop gap, local RPE, jumps), a run/score/table CLI, plug-in adapters for external SLAM systems via JSON spec, and tests. LaMAria's own metrics (ATE after Umeyama, pose recall at 5 m, control-point score) are what count here, so use the official evaluators in `cvg/lamaria` for any number you report, and `slambench` metrics only as extra diagnostics.
- `~/sudhir/slam/docs/slam_plan.md` and `docs/jetson_optimisation_report.html`: the earlier plan and every optimisation experiment, including failures.

## Hard-won lessons (apply them here)

1. **A single run per setting is chaotic.** On the Kimera and Rosario datasets, the ranking of three OpenVINS settings differed between datasets and between seeds. Never decide from one run or one sequence: use several sequences, and rerun for seeds where results depend on randomness (RANSAC, feature tracking). Report per-sequence numbers, not only averages.
2. **Short windows hide drift.** A cheap setting matched the full one over 40 s windows but drifted 2.6x more over a 554 s run. Validate on the long and hard sequences, not only the easy ones.
3. **Validate on degraded input** (low light, noise): lighter settings that looked fine on an easy segment failed on held-out ones. LaMAria has low-light and moving-platform challenges.
4. **Scale can dominate error**: on a slow ground robot, ATE fell from 13.8 m to 4.7 m after fitting a scale. Check the sim3 scale factor to see whether the error is scale, drift or tracking loss.
5. **The recall metric rewards always producing a pose.** A system that tracks perfectly then crashes loses everything after the crash. Build failure recovery and reinitialisation early, and always write one pose per image (carry the last pose forward or use IMU propagation if tracking is lost).
6. **Measure timing offset and calibration quality before blaming the algorithm.** Camera–IMU time offset errors and bad noise parameters look like algorithm failure.
7. **Frame rate barely affects accuracy; latency does** (VIO result from the Nano work). Not directly applicable to offline scoring, but matters for the Nano.

## Hardware and safety constraints

- **This PC**: 16 cores, 15 GB RAM (about 11 GB usually free), Quadro P620 (2 GB, not useful for heavy GPU work), NVMe with roughly 225 GB free at last check. LaMAria is large (1.2–15 GB per training sequence in ASL form); check `df -h` before downloading, and **ask the owner before downloading data** (a previous download was declined; the owner wants control of that).
- **A100 server**: heavy builds, learned components and long batch runs go here once the owner moves to it.
- **Jetson Nano (4 GB, JetPack 4, Maxwell)**: ssh `jetson@10.8.0.165`. **Never build large C++ or export models on it** (OpenVINS with `-j4` and ONNX exports hung it for hours and needed a physical power cycle; remote recovery is impossible once it hangs). If a rebuild is unavoidable use `-j1` and one changed file, and cap memory (systemd `MemoryMax`). It is the constrained case: cross-build or build on the PC and copy binaries.
- Do not run long background jobs without a way to check them, and clean up processes you start.

## Working conventions

- **Tracking lives in `track_logs_v2/`** (the owner bumps the version suffix on substantial changes; v1 = OpenVINS tuning, archived in `track_logs_v1/`; v2 = exploration of estimator classes): `logs.md` is append-only, timestamped decisions; `status.md` is the current situation, edited in place; `experiments.md` holds the scoreboard at the top and one section per experiment (hypothesis, change, exact command, per-sequence result, cost, decision, insights), timestamped but editable. `purpose.md` at the root states the goal. Keep all four current. Change one thing at a time and compare against the current reference on identical sequences, across several start offsets (runs are deterministic). Record failures.
- **Configs, not code constants**: every tunable lives in a config file under `configs/`, versioned, so a result is reproducible from a commit.
- **Reproducibility**: record the git commit, host and exact command in each experiment section; `scripts/run_sequence.sh` writes them to `results/<exp>/<seq>/run_info.txt`. Large outputs go to `results/` (git-ignored); commit only small summaries and configs.
- **Scripts** go in `scripts/` and must run on any host (no hard-coded `/home/ubuntu` paths where avoidable; take data and tool paths as arguments or environment variables).
- **Honesty**: report what was measured, say when a result is a single run or a short window, say when a claim comes only from a screenshot or paper rather than from our own measurement. If tests or evaluations fail, show the output. Do not tune against the hidden test set; there is no ground truth for it, so submit only finished versions to the leaderboard (24 h between test updates) and only with the owner's go-ahead, since a submission is public.
- **Git**: commit when the owner asks or at the end of a coherent unit of work they have approved; do not push to a remote unless asked. Commit messages end with the attribution line your harness specifies.
- **Reports and deliverables**: write local files in this folder (markdown or HTML) and tell the owner the path. Never publish to Artifacts or any shareable link unless the owner explicitly asks in that moment.
- **Style**: match the surrounding code, keep comments sparse and about why, prefer small tested helpers. Use they/them for people whose pronouns are unknown.

## First steps for a new agent

1. Read `README.md`, `purpose.md`, `docs/benchmark_notes.md`, then `track_logs_v2/status.md` and the tail of `track_logs_v2/logs.md` (v1 summary at the top of `track_logs_v1/experiments.md`).
2. Clone `https://github.com/cvg/lamaria` into `third_party/` (git-ignored), read its evaluators (`evaluate_wrt_pgt.py`, `evaluate_wrt_control_points.py`, `evaluate_wrt_mps.py`) and its pipeline code.
3. Data: the owner approved downloading the whole training set in ASL form (2026-10-02, `scripts/fetch_sequences.sh`, zips deleted after unpacking). Any other download (e.g. raw `.vrs` for fisheye) still needs the owner's approval.
4. Build the harness: run OpenVINS stereo+IMU on a training sequence, write the per-image pose file in the required submission format, score it with the official evaluators, and record it. (Done in v1, 2026-10-02.) First reproduce the published open baseline's behaviour (OpenVINS with a sensible fisheye or pinhole config) before changing anything.
5. Decide fisheye-raw versus pinhole-undistorted input by experiment, and the IMU choice and noise parameters likewise (open questions in `docs/benchmark_notes.md`).
6. Iterate with the ladder in the README: tracking and tuning, initialisation and recovery, then loop closure and mapping (the biggest gap to the leader on medium and long sequences).
