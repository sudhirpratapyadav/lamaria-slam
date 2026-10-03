# Thoughts

## 2026-10-03

- Systems work roughly like the open baseline; the damage comes from specific events (edge cases), not general tracking error: those derail the whole run. Candidates: rotation, lighting changes, dynamic objects entering the scene. These are front-end feature problems. Giving the IMU more weight to reduce the visual weight did not work.
- Before deciding, understand each method in detail: what is common, their pipelines, differences, filter-based vs optimisation-based, what is lacking, what the latest front ends look like.
