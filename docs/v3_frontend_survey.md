# v3 front-end survey (2026-10-03, research agent; licences and dates from GitHub that day, runtimes are the authors' claims)

Question: what exists for (1) dynamic and ego-body masking, (2) IMU-aided outlier rejection, (3) learned keypoints and matchers, (4) learned trackers and learned VO, for a stereo fisheye + IMU front end whose failures are wrong features (people, the wearer's arm and shoe, reflections) and too few features (dark, low texture, overexposed).

## Background

- LaMAria paper (arXiv 2509.26639) ran DPVO and DPV-SLAM vision-only on pinhole-undistorted images: main-benchmark scores 9.4 / 5.2 / 1.2 and 7.5 / 5.2 / 0.4 (OpenVINS 18.1 / 10.9 / 4.7). No reason given; likely no IMU (scale), lost field of view, synthetic training, low light.
- OpenVINS's KLT seeds with the previous pixel, then 8-point RANSAC at 2 px; nothing uses the IMU. Basalt's optical flow likewise. msckf_vio, Kimera-VIO, Dynamic-VINS and DynaVINS do use the IMU against lying features.

## 1. Dynamic and ego-body masking

| Candidate | What | Evidence | Licence / compute / maturity | Plug-in |
|---|---|---|---|---|
| Dynamic-VINS (RA-L 2022), [paper](https://arxiv.org/abs/2304.10987), [code](https://github.com/HITSZ-NRSL/Dynamic-VINS) | YOLO boxes + IMU-predicted motion-consistency check | real-time on Jetson AGX Xavier; dynamic RGB-D sets | no licence file; pushed 2026-09 | pattern to copy (box mask + outlier filter); RGB-D depth test must come from our stereo |
| YOLOv8/11n-seg ([Ultralytics](https://github.com/ultralytics/ultralytics)) | person instance masks | COCO; ~23-27 ms detection on Orin Nano FP16/INT8 | AGPL-3.0; very active | detection mask + drop tracks inside; trained on RGB, expect a gap on grey fisheye |
| EgoHOS (ECCV 2022), [code](https://github.com/owenzlz/EgoHOS) | egocentric hand/held-object segmentation | 11k labelled images | MIT; Swin/ResNet, desktop GPU; 2024-02 | offline teacher for hands and arms (not shoes) |
| MobileSAM, [code](https://github.com/ChaoningZhang/MobileSAM) | promptable masks | widely used | Apache-2.0 | refine boxes into masks, optional |
| DynaSLAM (RA-L 2018) | Mask R-CNN + multi-view geometry on ORB-SLAM2 | TUM-dynamic baseline | GPL; hundreds of ms; abandoned | reference only |
| Static ego-region prior (own idea) | per-pixel map of where tracks get rejected on our data (camera rigid on the head) | build from training data | free | fixed detection mask |

## 2. IMU-aided outlier rejection (all CPU-cheap)

| Candidate | What | Licence / maturity | Plug-in |
|---|---|---|---|
| Troiani 2-point RANSAC (ICRA 2014), [pdf](https://rpg.ifi.uzh.ch/docs/ICRA14_Troiani.pdf) | known gyro rotation: 2 correspondences give the translation direction | paper | replaces F-matrix RANSAC |
| msckf_vio (RA-L 2018), [code](https://github.com/KumarRobotics/msckf_vio) | gyro-compensated KLT prediction, 2-point RANSAC, stereo check | Penn research-only licence (read, do not copy); 2023 | reference design |
| Kimera-VIO front end, [paper](https://arxiv.org/abs/1910.02490), [code](https://github.com/MIT-SPARK/Kimera-VIO) | KLT seeded by IMU rotational flow; 2-point mono and 1-point stereo RANSAC via OpenGV | BSD-2 (copyable); active 2026-08 | drop-in source for tracking and RANSAC |
| Hwangbo, Kim, Kanade gyro-aided KLT (IROS 2009 / IJRR 2011) | gyro prediction + template pre-warp | no maintained code | tracker; helps under fast head rotation |
| DynaVINS (RA-L 2022), [code](https://github.com/url-kaist/dynaVINS) | robust BA down-weighting features that disagree with the IMU prior | GPL-3; ROS Melodic; 2025-08 | back-end weighting, complements a front-end test |

## 3. Learned detectors, descriptors, matchers

| Candidate | Evidence | Licence / compute | Plug-in |
|---|---|---|---|
| XFeat (CVPR 2024), [code](https://github.com/verlab/accelerated_features) | ~27 FPS sparse on an i5 CPU at VGA; most robust in low-light caves and overexposure in a LIDAR-visual-inertial benchmark ([arXiv 2603.18589](https://arxiv.org/html/2603.18589v1)), 5-7 ms/frame | Apache-2.0; CPU; 2025-01 | re-detection and re-finding lost tracks |
| SuperPoint + LightGlue ([LightGlue](https://github.com/cvg/LightGlue)) | inside VIO: SuperVINS ([code](https://github.com/luohongk/SuperVINS), GPL-3; better than VINS-Fusion on 6/11 EuRoC), LightGlue-VINS-Mono (Hamesse 2024); ~3 GB GPU | LightGlue Apache-2.0; SuperPoint original weights non-commercial, [rpautrat retrain](https://github.com/rpautrat/SuperPoint) MIT | matcher replacing KLT; tight on the 2 GB P620 |
| ALIKED (2023), [code](https://github.com/Shiaoming/ALIKED) | LightGlue weights exist | BSD-3; GPU; idle since 2024-05 | SuperPoint alternative with a clean licence |
| AirSLAM / PLNet (T-RO 2025), [paper](https://arxiv.org/abs/2408.03520), [code](https://github.com/sair-lab/AirSLAM) | illumination-robust points + lines, TensorRT, ~40 Hz on Orin, optional IMU | GPL-3; TensorRT 8.6 / CUDA 12.1; 2025-11 | closest existing "sees in the dark" front end; fisheye and Pascal support unverified |
| DISK | accurate | Apache-2.0; heavy | avoid for real time |
| DarkFeat (AAAI 2023) | low-light-specific | needs RAW sensor images | not applicable |

## 4. Learned trackers and learned VO/VIO

| Candidate | Evidence | Licence / compute | Weakness for us |
|---|---|---|---|
| DPVO / DPV-SLAM, [code](https://github.com/princeton-vl/DPVO) | strong on EuRoC, TartanAir | MIT; desktop GPU | monocular, no IMU, measured poor on LaMAria |
| DROID-SLAM and DBA-Fusion (DROID + IMU, RA-L 2024), [code](https://github.com/GREAT-WHU/DBA-Fusion) | DBA-Fusion much better than DROID with IMU | BSD-3 / GPL-3; large GPU | A100-only; not embedded |
| MAC-VO (ICRA 2025), [code](https://github.com/MAC-VO/MAC-VO) | learned stereo VO with uncertainty-weighted keypoints, 7-12 FPS at 480x640 desktop | MIT | no IMU; GPU-heavy |
| CoTracker3 online, [code](https://github.com/facebookresearch/co-tracker) | best-known point tracker, causal mode | CC-BY-NC; heavy | licence unsuitable for the product |
| TAPIR / BootsTAP, [code](https://github.com/google-deepmind/tapnet) | online causal variant | Apache-2.0; active | not proven inside VIO |
| LEAP-VO (CVPR 2024), [code](https://github.com/wrchen530/leapvo) | long-term tracking that flags dynamic tracks | licence unclear | monocular, desktop GPU |

## Recommendations (P620 2 GB + 16 cores now, A100 later)

1. **IMU-aided rejection first** (cheap, CPU, general): gyro-seeded KLT; 2-point known-rotation RANSAC (+1-point stereo), portable from Kimera-VIO (BSD-2); per-track rotation-compensated residual-flow test against the inlier model; later DynaVINS-style back-end weighting. Read msckf_vio's design, do not copy its code.
2. **Masking**: build the static ego-region prior from our own rejection statistics; then YOLO11n-seg for people on the P620; EgoHOS only offline to measure how often hands matter; avoid Mask R-CNN-class models.
3. **Learned features**: XFeat on CPU for re-detection in dark/low-texture stretches, KLT kept for precision; SuperPoint (MIT retrain) or ALIKED + LightGlue on the A100 later; AirSLAM as a benchmark reference; avoid DISK, DarkFeat.
4. **Learned VO**: none now; DBA-Fusion as a single A100 diagnostic later; avoid CoTracker3 (licence).
