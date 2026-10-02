# LaMAria notes

Sources: [site](https://lamaria.ethz.ch), [leaderboard](https://lamaria.ethz.ch/leaderboard), [documentation](https://lamaria.ethz.ch/slam_documentation), [code](https://github.com/cvg/lamaria), paper "Benchmarking Egocentric Visual-Inertial SLAM at City Scale" (ICCV 2025, arXiv 2509.26639).

## Download

Index pages at `https://cvg-data.inf.ethz.ch/lamaria/{raw_data,aria_calibrations,asl_folder,pinhole_calibrations,rosbag,ground_truth}/{training,test}/`. The official script: `python -m tools.download_lamaria --output_dir DIR --sequences R_01_easy --type asl`.

Training sizes in ASL form: R_01_easy 1.3 G, R_02_easy 1.2 G, R_03_easy 1.5 G, R_04_medium 2.3 G, R_05_medium 2.1 G, R_06_medium 3.1 G, R_07_medium 3.0 G, R_08_hard 5.2 G, R_09_hard 6.3 G, R_10_hard 7.7 G, R_11_5cp 3.8 G, R_12_10cp 7.8 G, R_13_15cp 13 G, sequence_1_19 8.6 G, sequence_1_20 9.1 G, sequence_2_11 8.6 G, sequence_2_12 12 G, sequence_3_17 15 G, sequence_3_18 14 G (and more).

## Open questions (resolve when the first data arrives)

- Pinhole (undistorted) versus raw fisheye input: the ASL downloads come with pinhole calibration; OpenVINS supports a fisheye (equidistant) model on raw data. Which is better is an experiment.
- Which IMU of the two to use, and what the noise parameters should be.
- Exactly how the pose-recall metric treats missing poses (it should punish them; always output a pose).
