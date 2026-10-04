#!/usr/bin/env python3
"""Build a sequence folder with the two cameras swapped (cam1 becomes cam0 and vice versa),
for diagnosing camera-geometry-dependent biases of a front end that treats cam0 as primary.

Usage: make_swapped_input.py SEQ_DIR OUT_DIR
Writes OUT_DIR/runner_input (stereo.csv columns swapped, cam folders cross-linked, imu and
timestamps linked), OUT_DIR/pinhole_calibrations/<name>.json with cam0/cam1 entries swapped,
and links aria_calibrations and ground_truth unchanged.
"""
import json
import os
import sys
from pathlib import Path


def main():
    seq, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    ri = out / "runner_input"
    ri.mkdir(parents=True, exist_ok=True)
    src = seq / "runner_input"
    for a, b in (("cam0", "cam1"), ("cam1", "cam0")):
        link = ri / a
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(os.path.relpath(src / b, ri), link)
    for f in ("imu.csv", "image_timestamps_ns.txt"):
        link = ri / f
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(os.path.relpath(src / f, ri), link)
    lines = []
    for l in (src / "stereo.csv").read_text().splitlines():
        if not l or l.startswith("#"):
            lines.append(l)
            continue
        t, c0, c1 = l.split(",")
        lines.append(",".join([t, c1.replace("cam1/", "cam0/"), c0.replace("cam0/", "cam1/")]))
    (ri / "stereo.csv").write_text("# cameras swapped\n" + "\n".join(lines) + "\n")
    pc = out / "pinhole_calibrations"
    pc.mkdir(exist_ok=True)
    for cj in (seq / "pinhole_calibrations").glob("*.json"):
        c = json.loads(cj.read_text())
        c["cam0"], c["cam1"] = c["cam1"], c["cam0"]
        (pc / cj.name).write_text(json.dumps(c, indent=2) + "\n")
    for d in ("aria_calibrations", "ground_truth"):
        link = out / d
        if (seq / d).exists() and not link.exists():
            os.symlink(os.path.relpath(seq / d, out), link)
    print(f"swapped input in {out}: {len(lines)} stereo rows")


if __name__ == "__main__":
    main()
