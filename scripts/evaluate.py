#!/usr/bin/env python3
"""Score a submission-format estimate with the official LaMAria evaluators.

Always: ATE RMSE after Umeyama (sim3) against the pseudo-GT (evaluate_wrt_mps).
If the sequence has control points: CP score, CP recall @1 m, and pose recall
@1 m / @5 m against the pseudo-GT (evaluate_wrt_control_points + evaluate_wrt_pgt).
Also reports the fitted sim3 scale and the trajectory coverage, as diagnostics.

Run with the project .venv. Usage:
  evaluate.py ESTIMATE.txt data/training/R_01_easy [--out-dir DIR] [--aria-calib JSON]
Prints one JSON line with all numbers; also writes it to --out-dir/eval.json.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from evo.core import sync

from lamaria.eval.evo_evaluation import convert_trajectory_to_evo_posetrajectory, evaluate_wrt_mps
from lamaria.structs.trajectory import Trajectory


def umeyama_scale(est_path: Path, gt_path: Path) -> float | None:
    est = convert_trajectory_to_evo_posetrajectory(Trajectory.load_from_file(est_path, invert_poses=False))
    gt = convert_trajectory_to_evo_posetrajectory(Trajectory.load_from_file(gt_path, invert_poses=False))
    gt_s, est_s = sync.associate_trajectories(gt, est, max_diff=1e6)
    try:
        _, _, s = est_s.align(gt_s, correct_scale=True)
    except Exception:
        return None
    return float(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("estimate", type=Path)
    ap.add_argument("seq_dir", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--aria-calib", type=Path, help="aria calibration JSON (needed for control-point eval)")
    args = ap.parse_args()
    seq = args.seq_dir.name
    gt_pgt = next(iter(args.seq_dir.glob("ground_truth/**/pGT/*.txt")), None) or \
        next(iter(args.seq_dir.glob("ground_truth/**/*.txt")), None)
    if gt_pgt is None:
        sys.exit(f"no pseudo-GT under {args.seq_dir}/ground_truth")
    result = {"sequence": seq, "estimate": str(args.estimate), "pgt": str(gt_pgt)}

    est = Trajectory.load_from_file(args.estimate, invert_poses=False)
    gt = Trajectory.load_from_file(gt_pgt, invert_poses=False)
    result["est_poses"] = len(est)
    result["gt_keyframes"] = len(gt)
    result["est_duration_s"] = (est.timestamps[-1] - est.timestamps[0]) / 1e9
    result["gt_duration_s"] = (gt.timestamps[-1] - gt.timestamps[0]) / 1e9

    ate = evaluate_wrt_mps(
        Trajectory.load_from_file(args.estimate, invert_poses=False),
        Trajectory.load_from_file(gt_pgt, invert_poses=False),
    )
    result["ate_rmse_m"] = None if ate is None else float(ate)
    result["sim3_scale"] = umeyama_scale(args.estimate, gt_pgt)

    cp_json = next(iter(args.seq_dir.glob("ground_truth/**/control_points/*.json")), None) or \
        next(iter(args.seq_dir.glob("ground_truth/**/*.json")), None)
    if cp_json is not None and args.aria_calib is not None:
        out = args.out_dir or args.estimate.parent
        out.mkdir(parents=True, exist_ok=True)
        import evaluate_wrt_control_points as cp_eval  # noqa: E402  (lamaria repo module)
        import evaluate_wrt_pgt as pgt_eval  # noqa: E402
        from lamaria.eval.pgt_evaluation import evaluate_wrt_pgt
        from lamaria.structs.sparse_eval import SparseEvalResult
        from lamaria.utils.metrics import (calculate_control_point_recall, calculate_control_point_score,
                                           calculate_pose_recall)
        ok = cp_eval.run(args.estimate, cp_json, args.aria_calib, out, "imu")
        result["cp_eval_ok"] = bool(ok)
        if ok:
            sres = SparseEvalResult.load_from_npy(out / "sparse_eval_result.npy")
            result["cp_score"] = float(calculate_control_point_score(sres))
            result["cp_recall_1m"] = float(calculate_control_point_recall(sres))
            err = evaluate_wrt_pgt(Trajectory.load_from_file(args.estimate, invert_poses=False),
                                   Trajectory.load_from_file(gt_pgt, invert_poses=False), sres.alignment)
            if err is not None:
                for t in (1.0, 5.0):
                    result[f"pose_recall_{int(t)}m"] = float(calculate_pose_recall(err, len(gt), t))
        del pgt_eval
    elif cp_json is not None:
        result["cp_eval_ok"] = "skipped: pass --aria-calib"

    line = json.dumps(result)
    print(line)
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "eval.json").write_text(line + "\n")


if __name__ == "__main__":
    main()
