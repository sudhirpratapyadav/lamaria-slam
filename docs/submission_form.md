# LaMAria leaderboard: submission form fields (saved 2026-10-05, from the owner)

Source: the "Create new submission" page at https://lamaria.ethz.ch (pasted by the owner). Method details are entered first;
the submission stays private until test-set results are uploaded, and the details can be edited later. Fields marked
required on the site are tagged (required) below; the rest are optional.

## Fields, as on the form

**Method**
- Short method name (up to 30 letters) (required), e.g. "Aria MPS"
- Full method name, e.g. "Aria Machine Perception Services"
- Method description
- Parameter settings
- Image input type (required): Monocular / Binocular
- Does your method utilise IMU data? (required): Yes / No

**Related publication**
- Title
- Author(s), comma-separated
- Venue
- Link

**Runtime & Links**
- Programming language(s) used, e.g. "C++ with CUDA"
- Hardware on which the method ran, e.g. "Core i7-4770K, GeForce 780 GTX, 32 GB RAM"
- Method website URL
- Availability (required): Not available / Binary available / Open source with copyleft (e.g. GPL) or other restrictive terms (e.g. non-commercial use only) / Open source, permissive (e.g. BSD, MIT)
- Method source code or download URL

**Submitter**
- By default the submitter's name and webpage are shown; an "Anonymous submission" box hides them (then enter no identifying information on the page).

## Draft answers (to be confirmed by the owner before anything is entered; nothing has been submitted)

- Short method name: to be chosen by the owner.
- Image input type: Binocular. IMU: Yes.
- Method description (draft): Causal stereo-inertial odometry built on Basalt's square-root VIO (patched: landmarks hosted in both cameras, robust initialisation with a 1 s window, gravity from the gyro-rotated accelerometer mean, linear velocity solve, weak gauge prior; failure detection and segment stitching so one pose is written per image), with the Aria factory IMU model and the measured camera-IMU time offset applied to the input. No loop closure, no map reuse.
- Parameter settings (draft): the current reference config name and its options (see `track_logs_v4/status.md`, "Reference"), the binary snapshot md5, and the commit.
- Programming languages: C++ (Basalt, Ceres backend), Python (driver, evaluation).
- Hardware: this PC, 16-core CPU, 15 GB RAM, no GPU used.
- Availability: Basalt is BSD-3; our patches and scripts: the owner decides the licence and whether the repository is public before choosing between "Binary available", copyleft or permissive. GPL is acceptable to the owner (AGENTS.md).
- Publication: none.
- Anonymous: owner's choice.

## Submission policy (from the site, pasted by the owner 2026-10-05)

- Continuous submissions to the test set are not allowed: parameter tuning is strictly limited to the training data, and test-set evaluation through the server is only for the **final** system.
- After any successfully evaluated test submission, updates to that method's test results are blocked for 24 hours, for all test sequences, even if the submission concerned only one of them.
- Multiple test-set submissions for the same method are not permitted, nor registering with multiple e-mail addresses; users or domains can be banned.

Consequences for us: one method entry, submitted once with the finished system (not an F17e today / F20 tomorrow sequence); every version decision is made on the training set before the single upload; the owner gives the go-ahead (purpose.md, AGENTS.md).

Related: submission format and rules in `README.md` (zip with `/slam/<sequence>.txt`, one pose per image, `world_from_imu`, 24 h between test updates) and `docs/benchmark_notes.md`.
