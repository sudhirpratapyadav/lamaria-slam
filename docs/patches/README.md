# Third-party patches

The clones under `third_party/` are git-ignored except OpenVINS (tracked). These diffs reproduce the local changes:

- `basalt-0f3b2b5.patch` (gitlab VladyslavUsenko/basalt @ 0f3b2b5): mapper saves its keyframe trajectory headless; `-Werror` removed; `realsense2` dropped from `vcpkg.json`. Build: `cmake --preset release` with the venv's CMake >= 3.24 and Ninja, `VCPKG_MAX_CONCURRENCY=2`, `-j2..3` (memory).
- `ORB_SLAM3-4452a3c.patch` (UZ-SLAMLab/ORB_SLAM3 @ 4452a3c): C++14 instead of C++11 in all CMakeLists, viewer disabled in the stereo-inertial EuRoC example. Needs Pangolin v0.9.1 built locally (`third_party/Pangolin/install`).
- OKVIS2 (smartroboticslab/okvis2 @ a2ea006): unmodified, built with `-DUSE_NN=OFF -DBUILD_ROS2=OFF`.
