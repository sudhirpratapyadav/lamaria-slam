import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import numpy as np

from slambench import datasets, metrics, runner
from slambench.sysmon import Sampler
from slambench.tests.test_metrics import spiral


def make_dataset(root, with_reference=True):
    """A registry with one synthetic dataset: a flat closed loop as the reference."""
    ref = spiral(turns=2.0, climb=0.)
    recording = root / 'rec'
    recording.mkdir()
    (recording / 'stereo.csv').write_text('# t,l,r\n')
    (recording / 'imu.csv').write_text('# t\n')
    config = root / 'cfg'
    config.mkdir()
    metrics.write_tum(root / 'ref.tum', ref)
    entry = {'label': 'synthetic', 'recording': str(recording), 'config': str(config), 'has_loop': True}
    if with_reference:
        entry['reference'] = {'path': str(root / 'ref.tum'), 'format': 'tum', 'kind': 'synthetic', 'max_dt': 0.05}
    registry = root / 'datasets.json'
    registry.write_text(json.dumps({'synthetic': entry}))
    return registry, ref


# A stand-in SLAM system: writes the reference trajectory with a growing drift of 5 % of distance plus a small time-varying offset.
FAKE_SYSTEM = textwrap.dedent('''
    import sys, numpy as np
    from slambench import metrics
    ref = metrics.read_tum(sys.argv[1])
    out = ref.copy()
    s = metrics.cumulative_length(ref[:, 1:4])
    out[:, 1] += 0.05 * s
    metrics.write_tum(sys.argv[2], out)
''')


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry, self.ref = make_dataset(self.root)
        script = self.root / 'fake.py'
        script.write_text(FAKE_SYSTEM)
        self.spec = {'cmd': [sys.executable, str(script), str(self.root / 'ref.tum'), '{out}/traj.tum'], 'trajectory': '{out}/traj.tum', 'frame': 'body',
                     'env': {'PYTHONPATH': str(Path(__file__).resolve().parents[2])}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_end_to_end_with_an_external_system(self):
        record = runner.run('synthetic', 'command', 'fake', self.root / 'out', command_spec=self.spec, registry_path=self.registry)
        m = record['metrics']
        self.assertEqual(m['poses'], len(self.ref))
        self.assertGreater(m['ate_yaw']['rmse_m'], 1.0)                      # the injected drift is visible
        self.assertGreater(m['drift']['10m']['trans_pct'], 0.5)
        self.assertTrue(m['loop']['closed_loop'])
        self.assertGreater(m['loop']['est_gap_m'], 5.0)                      # the loop does not close because of the drift
        self.assertEqual(m['jumps'], 0)
        self.assertIn('wall_s', record['timing'])
        self.assertIn('samples', record['sysmon'])
        saved = json.loads((self.root / 'out' / 'synthetic' / 'command_fake' / 'result.json').read_text())
        self.assertEqual(saved['dataset'], 'synthetic')
        self.assertTrue((self.root / 'out' / 'synthetic' / 'command_fake' / 'trajectory.tum').exists())

    def test_table_lists_every_result_and_handles_missing_values(self):
        runner.run('synthetic', 'command', 'fake', self.root / 'out', command_spec=self.spec, registry_path=self.registry)
        text = runner.table(runner.collect(self.root / 'out'))
        self.assertIn('| synthetic | command | fake |', text)
        self.assertEqual(len(text.splitlines()), 3)
        self.assertIn('–', text)       # compute time is not reported by an external system

    def test_run_without_reference_still_reports_self_contained_measures(self):
        (self.root / 'sub').mkdir()
        registry, _ = make_dataset(self.root / 'sub', with_reference=False)
        record = runner.run('synthetic', 'command', 'fake', self.root / 'out2', command_spec=self.spec, registry_path=registry)
        self.assertNotIn('ate_yaw', record['metrics'])
        self.assertIn('loop', record['metrics'])
        self.assertIn('est_path_m', record['metrics'])

    def test_missing_dataset_files_give_a_clear_error(self):
        registry = json.loads(self.registry.read_text())
        registry['synthetic']['recording'] = str(self.root / 'nope')
        self.registry.write_text(json.dumps(registry))
        with self.assertRaises(FileNotFoundError):
            runner.run('synthetic', 'command', 'fake', self.root / 'out3', command_spec=self.spec, registry_path=self.registry)

    def test_unknown_dataset_and_system(self):
        with self.assertRaises(KeyError):
            runner.run('nope', 'command', 'x', self.root / 'o', command_spec=self.spec, registry_path=self.registry)
        with self.assertRaises(ValueError):
            runner.run('synthetic', 'mystery', 'x', self.root / 'o', registry_path=self.registry)


class DatasetTests(unittest.TestCase):
    def test_bundled_registry_entries_are_well_formed(self):
        registry = datasets.load_registry()
        self.assertIn('kimera_thoth', registry)
        for name, entry in registry.items():
            for key in ('label', 'recording', 'config'):
                self.assertIn(key, entry, name)

    def test_kimera_reference_and_frame_when_available(self):
        d = datasets.get('kimera_thoth')
        if not d.exists():
            self.skipTest('Kimera data not on this machine')
        ref = d.reference()
        self.assertEqual(ref.shape[1], 8)
        self.assertTrue(np.all(np.diff(ref[:, 0]) > 0))
        self.assertAlmostEqual(np.linalg.det(d.body_from_imu()[:3, :3]), 1.0, places=6)
        self.assertLess(metrics.loop_gap(ref)['est_gap_m'], 3.0)      # the ground truth is a closed loop

    def test_rosario_config_is_given_canonical_names(self):
        d = datasets.get('rosario05')
        if not (datasets.ROOT / 'configs/rosario_v2').exists():
            self.skipTest('Rosario config not present')
        with tempfile.TemporaryDirectory() as cache:
            cfg = d.config_dir(cache)
            for name in ('estimator.yaml', 'imucam.yaml', 'imu.yaml'):
                self.assertTrue((cfg / name).exists())
            text = (cfg / 'estimator.yaml').read_text()
            self.assertIn('relative_config_imu: "imu.yaml"', text)
            self.assertIn('relative_config_imucam: "imucam.yaml"', text)

    def test_add_recording_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / 'r.json'
            registry.write_text('{}')
            datasets.add_recording('mine', '/data/a', '/cfg/a', reference='/ref/a.tum', has_loop=True, registry_path=registry)
            entry = datasets.load_registry(registry)['mine']
            self.assertEqual(entry['recording'], '/data/a')
            self.assertEqual(entry['reference']['format'], 'tum')
            self.assertTrue(entry['has_loop'])


class SysmonTests(unittest.TestCase):
    def test_sampler_reports_cpu_and_memory(self):
        import subprocess
        import time
        sampler = Sampler(interval=0.1).start()
        burn = subprocess.Popen([sys.executable, '-c', 'import time\nend=time.time()+1.0\nwhile time.time()<end: sum(i*i for i in range(10000))'])
        time.sleep(1.3)          # the main thread sleeps, so the sampler is never starved; a child process does the burning
        burn.wait()
        summary = sampler.stop()
        self.assertGreaterEqual(summary['samples'], 3)
        self.assertGreater(summary['cpu_cores_max'], 0.5)       # system-wide, so the child's work counts
        self.assertGreater(summary['mem_used_mb_mean'], 100)

if __name__ == '__main__':
    unittest.main()


class ParallelSafetyTests(unittest.TestCase):
    def test_each_run_builds_its_own_config_directory(self):
        d = datasets.get('rosario05')
        if not (datasets.ROOT / 'configs/rosario_v2').exists():
            self.skipTest('Rosario config not present')
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first, second = d.config_dir(a), d.config_dir(b)
            self.assertNotEqual(first, second)
            self.assertTrue((first / 'estimator.yaml').exists())      # building the second must not disturb the first


class ReevaluateTests(unittest.TestCase):
    def test_saved_results_can_be_rescored_without_rerunning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry, ref = make_dataset(root)
            script = root / 'fake.py'
            script.write_text(FAKE_SYSTEM)
            spec = {'cmd': [sys.executable, str(script), str(root / 'ref.tum'), '{out}/traj.tum'], 'trajectory': '{out}/traj.tum', 'frame': 'body',
                    'env': {'PYTHONPATH': str(Path(__file__).resolve().parents[2])}}
            record = runner.run('synthetic', 'command', 'fake', root / 'out', command_spec=spec, registry_path=registry)
            path = root / 'out' / 'synthetic' / 'command_fake' / 'result.json'
            stale = json.loads(path.read_text())
            stale['metrics'] = {'poses': 1}                                   # pretend an older version of the metrics wrote this
            path.write_text(json.dumps(stale))
            self.assertEqual(runner.reevaluate(root / 'out', registry), 1)
            fresh = json.loads(path.read_text())
            self.assertIn('ate_sim3', fresh['metrics'])
            self.assertAlmostEqual(fresh['metrics']['ate_yaw']['rmse_m'], record['metrics']['ate_yaw']['rmse_m'], places=9)
            self.assertAlmostEqual(fresh['metrics']['ate_sim3']['scale'], 1 / 1.0, delta=0.06)     # a 5 % path-proportional drift is a small global scale change
