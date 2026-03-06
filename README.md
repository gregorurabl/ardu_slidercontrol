# Slidercontrol V2.1
### Motorized Camera Slider - Sources and Hardware Documentation

**Author:** Gregor Urabl | [gregorurabl.at](https://gregorurabl.at)  
**Version:** 2.1  
**Platform:** Arduino Mega 2560 (AZ-Delivery Clone)  
**Slider:** Rollei / iFootage Shark S1

> **Work in Progress** - This documentation is incomplete and subject to change without notice.

> **Disclaimer:** This project is shared for educational and personal reference purposes only. No support is provided. If you choose to replicate this project, you do so entirely at your own risk. The author accepts no responsibility for any damage to equipment, components, cameras, or any other property, nor for any personal injury, that may result from building or operating this or a similar system. Working with stepper motors, motor drivers and external power supplies involves voltages and currents that can cause permanent hardware damage if wired incorrectly. Always verify your wiring before applying power.

![image (8)](https://github.com/user-attachments/assets/612e09ca-9940-4b95-91f2-3881276d3afc)

---

## Table of Contents

1. [Sources & Libraries](#1-sources--libraries)
   - [1.1 Project Base](#11-project-base)
   - [1.2 Arduino Libraries](#12-arduino-libraries)
2. [Schematic](#schematic)
3. [Hardware](#2-hardware)
   - [2.1 Main Components](#21-main-components)
   - [2.2 Hardware History & Incidents](#22-hardware-history--incidents)
   - [2.3 Stepper Motor & Gearbox](#23-stepper-motor--gearbox)
   - [2.4 Camera Trigger Circuit](#24-camera-trigger-circuit)
   - [2.5 Optional Ultrasonic End-Stop Sensor](#25-optional-ultrasonic-end-stop-sensor)
   - [2.6 Controller Housing](#26-controller-housing)
4. [Pin Reference (Arduino Mega 2560)](#3-pin-reference-arduino-mega-2560)
   - [3.1 TFT Display](#31-tft-display)
   - [3.2 Touchscreen (Resistive)](#32-touchscreen-resistive)
   - [3.3 Stepper Motor Driver (A4988)](#33-stepper-motor-driver-a4988)
   - [3.4 Sonar / Camera Trigger (shared)](#34-sonar--camera-trigger-shared)

---


## Overview

Slidercontrol V2.1 is a fully self-contained motorized camera slider controller built around an Arduino Mega 2560. It drives a NEMA 17 stepper motor with planetary gearbox via an A4988 driver and provides a touchscreen UI on a 3.5" TFT shield. An optional ultrasonic sensor acts as an automatic end-stop, and a galvanically isolated camera trigger fires a Canon DSLR in sync with slider movement for timelapse sequences.

### Project History - Fork of Mega-Testberichte.de

This project started as a close implementation of the [Mega-Testberichte.de motorized slider guide](https://www.mega-testberichte.de/artikel/kameraslider-motorisieren) by Marco Kleine-Albers, which I recommend consulting alongside this documentation for build photos, a step-by-step walkthrough and additional context - it is the more visually complete reference.

Over time the project diverged significantly in both hardware and software. Key reasons for branching off:

- **MobaTools instead of AccelStepper:** The original guide uses AccelStepper, which generates blocking code during motor movement. When the ultrasonic end-stop sensor was added to the system (which predates the camera trigger), non-blocking motor control became a hard requirement - the sonar loop must keep running while the motor moves. MobaTools, developed by MicroBahner as an Arduino library for model railroaders (MOdel BAhn), provides a fully non-blocking stepper implementation and is optimized for fine-grained, precise movement control - exactly what smooth camera slider travel requires. The library origins in model rail applications mean it handles slow, precise, repeatable motion particularly well.
- **Planetary gearbox motor:** The motor choice with integrated 1:14 gearbox changes the tuning, microstepping strategy and speed range significantly compared to a standard NEMA 17.
- **Camera trigger system:** An entirely new hardware and software subsystem not present in the original guide.
- **Serial remote control:** Added for computer-controlled timelapse sequences.

The original guide remains the better starting point for someone new to the project. This documentation focuses on what has changed, the reasoning behind it, and the specifics of this particular build.

### Tested Payloads

The system has been tested with the following camera setups on a horizontal slider:

| Setup | Approx. Weight | Result |
|---|---|---|
| Canon EOS 7D + lens | ~1.5 kg | Reliable at all speed settings |
| Canon EOS 5D Mark IV + lens | ~2.5 kg | Reliable at all speed settings |
| Canon EOS C400 (fully rigged) | ~6 kg | Moved without issues |

The Canon C400 test in particular is notable - a cinema camera fully rigged approaches the practical limits of the slider platform itself.

#### Theoretical Maximum Load

The following is a rough estimate based on component datasheets. Real-world load capacity depends heavily on slider bearing condition, belt tension, incline angle and chosen speed.

**Motor output torque (at gearbox output shaft):**
```
T_out = T_motor × gear_ratio × efficiency
T_out = 0.52 Nm × 13.73 × 0.80 = ~5.7 Nm (theoretical peak)
```
The gearbox max permissible continuous torque is rated at **3 Nm**, which is the practical ceiling regardless of motor output.

**Force available at belt/drive:**  
Assuming a typical belt pulley radius of ~10–15 mm:
```
F = T / r = 3 Nm / 0.012 m = 250 N (~25 kg-equivalent)
```

**Real limiting factors (in order of likely constraint):**
1. **Slider rated payload** - the iFootage Shark S1 is rated for approximately 8 kg. This is the most restrictive limit for horizontal use.
2. **Gearbox max continuous torque** - 3 Nm (5 Nm momentary peak)
3. **Gearbox shaft max axial load** - 50 N (~5 kg linear force along the shaft axis)
4. **A4988 current limit** - set to ~1.18 A in this build (~70% of rated); higher current settings increase torque headroom but also heat

For horizontal use, the slider's own payload rating is the practical limit. The motor and gearbox have significant torque headroom for loads within that rating. Inclined or vertical use would require a separate calculation and is untested.

> These figures are theoretical estimates derived from component datasheets and standard engineering assumptions. They are not guaranteed values. Do not exceed the rated capacity of your slider platform.

### What This Project Does

The controller moves a camera along a slider rail at configurable speed, distance and direction. Three operating modes are available:

- **Normal Run** - moves the slider a set distance at a set speed, with optional return to start position
- **Manual Run** - continuous motor rotation for free-form positioning, start/stop via touchscreen
- **Timelapse** - divides the total travel into equal sub-steps, pauses at each position for a configurable delay, and optionally fires the camera shutter at every stop

All parameters (speed, distance, ramp, delay, subdivisions) are adjusted on the touchscreen. The controller can also be operated via serial commands over USB.

### What You Need

**Electronics**
| Item | Notes |
|---|---|
| Arduino Mega 2560 (or clone) | AZ-Delivery clone confirmed working |
| 3.5" parallel TFT LCD shield, 480×320 | MCUFRIEND_kbv-compatible |
| A4988 stepper driver breakout board | Check R_CS marking before use (see [3.3](#33-stepper-motor-driver-a4988)) |
| NEMA 17 stepper motor | 17HS19-1684s-PG14 with 1:14 planetary gearbox used here |
| 100 µF electrolytic capacitor | Motor supply decoupling, placed close to A4988 |
| 12V / 5A DC power supply | Motor supply |
| USB power bank or 5V supply | Arduino logic supply |
| 4N33 optocoupler + 390 Ω resistor | Camera trigger circuit (optional) |
| 2.5 mm TRS female jack | Camera trigger output (optional) |
| 2.5 mm male to Canon N3 female cable | Off-the-shelf adapter cable (optional) |
| HC-SR04 ultrasonic sensor | End-stop safety (optional, mutually exclusive with camera trigger) |

**Mechanical**
- Camera slider with accessible drive shaft (e.g. Rollei / iFootage Shark S1)
- 3D-printed motor mount adapted to your slider model (see [1.1 Sources](#11-project-base))

**Tools**
- Soldering iron
- Multimeter - required for A4988 current limit calibration

### Wiring Overview

```
USB Power Bank ──────────────────────── Arduino Mega 2560
                                               │
                         ┌─────────────────────┼──────────────────┐
                         │                     │                  │
                    TFT Shield            A4988 Driver        D47 / D49
                  (direct plug-in         VDD  ← 5V           Camera trigger
                   onto Mega headers)     GND  ← GND (logic)  or HC-SR04
                                          EN   ← D23
                                          STEP ← D25
                                          DIR  ← D27
                                               │
12V / 5A PSU ──── [100 µF] ──── VMOT          │
             └──────────────── GND (motor)    │
                                          1A / 1B / 2A / 2B
                                               │
                                         Stepper Motor
```

The TFT shield plugs directly onto the Arduino Mega headers - no separate display wiring required. Motor, A4988 and power supply are wired as a separate circuit. The camera trigger is a standalone optocoupler circuit connected to D47 and GND.

**Important:** The Arduino (logic) and the motor driver (power) use separate ground connections that share a common reference point only at the DC jack. See [Ground Separation](#33-stepper-motor-driver-a4988) for details.

### Serial / USB Remote Control

The controller can be operated remotely over USB via any serial terminal (e.g. Arduino Serial Monitor, PuTTY) at **115200 baud**.

Commands are comma-separated strings terminated with a newline (`\n`). Each field can optionally carry a label prefix using a colon (`label:value`) - the parser strips everything up to and including the last colon, so both formats are accepted.

**Command format:**

```
mode,speed,distance,ramp,time,steps
```

| Index | Field | Description |
|---|---|---|
| 0 | mode | `normal`, `timelapse`, or `rth` (case-insensitive) |
| 1 | speed | Motor speed (steps/s) |
| 2 | distance | Travel distance in steps |
| 3 | ramp | Ramp/acceleration length in steps |
| 4 | time | Timelapse delay between stops in seconds |
| 5 | steps | Number of timelapse subdivisions (minimum 2) |

**Examples:**

```
normal,600,33000,0,0,2
timelapse,400,33000,0,30,10
rth,0,0,0,0,0
```

Unused fields still need to be present as placeholders. For `rth`, all fields after index 0 are ignored. The controller responds with status messages over the same serial connection.

---

## 1. Sources & Libraries

### 1.1 Project Base

This project is based on a guide by Marco Kleine-Albers (Mega-Testberichte.de) and was adapted and extended for use with Adafruit TFT and MobaTools by Gregor Urabl (gregorurabl.at), optimized for the Rollei/iFootage Shark S1 slider and a planetary-geared stepper motor.

| Source | Details | URL |
|---|---|---|
| Original Guide | Marco Kleine-Albers, Mega-Testberichte.de - complete build guide incl. schematic, parts list and software base | [mega-testberichte.de/artikel/kameraslider-motorisieren](https://www.mega-testberichte.de/artikel/kameraslider-motorisieren) ✅ |
| Adaptation & Extension | Gregor Urabl (gregorurabl.at) - adapted for Adafruit TFT & MobaTools, optimized for planetary geared stepper, camera trigger extension | [gregorurabl.at](https://gregorurabl.at) |
| Display | Niunion 3.5" TFT LCD Shield, 480×320, 8-bit parallel, resistive touchscreen, MCUFRIEND_kbv-compatible - ASIN: B08KG51VLW | [amazon.de](https://www.amazon.de/dp/B08KG51VLW) ✅ |
| Motor Mount (3D Print) | Parametric mount for iFootage Shark S1 motorization. Author: Benjamin (Hamburg). Original page no longer available. | mein-slider.de/ifootage-shark-s1-motorhalterung ❌ offline |
| Camera Trigger Reference | Martyn Currey - "Using an Arduino and an optocoupler to activate a camera shutter" - basis for optocoupler circuit design, resistor calculation and jack pinout | [martyncurrey.com/activating-the-shutter-release](https://www.martyncurrey.com/activating-the-shutter-release/) ✅ |
| Microstepping Reference | A4988 driver pin mapping and microstepping mode table | [lastminuteengineers.com](https://lastminuteengineers.com/a4988-stepper-motor-driver-arduino-tutorial/) ✅ |
| A4988 Product & Datasheet | Pololu A4988 stepper driver carrier - official product page incl. schematic, pinout and datasheet | [pololu.com/product/1182](https://www.pololu.com/product/1182) ✅ |
| MobaTools Library | Arduino library by MicroBahner (f-pm+gh@mailbox.org). Originally developed for model railroaders (MOdel BAhn), optimized for precise, fine-grained stepper control - which maps directly to the needs of smooth camera slider movement. Used here as a non-blocking replacement for AccelStepper. | [github.com/MicroBahner/MobaTools](https://github.com/MicroBahner/MobaTools) ✅ |

### 1.2 Arduino Libraries

| Library | Purpose | Source |
|---|---|---|
| Adafruit_GFX | Core graphics library | Adafruit Industries |
| Adafruit_TFTLCD | TFT display driver | Adafruit Industries |
| TouchScreen | Resistive touchscreen input | Adafruit Industries |
| MCUFRIEND_kbv | Hardware-specific TFT driver | David Prentice (GitHub) |
| MobaTools | Stepper motor and timer control. Non-blocking implementation, originally developed for model railroaders (MOdel BAhn) by MicroBahner - optimized for fine-grained, precise movement. Replaces AccelStepper to enable concurrent sonar and motor operation. | [github.com/MicroBahner/MobaTools](https://github.com/MicroBahner/MobaTools) |
| NewPing | HC-SR04 ultrasonic sensor | Tim Eckel (Arduino Library Manager) |

---


## Schematic

![SliderControl_Schematic](https://github.com/user-attachments/assets/05a1f284-e010-41c4-a1aa-6b4b2ab373f1)

The KiCad schematic file is at `KiCad/Slidercontrol_V2_1_Corrected.kicad_sch`.

The schematic covers:
- Arduino Mega 2560 with all used pin connections
- A4988 driver with motor power supply, 100 µF decoupling capacitor and stepper motor
- Camera trigger circuit (4N33, R1, 2.5 mm jack)
- HC-SR04 ultrasonic sensor (optional, shared pins D47/D49)
- TFT shield pin mapping

In the meantime, refer to the pin reference tables in [Section 3](#3-pin-reference-arduino-mega-2560) and the circuit diagrams in [Section 2.4](#24-camera-trigger-circuit) and [Section 3.3](#33-stepper-motor-driver-a4988).

---


## 2. Hardware

### 2.1 Main Components

| Component | Description / Specification |
|---|---|
| Microcontroller | AZ-Delivery Arduino Mega 2560 Clone (replacement after hardware incident, see [2.2](#22-hardware-history--incidents)) |
| Display | 3.5" Parallel TFT Shield, MCUFRIEND_kbv-compatible, 480×320 px |
| Stepper Motor | Stepperonline 17HS19-1684s-PG14 - 1.8°/step - Planetary Gearbox 1:14 |
| Motor Driver | A4988 (final version; TMC2209 tested previously, see [2.2](#22-hardware-history--incidents)) |
| Slider Platform | Rollei / iFootage Shark S1 |
| Camera Trigger | 4N33 optocoupler + 390 Ω resistor + 2.5 mm TRS jack |
| Ultrasonic Sensor (opt.) | HC-SR04 (end-stop safety) |

---

### 2.2 Hardware History & Incidents

#### TMC2209 V2.0 - tested, not used in final version

A test with a TMC2209 V2.0 Ultra Silent 2.5A stepper driver resulted in a cable fire and the burnout of the Arduino Mega's DC-In voltage regulator. The driver was also destroyed in the process. The exact root cause could not be conclusively determined; possible contributing factors include undersized wiring, a pre-existing defect in the DC-In regulator, or an overcurrent condition caused by the driver.

Apart from slightly quieter motor operation, the TMC2209 showed no meaningful improvement in motion smoothness compared to the A4988. The stepper motor's planetary gearbox (1:14) already provides inherently smooth and consistent motion, which largely eliminates the benefit of Stealthchop. The final version therefore uses the A4988.

#### AZ-Delivery Mega 2560 Clone - replacement after hardware incident

Following the failure of the original Arduino Mega 2560, the system runs successfully on an AZ-Delivery Mega 2560 clone. Pin mapping and feature set are fully compatible with the original; all documented functions operate reliably on the clone.

---

### 2.3 Stepper Motor & Gearbox

The Stepperonline 17HS19-1684s-PG14 features an integrated planetary gearbox with a 1:14 ratio, providing high holding torque at low RPM - well suited for smooth, consistent slider travel. Microstepping is disabled in firmware because the gearbox already provides sufficient mechanical smoothing.

| Parameter | Value |
|---|---|
| Step angle | 1.8° (200 full steps/rev) |
| Gearbox ratio | 1:14 |
| Microstepping | Disabled (pins M1–M3 NC) |
| Steps/rev in firmware | 3200 (200 × 16) - constant retained for reference |

> **Note:** The 3200 steps/rev constant in the code reflects the full microstepping configuration. With the planetary gearbox and microstepping disabled, effective mechanical resolution differs. The constant is kept for potential use without the gearbox.

---

### 2.4 Camera Trigger Circuit

The camera trigger provides galvanic isolation between the Arduino and the camera using a 4N33 optocoupler. The Arduino is directly wired into the optocoupler circuit. The optocoupler output is connected via a soldered cable to a **2.5 mm TRS female jack** permanently mounted on the controller housing. From there, a commercially available **2.5 mm male to Canon N3 female adapter cable** connects to the camera.

The circuit design follows the approach described by Martyn Currey ([martyncurrey.com/activating-the-shutter-release](https://www.martyncurrey.com/activating-the-shutter-release/)), adapted for the 4N33 with a 390 Ω input resistor.

#### Signal Chain

```
Arduino D47
    │ (direct wiring)
    ▼
Optocoupler circuit (4N33 + R1 390 Ω)
    │ (soldered cable)
    ▼
2.5 mm TRS Female Jack  ←── permanently mounted on housing
    │ (commercial cable: 2.5 mm Male → Canon N3 Female)
    ▼
Camera (Canon N3)
```

#### How It Works

The Canon N3 connector places approximately 3.2V on the shutter and focus lines - **this voltage is supplied by the camera itself**, not by the Arduino. Triggering is achieved by **shorting the shutter line to ground** via the optocoupler. The optocoupler ensures there is no electrical connection between the Arduino circuit and the camera circuit, protecting the camera from any voltage on the controller side.

#### Circuit

```
Arduino D47 ──── R1 (390 Ω) ──── 4N33 Pin 1 (Anode)
                                  4N33 Pin 2 (Cathode) ──── Arduino GND
                                  4N33 Pin 5 (Collector) ── Jack Tip   ──[cable]── N3 Shutter (~3.2V)
                                  4N33 Pin 4 (Emitter) ──── Jack Sleeve ──[cable]── N3 GND
                                  4N33 Pin 3 (Base) ──── NC
                                  Jack Ring ──── NC         ──[cable]── N3 Focus (not triggered)
```

![CameraTrigger](https://github.com/user-attachments/assets/dd89f23e-06e8-402b-b35b-606da665f3c8)

#### 2.5 mm TRS Jack Pinout

| Contact | Connected to | Via adapter cable |
|---|---|---|
| Tip | 4N33 Pin 5 (Collector) | N3 Shutter |
| Ring | NC | N3 Focus (not used) |
| Sleeve | 4N33 Pin 4 (Emitter) | N3 GND |

#### Resistor Dimensioning

| Parameter | Value |
|---|---|
| Supply voltage | 5V (Arduino digital pin) |
| LED forward voltage (4N33) | ≈ 1.2V |
| Resistor | 390 Ω |
| LED current | (5V − 1.2V) / 390 Ω ≈ **9.7 mA** |
| 4N33 maximum I_F | 60 mA |
| Arduino pin max. current | 40 mA |

#### Trigger Pulse

Arduino drives `TRIGGER_PIN` (D47) `LOW` to close the optocoupler and short the N3 shutter pin to ground, then returns `HIGH` to release. Pulse duration is configurable in firmware (default: 100 ms).

> **Note:** Only the shutter contact is triggered. Focus is not connected. For cameras requiring focus + shutter simultaneously (e.g. bulb mode), the focus line would need to be wired in parallel.

---

### 2.5 Optional Ultrasonic End-Stop Sensor

An HC-SR04 ultrasonic module can be used as an end-stop safety mechanism. It stops the motor automatically when an obstacle (e.g. the end of the slider rail) is detected within 7 cm. The module shares pins D47 and D49 with the camera trigger - **only one module can be connected at a time.**

Module detection is automatic at startup: the firmware sends a single ping at maximum range. If a response is received, Sonar Mode is activated (green indicator on display). If the ping fails, Camera Mode is activated (blue indicator).

| Parameter | Value |
|---|---|
| TRIGGER_PIN | D47 (brown wire) |
| ECHO_PIN | D49 (black wire) |
| VCC | 5V (red wire) |
| GND | GND (white wire) |
| Max. ping distance | 200 cm (configurable) |
| Stop threshold | ≤ 7 cm |
| Ping interval | 50 ms (20× per second) |

---

### 2.6 Controller Housing

The housing used in early versions of this build is the enclosure published by Marco Kleine-Albers on Thingiverse: [thingiverse.com/thing:3344179](https://www.thingiverse.com/thing:3344179). It was printed and used through several beta versions.

The original STL files are included in this repository at `3D Print/Mega-Testberichte Slider-Case (Arduino Mega+Touch LCD Sainsmart) - 3344179/` as an unmodified reference baseline.

The housing was later modified to increase internal volume for the additional camera trigger wiring and to improve structural stability through thicker walls. Modified lid files are in `3D Print/Drive_Fork/`:

| File | Description |
|---|---|
| `deckel_displayseite.v2.stl` | Modified lid - flat variant, increased wall thickness |
| `deckel_displayseite.stl` | Modified lid - raised variant, additional height for cable and electronics volume |
| `deckel_unterseite.stl` | Lid underside (modifier body) |

<details>
<summary>Show Photos</summary>summary>
![image (9)](https://github.com/user-attachments/assets/3e00675c-9bf6-42bb-94b2-72b41b06fc5e)
![image (10)](https://github.com/user-attachments/assets/b407b3cb-b684-4bd1-9aa5-fee09aea446c)
![image (7)](https://github.com/user-attachments/assets/8d7ac38e-9bfa-4386-b78f-8393ffd9c3dc)
</details>

Original Housing before raising lid

### 2.7 Motor Drive - Direct Drive vs. Belt Drive

**Mega-Testberichte.de approach:** The original guide attaches the motor directly to the slider's existing drive belt via a gear adapter, effectively replacing the manual knob with a motor. This removes the ability to operate the slider by hand.

**mein-slider.de housing (used as base here):** The 3D-printed motor housing from mein-slider.de was specifically designed for the iFootage Shark S1 and preserves manual operability by using a separate add-on adapter rather than replacing the original drive belt. However, it routes motor torque through a dedicated secondary drive belt, which created the sourcing problem: no correctly sized belt could be found. The only available belt was too long to tension properly.

<details>
<summary>Show Photos</summary>summary>
![image (1)](https://github.com/user-attachments/assets/7f87cc37-3e26-4848-8b87-030039ecb564)
![image (2)](https://github.com/user-attachments/assets/4b8538b5-b228-4e78-84f2-9b9a01a2033c)
![image (3)](https://github.com/user-attachments/assets/746a09bd-04a1-4035-9f70-b4e28effbdca)
![image (4)](https://github.com/user-attachments/assets/de8bf87c-e76c-4417-a536-cbc389ef689a)
![image](https://github.com/user-attachments/assets/c1c4d273-ce9e-4c24-9468-c92c2bc1083e)
</details>
   
**Direct drive solution:** After several experiments scaling the motor housing, a direct drive variant was developed. The motor shaft couples directly to the slider's drive element via a printed adapter, with no belt or intermediate gears.

This turned out to be the better solution in every respect:
- Full motor torque delivered directly to the slider with no belt slip or stretch
- Fewer moving parts means fewer failure points
- Smaller and simpler housing
- Manual operability of the Shark S1 is retained through the add-on adapter design

Original drive STL files from the reference design are in `3D Print/Original_Drive_STL/`.

| File | Description |
|---|---|
| `gehaeuse_unterseite_v2.stl` | Motor housing - underside |
| `gehaeuse_motorseite_v02.stl` | Motor housing - motor-facing side |
| `antrieb_v02.stl` | Drive element / motor shaft adapter |

The iterative development process - including test prints, fit experiments and the final direct drive solution - is also documented in `Fotos_Videos/`.

---

### Repository Structure

```
/
├── 3D Print/
│   ├── Drive_Fork/                          # Modified direct drive and housing files
│   │   ├── antrieb_v02.stl
│   │   ├── deckel_displayseite.stl          # Lid raised variant
│   │   ├── deckel_displayseite.v2.stl       # Lid flat variant
│   │   ├── deckel_unterseite.stl
│   │   ├── gehaeuse_motorseite_v02.stl
│   │   └── gehaeuse_unterseite_v2.stl
│   ├── Mega-Testberichte Slider-Case (Arduino Mega+Touch LCD Sainsmart) - 3344179/
│   │   └── ...                              # Original Thingiverse files (unmodified)
│   └── Original_Drive_STL/                  # Original belt drive reference files
├── Datasheets/                              # Component datasheets
├── Fotos_Videos/                            # Build photos and videos
├── KiCad/
│   └── Slidercontrol_V2_1_Corrected.kicad_sch
└── README.md
```

---

### Planned Features

| Feature | Status |
|---|---|
| Timelapse runtime pre-calculation | Planned - display estimated total duration before a timelapse run starts, based on distance, subdivisions, delay and motor speed |


## 3. Pin Reference (Arduino Mega 2560)

### 3.1 TFT Display

The PCB silkscreen uses the prefix `LCD_` (not `TFT_`). The signal `tft_CD` in firmware corresponds to `LCD_RS` on the board - RS (Register Select) and CD (Command/Data) are the same signal: LOW = command, HIGH = data.

| Firmware Name | PCB Label | Arduino Mega Pin | Notes |
|---|---|---|---|
| tft_CS | LCD_CS | A3 | Chip Select |
| tft_CD | **LCD_RS** | A2 | Register Select (= Command/Data) |
| tft_WR | LCD_WR | A1 | Write |
| tft_RD | LCD_RD | A0 | Read |
| tft_RST | LCD_RST | A4 | Reset (can also connect to Arduino RST) |
| tft_D0 – tft_D1 | LCD_D0, LCD_D1 | 8, 9 | 8-bit data bus (low bits) |
| tft_D2 – tft_D7 | LCD_D2 – LCD_D7 | 2, 3, 4, 5, 6, 7 | 8-bit data bus (high bits) |
| *(not used)* | SD_SS, SD_DI, SD_DO, SD_SCK | 10, 11, 12, 13 | SD card interface - not used in this project |

### 3.2 Touchscreen (Resistive)

| Signal | Arduino Mega Pin | Notes |
|---|---|---|
| YP | A1 | Analog pin - shared with tft_WR |
| XM | A2 | Analog pin - shared with tft_CD |
| YM | 7 | Digital pin |
| XP | 6 | Digital pin |

> A1 and A2 are shared between the TFT data bus and the resistive touchscreen. This is handled by the MCUFRIEND_kbv and TouchScreen libraries automatically.

### 3.3 Stepper Motor Driver (A4988)

#### Control Pins (Arduino → A4988)

| Signal | Arduino Mega Pin | A4988 Pin | Notes |
|---|---|---|---|
| ENABLE | 23 | ENABLE | Active LOW - motor disabled by default |
| STEP | 25 | STEP | Step pulse |
| DIR | 27 | DIR | Direction |
| M1 | A8 | MS1 | Microstepping bit 1 - NC (disabled) |
| M2 | A9 | MS2 | Microstepping bit 2 - NC (disabled) |
| M3 | A10 | MS3 | Microstepping bit 3 - NC (disabled) |
| 5V | 5V | VDD | Logic supply |
| GND | GND | GND | Logic ground |

> RESET and SLEEP are bridged together on the A4988 breakout board (tied HIGH).

#### Ground Separation

The A4988 has two separate GND pins that must **not** be treated as a single connection:

| A4988 GND Pin | Connected to | Carries |
|---|---|---|
| GND (power side, next to VMOT) | 100 µF capacitor (−), then DC jack (−) | Motor current (up to 2A) |
| GND (logic side, next to VDD) | Arduino GND | Logic signals only (mA range) |

Both grounds share a common reference point at the power supply / DC jack, but should be routed separately on the PCB or in the schematic to avoid mixing high-current motor return paths with logic ground.

#### Motor Power (PSU → A4988)

| A4988 Pin | Connection | Notes |
|---|---|---|
| VMOT | 12V PSU (+) | Motor supply voltage - 8–35V supported |
| GND (power side) | 12V PSU (−) | Motor ground |

**100 µF electrolytic capacitor** across VMOT and GND, placed as close to the A4988 as possible. Protects the driver from voltage spikes caused by the motor's inductance.

#### Motor Coils (A4988 → Stepper)

| A4988 Pin | Stepper Wire | Coil |
|---|---|---|
| 1A | - | Coil A, terminal 1 |
| 1B | - | Coil A, terminal 2 |
| 2A | - | Coil B, terminal 1 |
| 2B | - | Coil B, terminal 2 |

> Coil assignment and wire color depend on the specific motor. For the **17HS19-1684s-PG14** consult the datasheet. Swapping both wires of one coil reverses that coil's polarity and changes rotation direction - equivalent to toggling DIR.


#### Current Limit Calibration (VREF)

The A4988 current limit must be set **before connecting the motor**. An incorrectly set current limit risks overheating or damaging the driver and motor.

**Required tools:** multimeter, small flathead screwdriver

**Formula (per Pololu):**

```
VREF = I_max x 8 x R_CS
```

| Variable | Description |
|---|---|
| VREF | Reference voltage to set (measured at potentiometer) |
| I_max | Target current limit in amps |
| R_CS | Current sense resistor value on the board |

**Determine R_CS first** by inspecting the two small SMD resistors next to the A4988 chip:

| Marking | R_CS value |
|---|---|
| R050 | 0.05 Ohm (original Pololu board) |
| R100 | 0.10 Ohm (most Chinese clones) |
| R200 | 0.20 Ohm |

**Measurement procedure:** Connect multimeter negative lead to GND, positive lead to the potentiometer wiper (the metal adjustment screw). Adjust the potentiometer while reading the voltage.

**Example calculation for the 17HS19-1684s-PG14 (rated 1.68 A):**

A conservative target of 70% of rated current reduces heat while maintaining reliable torque:

```
I_target = 1.68 A x 0.70 = 1.18 A
VREF (R100) = 1.18 x 8 x 0.10 = 0.94 V
VREF (R050) = 1.18 x 8 x 0.05 = 0.47 V
```

Per Mega-Testberichte.de, a VREF of **~0.8 V** on an R100 board was found to work well in practice with this motor type, providing reliable torque with acceptable heat generation.

> **Warning (per Pololu):** Never connect or disconnect the stepper motor while the driver is powered. This can permanently destroy the A4988. Set VREF before attaching the motor, and increase gradually from a low starting value.

### 3.4 Sonar / Camera Trigger (shared)

| Signal | Arduino Mega Pin | Notes |
|---|---|---|
| TRIGGER_PIN | 47 | Sonar: trigger output - Camera: shutter pulse (LOW-active) |
| ECHO_PIN | 49 | Sonar: echo input - Camera: not used |

> **D47 and D49 are shared between the sonar module and the camera trigger.** Automatic detection at startup determines which module is active. Never connect both simultaneously.
