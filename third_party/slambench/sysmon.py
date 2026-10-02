"""Whole-system CPU, memory, temperature and (on Jetson) power sampling while a benchmark runs. No dependencies."""
import glob
import re
import shutil
import subprocess
import threading
import time


def _cpu_times():
    cores = {}
    with open('/proc/stat') as stat:
        for line in stat:
            if line.startswith('cpu') and line[3].isdigit():
                f = list(map(int, line.split()[1:]))
                cores[line.split()[0]] = (sum(f) - f[3] - f[4], sum(f))     # busy, total (idle and iowait excluded)
    return cores


def _mem_used_mb():
    with open('/proc/meminfo') as meminfo:
        info = {l.split(':')[0]: int(l.split()[1]) for l in meminfo if ':' in l}
    return (info['MemTotal'] - info['MemAvailable']) / 1024.


def _max_temp_c():
    temps = []
    for path in glob.glob('/sys/class/thermal/thermal_zone*/temp'):
        try:
            with open(path) as f:
                temps.append(int(f.read()) / 1000.)
        except (OSError, ValueError):
            pass
    return max(temps) if temps else None


class Sampler:
    def __init__(self, interval=1.0):
        self.interval = interval
        self.rows = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.tegra = None

    def start(self):
        if shutil.which('tegrastats'):
            try:
                self.tegra = subprocess.Popen(['tegrastats', '--interval', str(int(self.interval * 1000))], stdout=subprocess.PIPE,
                                              stderr=subprocess.DEVNULL, text=True)
            except OSError:
                self.tegra = None
        self.power = []
        if self.tegra:
            threading.Thread(target=self._read_power, daemon=True).start()
        self.thread.start()
        return self

    def _read_power(self):
        for line in self.tegra.stdout:
            m = re.search(r'(?:POM_5V_IN|VDD_IN) (\d+)/', line)
            if m:
                self.power.append(int(m.group(1)))

    def _run(self):
        previous = _cpu_times()
        while not self.stop_event.wait(self.interval):
            now = _cpu_times()
            per_core = [100. * (now[c][0] - previous[c][0]) / max(now[c][1] - previous[c][1], 1) for c in now if c in previous]
            previous = now
            self.rows.append({'t': time.time(), 'cpu_pct': sum(per_core), 'cores': per_core, 'mem_mb': _mem_used_mb(), 'temp_c': _max_temp_c()})

    def stop(self):
        self.stop_event.set()
        self.thread.join(5)
        if self.tegra:
            self.tegra.terminate()
        return self.summary()

    def summary(self):
        rows = self.rows
        if not rows:
            return {'samples': 0}
        cpu = [r['cpu_pct'] for r in rows]
        temps = [r['temp_c'] for r in rows if r['temp_c'] is not None]
        out = {'samples': len(rows), 'cpu_cores_mean': sum(cpu) / len(cpu) / 100., 'cpu_cores_max': max(cpu) / 100.,
               'mem_used_mb_mean': sum(r['mem_mb'] for r in rows) / len(rows), 'mem_used_mb_max': max(r['mem_mb'] for r in rows),
               'temp_c_max': max(temps) if temps else None}
        if getattr(self, 'power', None):
            out['power_w_mean'] = sum(self.power) / len(self.power) / 1000.
            out['power_w_max'] = max(self.power) / 1000.
        return out
