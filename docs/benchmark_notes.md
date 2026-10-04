# LaMAria notes

Sources: [site](https://lamaria.ethz.ch), [leaderboard](https://lamaria.ethz.ch/leaderboard), [documentation](https://lamaria.ethz.ch/slam_documentation), [code](https://github.com/cvg/lamaria), paper "Benchmarking Egocentric Visual-Inertial SLAM at City Scale" (ICCV 2025, arXiv 2509.26639).

## Download

Index pages at `https://cvg-data.inf.ethz.ch/lamaria/{raw_data,aria_calibrations,asl_folder,pinhole_calibrations,rosbag,ground_truth}/{training,test}/`. The official script: `python -m tools.download_lamaria --output_dir DIR --sequences R_01_easy --type asl`.

Training sizes in ASL form: R_01_easy 1.3 G, R_02_easy 1.2 G, R_03_easy 1.5 G, R_04_medium 2.3 G, R_05_medium 2.1 G, R_06_medium 3.1 G, R_07_medium 3.0 G, R_08_hard 5.2 G, R_09_hard 6.3 G, R_10_hard 7.7 G, R_11_5cp 3.8 G, R_12_10cp 7.8 G, R_13_15cp 13 G, sequence_1_19 8.6 G, sequence_1_20 9.1 G, sequence_2_11 8.6 G, sequence_2_12 12 G, sequence_3_17 15 G, sequence_3_18 14 G (and more).

## Resolved on first contact with the data (2026-10-02)

- The ASL download is **pinhole-undistorted** by COLMAP (758x572 left, 757x569 right, f about 241 px), not raw fisheye. Raw fisheye needs the `.vrs` files (0.9 to 3.7 GB each for our three) plus `projectaria_tools`; the `tools/vrs_to_asl_folder.py` script in `cvg/lamaria` writes a raw ASL folder from a `.vrs`.
- The benchmark uses only `imu-right` (1 kHz); the ASL `imu0` is that IMU, and the calibration body frame is that IMU, so each camera's `T_b_s` is `T_imu_cam`. Noise values in the JSON: acc 7.8e-4, gyro 1.7e-4, acc walk 6.4e-3, gyro walk 2.4e-4 (Kalibr units). Experiment 001 found the densities need inflating (x10) for OpenVINS.
- Pose recall is 2D (xy) error after the control-point Sim3 alignment, counted over all pseudo-GT keyframes; a keyframe without a submitted pose is a miss. The ATE evaluator rejects estimates spanning less than half the ground-truth duration.
- Controlled-set pseudo-GT files have one pose per image; comparing our IMU-frame poses directly scores better than converting to the left-camera frame, so submit `world_from_imu` as documented.
- Pseudo-GT body frames differ between the two sets (v4 X01, detected from angular rates): the controlled set's pGT is `world_from_imu`; the additional set's pGT is in the **left camera (cam0) frame**, 105.5 degrees from the IMU. The ATE evaluator uses positions only, so the 13 cm lever arm is noise against the metre-level ATE, and the control-point evaluator projects through the device calibration (`corresponding_sensor=imu`), so scores are frame-correct. The calibration `qvec` fields are xyzw, not COLMAP's wxyz. Any orientation comparison against the additional-set pGT must apply that frame first (`scripts/gyro_yaw_check.py` does).

## Open questions

- Fisheye versus pinhole input (needs the `.vrs` download).
- Why the sim3 scale is 2 to 4 % off in every surviving run of experiment 001.

## Published baselines on the public controlled set (paper Table 2, ATE RMSE in m, stereo + IMU rows)

Source: arXiv 2509.26639 Table 2 (read from the HTML version on 2026-10-02; it does not say whether each cell is one run or a mean). Sequences 1 to 13 = R_01_easy ... R_10_hard, R_11_5cp, R_12_10cp, R_13_15cp. Aria's SLAM is not in this table because the controlled-set pseudo-GT is derived from it.

| Method | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OpenVINS | 0.66 | 2.36 | 0.68 | 0.94 | 1.43 | 1.35 | 2.96 | 4.25 | 4.31 | 8.01 | 1.04 | 18.72 | 10.35 |
| OpenVINS + Maplab | 0.65 | 2.30 | 0.68 | 1.05 | 1.22 | 1.19 | 2.01 | 3.97 | 4.29 | 8.22 | 1.62 | 16.59 | 8.37 |
| OKVIS2 | 0.02 | 0.72 | 0.03 | 1.36 | 0.80 | 3.78 | fail | 6.81 | 5.32 | 7.06 | 1.85 | 16.55 | 6.65 |

The same metric is what the leaderboard reports for the controlled set, so our local ATE numbers are directly comparable to these rows. The main-set and additional-set metrics (score 2D, CP recall @ 1 m, pose recall @ 5 m) can only be computed locally on training sequences that observe control points (R_11, R_12, R_13 and the `sequence_*` additional set), none of which are downloaded yet. The website also evaluates uploaded training-set results with the official pipeline.

## Two devices in the training set (v4 X05, 2026-10-05)

The training sequences come from two Aria units, told apart by the md5 of `aria_calibrations/*.json`: device A (`cc5c2f57`) recorded 2_11, 2_12, 3_17, 3_18, 4_10, 4_11, 5_11, 5_12 and R_01 to R_07 and R_09 to R_13; device B (`5f4f20ee`) recorded 1_19, 1_20 and R_08. Their undistorted image sizes differ (758x572 / 757x569 against 780x584 / 776x590). The steady heading drift of the long walks occurs only on device A with landmarks hosted in cam0 (see `track_logs_v4/status.md`); device A's sim3 scale is 1 to 3 % low on every sequence, device B's is 1.00. The factory IMU models of both devices (scale, misalignment, bias; the ASL export ships raw IMU) are in `configs/aria_factory_imu/`.
