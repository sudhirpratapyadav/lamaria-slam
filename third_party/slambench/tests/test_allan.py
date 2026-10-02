import tempfile
import unittest
from pathlib import Path

import numpy as np

from slambench.tools import allan_variance as av


def synthetic(rate=100., seconds=4000., noise=1e-3, walk=2e-4, bias=0.02, seed=0):
    """A rate signal with known white noise density (units/sqrt(Hz)), random walk (units/s/sqrt(Hz)) and constant bias."""
    rng = np.random.default_rng(seed)
    n = int(rate * seconds)
    dt = 1. / rate
    white = rng.normal(0, noise * np.sqrt(rate), n)
    rw = np.cumsum(rng.normal(0, walk * np.sqrt(dt), n))
    return np.arange(n) * dt, white + rw + bias


class AllanTests(unittest.TestCase):
    def test_white_noise_density_is_recovered(self):
        t, x = synthetic(walk=0.0, seconds=1200)
        taus, sigma = av.allan_deviation(x, 100.)
        self.assertAlmostEqual(av.noise_parameters(taus, sigma)['noise_density'], 1e-3, delta=0.06e-3)

    def test_random_walk_is_recovered_when_the_recording_is_long_enough(self):
        t, x = synthetic()
        taus, sigma = av.allan_deviation(x, 100.)
        p = av.noise_parameters(taus, sigma)
        self.assertAlmostEqual(p['noise_density'], 1e-3, delta=0.1e-3)
        self.assertIsNotNone(p['random_walk'])
        self.assertAlmostEqual(p['random_walk'], 2e-4, delta=0.6e-4)

    def test_short_recording_reports_no_random_walk_instead_of_a_wrong_one(self):
        t, x = synthetic(walk=0.0, seconds=120)
        taus, sigma = av.allan_deviation(x, 100.)
        self.assertIsNone(av.noise_parameters(taus, sigma)['random_walk'])

    def test_constant_bias_does_not_change_the_result(self):
        t, x = synthetic(walk=0.0, seconds=600, bias=0.0)
        _, y = synthetic(walk=0.0, seconds=600, bias=5.0)
        a = av.noise_parameters(*av.allan_deviation(x, 100.))['noise_density']
        b = av.noise_parameters(*av.allan_deviation(y, 100.))['noise_density']
        self.assertAlmostEqual(a, b, delta=0.02 * a)

    def test_full_pipeline_through_a_csv_with_unit_conversion(self):
        # gyro in deg/s and accel in g, as a datasheet would give them
        t, gx = synthetic(walk=0.0, seconds=600, noise=0.0028, bias=0.0)       # 2.8 mdps/sqrt(Hz) -> ICM-42688-P class
        _, gy = synthetic(walk=0.0, seconds=600, noise=0.0028, bias=0.0, seed=1)
        _, gz = synthetic(walk=0.0, seconds=600, noise=0.0028, bias=0.0, seed=2)
        _, ax = synthetic(walk=0.0, seconds=600, noise=70e-6, bias=0.0, seed=3)
        _, ay = synthetic(walk=0.0, seconds=600, noise=70e-6, bias=0.0, seed=4)
        _, az = synthetic(walk=0.0, seconds=600, noise=70e-6, bias=1.0, seed=5)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'imu.csv'
            np.savetxt(path, np.column_stack([t, gx, gy, gz, ax, ay, az]), delimiter=',', header='t,wx,wy,wz,ax,ay,az')
            tt, g, a = av.load_csv(path)
        result = av.analyse(tt, g, a, np.pi / 180, av.G)
        s = result['summary']
        self.assertAlmostEqual(s['gyroscope_noise_density'], 4.89e-5, delta=0.3e-5)       # rad/s/sqrt(Hz)
        self.assertAlmostEqual(s['accelerometer_noise_density'], 6.86e-4, delta=0.4e-4)   # m/s^2/sqrt(Hz)
        self.assertEqual(s['update_rate'], 100.0)
        self.assertIn('gyroscope_noise_density:', av.yaml_snippet(s, inflate_noise=5.0))
        self.assertIn('null', av.yaml_snippet(s))        # no random walk from a 10 minute log

    def test_gaps_are_reported(self):
        t, x = synthetic(walk=0.0, seconds=60)
        t = t.copy()
        t[3000:] += 1.0                       # a one second dropout
        result = av.analyse(t, np.column_stack([x, x, x]), np.column_stack([x, x, x]))
        self.assertEqual(result['gaps_over_2_5_periods'], 1)


if __name__ == '__main__':
    unittest.main()
