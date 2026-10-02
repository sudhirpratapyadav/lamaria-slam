# Scoreboard

Current best per host. Update after every experiment that is kept. ATE = RMSE in metres after sim3 Umeyama against the controlled-set pseudo-GT (official `evaluate_wrt_mps`), single runs unless stated.

| # | Date | Host | Change | R_01_easy | R_04_medium | R_08_hard | Notes |
|---|---|---|---|---|---|---|---|
| 001 | 2026-10-02 | pc | OpenVINS stereo+IMU, pinhole ASL, dynamic init, dt calib off, IMU noise densities x10 (`configs/ov_ref001`) | 0.301 | 0.739 | 4.49 | reference; datasheet-noise baseline: 0.169 / diverged / 10.59 |
