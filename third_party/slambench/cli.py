"""python -m slambench  datasets | run | eval | table | add-dataset"""
import argparse
import json
import sys
from pathlib import Path

from . import datasets, metrics, robustness, runner

DEFAULT_OUT = Path(__file__).resolve().parents[1] / 'results' / 'slambench'


def main(argv=None):
    ap = argparse.ArgumentParser(prog='slambench', description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('datasets', help='list registered datasets and whether they are available here')

    r = sub.add_parser('run', help='run one system on one dataset and score it')
    r.add_argument('dataset')
    r.add_argument('--system', default='openvins', choices=['openvins', 'command'])
    r.add_argument('--variant', default='full', help='openvins: full | balanced | robust | recorded')
    r.add_argument('--spec', type=Path, help='JSON spec for --system command (cmd, trajectory, frame)')
    r.add_argument('--max-seconds', type=float, default=0.)
    r.add_argument('--augment', default='', help='degrade the images, e.g. gamma=1.6,gain=.6,noise=6,seed=1')
    r.add_argument('--set', action='append', default=[], metavar='KEY=VALUE', help='openvins: override an estimator setting')
    r.add_argument('--out', type=Path, default=DEFAULT_OUT)

    e = sub.add_parser('eval', help='score an existing trajectory (TUM) against a dataset reference')
    e.add_argument('dataset')
    e.add_argument('trajectory', type=Path)
    e.add_argument('--frame', default='body', choices=['body', 'imu'])

    b = sub.add_parser('robustness', help='clean vs darkened/noisy images over several seeds, counting failures')
    b.add_argument('dataset')
    b.add_argument('--system', default='openvins', choices=['openvins', 'command'])
    b.add_argument('--variant', default='robust')
    b.add_argument('--spec', type=Path)
    b.add_argument('--max-seconds', type=float, default=150.)
    b.add_argument('--seeds', type=int, default=4)
    b.add_argument('--workers', type=int, default=2)
    b.add_argument('--out', type=Path, default=DEFAULT_OUT / 'robustness')

    t = sub.add_parser('table', help='print a markdown table of all results under a folder')
    t.add_argument('root', type=Path, nargs='?', default=DEFAULT_OUT)

    re_ = sub.add_parser('reeval', help='re-score saved results with the current metrics (no re-run)')
    re_.add_argument('root', type=Path, nargs='?', default=DEFAULT_OUT)

    a = sub.add_parser('add-dataset', help='register one of our own recordings')
    a.add_argument('name')
    a.add_argument('recording', type=Path)
    a.add_argument('config', type=Path)
    a.add_argument('--reference', type=Path)
    a.add_argument('--reference-format', default='tum', choices=['tum', 'kimera_csv'])
    a.add_argument('--loop', action='store_true', help='the route ends where it started')

    args = ap.parse_args(argv)
    if args.command == 'datasets':
        for name, entry in datasets.load_registry().items():
            d = datasets.Dataset(name, entry)
            print(f"{name:16} {'available' if d.exists() else 'MISSING  '}  {entry['label']}")
    elif args.command == 'run':
        spec = json.loads(args.spec.read_text()) if args.spec else None
        record = runner.run(args.dataset, args.system, args.variant, args.out, args.max_seconds, args.augment, args.set, spec)
        print(runner.table([record]))
    elif args.command == 'eval':
        d = datasets.get(args.dataset)
        scores = metrics.evaluate(metrics.read_tum(args.trajectory), d.reference(), d.body_from_imu() if args.frame == 'imu' else None, d.max_dt())
        print(json.dumps(scores, indent=2))
    elif args.command == 'robustness':
        spec = json.loads(args.spec.read_text()) if args.spec else None
        result = robustness.run_suite(args.dataset, args.system, args.variant, args.out, args.max_seconds, args.seeds, workers=args.workers, command_spec=spec)
        print(robustness.format_suite(result, f'{args.dataset} {args.system}/{args.variant}:'))
    elif args.command == 'table':
        print(runner.table(runner.collect(args.root)))
    elif args.command == 'reeval':
        print(f're-scored {runner.reevaluate(args.root)} results')
    elif args.command == 'add-dataset':
        datasets.add_recording(args.name, args.recording, args.config, args.reference, args.reference_format, args.loop or None)
        print(f'registered {args.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
