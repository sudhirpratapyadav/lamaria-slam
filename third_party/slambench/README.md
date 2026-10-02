# slambench

One way to run, score and compare SLAM/VIO systems on any machine (PC, A100, Jetson, RK3588 board). The same recordings and metrics everywhere, so a number measured on one host is comparable with another.

```bash
python -m slambench datasets                                    # what is registered, and what is available on this machine
python -m slambench run kimera_thoth --variant robust           # run OpenVINS and score it (results/slambench/...)
python -m slambench run rosario05 --variant full --max-seconds 200
python -m slambench table                                       # markdown table of every result
python -m slambench robustness kimera_thoth --variant robust    # clean vs dark/noisy images over several seeds, counting failures
python -m slambench reeval                                      # re-score saved results with the current metrics, no re-run
python -m slambench eval kimera_thoth my_trajectory.tum         # score a trajectory from any other system
scripts/slambench_baselines.sh results/slambench 6              # the full baseline table (3 settings x 2 datasets)
```

## What is measured

| Metric | Meaning |
|---|---|
| ATE yaw / ATE se3 | Error of the whole trajectory after alignment. **Yaw** (4 degrees of freedom: rotation about the vertical axis plus translation) is the right alignment for gravity-aligned VIO and does not hide a tilt error; **se3** (full rigid alignment) is the usual figure in the literature. |
| ATE sim3 / scale | Error after also fitting a scale factor. `scale` is the factor that makes the estimate match the reference's metric size (0.80 means the estimate is about 25% too long). A big gap between ATE se3 and sim3 means the error is mostly scale, which wheel odometry or a known baseline can fix. |
| drift (% per 100 m) | KITTI-style relative error over path segments, independent of alignment. The honest measure of long-run drift. |
| start→end gap | On a route that returns to its start, how far apart the estimated start and end land, as a percent of the path. Only shown for closed loops that the run fully covers. This is what loop closure should fix. |
| local 1 s | Error over 1 second. Local accuracy, unaffected by drift. |
| jumps | Pose steps over 2 m between samples: tracking failures. |
| compute p50, CPU, RAM, temperature | Cost. CPU/RAM/temperature are whole-system (so run on an idle machine for timing); RAM is the run's peak. |

Rosario's reference is a GNSS-fused estimate, not independent ground truth; Kimera's is ground truth. Read each result with its `reference_kind`.

## Adding another SLAM system

No code needed: write a JSON spec that runs it and says where its trajectory (TUM format, `t x y z qx qy qz qw`) ends up, then run it through the same scoring.

```json
{"cmd": ["/path/to/basalt_vio", "--dataset-path", "{recording}", "--cam-calib", "{config}/calib.json", "--result-path", "{out}/traj.tum"],
 "trajectory": "{out}/traj.tum", "frame": "body"}
```

`{recording}`, `{config}`, `{out}` and `{max_seconds}` are filled in. Use `"frame": "imu"` if the system reports the IMU pose (the pose is then converted to the reference body frame, as for OpenVINS). Then `python -m slambench run DATASET --system command --variant basalt --spec spec.json`.

## Recording your own data (what the plan needs)

Use the app's **Record only** mode, or `curl` its `/api/start` with `"mode":"capture"`. It writes `stereo.csv`, `imu.csv`, the images and a calibration `config/` folder, the layout everything here reads.

1. **Looped routes, 3-5 minutes each**: a room, a corridor circuit, a figure-eight, and the same route driven twice. End each loop where it started, as closely as you can (mark the start with tape). Loops are how we measure drift without a motion-capture system.
2. **Lighting and scene variants**: normal light, dim light, and people moving through the scene.
3. **Log the wheel odometry** alongside (the robot app's odometry history, with timestamps).
4. **Static IMU log for noise**: the sensor perfectly still and warm, ideally 2+ hours (a few minutes gives noise density but not random walk). `python -m slambench.tools.allan_variance RECORDING/imu.csv`.
5. **Timing check**: shake the camera briskly by hand (about 2-4 Hz) for 30-60 s in a textured scene. `python -m slambench.tools.timing_check RECORDING`. A strong peak and an offset that is stable across segments mean the timing is trustworthy.
6. Register a recording: `python -m slambench add-dataset NAME RECORDING_DIR CONFIG_DIR --loop`. Without a reference trajectory it is scored on start→end gap, jumps and path length (still a meaningful drift signal for a loop).

## Tools

- `tools/allan_variance.py`: IMU noise density, bias instability and random walk from a static log, with a ready-to-paste `imu.yaml` block.
- `tools/timing_check.py`: camera-IMU time offset from image rotation versus gyro rotation. Needs fast rotation to see a timing error.
- `tools/make_fisheye.py`: turn a pinhole recording into an equidistant-fisheye one, to test a pipeline's fisheye handling before the camera arrives.

## Tests

`python -m unittest discover -s slambench/tests -t .` (about a minute; the timing-check tests render images).
