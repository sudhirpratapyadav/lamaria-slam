import unittest

import numpy as np

from slambench.tools import make_fisheye as mf

K = np.array([[400., 0, 320.], [0, 400., 240.], [0, 0, 1.]])


class FisheyeMapTests(unittest.TestCase):
    def setUp(self):
        self.f = 300.
        self.x, self.y = mf.fisheye_maps(K, np.zeros(4), (640, 480), self.f)

    def test_the_optical_axis_maps_to_the_source_principal_point(self):
        # the fisheye centre is (319.5, 239.5), so pixel (320, 240) is half a pixel (0.5 / f rad) off the axis
        offset = 400.0 * np.tan(0.5 / self.f)
        self.assertAlmostEqual(float(self.x[240, 320]), 320.0 + offset, delta=0.01)
        self.assertAlmostEqual(float(self.y[240, 320]), 240.0 + offset, delta=0.01)
        self.assertAlmostEqual(float(self.x[239, 319]), 320.0 - offset, delta=0.01)

    def test_a_pixel_at_a_known_angle_maps_to_the_pinhole_projection_of_that_ray(self):
        theta = np.radians(25.0)                                 # equidistant: radius = f * theta
        u = 319.5 + self.f * theta                               # centre of a 640 px wide image is 319.5
        col = int(round(u))
        theta_actual = (col - 319.5) / self.f                    # use the exact angle of the sampled column
        expected = 400.0 * np.tan(theta_actual) + 320.0
        self.assertAlmostEqual(float(self.x[240, col]), expected, delta=0.5)

    def test_angles_beyond_ninety_degrees_are_marked_invalid(self):
        wide_x, _ = mf.fisheye_maps(K, np.zeros(4), (640, 480), 150.)         # corner angle = 400/150 rad = 153 degrees
        self.assertEqual(float(wide_x[0, 0]), -1.0)
        self.assertGreater(float(wide_x[240, 320]), 0)

    def test_source_distortion_is_applied_to_the_sampling_position(self):
        dist = np.array([0.1, 0.0, 0.0, 0.0])
        x_d, _ = mf.fisheye_maps(K, dist, (640, 480), self.f)
        col = 500
        self.assertGreater(float(x_d[240, col]), float(self.x[240, col]))     # positive k1 pushes the sample outward


if __name__ == '__main__':
    unittest.main()
