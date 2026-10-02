import unittest

from slambench import robustness as rb


def rec(ate, poses=1000, jumps=0):
    return {'metrics': {'ate_yaw': {'rmse_m': ate}, 'poses': poses, 'jumps': jumps}}


class FailureRuleTests(unittest.TestCase):
    def test_small_changes_are_not_failures(self):
        self.assertIsNone(rb.is_failure(rec(1.0), rec(1.4)))
        self.assertIsNone(rb.is_failure(rec(1.0), rec(2.9)))

    def test_an_ate_blow_up_needs_both_the_ratio_and_the_margin(self):
        self.assertEqual(rb.is_failure(rec(1.0), rec(3.5)), 'ATE blow-up')
        self.assertIsNone(rb.is_failure(rec(0.05), rec(0.2)))      # 4x worse but only 15 cm: not a failure
        self.assertEqual(rb.is_failure(rec(0.05), rec(0.7)), 'ATE blow-up')

    def test_jumps_and_lost_poses_are_failures(self):
        self.assertEqual(rb.is_failure(rec(1.0), rec(1.0, jumps=1)), 'jump')
        self.assertEqual(rb.is_failure(rec(1.0), rec(1.0, poses=700)), 'lost poses')
        self.assertIsNone(rb.is_failure(rec(1.0), rec(1.0, poses=850)))

    def test_formatting_lists_each_condition(self):
        result = {'clean_ate_m': 1.0, 'seeds': 2, 'conditions': {'noise': {'ate': [1.1, 9.0], 'fails': 1, 'reasons': ['ATE blow-up']}}}
        text = rb.format_suite(result, 'x:')
        self.assertIn('fails 1/2', text)
        self.assertIn('ATE blow-up', text)


if __name__ == '__main__':
    unittest.main()
