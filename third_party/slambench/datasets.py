"""Dataset registry: where a recording, its estimator config and its reference trajectory live."""
import json
import re
import shutil
from pathlib import Path

import numpy as np

from .metrics import read_tum

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = Path(__file__).with_name('datasets.json')


def load_registry(path=None):
    return json.loads(Path(path or REGISTRY).read_text())


def save_registry(registry, path=None):
    Path(path or REGISTRY).write_text(json.dumps(registry, indent=2) + '\n')


def _resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_reference(spec):
    path = _resolve(spec['path'])
    if spec['format'] == 'tum':
        return read_tum(path)
    if spec['format'] == 'kimera_csv':      # #timestamp_kf(ns),x,y,z,qw,qx,qy,qz
        rows = [line.split(',') for line in path.read_text().splitlines() if line and not line.startswith('#')]
        return np.array([[int(r[0]) / 1e9, *map(float, r[1:4]), *map(float, r[5:8]), float(r[4])] for r in rows])
    raise ValueError(f"Unknown reference format {spec['format']}")


class Dataset:
    def __init__(self, name, entry):
        self.name, self.entry = name, entry

    @property
    def recording(self):
        return _resolve(self.entry['recording'])

    def has_reference(self):
        return bool(self.entry.get('reference'))

    def reference(self):
        return read_reference(self.entry['reference']) if self.has_reference() else None

    def max_dt(self):
        return float(self.entry.get('reference', {}).get('max_dt', 0.05))

    def body_from_imu(self):
        ref = self.entry.get('reference') or {}
        if not ref.get('body_from_imu'):
            return None
        return np.array(json.loads(_resolve(ref['body_from_imu']).read_text())['T_base_imu'], float)

    def exists(self):
        ok = (self.recording / 'stereo.csv').exists() and (self.recording / 'imu.csv').exists()
        if self.has_reference():
            ok = ok and _resolve(self.entry['reference']['path']).exists()
        return ok

    def config_dir(self, cache):
        """The estimator config under the canonical file names (estimator.yaml, imucam.yaml, imu.yaml)."""
        source = _resolve(self.entry['config'])
        files = self.entry.get('config_files')
        if not files:
            return source
        target = Path(cache) / self.name
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        for key, canonical in (('estimator', 'estimator.yaml'), ('imucam', 'imucam.yaml'), ('imu', 'imu.yaml')):
            shutil.copy2(source / files[key], target / canonical)
        text = (target / 'estimator.yaml').read_text()
        text = re.sub(r'^relative_config_imu:.*$', 'relative_config_imu: "imu.yaml"', text, flags=re.MULTILINE)
        text = re.sub(r'^relative_config_imucam:.*$', 'relative_config_imucam: "imucam.yaml"', text, flags=re.MULTILINE)
        (target / 'estimator.yaml').write_text(text)
        return target


def get(name, registry=None):
    registry = registry or load_registry()
    if name not in registry:
        raise KeyError(f'Unknown dataset {name!r}; known: {", ".join(registry)}')
    return Dataset(name, registry[name])


def add_recording(name, recording, config, reference=None, reference_format='tum', has_loop=None, label=None,
                  body_from_imu=None, registry_path=None):
    """Register one of our own recordings (a record-only capture folder works as is)."""
    registry = load_registry(registry_path)
    entry = {'label': label or f'Own recording {name}', 'recording': str(recording), 'config': str(config)}
    if reference:
        entry['reference'] = {'path': str(reference), 'format': reference_format, 'kind': 'user reference', 'max_dt': 0.05}
        if body_from_imu:
            entry['reference']['body_from_imu'] = str(body_from_imu)
    if has_loop is not None:
        entry['has_loop'] = bool(has_loop)
    registry[name] = entry
    save_registry(registry, registry_path)
    return entry
