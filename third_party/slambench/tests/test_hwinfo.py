import unittest

from slambench import hwinfo, runner


class HardwareInfoTests(unittest.TestCase):
    def test_reports_the_basics_on_this_machine(self):
        info = hwinfo.hardware_info()
        for key in ('machine', 'kernel', 'cpus', 'mem_gb'):
            self.assertIn(key, info)
        self.assertGreaterEqual(info['cpus'], 1)
        self.assertGreater(info['mem_gb'], 0.5)
        self.assertTrue(info.get('cpu_model'))

    def test_host_info_used_in_results_includes_hardware_and_python(self):
        info = runner.host_info()
        self.assertIn('cpu_model', info)
        self.assertIn('python', info)

    def test_cpu_model_parsing_of_an_arm_board(self):
        import tempfile
        from pathlib import Path
        text = 'processor\t: 0\nBogoMIPS\t: 48.00\nCPU implementer\t: 0x41\nCPU part\t: 0xd0b\n\nprocessor\t: 4\nCPU part\t: 0xd05\n'
        original = hwinfo._read
        try:
            hwinfo._read = lambda path: text if path == '/proc/cpuinfo' else original(path)
            self.assertEqual(hwinfo.cpu_model(), 'ARM core part 0xd05/0xd0b')      # an RK3588-style big.LITTLE mix is listed, not hidden
        finally:
            hwinfo._read = original


if __name__ == '__main__':
    unittest.main()
