import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from slambench import metrics as m


def spiral(n=3000, hz=10., turns=3., radius=20., climb=3.):
    """A smooth ~380 m path with heading along the direction of travel."""
    t = np.arange(n) / hz
    a = np.linspace(0, turns * 2 * np.pi, n)
    p = np.column_stack([radius * np.cos(a), radius * np.sin(a), climb * np.sin(a / 3)])
    d = np.gradient(p, axis=0)
    yaw = np.arctan2(d[:, 1], d[:, 0])
    q = Rotation.from_euler('z', yaw).as_quat()
    return np.column_stack([t, p, q])


def transformed(traj, rot, trans, scale=1.0):
    out = traj.copy()
    out[:, 1:4] = scale * traj[:, 1:4] @ rot.T + trans
    out[:, 4:8] = (Rotation.from_matrix(rot) * Rotation.from_quat(traj[:, 4:8])).as_quat()
    return out


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.ref = spiral()

    def test_yaw_and_translation_offset_gives_zero_error(self):
        est = transformed(self.ref, Rotation.from_euler('z', 40, degrees=True).as_matrix(), np.array([5., -3., 1.]))
        for mode in ('yaw', 'se3'):
            self.assertLess(m.ate(est, self.ref, mode)['rmse_m'], 1e-9)

    def test_tilt_error_is_visible_to_yaw_alignment_but_not_se3(self):
        est = transformed(self.ref, Rotation.from_euler('xyz', [3, -2, 25], degrees=True).as_matrix(), np.array([1., 2., 3.]))
        self.assertLess(m.ate(est, self.ref, 'se3')['rmse_m'], 1e-9)
        self.assertGreater(m.ate(est, self.ref, 'yaw')['rmse_m'], 0.5)   # a real gravity-direction error must not be hidden

    def test_scale_error_needs_sim3(self):
        est = transformed(self.ref, np.eye(3), np.zeros(3), scale=1.02)
        self.assertGreater(m.ate(est, self.ref, 'se3')['rmse_m'], 0.1)
        sim3 = m.ate(est, self.ref, 'sim3')
        self.assertLess(sim3['rmse_m'], 1e-9)
        self.assertAlmostEqual(sim3['scale'], 1 / 1.02, places=6)      # the factor that brings the estimate to the reference's metric size
        self.assertIsNone(m.ate(est, self.ref, 'se3')['scale'])

    def test_noise_level_is_recovered(self):
        rng = np.random.default_rng(0)
        est = self.ref.copy()
        est[:, 1:4] += rng.normal(0, 0.05, (len(est), 3))
        result = m.ate(est, self.ref, 'yaw')
        self.assertAlmostEqual(result['rmse_m'], 0.05 * np.sqrt(3), delta=0.01)


class DriftTests(unittest.TestCase):
    def test_one_percent_scale_error_is_one_percent_drift_on_a_straight_path(self):
        n = 2000
        t = np.arange(n) / 10.
        ref = np.column_stack([t, np.linspace(0, 300, n), np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n), np.ones(n)])
        est = transformed(ref, np.eye(3), np.zeros(3), scale=1.01)
        drift = m.drift_per_distance(est, ref, deltas=(10., 50.))
        for key in ('10m', '50m'):
            self.assertAlmostEqual(drift[key]['trans_pct'], 1.0, delta=0.02)
            self.assertLess(drift[key]['rot_deg_per_100m'], 0.01)

    def test_drift_on_a_curved_path_is_measured_against_the_chord(self):
        # on a circle of radius R the chord of a path segment delta is 2R sin(delta/2R) < delta, so a 1% scale error reads below 1%
        ref = spiral(climb=0.)
        est = transformed(ref, np.eye(3), np.zeros(3), scale=1.01)
        drift = m.drift_per_distance(est, ref, deltas=(50.,))
        expected = 100. * 0.01 * (2 * 20 * np.sin(50. / 40.)) / 50.
        self.assertAlmostEqual(drift['50m']['trans_pct'], expected, delta=0.03)

    def test_drift_is_independent_of_global_alignment(self):
        ref = spiral()
        rot = Rotation.from_euler('xyz', [10, 20, 30], degrees=True).as_matrix()
        est = transformed(ref, rot, np.array([100., 50., -20.]))
        drift = m.drift_per_distance(est, ref, deltas=(10.,))
        self.assertLess(drift['10m']['trans_pct'], 1e-6)

    def test_rotation_drift_is_reported(self):
        ref = spiral()
        est = ref.copy()
        s = m.cumulative_length(ref[:, 1:4])
        est[:, 4:8] = (Rotation.from_euler('z', np.radians(0.01) * s) * Rotation.from_quat(ref[:, 4:8])).as_quat()  # 0.01 deg per metre
        drift = m.drift_per_distance(est, ref, deltas=(50.,))
        self.assertAlmostEqual(drift['50m']['rot_deg_per_100m'], 1.0, delta=0.15)

    def test_local_error_over_one_second(self):
        ref = spiral()
        est = transformed(ref, np.eye(3), np.zeros(3), scale=1.1)
        speed = np.linalg.norm(np.diff(ref[:, 1:4], axis=0), axis=1).mean() * 10.
        self.assertAlmostEqual(m.rpe_time(est, ref, 1.0)['rmse_m'], 0.1 * speed, delta=0.03 * speed)


