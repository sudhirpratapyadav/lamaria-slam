// lamaria-slam v4 (G01): non-causal global visual-inertial bundle adjustment.
//
// Input (a problem folder written by scripts/vi_ba_prepare.py from a Basalt run with BASALT_OBS_DUMP):
//   problem.json   cameras (pinhole fx fy cx cy, T_i_c), IMU noise, gravity
//   keyframes.txt  idx t_ns tx ty tz qx qy qz qw vx vy vz          (initial states from the VIO)
//   imu.txt        t_ns gx gy gz ax ay az
//   obs.bin        records {int32 kf, int32 cam, int32 id, float x, y, vx, vy} (pixel, pixel velocity px/s)
// Output: kf_poses.tum, kf_states.txt, report.json in the output folder.
//
// States: per keyframe pose (SE3), velocity, gyro and accelerometer bias; per landmark an inverse
// depth along the bearing of its first observation (host keyframe + camera); one calibration block
// (T_i_c0, T_i_c1, intrinsics, a common camera time offset) that is constant unless the config frees it.
// Residuals: pinhole reprojection (Huber), Basalt preintegrated IMU between consecutive keyframes
// with first-order bias correction, bias random walk, weak bias prior on the first keyframe.
// The first keyframe pose fixes the gauge; scale comes from the IMU.
#include <ceres/ceres.h>
#include <nlohmann/json.hpp>
// Sophus's ensure macro formats Eigen matrices of ceres::Jet, which this Eigen/Ceres pair cannot print;
// the checks are not needed here (all inputs are finite, unit quaternions are maintained by Sophus).
#include <sophus/common.hpp>
#undef SOPHUS_ENSURE
#define SOPHUS_ENSURE(expr, ...) ((void)0)
#include <sophus/se3.hpp>
#include <basalt/imu/preintegration.h>

#include <Eigen/Dense>
#include <algorithm>
#include <array>
#include <filesystem>
#include <iomanip>
#include <set>
#include <sstream>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

using json = nlohmann::json;
using SE3 = Sophus::SE3d;
using SO3 = Sophus::SO3d;
using Vec3 = Eigen::Vector3d;
using Vec2 = Eigen::Vector2d;

