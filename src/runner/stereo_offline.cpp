#include "core/VioManager.h"
#include "core/VioManagerOptions.h"
#include "state/State.h"
#include "utils/opencv_yaml_parse.h"
#include "utils/print.h"
#include <opencv2/opencv.hpp>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

// Input: header timestamps in seconds, gyro rad/s, acceleration m/s^2.
// Output: TUM poses of the IMU in the world at the image (camera-clock) timestamp; Hamilton xyzw quaternion.
int main(int argc, char **argv) {
  try {
    if (argc != 4 && argc != 5) throw std::runtime_error("Usage: stereo_offline CONFIG EXTRACTED_DIR OUTPUT_DIR [SKIP_FRAMES]");
    const size_t skip_frames = argc == 5 ? std::stoul(argv[4]) : 0;
    const std::filesystem::path data(argv[2]), out(argv[3]);
    std::filesystem::create_directories(out);
    std::filesystem::create_directories(out / "tracking_snapshots");
    auto parser = std::make_shared<ov_core::YamlParser>(argv[1]);
    std::string verbosity = "WARNING";
    parser->parse_config("verbosity", verbosity, false);
    ov_core::Printer::setPrintLevel(verbosity);
    ov_msckf::VioManagerOptions opts;
    opts.print_and_load(parser);
    bool stationary_guard = false;
    double accel_noise_floor = 0;
    parser->parse_config("stationary_guard_v1", stationary_guard, false);
    parser->parse_config("imu_accel_noise_floor", accel_noise_floor, false);
    if (stationary_guard || accel_noise_floor != 0)
      throw std::runtime_error("This baseline runner does not implement the web tracking profiles; use scripts/replay_diagnostics.py with the web native adapter");
    if (!parser->successful() || opts.state_options.num_cameras != 2)
      throw std::runtime_error("Need a valid two-camera calibration");
    opts.num_opencv_threads = 2;
    opts.use_multi_threading_pubs = false;
    opts.use_multi_threading_subs = false;
    // Divergence detection + re-initialisation (runner-level, see track_logs_v1 experiment 009).
    // 0 disables a check. On divergence the estimator is rebuilt, re-fed the last seconds of IMU,
    // and its new local frame is stitched onto the last good pose so the output stays continuous.
    double reinit_max_velocity = 0, reinit_max_jump = 0, reinit_imu_replay_s = 3.0, reinit_grace_s = 1.0;
    parser->parse_config("reinit_max_velocity", reinit_max_velocity, false);
    parser->parse_config("reinit_grace_s", reinit_grace_s, false);  // no checks this long after an (re)initialisation
    parser->parse_config("reinit_max_jump", reinit_max_jump, false);
    parser->parse_config("reinit_imu_replay_s", reinit_imu_replay_s, false);
    auto make_system = [&]() { return std::make_shared<ov_msckf::VioManager>(opts); };
    auto sys = make_system();
    Eigen::Isometry3d world_from_segment = Eigen::Isometry3d::Identity(), last_good = Eigen::Isometry3d::Identity();
    bool have_last_good = false, pending_stitch = false;
    size_t reinits = 0;
    double init_time = -1;  // image time of the current estimator's first pose
    std::ifstream imu_file(data / "imu.csv"), cam_file(data / "stereo.csv");
    if (!imu_file || !cam_file) throw std::runtime_error("Missing imu.csv or stereo.csv");
    std::vector<ov_core::ImuData> imus;
    std::string line;
    double last_imu = -1;
    while (std::getline(imu_file, line)) {
      if (line.empty() || line[0] == '#') continue;
      std::replace(line.begin(), line.end(), ',', ' ');
      std::istringstream row(line);
      ov_core::ImuData m;
      if (!(row >> m.timestamp >> m.wm.x() >> m.wm.y() >> m.wm.z() >> m.am.x() >> m.am.y() >> m.am.z())
          || !m.wm.allFinite() || !m.am.allFinite() || !std::isfinite(m.timestamp) || m.timestamp <= last_imu)
        throw std::runtime_error("Invalid or nonmonotonic IMU row");
      imus.push_back(m); last_imu = m.timestamp;
    }
    if (imus.empty()) throw std::runtime_error("Empty IMU input");
    std::ofstream trajectory(out / "trajectory.tum"), timings(out / "frame_times.csv");
    std::ofstream diagnostics(out / "state_diagnostics.csv");
    diagnostics << "# timestamp,cam_to_imu_offset_s,bgx,bgy,bgz,bax,bay,baz\n" << std::setprecision(12);
    trajectory << "# timestamp tx ty tz qx qy qz qw; IMU frame, image timestamp\n" << std::fixed << std::setprecision(9);
    timings << "# timestamp,processing_seconds,initialized,msckf_update_points,slam_points\n" << std::setprecision(12);
    size_t idx = 0, frames = 0, poses = 0, skipped = 0, skipped_start = 0;
    double last_cam = -1, last_state = -1;
    const auto start = std::chrono::steady_clock::now();
    while (std::getline(cam_file, line)) {
      if (line.empty() || line[0] == '#') continue;
      std::replace(line.begin(), line.end(), ',', ' ');
      std::istringstream row(line);
      double timestamp;
      std::string left, right;
      if (!(row >> timestamp >> left >> right) || timestamp <= last_cam)
        throw std::runtime_error("Invalid or nonmonotonic stereo row");
      last_cam = timestamp;
      // Start-frame offset: the only way to get "different seeds" from a deterministic estimator.
      if (skipped_start < skip_frames) { skipped_start++; continue; }
      const double dt = sys->get_state()->_calib_dt_CAMtoIMU->value()(0);
      const double target = timestamp + dt;
      if (target < imus.front().timestamp || target >= imus.back().timestamp) { skipped++; continue; }
      // Include one IMU sample past the camera exposure for endpoint interpolation.
      while (idx < imus.size() && imus[idx].timestamp <= target) sys->feed_measurement_imu(imus[idx++]);
      if (idx < imus.size()) sys->feed_measurement_imu(imus[idx++]);
      ov_core::CameraData cam;
      cam.timestamp = timestamp;
      cam.sensor_ids = {0, 1};
      for (const auto &name : {left, right}) {
        auto img = cv::imread((data / name).string(), cv::IMREAD_GRAYSCALE);
        if (img.empty()) throw std::runtime_error("Cannot read image: " + name);
        if (opts.downsample_cameras) cv::pyrDown(img, img);
        const auto model = opts.camera_intrinsics.at(cam.images.size());
        if (img.cols > model->w() || img.rows > model->h())
          throw std::runtime_error("Image larger than calibration: " + name);
        // Smaller images (LaMAria pinhole: 757x569 right vs 758x572 left) are padded at the
        // bottom/right so intrinsics stay valid; the padding is masked out (255 = ignore).
        cv::Mat mask = cv::Mat::zeros(model->h(), model->w(), CV_8UC1);
        if (img.cols != model->w() || img.rows != model->h()) {
          mask.setTo(255);
          mask(cv::Rect(0, 0, img.cols, img.rows)).setTo(0);
          cv::copyMakeBorder(img, img, 0, model->h() - img.rows, 0, model->w() - img.cols, cv::BORDER_CONSTANT, 0);
        }
        cam.images.push_back(img);
        cam.masks.push_back(mask);
      }
      const auto before = std::chrono::steady_clock::now();
      sys->feed_measurement_camera(cam);
      const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - before).count();
      timings << timestamp << ',' << seconds << ',' << sys->initialized() << ','
              << sys->get_good_features_MSCKF().size() << ',' << sys->get_features_SLAM().size() << '\n';
      frames++;
      const auto state = sys->get_state();
      if (sys->initialized() && state->_timestamp > last_state) {
        const auto p_raw = state->_imu->pos();
        Eigen::Quaterniond q_raw(state->_imu->Rot().transpose());
        const double speed = state->_imu->vel().norm();
        Eigen::Isometry3d T_seg = Eigen::Isometry3d::Identity();
        T_seg.linear() = q_raw.normalized().toRotationMatrix(); T_seg.translation() = p_raw;
        if (last_state < 0) init_time = state->_timestamp;
        if (pending_stitch) {
          // first pose of the rebuilt estimator: map its frame onto the last good pose
          world_from_segment = last_good * T_seg.inverse();
          pending_stitch = false;
        }
        const bool in_grace = state->_timestamp - init_time < reinit_grace_s;
        Eigen::Isometry3d T = world_from_segment * T_seg;
        const bool nonfinite = !p_raw.allFinite() || !q_raw.coeffs().allFinite();
        const bool too_fast = !in_grace && reinit_max_velocity > 0 && speed > reinit_max_velocity;
        const bool jumped = !in_grace && reinit_max_jump > 0 && have_last_good && (T.translation() - last_good.translation()).norm() > reinit_max_jump;
        if (nonfinite || too_fast || jumped) {
          reinits++;
          std::cout << "reinit #" << reinits << " at " << std::fixed << std::setprecision(3) << timestamp
                    << (nonfinite ? " non-finite" : too_fast ? " speed " : " jump ") << (too_fast ? speed : 0.0) << std::endl;
          sys = make_system();
          pending_stitch = have_last_good;  // if nothing good yet, the new segment simply starts at identity
          last_state = -1;
          // replay recent IMU so the dynamic initialiser has a window immediately
          size_t j = idx;
          while (j > 0 && imus[idx - 1].timestamp - imus[j - 1].timestamp < reinit_imu_replay_s) j--;
          for (; j < idx; j++) sys->feed_measurement_imu(imus[j]);
          continue;
        }
        last_good = T; have_last_good = true;
        const Eigen::Vector3d p = T.translation();
        const Eigen::Quaterniond q(T.linear());
        trajectory << state->_timestamp << ' '
                   << p.x() << ' ' << p.y() << ' ' << p.z() << ' '
                   << q.x() << ' ' << q.y() << ' ' << q.z() << ' ' << q.w() << '\n';
        const auto bg = state->_imu->bias_g(), ba = state->_imu->bias_a();
        diagnostics << state->_timestamp << ',' << state->_calib_dt_CAMtoIMU->value()(0) << ','
                    << bg.x() << ',' << bg.y() << ',' << bg.z() << ','
                    << ba.x() << ',' << ba.y() << ',' << ba.z() << '\n';
        last_state = state->_timestamp; poses++;
      }
      if (poses && (poses == 1 || frames % 450 == 0)) {
        auto viz = sys->get_historical_viz_image();
        if (!viz.empty()) cv::imwrite((out / "tracking_snapshots" / (std::to_string(frames) + ".jpg")).string(), viz);
      }
      if (frames % 150 == 0) std::cout << "frames=" << frames << " poses=" << poses << std::endl;
    }
    const double wall = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    std::ofstream stats(out / "run_stats.json");
    stats << "{\"frames\":" << frames << ",\"poses\":" << poses << ",\"imu_samples\":" << idx
          << ",\"skipped_no_imu_coverage\":" << skipped << ",\"skipped_start_frames\":" << skipped_start << ",\"reinits\":" << reinits << ",\"wall_seconds\":" << wall << "}\n";
    std::cout << "Finished: " << frames << " stereo pairs, " << poses << " poses, " << wall << " seconds" << std::endl;
    if (!poses) throw std::runtime_error("Estimator never initialized");
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
  return 0;
}
