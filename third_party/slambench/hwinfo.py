"""What machine produced a result: CPU, memory, frequency policy, power mode, kernel. Safe on any Linux; missing tools are skipped."""
import os
import platform
import re
import shutil
import subprocess


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def _run(cmd):
    if not shutil.which(cmd[0]):
        return None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def cpu_model():
    text = _read('/proc/cpuinfo') or ''
    for key in ('model name', 'Model', 'Hardware', 'cpu model'):
        m = re.search(rf'^{key}\s*:\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    parts = sorted(set(re.findall(r'^CPU part\s*:\s*(\S+)', text, re.MULTILINE)))
    return 'ARM core part ' + '/'.join(parts) if parts else platform.processor() or None


def hardware_info():
    meminfo = _read('/proc/meminfo') or ''
    mem = re.search(r'MemTotal:\s+(\d+) kB', meminfo)
    freqs = [int(x) for x in (_read(f'/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_max_freq') for i in range(os.cpu_count() or 1)) if x]
    info = {'machine': platform.machine(), 'node': platform.node(), 'kernel': platform.release(), 'cpu_model': cpu_model(),
            'cpus': len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count(),
            'mem_gb': round(int(mem.group(1)) / 1048576, 1) if mem else None,
            'cpu_max_mhz': sorted(set(round(f / 1000) for f in freqs)) or None,
            'governor': _read('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'),
            'device_tree_model': (_read('/proc/device-tree/model') or '').strip('\x00') or None}
    nvpmodel = _run(['nvpmodel', '-q'])                          # Jetson power mode
    if nvpmodel:
        modes = re.findall(r'NV Power Mode:\s*(\S+)', nvpmodel)
        info['nvpmodel'] = modes[0] if modes else None
    gpu = _run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'])
    if gpu:
        info['gpu'] = gpu.splitlines()[0]
    return {k: v for k, v in info.items() if v is not None}