namespace {

constexpr int kCalibSize = 23;  // T_i_c0 (7), T_i_c1 (7), intr0 (4), intr1 (4), td (1)
constexpr int kCalibLocal = 21;  // 6 + 6 + 4 + 4 + 1
inline int calibPoseOff(int cam) { return 7 * cam; }
inline int calibIntrOff(int cam) { return 14 + 4 * cam; }
constexpr int kCalibTdOff = 22;

struct Config {
  int min_obs_kfs = 2;
  double pixel_sigma = 1.0, huber_px = 1.0, init_outlier_px = 20.0;
  std::vector<double> outlier_px{5.0, 3.0};
  int max_iterations = 30, threads = 8;
  double gyro_noise_scale = 1.0, accel_noise_scale = 1.0, gyro_walk_scale = 1.0, accel_walk_scale = 1.0, g = 9.81;
  double bias_prior_bg = 0.01, bias_prior_ba = 0.1;
  bool stereo_in_host = true;
  bool calib_extr = false, calib_extr_rot_only = true, calib_intr = false, calib_td = false;
  double far_depth_m = 50.0;
  double td_init_ms = 0.0;  // starting (or, when time_offset is false, fixed) camera time offset
};

Config loadConfig(const std::string& path) {
  Config c;
  std::ifstream f(path);
  if (!f) throw std::runtime_error("cannot open config " + path);
  json j; f >> j;
  c.min_obs_kfs = j.value("min_obs_kfs", c.min_obs_kfs);
  c.pixel_sigma = j.value("pixel_sigma", c.pixel_sigma);
  c.huber_px = j.value("huber_px", c.huber_px);
  c.init_outlier_px = j.value("init_outlier_px", c.init_outlier_px);
  if (j.contains("outlier_px")) c.outlier_px = j["outlier_px"].get<std::vector<double>>();
  c.max_iterations = j.value("max_iterations", c.max_iterations);
  c.threads = j.value("threads", c.threads);
  // noise scales multiply the run's calib.json values (which already carry the VIO's x20); one key for both or per sensor
  c.gyro_noise_scale = c.accel_noise_scale = j.value("imu_noise_scale", 1.0);
  c.gyro_walk_scale = c.accel_walk_scale = j.value("imu_walk_scale", 1.0);
  c.gyro_noise_scale = j.value("gyro_noise_scale", c.gyro_noise_scale);
  c.accel_noise_scale = j.value("accel_noise_scale", c.accel_noise_scale);
  c.gyro_walk_scale = j.value("gyro_walk_scale", c.gyro_walk_scale);
  c.accel_walk_scale = j.value("accel_walk_scale", c.accel_walk_scale);
  c.g = j.value("g", c.g);
  if (j.contains("bias_prior_std")) { c.bias_prior_bg = j["bias_prior_std"][0]; c.bias_prior_ba = j["bias_prior_std"][1]; }
  c.stereo_in_host = j.value("stereo_in_host", c.stereo_in_host);
  c.far_depth_m = j.value("far_depth_m", c.far_depth_m);
  c.td_init_ms = j.value("td_init_ms", c.td_init_ms);
  if (j.contains("calib")) {
    const auto& k = j["calib"];
    c.calib_extr = k.value("extrinsics", false);
    c.calib_extr_rot_only = k.value("extr_rotation_only", true);
    c.calib_intr = k.value("intrinsics", false);
    c.calib_td = k.value("time_offset", false);
  }
  return c;
}

struct Cam { double fx, fy, cx, cy; int w, h; SE3 T_i_c; };
struct ImuNoise { Vec3 accel_std, gyro_std, accel_walk, gyro_walk; double rate; };

struct KF {
  int64_t t_ns;
  std::array<double, 7> pose;  // Sophus SE3 data: qx qy qz qw tx ty tz
  Vec3 v, bg, ba;
  SE3 T() const { return Eigen::Map<const SE3>(pose.data()); }
  void setT(const SE3& T) { Eigen::Map<SE3>(pose.data()) = T; }
};

struct Obs { int kf, cam, id; float x, y, vx, vy; bool active = true; };
struct ImuSample { int64_t t_ns; Vec3 gyro, accel; };

struct Landmark {
  int host_obs = -1;  // index into obs
  double rho = 0.02;
  std::vector<int> obs;  // indices into obs (host included)
  bool valid = true;
};

// ---------- parameterisations ----------
struct SE3Plus {
  template <class T>
  bool operator()(const T* x, const T* d, T* y) const {
    Eigen::Map<const Sophus::SE3<T>> X(x);
    Eigen::Map<const Eigen::Matrix<T, 6, 1>> D(d);
    Eigen::Map<Sophus::SE3<T>> Y(y);
    Y = Sophus::SE3<T>::exp(D) * X;
    return true;
  }
};

struct CalibPlus {
  bool extr, rot_only, intr, td;
  template <class T>
  bool operator()(const T* x, const T* d, T* y) const {
    for (int i = 0; i < kCalibSize; i++) y[i] = x[i];
    for (int c = 0; c < 2; c++) {
      if (!extr) continue;
      Eigen::Map<const Sophus::SE3<T>> X(x + calibPoseOff(c));
      Eigen::Matrix<T, 6, 1> D = Eigen::Map<const Eigen::Matrix<T, 6, 1>>(d + 6 * c);
      if (rot_only) D.template head<3>().setZero();
      Eigen::Map<Sophus::SE3<T>> Y(y + calibPoseOff(c));
      Y = X * Sophus::SE3<T>::exp(D);  // perturbation in the camera frame
    }
    if (intr)
      for (int c = 0; c < 2; c++)
        for (int i = 0; i < 4; i++) y[calibIntrOff(c) + i] = x[calibIntrOff(c) + i] + d[12 + 4 * c + i];
    if (td) y[kCalibTdOff] = x[kCalibTdOff] + d[20];
    return true;
  }
};

// ---------- residuals ----------
template <class T>
inline Eigen::Matrix<T, 3, 1> bearing(const T* intr, T u, T v) {
  return Eigen::Matrix<T, 3, 1>((u - intr[2]) / intr[0], (v - intr[3]) / intr[1], T(1));
}

// Observation of a landmark in another keyframe (same or other camera).
struct Reproj {
  Vec2 h_px, h_v, o_px, o_v;  // host / observed pixel and pixel velocity (px/s)
  int h_cam, o_cam;
  double inv_sigma;
  template <class T>
  bool operator()(const T* pose_h, const T* pose_o, const T* rho, const T* calib, T* res) const {
    Eigen::Map<const Sophus::SE3<T>> T_w_h(pose_h), T_w_o(pose_o);
    Eigen::Map<const Sophus::SE3<T>> T_i_ch(calib + calibPoseOff(h_cam)), T_i_co(calib + calibPoseOff(o_cam));
    const T td = calib[kCalibTdOff];
    const T* in_h = calib + calibIntrOff(h_cam);
    const T* in_o = calib + calibIntrOff(o_cam);
    Eigen::Matrix<T, 3, 1> f_h = bearing(in_h, T(h_px.x()) - td * T(h_v.x()), T(h_px.y()) - td * T(h_v.y()));
    Sophus::SE3<T> T_co_ch = T_i_co.inverse() * T_w_o.inverse() * T_w_h * T_i_ch;
    Eigen::Matrix<T, 3, 1> p = T_co_ch.so3() * f_h + rho[0] * T_co_ch.translation();
    T z = p.z() > T(1e-6) ? p.z() : T(1e-6);
    res[0] = (in_o[0] * p.x() / z + in_o[2] - (T(o_px.x()) - td * T(o_v.x()))) * T(inv_sigma);
    res[1] = (in_o[1] * p.y() / z + in_o[3] - (T(o_px.y()) - td * T(o_v.y()))) * T(inv_sigma);
    return true;
  }
};

// Stereo observation in the host keyframe: the pose cancels.
struct ReprojStereo {
  Vec2 h_px, h_v, o_px, o_v;
  int h_cam, o_cam;
  double inv_sigma;
  template <class T>
  bool operator()(const T* rho, const T* calib, T* res) const {
    Eigen::Map<const Sophus::SE3<T>> T_i_ch(calib + calibPoseOff(h_cam)), T_i_co(calib + calibPoseOff(o_cam));
    const T td = calib[kCalibTdOff];
    const T* in_h = calib + calibIntrOff(h_cam);
    const T* in_o = calib + calibIntrOff(o_cam);
    Eigen::Matrix<T, 3, 1> f_h = bearing(in_h, T(h_px.x()) - td * T(h_v.x()), T(h_px.y()) - td * T(h_v.y()));
    Sophus::SE3<T> T_co_ch = T_i_co.inverse() * T_i_ch;
    Eigen::Matrix<T, 3, 1> p = T_co_ch.so3() * f_h + rho[0] * T_co_ch.translation();
    T z = p.z() > T(1e-6) ? p.z() : T(1e-6);
    res[0] = (in_o[0] * p.x() / z + in_o[2] - (T(o_px.x()) - td * T(o_v.x()))) * T(inv_sigma);
    res[1] = (in_o[1] * p.y() / z + in_o[3] - (T(o_px.y()) - td * T(o_v.y()))) * T(inv_sigma);
    return true;
  }
};

// Basalt preintegrated IMU between keyframes 0 and 1 (residual as in basalt/imu/preintegration.h).
struct ImuFactor {
  double dt;
  SO3 dR; Vec3 dv, dp;
  Eigen::Matrix<double, 9, 3> J_bg, J_ba;  // rows: p (0..2), R (3..5), v (6..8)
  Vec3 bg_lin, ba_lin, g;
  Eigen::Matrix<double, 9, 9> sqrt_info;
  template <class T>
  bool operator()(const T* pose0, const T* v0, const T* bg0, const T* ba0, const T* pose1, const T* v1, T* res) const {
    using V3 = Eigen::Matrix<T, 3, 1>;
    Eigen::Map<const Sophus::SE3<T>> T0(pose0), T1(pose1);
    Eigen::Map<const V3> V0(v0), V1(v1), BG(bg0), BA(ba0);
    V3 dbg = BG - bg_lin.cast<T>(), dba = BA - ba_lin.cast<T>();
    Eigen::Matrix<T, 9, 1> cbg = J_bg.cast<T>() * dbg, cba = J_ba.cast<T>() * dba;
    Sophus::SO3<T> R0inv = T0.so3().inverse();
    V3 gT = g.cast<T>();
    V3 tmp = R0inv * (T1.translation() - T0.translation() - V0 * T(dt) - gT * T(0.5 * dt * dt));
    Eigen::Matrix<T, 9, 1> r;
    r.template segment<3>(0) = tmp - (dp.cast<T>() + cbg.template segment<3>(0) + cba.template segment<3>(0));
    r.template segment<3>(3) = (Sophus::SO3<T>::exp(cbg.template segment<3>(3)) * dR.cast<T>() * T1.so3().inverse() * T0.so3()).log();
    V3 tmp2 = R0inv * (V1 - V0 - gT * T(dt));
    r.template segment<3>(6) = tmp2 - (dv.cast<T>() + cbg.template segment<3>(6) + cba.template segment<3>(6));
    Eigen::Map<Eigen::Matrix<T, 9, 1>> R(res);
    R = sqrt_info.cast<T>() * r;
    return true;
  }
};

struct BiasWalk {
  Vec3 inv_std_bg, inv_std_ba;
  template <class T>
  bool operator()(const T* bg0, const T* ba0, const T* bg1, const T* ba1, T* res) const {
    for (int i = 0; i < 3; i++) {
      res[i] = (bg1[i] - bg0[i]) * T(inv_std_bg[i]);
      res[3 + i] = (ba1[i] - ba0[i]) * T(inv_std_ba[i]);
    }
    return true;
  }
};

struct BiasPrior {
  double inv_bg, inv_ba;
  template <class T>
  bool operator()(const T* bg, const T* ba, T* res) const {
    for (int i = 0; i < 3; i++) { res[i] = bg[i] * T(inv_bg); res[3 + i] = ba[i] * T(inv_ba); }
    return true;
  }
};

// ---------- problem data ----------
struct Problem {
  Config cfg;
  std::vector<Cam> cams;
  ImuNoise imu_noise;
  std::vector<KF> kfs;
  std::vector<Obs> obs;
  std::vector<ImuSample> imu;
  std::unordered_map<int, Landmark> lms;  // by track id
  std::array<double, kCalibSize> calib{};
  std::array<double, kCalibSize> calib0{};
  std::vector<std::unique_ptr<basalt::IntegratedImuMeasurement<double>>> preint;  // per consecutive kf pair
};

SE3 se3FromJson(const json& a) {
  Eigen::Quaterniond q(a[6], a[3], a[4], a[5]);
  return SE3(q.normalized(), Vec3(a[0], a[1], a[2]));
}

void loadProblem(const std::string& dir, Problem& P) {
  {
    std::ifstream f(dir + "/problem.json");
    if (!f) throw std::runtime_error("no problem.json in " + dir);
    json j; f >> j;
    for (const auto& c : j["cams"]) {
      Cam cam{c["fx"], c["fy"], c["cx"], c["cy"], c["w"], c["h"], se3FromJson(c["T_i_c"])};
      P.cams.push_back(cam);
    }
    if (P.cams.size() != 2) throw std::runtime_error("expect two cameras");
    const auto& n = j["imu"];
    auto v3 = [](const json& a) { return Vec3(a[0], a[1], a[2]); };
    P.imu_noise = {v3(n["accel_noise_std"]), v3(n["gyro_noise_std"]), v3(n["accel_bias_std"]), v3(n["gyro_bias_std"]), n["rate"]};
  }
  {
    std::ifstream f(dir + "/keyframes.txt");
    std::string line;
    while (std::getline(f, line)) {
      if (line.empty() || line[0] == '#') continue;
      std::istringstream ss(line);
      int idx; KF k; double tx, ty, tz, qx, qy, qz, qw;
      ss >> idx >> k.t_ns >> tx >> ty >> tz >> qx >> qy >> qz >> qw >> k.v.x() >> k.v.y() >> k.v.z();
      k.setT(SE3(Eigen::Quaterniond(qw, qx, qy, qz).normalized(), Vec3(tx, ty, tz)));
      k.bg.setZero(); k.ba.setZero();
      if ((int)P.kfs.size() != idx) throw std::runtime_error("keyframe indices must be 0..n-1 in order");
      P.kfs.push_back(k);
    }
  }
  {
    std::ifstream f(dir + "/imu.txt");
    std::string line;
    while (std::getline(f, line)) {
      if (line.empty() || line[0] == '#') continue;
      std::istringstream ss(line);
      ImuSample s;
      ss >> s.t_ns >> s.gyro.x() >> s.gyro.y() >> s.gyro.z() >> s.accel.x() >> s.accel.y() >> s.accel.z();
      P.imu.push_back(s);
    }
  }
  {
    std::ifstream f(dir + "/obs.bin", std::ios::binary);
    struct Rec { int32_t kf, cam, id; float x, y, vx, vy; };
    Rec r;
    while (f.read(reinterpret_cast<char*>(&r), sizeof(r))) {
      if (r.kf < 0 || r.kf >= (int)P.kfs.size() || r.cam < 0 || r.cam > 1) continue;
      P.obs.push_back({r.kf, r.cam, r.id, r.x, r.y, r.vx, r.vy, true});
    }
  }
  // calibration block
  for (int c = 0; c < 2; c++) {
    Eigen::Map<SE3>(P.calib.data() + calibPoseOff(c)) = P.cams[c].T_i_c;
    P.calib[calibIntrOff(c) + 0] = P.cams[c].fx; P.calib[calibIntrOff(c) + 1] = P.cams[c].fy;
    P.calib[calibIntrOff(c) + 2] = P.cams[c].cx; P.calib[calibIntrOff(c) + 3] = P.cams[c].cy;
  }
  P.calib[kCalibTdOff] = P.cfg.td_init_ms * 1e-3;
  P.calib0 = P.calib;
}

SE3 camPose(const Problem& P, int kf, int cam) {
  return P.kfs[kf].T() * Eigen::Map<const SE3>(P.calib.data() + calibPoseOff(cam));
}

Vec3 bearingD(const Problem& P, const Obs& o) {
  const double* in = P.calib.data() + calibIntrOff(o.cam);
  return Vec3((o.x - in[2]) / in[0], (o.y - in[3]) / in[1], 1.0);
}

// depth along the host ray from a second view; negative when behind or degenerate
double twoViewDepth(const SE3& T_w_h, const Vec3& f_h, const SE3& T_w_o, const Vec3& f_o) {
  Vec3 oh = T_w_h.translation(), dh = T_w_h.so3() * f_h;
  Vec3 oo = T_w_o.translation(), dob = T_w_o.so3() * f_o;
  // minimise |oh + s dh - (oo + t dob)|
  Eigen::Matrix<double, 3, 2> A; A.col(0) = dh; A.col(1) = -dob;
  Vec3 b = oo - oh;
  Eigen::Matrix2d N = A.transpose() * A;
  if (N.determinant() < 1e-10) return -1;
  Vec2 st = N.ldlt().solve(A.transpose() * b);
  if (st(1) <= 0) return -1;
  return st(0);
}

void buildLandmarks(Problem& P) {
  P.lms.clear();
  std::unordered_map<int, std::vector<int>> by_id;
  for (int i = 0; i < (int)P.obs.size(); i++) by_id[P.obs[i].id].push_back(i);
  int n_single = 0;
  for (auto& kv : by_id) {
    auto& idx = kv.second;
    std::sort(idx.begin(), idx.end(), [&](int a, int b) {
      return std::make_pair(P.obs[a].kf, P.obs[a].cam) < std::make_pair(P.obs[b].kf, P.obs[b].cam);
    });
    std::set<int> kfset;
    for (int i : idx) kfset.insert(P.obs[i].kf);
    bool stereo_only = kfset.size() == 1 && idx.size() >= 2 && P.cfg.stereo_in_host;
    if ((int)kfset.size() < P.cfg.min_obs_kfs && !stereo_only) { n_single++; continue; }
    Landmark lm;
    lm.host_obs = idx[0];
    lm.obs = idx;
    // initial inverse depth: median two-view depth over the other observations
    const Obs& h = P.obs[lm.host_obs];
    SE3 T_w_h = camPose(P, h.kf, h.cam);
    Vec3 f_h = bearingD(P, h);
    std::vector<double> depths;
    for (int i : idx) {
      if (i == lm.host_obs) continue;
      const Obs& o = P.obs[i];
      double d = twoViewDepth(T_w_h, f_h, camPose(P, o.kf, o.cam), bearingD(P, o));
      if (d > 0.1) depths.push_back(d);
    }
    if (depths.empty()) lm.rho = 1.0 / P.cfg.far_depth_m;
    else { std::nth_element(depths.begin(), depths.begin() + depths.size() / 2, depths.end()); lm.rho = 1.0 / depths[depths.size() / 2]; }
    P.lms.emplace(kv.first, std::move(lm));
  }
  std::cout << "landmarks: " << P.lms.size() << " (tracks dropped for too few keyframes: " << n_single << ")" << std::endl;
}

// Reprojection error in pixels of one observation at the current state (host observation: 0).
double reprojErrorPx(const Problem& P, const Landmark& lm, const Obs& o) {
  const Obs& h = P.obs[lm.host_obs];
  if (&h == &o) return 0.0;
  double td = P.calib[kCalibTdOff];
  const double* in_h = P.calib.data() + calibIntrOff(h.cam);
  const double* in_o = P.calib.data() + calibIntrOff(o.cam);
  Vec3 f_h((h.x - td * h.vx - in_h[2]) / in_h[0], (h.y - td * h.vy - in_h[3]) / in_h[1], 1.0);
  SE3 T_co_ch = camPose(P, o.kf, o.cam).inverse() * camPose(P, h.kf, h.cam);
  Vec3 p = T_co_ch.so3() * f_h + lm.rho * T_co_ch.translation();
  if (p.z() <= 1e-6) return 1e9;
  double u = in_o[0] * p.x() / p.z() + in_o[2], v = in_o[1] * p.y() / p.z() + in_o[3];
  return std::hypot(u - (o.x - td * o.vx), v - (o.y - td * o.vy));
}

struct GateStats { long kept = 0, dropped = 0, kept_stereo = 0, dropped_stereo = 0; long lm_dropped = 0; };

GateStats removeOutliers(Problem& P, double thr_px) {
  GateStats s;
  for (auto& kv : P.lms) {
    Landmark& lm = kv.second;
    if (!lm.valid) continue;
    for (int i : lm.obs) {
      Obs& o = P.obs[i];
      if (!o.active || i == lm.host_obs) continue;
      bool stereo = o.cam != P.obs[lm.host_obs].cam;
      double e = reprojErrorPx(P, lm, o);
      if (e > thr_px) { o.active = false; s.dropped++; if (stereo) s.dropped_stereo++; }
      else { s.kept++; if (stereo) s.kept_stereo++; }
    }
    // still enough support?
    std::set<int> kfset; int n_active = 0;
    for (int i : lm.obs) if (P.obs[i].active) { kfset.insert(P.obs[i].kf); n_active++; }
    bool stereo_only = kfset.size() == 1 && n_active >= 2 && P.cfg.stereo_in_host;
    if (((int)kfset.size() < P.cfg.min_obs_kfs && !stereo_only) || n_active < 2) {
      lm.valid = false; s.lm_dropped++;
      for (int i : lm.obs) P.obs[i].active = false;
    }
  }
  return s;
}

void preintegrate(Problem& P) {
  P.preint.clear();
  const double sr = std::sqrt(P.imu_noise.rate);
  Vec3 accel_cov = (P.imu_noise.accel_std * sr * P.cfg.accel_noise_scale).array().square();
  Vec3 gyro_cov = (P.imu_noise.gyro_std * sr * P.cfg.gyro_noise_scale).array().square();
  size_t k = 0;
  for (size_t i = 0; i + 1 < P.kfs.size(); i++) {
    int64_t t0 = P.kfs[i].t_ns, t1 = P.kfs[i + 1].t_ns;
    auto m = std::make_unique<basalt::IntegratedImuMeasurement<double>>(t0, P.kfs[i].bg, P.kfs[i].ba);
    while (k < P.imu.size() && P.imu[k].t_ns <= t0) k++;
    size_t j = k;
    while (j < P.imu.size() && P.imu[j].t_ns <= t1) {
      basalt::ImuData<double> d; d.t_ns = P.imu[j].t_ns; d.accel = P.imu[j].accel; d.gyro = P.imu[j].gyro;
      m->integrate(d, accel_cov, gyro_cov);
      j++;
    }
    if (m->get_start_t_ns() + m->get_dt_ns() < t1 && j < P.imu.size()) {
      basalt::ImuData<double> d; d.t_ns = t1; d.accel = P.imu[j].accel; d.gyro = P.imu[j].gyro;
      m->integrate(d, accel_cov, gyro_cov);
    }
    P.preint.push_back(std::move(m));
  }
}

struct SolveResult { double cost0, cost1; int iterations; std::string termination; double seconds; };

SolveResult solveOnce(Problem& P, bool verbose) {
  ceres::Problem problem;
  const double inv_sigma = 1.0 / P.cfg.pixel_sigma;
  auto* se3_param = new ceres::AutoDiffLocalParameterization<SE3Plus, 7, 6>();
  bool calib_free = P.cfg.calib_extr || P.cfg.calib_intr || P.cfg.calib_td;
  ceres::LocalParameterization* calib_param = nullptr;
  if (calib_free) calib_param = new ceres::AutoDiffLocalParameterization<CalibPlus, kCalibSize, kCalibLocal>(
                                    new CalibPlus{P.cfg.calib_extr, P.cfg.calib_extr_rot_only, P.cfg.calib_intr, P.cfg.calib_td});
  problem.AddParameterBlock(P.calib.data(), kCalibSize, calib_param);
  if (!calib_free) problem.SetParameterBlockConstant(P.calib.data());
  for (auto& k : P.kfs) {
    problem.AddParameterBlock(k.pose.data(), 7, se3_param);
    problem.AddParameterBlock(k.v.data(), 3);
    problem.AddParameterBlock(k.bg.data(), 3);
    problem.AddParameterBlock(k.ba.data(), 3);
  }
  problem.SetParameterBlockConstant(P.kfs[0].pose.data());

  auto* ordering = new ceres::ParameterBlockOrdering;
  long n_rep = 0, n_stereo = 0;
  ceres::LossFunction* loss = new ceres::HuberLoss(P.cfg.huber_px / P.cfg.pixel_sigma);
  for (auto& kv : P.lms) {
    Landmark& lm = kv.second;
    if (!lm.valid) continue;
    const Obs& h = P.obs[lm.host_obs];
    problem.AddParameterBlock(&lm.rho, 1);
    problem.SetParameterLowerBound(&lm.rho, 0, 1e-4);  // 10 km
    problem.SetParameterUpperBound(&lm.rho, 0, 10.0);  // 10 cm
    ordering->AddElementToGroup(&lm.rho, 0);
    for (int i : lm.obs) {
      const Obs& o = P.obs[i];
      if (!o.active || i == lm.host_obs) continue;
      if (o.kf == h.kf) {
        if (o.cam == h.cam) continue;  // duplicate observation of the same track in one image
        auto* f = new ceres::AutoDiffCostFunction<ReprojStereo, 2, 1, kCalibSize>(new ReprojStereo{
            Vec2(h.x, h.y), Vec2(h.vx, h.vy), Vec2(o.x, o.y), Vec2(o.vx, o.vy), h.cam, o.cam, inv_sigma});
        problem.AddResidualBlock(f, loss, &lm.rho, P.calib.data());
        n_stereo++;
      } else {
        auto* f = new ceres::AutoDiffCostFunction<Reproj, 2, 7, 7, 1, kCalibSize>(new Reproj{
            Vec2(h.x, h.y), Vec2(h.vx, h.vy), Vec2(o.x, o.y), Vec2(o.vx, o.vy), h.cam, o.cam, inv_sigma});
        problem.AddResidualBlock(f, loss, P.kfs[h.kf].pose.data(), P.kfs[o.kf].pose.data(), &lm.rho, P.calib.data());
        if (o.cam != h.cam) n_stereo++;
      }
      n_rep++;
    }
  }
  for (auto& k : P.kfs) {
    ordering->AddElementToGroup(k.pose.data(), 1);
    ordering->AddElementToGroup(k.v.data(), 1);
    ordering->AddElementToGroup(k.bg.data(), 1);
    ordering->AddElementToGroup(k.ba.data(), 1);
  }
  ordering->AddElementToGroup(P.calib.data(), 1);

  // IMU factors
  Vec3 g(0, 0, -P.cfg.g);
  for (size_t i = 0; i + 1 < P.kfs.size(); i++) {
    const auto& m = *P.preint[i];
    if (m.get_dt_ns() <= 0) continue;
    auto* fac = new ImuFactor;
    fac->dt = m.get_dt_ns() * 1e-9;
    fac->dR = m.getDeltaState().T_w_i.so3();
    fac->dp = m.getDeltaState().T_w_i.translation();
    fac->dv = m.getDeltaState().vel_w_i;
    fac->J_bg = m.get_d_state_d_bg();
    fac->J_ba = m.get_d_state_d_ba();
    fac->bg_lin = P.kfs[i].bg; fac->ba_lin = P.kfs[i].ba;
    fac->g = g;
    fac->sqrt_info = m.get_sqrt_cov_inv();
    auto* f = new ceres::AutoDiffCostFunction<ImuFactor, 9, 7, 3, 3, 3, 7, 3>(fac);
    problem.AddResidualBlock(f, nullptr, P.kfs[i].pose.data(), P.kfs[i].v.data(), P.kfs[i].bg.data(), P.kfs[i].ba.data(),
                             P.kfs[i + 1].pose.data(), P.kfs[i + 1].v.data());
    double sdt = std::sqrt(fac->dt);
    auto* w = new BiasWalk{(P.imu_noise.gyro_walk * P.cfg.gyro_walk_scale * sdt).cwiseInverse(),
                           (P.imu_noise.accel_walk * P.cfg.accel_walk_scale * sdt).cwiseInverse()};
    problem.AddResidualBlock(new ceres::AutoDiffCostFunction<BiasWalk, 6, 3, 3, 3, 3>(w), nullptr,
                             P.kfs[i].bg.data(), P.kfs[i].ba.data(), P.kfs[i + 1].bg.data(), P.kfs[i + 1].ba.data());
  }
  problem.AddResidualBlock(new ceres::AutoDiffCostFunction<BiasPrior, 6, 3, 3>(new BiasPrior{1.0 / P.cfg.bias_prior_bg, 1.0 / P.cfg.bias_prior_ba}),
                           nullptr, P.kfs[0].bg.data(), P.kfs[0].ba.data());

  std::cout << "problem: " << P.kfs.size() << " keyframes, " << n_rep << " reprojection residuals (" << n_stereo
            << " cross-camera), " << P.preint.size() << " IMU factors, calib " << (calib_free ? "free" : "fixed") << std::endl;

  ceres::Solver::Options opt;
  opt.linear_solver_type = ceres::SPARSE_SCHUR;
  opt.sparse_linear_algebra_library_type = ceres::SUITE_SPARSE;
  opt.linear_solver_ordering.reset(ordering);
  opt.num_threads = P.cfg.threads;
  opt.max_num_iterations = P.cfg.max_iterations;
  opt.function_tolerance = 1e-6;
  opt.minimizer_progress_to_stdout = verbose;
  ceres::Solver::Summary summary;
  ceres::Solve(opt, &problem, &summary);
  std::cout << summary.BriefReport() << std::endl;
  return {summary.initial_cost, summary.final_cost, (int)summary.iterations.size(), ceres::TerminationTypeToString(summary.termination_type), summary.total_time_in_seconds};
}

json calibReport(const Problem& P) {
  json r;
  for (int c = 0; c < 2; c++) {
    SE3 T0 = Eigen::Map<const SE3>(P.calib0.data() + calibPoseOff(c)), T1 = Eigen::Map<const SE3>(P.calib.data() + calibPoseOff(c));
    SE3 d = T0.inverse() * T1;
    json cj;
    cj["rot_delta_deg"] = {d.so3().log().x() * 180 / M_PI, d.so3().log().y() * 180 / M_PI, d.so3().log().z() * 180 / M_PI};
    cj["rot_delta_norm_deg"] = d.so3().log().norm() * 180 / M_PI;
    cj["trans_delta_mm"] = {d.translation().x() * 1e3, d.translation().y() * 1e3, d.translation().z() * 1e3};
    cj["intr"] = {P.calib[calibIntrOff(c)], P.calib[calibIntrOff(c) + 1], P.calib[calibIntrOff(c) + 2], P.calib[calibIntrOff(c) + 3]};
    cj["intr_delta"] = {P.calib[calibIntrOff(c)] - P.calib0[calibIntrOff(c)], P.calib[calibIntrOff(c) + 1] - P.calib0[calibIntrOff(c) + 1],
                        P.calib[calibIntrOff(c) + 2] - P.calib0[calibIntrOff(c) + 2], P.calib[calibIntrOff(c) + 3] - P.calib0[calibIntrOff(c) + 3]};
    r["cam" + std::to_string(c)] = cj;
  }
  r["td_ms"] = P.calib[kCalibTdOff] * 1e3;
  return r;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 4) {
    std::cerr << "usage: vi_ba PROBLEM_DIR CONFIG_JSON OUT_DIR [--verbose]" << std::endl;
    return 2;
  }
  std::string pdir = argv[1], cfg_path = argv[2], out = argv[3];
  bool verbose = argc > 4 && std::string(argv[4]) == "--verbose";
  auto t_start = std::chrono::steady_clock::now();
  Problem P;
  P.cfg = loadConfig(cfg_path);
  loadProblem(pdir, P);
  std::cout << "loaded " << P.kfs.size() << " keyframes, " << P.obs.size() << " observations, " << P.imu.size() << " IMU samples" << std::endl;
  std::vector<Vec3> p_init; for (auto& k : P.kfs) p_init.push_back(k.T().translation());
  buildLandmarks(P);
  json report;
  report["config"] = cfg_path;
  report["n_keyframes"] = P.kfs.size();
  report["n_obs_total"] = P.obs.size();
  // gross outliers at the initial state
  {
    GateStats s = removeOutliers(P, P.cfg.init_outlier_px);
    std::cout << "initial gate " << P.cfg.init_outlier_px << " px: kept " << s.kept << " dropped " << s.dropped << " (stereo kept "
              << s.kept_stereo << " dropped " << s.dropped_stereo << "), landmarks dropped " << s.lm_dropped << std::endl;
    report["rounds"].push_back({{"gate_px", P.cfg.init_outlier_px}, {"kept", s.kept}, {"dropped", s.dropped}, {"stereo_kept", s.kept_stereo},
                                {"stereo_dropped", s.dropped_stereo}, {"lm_dropped", s.lm_dropped}, {"stage", "initial"}});
  }
  for (size_t round = 0; round <= P.cfg.outlier_px.size(); round++) {
    preintegrate(P);
    SolveResult r = solveOnce(P, verbose);
    json rj = {{"cost0", r.cost0}, {"cost1", r.cost1}, {"iterations", r.iterations}, {"termination", r.termination}, {"seconds", r.seconds}};
    if (round < P.cfg.outlier_px.size()) {
      GateStats s = removeOutliers(P, P.cfg.outlier_px[round]);
      std::cout << "gate " << P.cfg.outlier_px[round] << " px: kept " << s.kept << " dropped " << s.dropped << " (stereo kept " << s.kept_stereo
                << " dropped " << s.dropped_stereo << "), landmarks dropped " << s.lm_dropped << std::endl;
      rj["gate_px"] = P.cfg.outlier_px[round]; rj["kept"] = s.kept; rj["dropped"] = s.dropped; rj["stereo_kept"] = s.kept_stereo;
      rj["stereo_dropped"] = s.dropped_stereo; rj["lm_dropped"] = s.lm_dropped;
    }
    rj["calib"] = calibReport(P);
    report["rounds"].push_back(rj);
    std::cout << "calib: " << calibReport(P).dump() << std::endl;
  }
  // final residual statistics
  {
    std::vector<double> e, es;
    for (auto& kv : P.lms) {
      const Landmark& lm = kv.second;
      if (!lm.valid) continue;
      for (int i : lm.obs) {
        const Obs& o = P.obs[i];
        if (!o.active || i == lm.host_obs) continue;
        double v = reprojErrorPx(P, lm, o);
        e.push_back(v);
        if (o.cam != P.obs[lm.host_obs].cam) es.push_back(v);
      }
    }
    auto med = [](std::vector<double> v) { if (v.empty()) return 0.0; std::nth_element(v.begin(), v.begin() + v.size() / 2, v.end()); return v[v.size() / 2]; };
    auto rms = [](const std::vector<double>& v) { double s = 0; for (double x : v) s += x * x; return v.empty() ? 0.0 : std::sqrt(s / v.size()); };
    report["final"] = {{"n_obs", e.size()}, {"median_px", med(e)}, {"rms_px", rms(e)}, {"n_stereo", es.size()}, {"stereo_median_px", med(es)}, {"stereo_rms_px", rms(es)}};
    long n_lm = 0; for (auto& kv : P.lms) if (kv.second.valid) n_lm++;
    report["final"]["n_landmarks"] = n_lm;
    std::cout << "final: " << report["final"].dump() << std::endl;
  }
  report["calib"] = calibReport(P);
  {
    std::vector<double> d; for (size_t i = 0; i < P.kfs.size(); i++) d.push_back((P.kfs[i].T().translation() - p_init[i]).norm());
    double mx = *std::max_element(d.begin(), d.end()); std::nth_element(d.begin(), d.begin() + d.size() / 2, d.end());
    report["pose_change_m"] = {{"median", d[d.size() / 2]}, {"max", mx}, {"end", (P.kfs.back().T().translation() - p_init.back()).norm()}};
    std::cout << "pose change vs VIO (m): " << report["pose_change_m"].dump() << std::endl;
  }
  // biases
  {
    Vec3 bg_mean = Vec3::Zero(), ba_mean = Vec3::Zero();
    for (auto& k : P.kfs) { bg_mean += k.bg; ba_mean += k.ba; }
    bg_mean /= P.kfs.size(); ba_mean /= P.kfs.size();
    report["bias_mean"] = {{"bg_deg_s", {bg_mean.x() * 180 / M_PI, bg_mean.y() * 180 / M_PI, bg_mean.z() * 180 / M_PI}},
                           {"ba", {ba_mean.x(), ba_mean.y(), ba_mean.z()}}};
  }
  std::filesystem::create_directories(out);
  {
    std::ofstream f(out + "/kf_poses.tum");
    f << "# timestamp tx ty tz qx qy qz qw; IMU frame; vi_ba keyframes\n";
    for (auto& k : P.kfs) {
      SE3 T = k.T();
      Eigen::Quaterniond q = T.unit_quaternion();
      f << std::fixed << std::setprecision(9) << k.t_ns * 1e-9 << " " << T.translation().x() << " " << T.translation().y() << " " << T.translation().z()
        << " " << q.x() << " " << q.y() << " " << q.z() << " " << q.w() << "\n";
    }
  }
  {
    std::ofstream f(out + "/kf_states.txt");
    f << "# t_s vx vy vz bgx bgy bgz bax bay baz\n";
    for (auto& k : P.kfs)
      f << std::fixed << std::setprecision(9) << k.t_ns * 1e-9 << " " << k.v.transpose() << " " << k.bg.transpose() << " " << k.ba.transpose() << "\n";
  }
  report["seconds_total"] = std::chrono::duration<double>(std::chrono::steady_clock::now() - t_start).count();
  std::ofstream(out + "/report.json") << report.dump(1) << std::endl;
  std::cout << "done in " << report["seconds_total"] << " s" << std::endl;
  return 0;
}
