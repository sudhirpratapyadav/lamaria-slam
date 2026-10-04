# Configs

One directory per estimator configuration: `estimator.yaml` (OpenVINS) and an optional
`options.sh` (`NOISE_SCALE`, `WALK_SCALE` multipliers applied to the calibration JSON
values). The camera and IMU yaml files are generated per sequence by
`scripts/make_openvins_config.py` because each LaMAria recording has its own calibration.

- `ov_baseline`: experiment 001 first attempt, datasheet noise, online time offset. Diverges on R_04_medium.
- `ov_ref001`: reference after experiment 001 (time offset fixed at 0, noise densities x10).
- `explore-001/`: the bring-up variants tried in experiment 001, kept for reproducibility.
- `basalt_r17_{huber05,outlier2,obsstd1,epi0025}`: basalt_ref1 with one outlier-handling knob each (B17): `vio_obs_huber_thresh` 0.5, `vio_outlier_threshold` 2.0, `vio_obs_std_dev` 1.0, `optical_flow_epipolar_error` 0.0025.

## basalt_v3_ref (v3 reference, 2026-10-04)

`basalt_ref1` files unchanged plus `env.sh`: `BASALT_OUTLIER_PX=3`, `BASALT_OUTLIER_LM_RULE=1`, `BASALT_DETERMINISTIC=1` (track_logs_v3 F15/F16). Controlled two-offset mean 2.38 m, additional-set mean score 23.7 (F21, repeatable build). Needs the patched Basalt (`docs/patches/basalt-0f3b2b5.patch`).
