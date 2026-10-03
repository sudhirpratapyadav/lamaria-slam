#!/usr/bin/env python3
"""Print a markdown table of per-sequence results for one experiment directory.

Usage: summarize_experiment.py results/001-ov-baseline
Reads <dir>/<seq>/eval.json, submission_stats.json, run_stats.json, time.txt.
"""
import json
import re
import sys
from pathlib import Path


def main():
    root = Path(sys.argv[1])
    rows = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        ev = d / "eval.json"
        if not ev.exists():
            rows.append(f"| {d.name} | (no eval) | | | | | | |")
            continue
        e = json.loads(ev.read_text())
        s = json.loads((d / "submission_stats.json").read_text()) if (d / "submission_stats.json").exists() else {}
        r = json.loads((d / "run_stats.json").read_text()) if (d / "run_stats.json").exists() else {}
        t = (d / "time.txt").read_text() if (d / "time.txt").exists() else ""
        wall = re.search(r"wall_s=([\d.]+)", t)
        rss = re.search(r"max_rss_kb=(\d+)", t)
        ate = e.get("ate_rmse_m")
        scale = e.get("sim3_scale")
        recall = e.get("pose_recall_5m")
        cp = e.get("cp_score")
        rows.append(
            f"| {d.name} | {ate:.3f} | {scale:.4f} | "
            f"{'-' if recall is None else f'{recall:.1f}'} | {'-' if cp is None else f'{cp:.1f}'} | "
            f"{s.get('matched_within_tolerance', '?')}/{s.get('images', '?')} "
            f"(pre-init {s.get('images_before_first_estimate', '?')}, gaps {s.get('gap_filled_after_init', '?')}) | "
            f"{float(wall.group(1)):.0f} s / {e.get('est_duration_s', 0):.0f} s | "
            f"{int(rss.group(1)) / 1024:.0f} MB |"
            if ate is not None else
            (f"| {d.name} | (no pGT) | - | - | {cp:.1f} | {e.get('est_poses')} poses | | |" if cp is not None
             else f"| {d.name} | FAILED ({e.get('est_poses')} poses) | | | | | | |")
        )
    print("| Sequence | ATE RMSE (m, sim3) | sim3 scale | recall@5m | CP score | poses matched/images | wall / seq | RSS |")
    print("|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