class LoopAndTrackingTests(unittest.TestCase):
    def test_loop_gap_measures_end_point_drift(self):
        ref = spiral(turns=2.0, climb=0.)     # flat, so it starts and ends at the same point
        est = ref.copy()
        est[:, 1:4] += np.linspace(0, 1, len(est))[:, None] * np.array([6., 0., 8.])    # drift of 10 m by the end
        gap = m.loop_gap(est, ref)
        self.assertAlmostEqual(gap['est_gap_m'], 10.0, delta=0.5)
        self.assertTrue(gap['closed_loop'])

    def test_a_partial_run_is_not_judged_as_a_loop(self):
        ref = spiral(turns=2.0, climb=0.)                 # a closed loop overall
        partial = ref[:len(ref) // 3]                     # but the run only covers the first third
        result = m.evaluate(partial, ref)
        self.assertFalse(result['loop']['closed_loop'])   # the covered part of the reference does not return to its start
        self.assertTrue(m.evaluate(ref, ref)['loop']['closed_loop'])

    def test_open_path_is_not_reported_as_closed(self):
        ref = spiral(turns=1.5)
        self.assertFalse(m.loop_gap(ref, ref)['closed_loop'])

    def test_jump_detection(self):
        est = spiral()
        est[1500:, 1] += 50.0
        self.assertEqual(m.jumps(est), 1)
        self.assertEqual(m.jumps(spiral()), 0)

    def test_association_respects_max_dt(self):
        ref = spiral()
        est = ref.copy()
        est[:, 0] += 0.04
        self.assertEqual(len(m.associate(est, ref, 0.05)[0]), len(est))
        self.assertEqual(len(m.associate(est, ref, 0.01)[0]), 0)


class FrameAndIoTests(unittest.TestCase):
    def test_imu_to_body_moves_origin_by_the_lever_arm(self):
        ref = spiral()
        t_base_imu = np.eye(4)
        t_base_imu[:3, 3] = [0.0, 0.3, 0.0]      # body origin is 0.3 m to the side of the IMU
        body = m.imu_to_body(ref, t_base_imu)
        offsets = np.linalg.norm(body[:, 1:4] - ref[:, 1:4], axis=1)
        np.testing.assert_allclose(offsets, 0.3, atol=1e-9)

    def test_evaluate_with_frame_conversion_recovers_the_reference(self):
        body_ref = spiral()
        t_base_imu = np.eye(4)
        t_base_imu[:3, 3] = [0.1, -0.2, 0.05]
        t_imu_base = np.linalg.inv(t_base_imu)
        imu = body_ref.copy()          # build the IMU trajectory whose body-frame conversion equals body_ref
        rot = Rotation.from_quat(body_ref[:, 4:8])
        imu[:, 1:4] = body_ref[:, 1:4] - (rot * Rotation.from_matrix(t_imu_base[:3, :3]).inv()).apply(t_imu_base[:3, 3])
        imu[:, 4:8] = (rot * Rotation.from_matrix(t_imu_base[:3, :3]).inv()).as_quat()
        result = m.evaluate(imu, body_ref, body_from_imu=t_base_imu)
        self.assertLess(result['ate_se3']['rmse_m'], 1e-6)

    def test_tum_round_trip_and_sorting(self):
        ref = spiral(n=50)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'a.tum'
            m.write_tum(path, ref[::-1])
            back = m.read_tum(path)
        np.testing.assert_allclose(back, ref, atol=1e-8)

    def test_evaluate_full_set(self):
        ref = spiral()
        est = transformed(ref, np.eye(3), np.zeros(3), scale=1.005)
        result = m.evaluate(est, ref)
        for key in ('ate_yaw', 'ate_se3', 'drift', 'rpe_1s', 'loop', 'jumps', 'coverage_fraction'):
            self.assertIn(key, result)
        self.assertAlmostEqual(result['coverage_fraction'], 1.0)


if __name__ == '__main__':
    unittest.main()
