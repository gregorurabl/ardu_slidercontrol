# Slider Remote Control — User Manual

**Application:** `slider_remote_en`  
**Controller firmware:** Slidercontrol V2.1.2  
**Communication:** USB Serial @ 115200 baud

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
   - [2.1 Windows](#21-windows)
   - [2.2 Linux](#22-linux)
   - [2.3 macOS](#23-macos)
3. [Build Instructions — Self-Contained Binary](#3-build-instructions--self-contained-binary)
   - [3.1 Windows](#31-windows)
   - [3.2 Linux](#32-linux)
   - [3.3 macOS](#33-macos)
4. [Application Functions](#4-application-functions)
   - [4.1 Connection Bar](#41-connection-bar)
   - [4.2 Normal Tab](#42-normal-tab)
   - [4.3 Timelapse Tab](#43-timelapse-tab)
   - [4.4 Action Buttons](#44-action-buttons)
   - [4.5 Preset System](#45-preset-system)
   - [4.6 Log Output](#46-log-output)
   - [4.7 Calibration Bar](#47-calibration-bar)
5. [Calibration System](#5-calibration-system)
   - [5.1 Overview and Purpose](#51-overview-and-purpose)
   - [5.2 Calibration Run — Section 1: Slider Length](#52-calibration-run--section-1-slider-length)
   - [5.3 Calibration Run — Section 2: Speed Calibration](#53-calibration-run--section-2-speed-calibration)
   - [5.4 Loading a Saved Calibration](#54-loading-a-saved-calibration)
   - [5.5 Speed Percentage Mapping](#55-speed-percentage-mapping)
6. [Example Commands](#6-example-commands)
   - [6.1 Normal Run](#61-normal-run)
   - [6.2 Timelapse](#62-timelapse)

---

## 1. Overview

Slider Remote Control is a desktop GUI for the Slidercontrol V2.1.2 Arduino firmware. It communicates with the controller over a standard USB serial connection and provides a graphical interface for all four operating modes:

- **Normal Run** — single-pass movement over a set distance at constant speed
- **Manual Run** — continuous free-rotation until stopped; used for positioning and calibration
- **Timelapse** — stepped sequence with configurable delay, exposure time, and subdivisions
- **Return to Home (RTH)** — returns the slider to the start position

The application is built with Python, CustomTkinter, and pyserial. It runs from source or as a self-contained single-file binary produced by PyInstaller.

---

## 2. Installation

### Prerequisites (all platforms)

- Python 3.10 or later
- pip

### 2.1 Windows

1. Download and install Python from [python.org](https://python.org). During setup, check **"Add Python to PATH"**.

2. Open Command Prompt and install the dependencies:

   ```
   pip install customtkinter pyserial
   ```

3. Navigate to the project folder and start the application:

   ```
   cd path\to\slider_remote_en
   python main.py
   ```

4. **USB driver:** If the Arduino is not listed as a COM port, install the CH340 driver (AZ-Delivery clones) or the official Arduino driver. Re-plug the USB cable after installation.

### 2.2 Linux

1. Ensure Python 3 and pip are installed:

   ```
   sudo apt install python3 python3-pip
   ```

2. Install dependencies:

   ```
   pip3 install customtkinter pyserial
   ```

3. Grant serial port access (required on most distributions):

   ```
   sudo usermod -aG dialout $USER
   ```

   Log out and back in for the group change to take effect.

4. Start the application:

   ```
   cd path/to/slider_remote_en
   python3 main.py
   ```

5. The port appears as `/dev/ttyUSB0` or `/dev/ttyACM0`. Verify with `ls /dev/tty*` before and after plugging the USB cable if no port is detected.

### 2.3 macOS

1. Install Python 3 via [python.org](https://python.org) or Homebrew:

   ```
   brew install python
   ```

2. Install dependencies:

   ```
   pip3 install customtkinter pyserial
   ```

3. Start the application:

   ```
   cd path/to/slider_remote_en
   python3 main.py
   ```

4. The port appears as `/dev/cu.usbserial-*` or `/dev/cu.usbmodem*`. If macOS blocks the driver, open **System Settings → Privacy & Security** and approve the kernel extension.

---

## 3. Build Instructions — Self-Contained Binary

A single-file binary requires no Python installation on the target machine. The build script `build.py` in the project root automates this via PyInstaller.

### Prerequisites (all platforms)

```
pip install pyinstaller customtkinter pyserial
```

### 3.1 Windows

```
cd path\to\slider_remote_en
python build.py
```

The binary is created at `dist\SliderRemote.exe`. It can be copied to any Windows machine and run without a Python installation. CustomTkinter theme files are bundled automatically via the `--collect-data customtkinter` flag in `build.py`.

### 3.2 Linux

```
cd path/to/slider_remote_en
python3 build.py
```

The binary is created at `dist/SliderRemote`. Mark it executable if needed:

```
chmod +x dist/SliderRemote
./dist/SliderRemote
```

The binary is linked against the glibc version present at build time. Build on the oldest target distribution for maximum compatibility.

### 3.3 macOS

```
cd path/to/slider_remote_en
python3 build.py
```

The binary is created at `dist/SliderRemote`. The `--windowed` flag suppresses the terminal window. On Apple Silicon, build natively on an M-series Mac to produce an arm64 binary.

If macOS Gatekeeper blocks the binary on first launch, right-click → **Open**, or run:

```
xattr -d com.apple.quarantine dist/SliderRemote
```

### Manual PyInstaller invocation

```
pyinstaller --onefile --windowed --name SliderRemote --collect-data customtkinter main.py
```

---

## 4. Application Functions

### 4.1 Connection Bar

Located at the top of the window.

| Control | Function |
|---|---|
| Port dropdown | Lists all available serial ports detected at startup |
| Refresh | Re-scans serial ports without restarting the application |
| Connect / Disconnect | Opens or closes the serial connection to the selected port |
| Status indicator | Shows **Connected** (green) or **Disconnected** (red) |

The application connects at **115200 baud** with a 1-second read timeout. The connection is managed in a background thread; the UI remains responsive at all times.

**Auto-connect:** On startup, if a serial port is detected, the application begins a 5-second countdown and connects automatically. During the countdown the Connect button displays `Cancel (Xs)` in red. Clicking it cancels the auto-connect and leaves the port disconnected. Auto-connect only runs once per application launch; subsequent connections must be initiated manually.

When a connection is opened, the serial handler waits 2 seconds for the Arduino to finish its reset cycle (triggered by DTR on port open) before sending any data.

If no port is found, the dropdown shows "No port found" — verify the USB connection and, on Linux, confirm group membership (see Section 2.2).

---

### 4.2 Normal Tab

Controls for a single-pass slider movement at constant speed.

**Speed (10–100%)**  
Motor speed as a percentage of the maximum. Internally converted to steps/s (`steps = pct × 12`), giving a range of 120–1200 steps/s.

**Distance (steps)**  
Travel distance in motor steps. A cm conversion is displayed below the slider and updates in real time when a calibration is loaded (see Section 5). Without a calibration, the cm value falls back to the `STEPS_PER_MM` constant in `config.py`.

Three shortcut buttons are available below the distance slider:

- **Short** — sets the distance to 17 000 steps (half-length preset)
- **Long** — sets the distance to 34 000 steps (full-length preset)
- **Forward / Reverse** — toggles the motor direction. The button label and color reflect the current selection (green = Forward, red = Reverse). Direction is encoded as a sign on the distance value sent to the controller.

**Ramp (steps)**  
Acceleration and deceleration distance in steps. The motor ramps up over this many steps and ramps down symmetrically before stopping. The slider maximum is dynamically capped at `distance / 2`. Set to `0` to disable ramping.

A **progress bar** is shown below the tab during an active Normal run. Progress is time-based (steps / speed), as the firmware does not stream step-by-step serial feedback for Normal mode.

---

### 4.3 Timelapse Tab

Controls for a stepped timelapse sequence with optional camera shutter trigger.

**Speed (10–100%)**  
Applied to each individual inter-step movement. Conversion identical to Normal tab.

**Distance (steps)**  
Total travel distance. Shortcut buttons (Short / Long) and direction toggle (Forward / Reverse) are identical to the Normal tab.

**Delay (s)**  
Pause duration in seconds at each timelapse stop, excluding the exposure time. Range: 0–900 s.

**Exposure Time**  
Shutter speed selector using standard photography values (30 s down to 1/8000 s). Available as a slider (by index) and a linked dropdown. The exposure time is added to the delay value before the command is sent — the controller receives the combined total as its wait duration, ensuring the motor does not move during the exposure.

**Subdivisions**  
Number of stops the total distance is divided into. The slider travels `distance / subdivisions` steps per move. Minimum: 2. Range: 2–1000.

**Estimated Runtime**  
A calculated total timelapse duration, displayed below the subdivisions control and updated whenever any parameter changes. Formula:

```
total = subdivisions × (travel_time + 0.05 s overhead + exposure_s + delay_s) + 5 s end wait
```

If a calibration is loaded, `travel_time` per sub-step is interpolated from the speed calibration table. Without calibration it is estimated as `steps / speed_steps_per_s`.

The runtime field is also editable: enter a target duration in `h:mm:ss`, `m:ss`, or plain seconds and the required delay is back-calculated automatically.

> Ramp is not available for Timelapse mode. The firmware does not apply ramping to individual timelapse sub-steps.

---

### 4.4 Action Buttons

Four large buttons send immediate commands to the controller. All buttons require an active connection; a warning dialog is shown if the port is not connected. A 500 ms debounce prevents accidental rapid repeated sends.

**NORMAL START**  
Validates Normal tab parameters and sends a `normal` command. The progress bar starts immediately. Invalid parameters trigger a validation dialog before any command is sent.

**MANUAL START / STOP**  
Toggles continuous free rotation. First press sends a `start` command and changes the button label to **STOP** (red). Second press sends a `stop` command and restores the original label and color. The controller reports the exact step count traveled after stopping via serial.

**TIMELAPSE START**  
Validates Timelapse tab parameters and sends a `timelapse` command. The combined wait time (`delay + exposure_s`) is sent as the `time` field. After the sequence completes, the controller automatically performs RTH; the application waits 35 s before resetting the connection to allow the return to finish.

**RTH (Return to Home)**  
Sends an `rth` command. The controller reverses the motor and returns to the position it held when the session started — the point at which the Arduino's internal step counter was at zero (i.e. where the slider physically was when the controller was powered on or last reset). Speed is determined by the current speed setting on the controller's TFT display.

---

### 4.5 Preset System

Located in the utility row below the action buttons.

**Save Preset**  
Writes all current parameter values from both tabs to a `.json` file. Includes speed, distance, ramp, direction, delay, exposure index, and subdivision count for both Normal and Timelapse.

**Load Preset**  
Restores all tab values from a selected `.json` file. A negative `distance_steps` value encodes Reverse direction; positive encodes Forward. An error dialog identifies any missing or invalid fields.

Preset JSON structure:

```json
{
  "name": "My Preset",
  "normal_speed_pct": 50.0,
  "normal_distance_steps": 33000,
  "normal_ramp_steps": 0,
  "tl_speed_pct": 30.0,
  "tl_distance_steps": 33000,
  "tl_ramp_steps": 0,
  "tl_time_s": 30,
  "tl_subdivisions": 10,
  "tl_exposure_idx": 12
}
```

The `presets/` folder is created automatically on first save.

---

### 4.6 Log Output

A scrolling read-only text field displaying all application events.

| Control | Function |
|---|---|
| Timestamps: ON / OFF | Toggles `[HH:MM:SS]` prefixes on all log entries. State reflected in button color (green = on). |
| Export Log | Saves the current log content to a `.txt` file. |
| Clear Log | Clears all log entries immediately. |

Incoming controller messages are prefixed with `Controller:`. High-frequency step-counter progress messages are suppressed from the log and consumed internally for the progress bar only.

---

### 4.7 Calibration Bar

Located at the bottom of the window.

| Control | Function |
|---|---|
| Load Calibration | Opens a previously saved `.json` calibration file and activates it in memory |
| Calibration Run | Opens the calibration modal window (requires active connection) |
| Status label | Shows the loaded file name and slider length in steps, or "No calibration loaded" |

The calibration affects the cm distance readout, the Normal run progress bar accuracy, and the Timelapse runtime estimate. See Section 5 for the full procedure.

---

## 5. Calibration System

### 5.1 Overview and Purpose

The calibration system records two hardware-specific datasets:

- **Slider length in steps** — the exact step count for the full usable travel of the physical slider
- **Speed calibration table** — measured full-length travel durations at 10 speed levels (10%–100%)

These are used as follows:

- **Timelapse runtime estimate** — per-sub-step travel time is interpolated from the speed table
- **Normal run progress bar** — estimated from travel time, more accurate with calibration loaded
- **cm readout** — derived from `STEPS_PER_MM` in `config.py` (hardware-specific, must be set correctly)

Calibration is persisted as a `.json` file and can be re-loaded without repeating the procedure.

---

### 5.2 Calibration Run — Section 1: Slider Length

Measures the exact step count of the slider's full usable travel using a manual free run.

**Prerequisites:**

- Controller connected
- Slider carriage positioned at the **zero position** (the motor-mounted end of the rail)

**Procedure:**

1. Click **Calibration Run** in the calibration bar. The modal window opens.
2. In **Section 1 – Slider Length Calibration**, confirm the slider is at the zero position.
3. Click **Start**. A `start` command (Manual Run) is sent. The slider begins moving in the Forward direction at the current speed set on the controller's TFT display.
4. When the carriage approaches the physical end of the rail, click **Record**. A `stop` command is sent. The controller stops immediately and reports the exact step count via serial (`Manual Run stopped after X Steps.`).
5. The **Steps** field is populated automatically. The **Run Duration** field shows elapsed time.
6. If the value is not plausible (e.g. the slider was stopped early), adjust it manually in the Steps field.
7. Click **Apply Settings**. The slider length is stored and RTH is triggered automatically to return the carriage to the zero position.

After Apply, the **Confirm Zero Position** button in Section 2 becomes available.

---

### 5.3 Calibration Run — Section 2: Speed Calibration

Runs the slider at 10 preset speed levels (10%–100%) and records the full-length travel time for each. Results are used for runtime interpolation in the Timelapse tab.

**Prerequisites:**

- Section 1 completed and applied
- Slider carriage back at the zero position after RTH

**Procedure:**

1. Click **Confirm Zero Position** to confirm the carriage is at the start of the rail. This unlocks **Start Speed Calibration**.
2. Click **Start Speed Calibration**. The sequence runs fully automatically in a background thread.
3. For each of the 10 speed levels, the application sends a Normal Run command for the full slider length, waits for the `Target Reached` message, records the elapsed time, then sends RTH and waits for the return before proceeding to the next speed. A progress bar and result table update in real time.
4. Each individual run times out after 10 minutes. If a timeout occurs, the sequence is aborted, a warning dialog is shown, and the **Start Speed Calibration** button is re-enabled. Section 1 (slider length) does not need to be repeated — click **Start Speed Calibration** again to retry Section 2 from the beginning. The timeout is a deadlock safeguard: the calibration thread blocks waiting for a `Target Reached` message from the controller; without a timeout, a serial dropout or controller hang would freeze the calibration UI indefinitely. Under normal operating conditions the 10-minute limit is never reached.
5. When all 10 runs are complete, the **Save Calibration** button becomes active. The calibration is activated in memory immediately without requiring a save.
6. Click **Save Calibration** and choose a filename (e.g. `shark_s1_2025.json`).

Saved calibration file structure:

```json
{
  "slider_length_steps": 33600,
  "calibration_date": "2025-03-13",
  "speed_calibration": {
    "10": 182.4,
    "20": 94.1,
    "30": 63.5,
    "40": 48.2,
    "50": 38.9,
    "60": 32.7,
    "70": 28.1,
    "80": 24.6,
    "90": 22.3,
    "100": 21.7
  }
}
```

Values in `speed_calibration` are full-length travel times in seconds at each speed percentage.

---

### 5.4 Loading a Saved Calibration

Click **Load Calibration** and select a previously saved `.json` file. The file is validated (required keys: `slider_length_steps`, `speed_calibration`) and activated in memory. The status label updates to show the file name and slider length. The calibration is active for the current session only; it must be re-loaded after restarting the application.

---

### 5.5 Speed Percentage Mapping

The UI displays speed as 10–100%. The conversion to steps/s sent in the serial command is:

```
steps_per_second = percentage × 12
```

| Display | steps/s sent |
|---|---|
| 10% | 120 |
| 50% | 600 |
| 100% | 1200 |

The divisor `12` matches the TFT UI on the controller (`speed_set / 12 = displayed percentage`), ensuring both interfaces represent the same physical speed identically.

---

## 6. Example Commands

### 6.1 Normal Run

**Scenario:** Move the slider approximately 20 cm at 50% speed, no ramp, Forward direction.

| Parameter | Setting |
|---|---|
| Speed | 50% |
| Distance | 7874 steps |
| Ramp | 0 steps |
| Direction | Forward |

Serial command sent:

```
normal,600,7874,0,0,2
```

Field mapping: `mode=normal`, `speed=600 steps/s`, `distance=7874`, `ramp=0`, `time=0` (unused placeholder), `steps=2` (minimum placeholder).

---

### 6.2 Timelapse

**Scenario:** Full-length run (34 000 steps), 20 stops, 30 s delay, 1 s exposure, 30% speed, Forward direction.

| Parameter | Setting |
|---|---|
| Speed | 30% |
| Distance | 34 000 steps |
| Delay | 30 s |
| Exposure | 1 s |
| Subdivisions | 20 |
| Direction | Forward |

The application combines delay and exposure before sending: `total_wait = 30 + 1 = 31 s`.

Serial command sent:

```
timelapse,360,34000,0,31,20
```

Field mapping: `mode=timelapse`, `speed=360 steps/s`, `distance=34000`, `ramp=0`, `time=31 s`, `steps=20 subdivisions`.
