# Third-party patches

The clones under `third_party/` are git-ignored except OpenVINS (tracked). These diffs reproduce the local changes:

- `basalt-0f3b2b5.patch` (gitlab VladyslavUsenko/basalt @ 0f3b2b5): mapper saves its keyframe trajectory headless; `-Werror` removed; `realsense2` dropped from `vcpkg.json`; optional CLAHE at image load in the EuRoC reader (env `BASALT_CLAHE=<clip>`, 8x8 tiles, B16). Build: `cmake --preset release` with the venv's CMake >= 3.24 and Ninja, `VCPKG_MAX_CONCURRENCY=2`, `-j2..3` (memory).
- `ORB_SLAM3-4452a3c.patch` (UZ-SLAMLab/ORB_SLAM3 @ 4452a3c): C++14 instead of C++11 in all CMakeLists, viewer disabled in the stereo-inertial EuRoC example; bounds check on the example's IMU loop (it read past the IMU vector when an image lies after the last IMU sample, C03). Needs Pangolin v0.9.1 built locally (`third_party/Pangolin/install`).
- `okvis2-a2ea006.patch` (smartroboticslab/okvis2 @ a2ea006): optional CLAHE at image load in `DatasetReader.cpp` (env `OKVIS_CLAHE=<clip>`, A08). Built with `-DUSE_NN=OFF -DBUILD_ROS2=OFF`.
