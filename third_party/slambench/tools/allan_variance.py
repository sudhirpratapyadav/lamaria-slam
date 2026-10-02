"""IMU noise from a long static recording by Allan variance: noise density, bias instability and random walk per axis.

  python -m slambench.tools.allan_variance RECORDING/imu.csv [--gyro-units dps] [--accel-units g] [--json out.json]

Input is a CSV with columns t, wx, wy, wz, ax, ay, az (our recordings' imu.csv). Record the sensor perfectly still, thermally settled,
for 2-3 hours or more to see random walk (a few minutes is enough for noise density). Output is in SI units, as OpenVINS and Kalibr
expect: gyro rad/s/sqrt(Hz) and rad/s^2/sqrt(Hz), accelerometer m/s^2/sqrt(Hz) and m/s^3/sqrt(Hz).
"""
import argparse
import json
import sys

import numpy as np

G = 9.80665


def allan_deviation(x, rate_hz, points=60):
    """Overlapping Allan deviation of a rate signal x sampled at rate_hz. Returns (taus, sigma)."""
    x = np.asarray(x, float)
    n = len(x)
    dt = 1.0 / rate_hz
    theta = np.concatenate([[0.0], np.cumsum(x) * dt])
    max_m = (n - 1) // 2
    ms = np.unique(np.round(np.logspace(0, np.log10(max(max_m, 2)), points)).astype(int))
    taus, sigma = [], []
    for m in ms:
        if 2 * m >= len(theta):
            break
        d = theta[2 * m:] - 2 * theta[m:-m] + theta[:-2 * m]
        taus.append(m * dt)
        sigma.append(np.sqrt(np.mean(d ** 2) / (2 * (m * dt) ** 2)))
    return np.array(taus), np.array(sigma)


def noise_parameters(taus, sigma):
    """Noise density N (slope -1/2, read at tau = 1 s), bias instability B (minimum / 0.664) and random walk K (slope +1/2, read at
    tau = 3 s). K is None when the recording does not extend well past the minimum (too short to see the random walk)."""
    i_min = int(np.argmin(sigma))
    tau_min = taus[i_min]
    white = taus <= max(tau_min / 3.0, taus[0] * 3)
    noise = float(np.median(sigma[white] * np.sqrt(taus[white])))              # sigma = N / sqrt(tau)
    walk = None
    late = taus >= 3.0 * tau_min
    if late.sum() >= 3 and taus[-1] >= 6.0 * tau_min:
        walk = float(np.median(sigma[late] / np.sqrt(taus[late] / 3.0)))       # sigma = K sqrt(tau / 3)
    return {'noise_density': noise, 'bias_instability': float(sigma[i_min] / 0.664), 'bias_instability_tau_s': float(tau_min), 'random_walk': walk}


def analyse(t, gyro, accel, gyro_scale=1.0, accel_scale=1.0):
    """t: (N,) seconds; gyro, accel: (N, 3). Scales convert to rad/s and m/s^2."""
    dt = np.diff(t)
    rate = 1.0 / np.median(dt)
    gaps = int(np.sum(dt > 2.5 / rate))
    result = {'rate_hz': float(rate), 'duration_s': float(t[-1] - t[0]), 'samples': int(len(t)), 'gaps_over_2_5_periods': gaps, 'axes': {}}
    for name, data, scale in (('gyro', gyro, gyro_scale), ('accel', accel, accel_scale)):
        for k, axis in enumerate('xyz'):
            taus, sigma = allan_deviation(data[:, k] * scale, rate)
            result['axes'][f'{name}_{axis}'] = noise_parameters(taus, sigma)
    def mean_of(prefix, key):
        values = [result['axes'][f'{prefix}_{a}'][key] for a in 'xyz' if result['axes'][f'{prefix}_{a}'][key] is not None]
        return float(np.mean(values)) if values else None
    result['summary'] = {'gyroscope_noise_density': mean_of('gyro', 'noise_density'), 'gyroscope_random_walk': mean_of('gyro', 'random_walk'),
                         'accelerometer_noise_density': mean_of('accel', 'noise_density'), 'accelerometer_random_walk': mean_of('accel', 'random_walk'),
                         'update_rate': float(round(rate))}
    return result


def yaml_snippet(summary, inflate_noise=1.0, inflate_walk=1.0):
    def f(v, k):
        return 'null  # recording too short to see random walk' if v is None else f'{v * k:.6e}'
    return '\n'.join([f'gyroscope_noise_density: {f(summary["gyroscope_noise_density"], inflate_noise)}',
                      f'gyroscope_random_walk: {f(summary["gyroscope_random_walk"], inflate_walk)}',
                      f'accelerometer_noise_density: {f(summary["accelerometer_noise_density"], inflate_noise)}',
                      f'accelerometer_random_walk: {f(summary["accelerometer_random_walk"], inflate_walk)}',
                      f'update_rate: {summary["update_rate"]:.1f}'])


def load_csv(path):
    rows = np.loadtxt(path, delimiter=',', comments='#', ndmin=2)
    return rows[:, 0], rows[:, 1:4], rows[:, 4:7]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('imu_csv')
    ap.add_argument('--gyro-units', choices=['rads', 'dps'], default='rads')
    ap.add_argument('--accel-units', choices=['ms2', 'g'], default='ms2')
    ap.add_argument('--json')
    ap.add_argument('--inflate-noise', type=float, default=1.0, help='multiply noise densities in the YAML (VIO often wants 2-10x the Allan value)')
    ap.add_argument('--inflate-walk', type=float, default=1.0)
    args = ap.parse_args(argv)
    t, gyro, accel = load_csv(args.imu_csv)
    result = analyse(t, gyro, accel, np.pi / 180 if args.gyro_units == 'dps' else 1.0, G if args.accel_units == 'g' else 1.0)
    if result['gaps_over_2_5_periods']:
        print(f"warning: {result['gaps_over_2_5_periods']} gaps longer than 2.5 sample periods; Allan variance assumes a regular stream", file=sys.stderr)
    for name, p in result['axes'].items():
        print(f"{name}: noise density {p['noise_density']:.3e}  bias instability {p['bias_instability']:.3e} (at {p['bias_instability_tau_s']:.0f} s)  "
              f"random walk {'n/a (too short)' if p['random_walk'] is None else format(p['random_walk'], '.3e')}")
    print(f"\n{result['duration_s'] / 60:.1f} min at {result['rate_hz']:.0f} Hz\n")
    print(yaml_snippet(result['summary'], args.inflate_noise, args.inflate_walk))
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(result, f, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
