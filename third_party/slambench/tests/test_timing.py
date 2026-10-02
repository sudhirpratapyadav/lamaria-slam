import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from slambench.tools import timing_check as tc

ROOT = Path(__file__).resolve().parents[2]
REAL = ROOT / 'webapp/recordings/20260927_115654_d455_capture_a7d755'


def simulate(offset_s, seconds=14., fps=30, imu_hz=200, seed=3, speed=1.0):
    """A purely rotating camera looking at a textured wall. The IMU stamp of a gyro sample is t_cam + offset (t_imu = t_cam + offset)."""
    rng = np.random.default_rng(seed)
    base = cv2.GaussianBlur((rng.random((480, 640)) * 255).astype(np.float32), (0, 0), 1.6)
    base = cv2.normalize(base, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    K = np.array([[420., 0, 320.], [0, 420., 240.], [0, 0, 1.]])
    sim_hz = 600
    n = int(seconds * sim_hz)
    t = np.arange(n) / sim_hz
    f = speed        # multiplies the oscillation frequencies: 1 = slow sweeps (0.2-0.4 Hz), 6 = brisk hand shaking (about 2 Hz)
    omega = np.column_stack([0.6 * np.sin(2 * np.pi * 0.31 * f * t) + 0.05, 0.5 * np.sin(2 * np.pi * 0.23 * f * t + 1.0), 0.4 * np.sin(2 * np.pi * 0.41 * f * t + 2.0)])
    rot = [np.eye(3)]
    for k in range(n - 1):
        rot.append(rot[-1] @ Rotation.from_rotvec(omega[k] / sim_hz).as_matrix())
    frame_idx = np.arange(0, n, sim_hz // fps)
    images = [cv2.warpPerspective(base, K @ rot[i] @ np.linalg.inv(K), (640, 480), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) for i in frame_idx]
    imu_idx = np.arange(0, n, sim_hz // imu_hz)
    imu_t = t[imu_idx] + offset_s                                  # stamped on the IMU clock
    gyro_mag = np.linalg.norm(omega[imu_idx], axis=1)
    return {'images': images, 'frame_times': t[frame_idx], 'imu_t': imu_t, 'gyro_mag': gyro_mag, 'camera': {'K': K, 'dist': np.zeros(4), 'model': 'radtan'}}


class SyntheticTimingTests(unittest.TestCase):
    def estimate(self, offset, speed=1.0):
        s = simulate(offset, speed=speed)
        speeds = tc.visual_rotation_speeds(s['images'], s['frame_times'], s['camera'])
        return tc.estimate_offset(s['frame_times'], speeds, s['imu_t'], s['gyro_mag'])

    def test_a_known_offset_is_recovered_with_a_strong_peak(self):
        for offset in (0.012, -0.020, 0.0):
            result = self.estimate(offset)
            self.assertIsNotNone(result)
            self.assertAlmostEqual(result['offset_s'], offset, delta=0.002, msg=offset)
            self.assertGreater(result['peak_correlation'], 0.9)

    def test_fast_rotation_makes_a_timing_error_much_easier_to_see_than_slow_rotation(self):
        # slow sweeps barely change when shifted by 25 ms, so they cannot reveal a timing error; brisk shaking can
        slow = self.estimate(0.025, speed=1.0)
        fast = self.estimate(0.025, speed=6.0)
        slow_gain = slow['peak_correlation'] - slow['correlation_at_zero_offset']
        fast_gain = fast['peak_correlation'] - fast['correlation_at_zero_offset']
        self.assertGreater(fast_gain, 5 * slow_gain)
        self.assertGreater(fast_gain, 0.1)
        self.assertAlmostEqual(fast['offset_s'], 0.025, delta=0.002)

    def test_rotation_from_bearings_recovers_a_known_rotation_despite_outliers(self):
        rng = np.random.default_rng(0)
        v0 = rng.normal(size=(300, 3))
        v0 /= np.linalg.norm(v0, axis=1, keepdims=True)
        true = Rotation.from_rotvec([0.02, -0.03, 0.01]).as_matrix()
        v1 = v0 @ true.T
        v1[:60] = rng.normal(size=(60, 3))                          # 20 % gross outliers
        v1 /= np.linalg.norm(v1, axis=1, keepdims=True)
        est = tc.rotation_from_bearings(v0, v1)
        self.assertLess(np.degrees(Rotation.from_matrix(est.T @ true).magnitude()), 0.2)

    def test_too_little_rotation_gives_no_answer_instead_of_a_wrong_one(self):
        s = simulate(0.0)
        speeds = np.full(len(s['frame_times']) - 1, 0.01)           # essentially stationary
        self.assertIsNone(tc.estimate_offset(s['frame_times'], speeds, s['imu_t'], s['gyro_mag']))


@unittest.skipUnless(REAL.exists(), 'hand-held D455 recording not on this machine')
class RealRecordingTimingTests(unittest.TestCase):
    def shifted(self, delta, tmp):
        tmp = Path(tmp)
        (tmp / 'left').symlink_to(REAL / 'left')
        (tmp / 'stereo.csv').write_text((REAL / 'stereo.csv').read_text())
        imu = np.loadtxt(REAL / 'imu.csv', delimiter=',', comments='#', ndmin=2)
        imu[:, 0] += delta
        np.savetxt(tmp / 'imu.csv', imu, delimiter=',', fmt='%.9f')
        return tc.check_recording(tmp, ROOT / 'configs/kimera_thoth', frames=700, start_frame=300)   # only the intrinsics file is used

    def test_shifting_the_imu_timestamps_shifts_the_estimate_by_the_same_amount(self):
        # the intrinsics of another D455 recording are used, which is fine for rotation-only angle estimation of a similar camera
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, tempfile.TemporaryDirectory() as c:
            base = self.shifted(0.0, a)['offset_ms']
            plus = self.shifted(0.020, b)['offset_ms']
            minus = self.shifted(-0.015, c)['offset_ms']
        self.assertAlmostEqual(plus - base, 20.0, delta=1.5)
        self.assertAlmostEqual(minus - base, -15.0, delta=1.5)


if __name__ == '__main__':
    unittest.main()
