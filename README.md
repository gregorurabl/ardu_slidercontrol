# Slidercontrol V2.1
### Motorized Camera Slider — Sources & Hardware Documentation

**Author:** Gregor Urabl | [gregorurabl.at](https://gregorurabl.at)  
**Version:** 2.1  
**Platform:** Arduino Mega 2560 (AZ-Delivery Clone)  
**Slider:** Rollei / iFootage Shark S1

---

## Table of Contents

1. [Sources & Libraries](#1-sources--libraries)
   - [1.1 Project Base](#11-project-base)
   - [1.2 Arduino Libraries](#12-arduino-libraries)
2. [Hardware](#2-hardware)
   - [2.1 Main Components](#21-main-components)
   - [2.2 Hardware History & Incidents](#22-hardware-history--incidents)
   - [2.3 Stepper Motor & Gearbox](#23-stepper-motor--gearbox)
   - [2.4 Camera Trigger Circuit](#24-camera-trigger-circuit)
   - [2.5 Optional Ultrasonic End-Stop Sensor](#25-optional-ultrasonic-end-stop-sensor)
3. [Pin Reference (Arduino Mega 2560)](#3-pin-reference-arduino-mega-2560)
   - [3.1 TFT Display](#31-tft-display)
   - [3.2 Touchscreen (Resistive)](#32-touchscreen-resistive)
   - [3.3 Stepper Motor Driver (A4988)](#33-stepper-motor-driver-a4988)
   - [3.4 Sonar / Camera Trigger (shared)](#34-sonar--camera-trigger-shared)

---

## 1. Sources & Libraries

### 1.1 Project Base

This project is based on a guide by Marco Kleine-Albers (Mega-Testberichte.de) and was adapted and extended for use with Adafruit TFT and MobaTools by Gregor Urabl (gregorurabl.at), optimized for the Rollei/iFootage Shark S1 slider and a planetary-geared stepper motor.

| Source | Details | URL |
|---|---|---|
| Original Guide | Marco Kleine-Albers, Mega-Testberichte.de — complete build guide incl. schematic, parts list and software base | [mega-testberichte.de/artikel/kameraslider-motorisieren](https://www.mega-testberichte.de/artikel/kameraslider-motorisieren) ✅ |
| Adaptation & Extension | Gregor Urabl (gregorurabl.at) — adapted for Adafruit TFT & MobaTools, optimized for planetary geared stepper, camera trigger extension | [gregorurabl.at](https://gregorurabl.at) |
| Display | Niunion 3.5" TFT LCD Shield, 480×320, 8-bit parallel, resistive touchscreen, MCUFRIEND_kbv-compatible — ASIN: B08KG51VLW | [amazon.de](https://www.amazon.de/dp/B08KG51VLW) ✅ |
| Motor Mount (3D Print) | Parametric mount for iFootage Shark S1 motorization. Author: Benjamin (Hamburg). Original page no longer available. | mein-slider.de/ifootage-shark-s1-motorhalterung ❌ offline |
| Camera Trigger Reference | Martyn Currey — "Using an Arduino and an optocoupler to activate a camera shutter" — basis for optocoupler circuit design, resistor calculation and jack pinout | [martyncurrey.com/activating-the-shutter-release](https://www.martyncurrey.com/activating-the-shutter-release/) ✅ |
| Microstepping Reference | A4988 driver pin mapping and microstepping mode table | [lastminuteengineers.com](https://lastminuteengineers.com/a4988-stepper-motor-driver-arduino-tutorial/) ✅ |
| A4988 Product & Datasheet | Pololu A4988 stepper driver carrier — official product page incl. schematic, pinout and datasheet | [pololu.com/product/1182](https://www.pololu.com/product/1182) ✅ |

### 1.2 Arduino Libraries

| Library | Purpose | Source |
|---|---|---|
| Adafruit_GFX | Core graphics library | Adafruit Industries |
| Adafruit_TFTLCD | TFT display driver | Adafruit Industries |
| TouchScreen | Resistive touchscreen input | Adafruit Industries |
| MCUFRIEND_kbv | Hardware-specific TFT driver | David Prentice (GitHub) |
| MobaTools | Stepper motor & timer control | MicroController.net |
| NewPing | HC-SR04 ultrasonic sensor | Tim Eckel (Arduino Library Manager) |

---

## 2. Hardware

### 2.1 Main Components

| Component | Description / Specification |
|---|---|
| Microcontroller | AZ-Delivery Arduino Mega 2560 Clone (replacement after hardware incident, see [2.2](#22-hardware-history--incidents)) |
| Display | 3.5" Parallel TFT Shield, MCUFRIEND_kbv-compatible, 480×320 px |
| Stepper Motor | Stepperonline 17HS19-1684s-PG14 — 1.8°/step — Planetary Gearbox 1:14 |
| Motor Driver | A4988 (final version; TMC2209 tested previously, see [2.2](#22-hardware-history--incidents)) |
| Slider Platform | Rollei / iFootage Shark S1 |
| Camera Trigger | 4N33 optocoupler + 390 Ω resistor + 2.5 mm TRS jack |
| Ultrasonic Sensor (opt.) | HC-SR04 (end-stop safety) |

---

### 2.2 Hardware History & Incidents

#### TMC2209 V2.0 — tested, not used in final version

A test with a TMC2209 V2.0 Ultra Silent 2.5A stepper driver resulted in a cable fire and the burnout of the Arduino Mega's DC-In voltage regulator. The driver was also destroyed in the process. The exact root cause could not be conclusively determined; possible contributing factors include undersized wiring, a pre-existing defect in the DC-In regulator, or an overcurrent condition caused by the driver.

Apart from slightly quieter motor operation, the TMC2209 showed no meaningful improvement in motion smoothness compared to the A4988. The stepper motor's planetary gearbox (1:14) already provides inherently smooth and consistent motion, which largely eliminates the benefit of Stealthchop. The final version therefore uses the A4988.

#### AZ-Delivery Mega 2560 Clone — replacement after hardware incident

Following the failure of the original Arduino Mega 2560, the system runs successfully on an AZ-Delivery Mega 2560 clone. Pin mapping and feature set are fully compatible with the original; all documented functions operate reliably on the clone.

---

### 2.3 Stepper Motor & Gearbox

The Stepperonline 17HS19-1684s-PG14 features an integrated planetary gearbox with a 1:14 ratio, providing high holding torque at low RPM — well suited for smooth, consistent slider travel. Microstepping is disabled in firmware because the gearbox already provides sufficient mechanical smoothing.

| Parameter | Value |
|---|---|
| Step angle | 1.8° (200 full steps/rev) |
| Gearbox ratio | 1:14 |
| Microstepping | Disabled (pins M1–M3 NC) |
| Steps/rev in firmware | 3200 (200 × 16) — constant retained for reference |

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

The Canon N3 connector places approximately 3.2V on the shutter and focus lines — **this voltage is supplied by the camera itself**, not by the Arduino. Triggering is achieved by **shorting the shutter line to ground** via the optocoupler. The optocoupler ensures there is no electrical connection between the Arduino circuit and the camera circuit, protecting the camera from any voltage on the controller side.

#### Circuit

```
Arduino D47 ──── R1 (390 Ω) ──── 4N33 Pin 1 (Anode)
                                  4N33 Pin 2 (Cathode) ──── Arduino GND
                                  4N33 Pin 5 (Collector) ── Jack Tip   ──[cable]── N3 Shutter (~3.2V)
                                  4N33 Pin 4 (Emitter) ──── Jack Sleeve ──[cable]── N3 GND
                                  4N33 Pin 3 (Base) ──── NC
                                  Jack Ring ──── NC         ──[cable]── N3 Focus (not triggered)
```

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

An HC-SR04 ultrasonic module can be used as an end-stop safety mechanism. It stops the motor automatically when an obstacle (e.g. the end of the slider rail) is detected within 7 cm. The module shares pins D47 and D49 with the camera trigger — **only one module can be connected at a time.**

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

## 3. Pin Reference (Arduino Mega 2560)

### 3.1 TFT Display

The PCB silkscreen uses the prefix `LCD_` (not `TFT_`). The signal `tft_CD` in firmware corresponds to `LCD_RS` on the board — RS (Register Select) and CD (Command/Data) are the same signal: LOW = command, HIGH = data.

| Firmware Name | PCB Label | Arduino Mega Pin | Notes |
|---|---|---|---|
| tft_CS | LCD_CS | A3 | Chip Select |
| tft_CD | **LCD_RS** | A2 | Register Select (= Command/Data) |
| tft_WR | LCD_WR | A1 | Write |
| tft_RD | LCD_RD | A0 | Read |
| tft_RST | LCD_RST | A4 | Reset (can also connect to Arduino RST) |
| tft_D0 – tft_D1 | LCD_D0, LCD_D1 | 8, 9 | 8-bit data bus (low bits) |
| tft_D2 – tft_D7 | LCD_D2 – LCD_D7 | 2, 3, 4, 5, 6, 7 | 8-bit data bus (high bits) |
| *(not used)* | SD_SS, SD_DI, SD_DO, SD_SCK | 10, 11, 12, 13 | SD card interface — not used in this project |

### 3.2 Touchscreen (Resistive)

| Signal | Arduino Mega Pin | Notes |
|---|---|---|
| YP | A1 | Analog pin — shared with tft_WR |
| XM | A2 | Analog pin — shared with tft_CD |
| YM | 7 | Digital pin |
| XP | 6 | Digital pin |

> A1 and A2 are shared between the TFT data bus and the resistive touchscreen. This is handled by the MCUFRIEND_kbv and TouchScreen libraries automatically.

### 3.3 Stepper Motor Driver (A4988)

#### Control Pins (Arduino → A4988)

| Signal | Arduino Mega Pin | A4988 Pin | Notes |
|---|---|---|---|
| ENABLE | 23 | ENABLE | Active LOW — motor disabled by default |
| STEP | 25 | STEP | Step pulse |
| DIR | 27 | DIR | Direction |
| M1 | A8 | MS1 | Microstepping bit 1 — NC (disabled) |
| M2 | A9 | MS2 | Microstepping bit 2 — NC (disabled) |
| M3 | A10 | MS3 | Microstepping bit 3 — NC (disabled) |
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
| VMOT | 12V PSU (+) | Motor supply voltage — 8–35V supported |
| GND (power side) | 12V PSU (−) | Motor ground |

**100 µF electrolytic capacitor** across VMOT and GND, placed as close to the A4988 as possible. Protects the driver from voltage spikes caused by the motor's inductance.

#### Motor Coils (A4988 → Stepper)

| A4988 Pin | Stepper Wire | Coil |
|---|---|---|
| 1A | — | Coil A, terminal 1 |
| 1B | — | Coil A, terminal 2 |
| 2A | — | Coil B, terminal 1 |
| 2B | — | Coil B, terminal 2 |

> Coil assignment and wire color depend on the specific motor. For the **17HS19-1684s-PG14** consult the datasheet. Swapping both wires of one coil reverses that coil's polarity and changes rotation direction — equivalent to toggling DIR.

### 3.4 Sonar / Camera Trigger (shared)

| Signal | Arduino Mega Pin | Notes |
|---|---|---|
| TRIGGER_PIN | 47 | Sonar: trigger output — Camera: shutter pulse (LOW-active) |
| ECHO_PIN | 49 | Sonar: echo input — Camera: not used |

> **D47 and D49 are shared between the sonar module and the camera trigger.** Automatic detection at startup determines which module is active. Never connect both simultaneously.
