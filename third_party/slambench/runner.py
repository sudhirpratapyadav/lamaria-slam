"""Run one (dataset, system, variant), score it, and write result.json; gather results into a table."""
import json
import platform
import shutil
import time
from pathlib import Path

from . import adapters, datasets, metrics
from .metrics import write_tum
from .sysmon import Sampler


def host_info():
    from .hwinfo import hardware_info
    info = hardware_info()
    info['python'] = platform.python_version()
    return info


def run(dataset_name, system, variant, out_root, max_seconds=0., augment='', sets=(), command_spec=None, registry_path=None):
    registry = datasets.load_registry(registry_path)
    dataset = datasets.get(dataset_name, registry)
    if not dataset.exists():
        raise FileNotFoundError(f'Dataset {dataset_name!r} is not available on this machine (missing recording or reference)')
    suffix = ('_' + augment.replace('=', '').replace(',', '_')) if augment else ''
    out = Path(out_root) / dataset_name / f'{system}_{variant}{suffix}'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    cache = out / '_config'            # per run, so parallel runs of the same dataset never rebuild each other's config
    sampler = Sampler().start()
    started = time.time()
    try:
        if system == 'openvins':
            result = adapters.run_openvins(dataset, variant, out / 'raw', cache, max_seconds, augment, sets)
        elif system == 'command':
            result = adapters.run_command(dataset, command_spec, out / 'raw', cache, max_seconds)
        else:
            raise ValueError(f'Unknown system {system!r}')
    finally:
        monitor = sampler.stop()
    trajectory = result['trajectory']
    write_tum(out / 'trajectory.tum', trajectory)
    reference = dataset.reference()
    body = dataset.body_from_imu() if result['frame'] == 'imu' else None
    scores = metrics.evaluate(trajectory, reference, body, dataset.max_dt()) if len(trajectory) else {'poses': 0}
    record = {'dataset': dataset_name, 'system': system, 'variant': variant, 'augment': augment, 'max_seconds': max_seconds,
              'reference_kind': (dataset.entry.get('reference') or {}).get('kind'), 'host': host_info(), 'started': started,
              'timing': result['timing'], 'sysmon': monitor, 'metrics': scores}
    (out / 'result.json').write_text(json.dumps(record, indent=2))
    return record


def reevaluate(root, registry_path=None):
    """Re-score every saved result from its trajectory.tum with the current metrics (no system is re-run). Returns the number updated."""
    registry = datasets.load_registry(registry_path)
    count = 0
    for path in sorted(Path(root).rglob('result.json')):
        record = json.loads(path.read_text())
        trajectory_path = path.parent / 'trajectory.tum'
        if record['dataset'] not in registry or not trajectory_path.exists():
            continue
        dataset = datasets.get(record['dataset'], registry)
        if not dataset.exists():
            continue
        trajectory = metrics.read_tum(trajectory_path)
        frame_is_imu = record['system'] == 'openvins'
        record['metrics'] = metrics.evaluate(trajectory, dataset.reference(), dataset.body_from_imu() if frame_is_imu else None, dataset.max_dt()) \
            if len(trajectory) else {'poses': 0}
        path.write_text(json.dumps(record, indent=2))
        count += 1
    return count


def collect(root):
    return [json.loads(p.read_text()) for p in sorted(Path(root).rglob('result.json'))]


def _g(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d or d[k] is None:
            return None
        d = d[k]
    return d


def table(records):
    def f(x, spec):
        return '–' if x is None else format(x, spec)
    head = ('| dataset | system | variant | ATE yaw (m) | ATE se3 (m) | ATE sim3 (m) | scale | drift 100 m (%) | start→end gap (% path) | local 1 s (cm) '
            '| jumps | compute p50 (ms) | CPU cores | RAM peak (MB) | temp max (°C) |')
    rows = [head, '|' + '---|' * 15]
    for r in records:
        m, t, s = r['metrics'], r['timing'], r.get('sysmon') or {}
        rpe = _g(m, 'rpe_1s', 'rmse_m')
        rows.append('| {} | {} | {}{} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |'.format(
            r['dataset'], r['system'], r['variant'], ' (' + r['augment'] + ')' if r.get('augment') else '',
            f(_g(m, 'ate_yaw', 'rmse_m'), '.2f'), f(_g(m, 'ate_se3', 'rmse_m'), '.2f'), f(_g(m, 'ate_sim3', 'rmse_m'), '.2f'),
            f(_g(m, 'ate_sim3', 'scale'), '.2f'), f(_g(m, 'drift', '100m', 'trans_pct'), '.2f'),
            f(_g(m, 'loop', 'est_gap_pct_of_path') if _g(m, 'loop', 'closed_loop') is not False else None, '.1f'), f(None if rpe is None else rpe * 100, '.1f'), f(m.get('jumps'), 'd'),
            f(_g(t, 'compute_ms', 'p50'), '.1f'), f(s.get('cpu_cores_mean'), '.2f'), f(t.get('peak_rss_mb') or s.get('mem_used_mb_max'), '.0f'),
            f(s.get('temp_c_max'), '.0f')))
    return '\n'.join(rows)
