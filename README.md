<<<<<<< HEAD
# TCL animation

Timed visual instructions and live head-pose feedback for research experiments.
Tracoline (TracInnovations, Danemark) is supported by default. 
Other equivalent tracking systems can be connected by implementing a converter to 
the shared `Pose` format (and an input source if they do not use UDP).

This package refactors `tcl_animation.py` (source release: 2024-03-29) 
into reusable protocol and pose modules with a command-line viewer.

Code cleanup and formatting were performed with the assistance of AI.

A blue outline marks the target; a red square shows the incoming pose, including
in-plane rotation. A warning appears during the five seconds preceding each step.

Associated publication: Zariry et al. (2026), **Intra-MRI Head Motion Tracking and
Correction: A Quantitative In Vivo Evaluation Framework**, *NMR in Biomedicine*,
39(9), e70368. [DOI: 10.1002/nbm.70368](https://doi.org/10.1002/nbm.70368).
--> Citation metadata is provided in `CITATION.cff`.

## Installation

Python 3.10 or newer is required. From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m tcl_animation --demo
```

On Linux/macOS, use `python3 -m venv .venv` and `.venv/bin/python`.
For development, install with `python -m pip install -e .` in your environment.
Only NumPy, SciPy, and Pygame are required. No global keyboard hooks, screeninfo,
external fonts, or administrator access are needed.

## Run

```powershell
# Synthetic pose; windowed by default
.\.venv\Scripts\python.exe -m tcl_animation --demo --protocol Trial

# TCL tracker sending to this computer's UDP port 6000
.\.venv\Scripts\python.exe -m tcl_animation --protocol 4_right --fullscreen --display 0

# Custom schedule with optional pose logging
.\.venv\Scripts\python.exe -m tcl_animation --protocol-file examples/custom_protocol.json --log session.csv

# Translation feedback with a stationary reference target
.\.venv\Scripts\python.exe -m tcl_animation --translation --recenter
```

Press **Space** or **Escape**, or close the window, to exit. The window must have
keyboard focus. `--duration 30` ends the session after 30 seconds; otherwise it
runs until manually stopped. `--help` lists all options. `tcl-animation` is also
installed as a console command.

The timer starts once the display is ready, independently of packet arrivals.
After three seconds without a valid packet, a waiting status appears; the last
pose stays visible and the target schedule continues. There is no scanner trigger
synchronization. Demo data are synthetic and explicitly labeled in the window
and CSV; the translation demo has zero displacement.

## Protocols and units

Built-ins: `Trial`, `ref`, `test_FL`, `2d_long`, `4d_long`, `4d`, `8d_diag`,
`8d4d`, `RL_8d4d`, `UD_8d4d`, `2_right`, `4_right`, `2_up`, `4_up`, `2_left`,
`4_left`, `4_down`. Values are stored in `src/tcl_animation/protocols.json`.

Each event has `name`, `sec`, `x`, and `y`. `sec` is elapsed session time;
`x` and `y` are **increments**, not absolute positions. Right and down are
positive screen directions. For example, `Trial` moves by (4, 0) at 10 s,
(-4, -4) at 20 s, and (-4, 4) at 30 s. Its cumulative final offset is (-4, 0).
Names such as `2m` in the original source are retained as labels; the `sec`
field defines the actual timing. Schedules must be ordered with finite values
and nonnegative times. They hold the final target after the last event.

Default scale is **30 pixels per degree** in rotational mode, matching the
original active `d2p()` function. This is a fixed display gain, not a calibrated
visual-angle conversion. In translation mode it is 30 pixels per tracker unit;
the source does not specify physical translation units. `--scale` changes this
gain. The unused `rot2dist()` monitor geometry calculation is not used here.

`--translation` forces `ref`, as in the source, and overrides custom protocols.
`--recenter` subtracts the initial displayed horizontal/vertical pose. It is
automatic for `RL_8d4d` and `UD_8d4d`. Roll is not recentered.

## Connect TCL or another tracking system

The architecture separates transport, system-specific conversion, and animation:

```text
TCL UDP packet -> UDPSource -> parse_tcl_packet -> tcl_to_pose -> Pose -> viewer
Other UDP data -> UDPSource -> your decoder(bytes) -----------> Pose -> viewer
SDK / serial  -> your PoseSource.poll() ---------------------> Pose -> viewer
```

The TCL adapter is explicitly defined in `src/tcl_animation/adapters/tcl.py`:
`parse_tcl_packet()` extracts a `TCLSample`, `tcl_to_pose()` transforms it to
the animation reference frame, and `decode_tcl_packet()` composes both.
The viewer never interprets TCL bytes itself. Other adapters must implement
their own coordinate transforms; they should not apply the TCL transform unless
their source has the same conventions.

### Other systems sending UDP

Write an importable Python function with this signature:

```python
from tcl_animation.pose import Pose

def decode_pose(data: bytes) -> Pose:
    # Parse your system's packet, calibrate its reference frame,
    # convert rotations to degrees and harmonize translation units.
    # Map the resulting components to the Pose contract below.
    ...
```

Run from a directory where your module can be imported, or install your adapter
package into the same Python environment:

```powershell
.\.venv\Scripts\python.exe -m tcl_animation --adapter my_tracker:decode_pose --port 6000

# Working JSON example; run from this repository's root
.\.venv\Scripts\python.exe -m tcl_animation --adapter examples.json_adapter:decode_pose
```

Example JSON datagram (UTF-8):

```json
{"frame": 1, "tx": 0, "ty": 0, "tz": 0, "rx": 2, "ry": 0, "rz": 4}
```

`examples/json_adapter.py` illustrates the conversion function. Its input is
already expressed in the animation frame; a real tracker adapter must supply
the appropriate axis mapping/calibration. Returning `Pose` avoids any requirement
to reproduce the TCL binary packet. `--packet-format` applies only to TCL.
Raise `ValueError` for malformed/unusable samples to skip them; adapter import,
return-type and programming errors remain visible. Pose components must be finite.
Custom adapters are local Python code executed in your environment.

### Pose convention

`Pose(frame, tx, ty, tz, rx, ry, rz, quality=1, frame_time_ms=0, table_position=0, flags=0)` 
contains transformed values, not raw tracker axes.
`rx`, `ry`, `rz` are degrees: positive `rz` moves right, positive `rx` moves
down, and `ry` rotates the red square according to Pygame's rotation convention.
Translation mode uses `tx` horizontally, `-tz` vertically and, for source
compatibility, `ty` as square rotation. Normalize translation to a chosen common
unit and set `--scale` accordingly; no physical unit is imposed by the viewer.

Unused metadata may use defaults. No tracker-specific transform is applied after
your decoder returns a pose. CSV `source` identifies `tcl`, the adapter name,
`custom-source`, or `demo`.


## TCL UDP interface and coordinates

Default bind: `0.0.0.0:6000`. Configure the sender's destination IP and port to
match the receiving computer, and allow incoming UDP through its firewall.
This application receives poses; it does not communicate with a scanner.

Default wire format `windows-le` is `struct` format `<ii8fiii`, **52 bytes**:

| Field | Wire type |
|---|---|
| Unused first field | int32 |
| Frame number | int32 |
| x, y, z | 3 × float32 |
| qr, qx, qy, qz | 4 × float32, scalar-first quaternion |
| Quality | float32 |
| Frame time (ms), cross-calibration table position, flags | 3 × int32 |

The Windows interpretation follows the original `il8fiii` format, whose native
`long` size and alignment vary by platform. Use `--packet-format native` only
if the sender uses the receiver's native ABI. This is not a verified vendor
protocol specification. Verify the sender's byte order and field layout before
collecting data. Trailing bytes are accepted; short, non-finite, and zero-norm
quaternion packets are ignored. Quality is recorded without threshold filtering.

Pose processing reproduces the active source equations:

1. Construct homogeneous pose A from translation and quaternion.
2. Compute `inverse(D @ A @ D)` with `D = diag(1, -1, 1, 1)`.
3. Extract `Tz, Ty, Tx` from its translation column, and extrinsic `xyz` Euler
   angles `Rx, Ry, Rz` in degrees from its rotation matrix.
4. Rotation feedback uses horizontal `Rz`, vertical `Rx`, square rotation `Ry`.
   Translation feedback uses horizontal `Tx`, vertical `-Tz`, rotation `Ty`,
   preserving the source's unusual use of a translation component as an angle.

The displayed components use 0.1-unit deadband. 

## Python API

```python
from tcl_animation.protocols import load_protocol, target_at
from tcl_animation.pose import Feedback
from tcl_animation.adapters.tcl import decode_tcl_packet

protocol = load_protocol("Trial")
dx, dy, warning = target_at(protocol, elapsed=20.0)
# decode_tcl_packet(datagram) -> transformed Pose
# Feedback(recenter=True).update(pose) -> horizontal, vertical, rotation
```

Importing the package or core modules does not initialize a display or socket.
The target calculation is stateless and supports repeated runs and replay.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover cumulative timing, warning boundaries, repeatability, packet decoding,
known coordinate transforms, malformed input, recentering, and deadband behavior.

GitHub Actions also runs a short headless demo on Windows and Linux.

## License

This software is released under the [MIT License](LICENSE).
Copyright (c) 2024-2026 Zakaria Zariry.
The license applies to this software; the associated publication has its own license.
=======
# MRImove
Python script to communicate visual instructions and control the subject's head movements in MRI
+ real-time feedback on the subject's head position (depending on the availability of a head movement tracking system)

** Will be available soon.
>>>>>>> origin/main
