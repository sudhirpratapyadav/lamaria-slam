# Configs

One directory per estimator configuration: `estimator.yaml` (OpenVINS) and an optional
`options.sh` (`NOISE_SCALE`, `WALK_SCALE` multipliers applied to the calibration JSON
values). The camera and IMU yaml files are generated per sequence by
`scripts/make_openvins_config.py` because each LaMAria recording has its own calibration.

- `ov_baseline`: experiment 001 first attempt, datasheet noise, online time offset. Diverges on R_04_medium.
- `ov_ref001`: reference after experiment 001 (time offset fixed at 0, noise densities x10).
- `explore-001/`: the bring-up variants tried in experiment 001, kept for reproducibility.
