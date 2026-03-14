# =============================================================================
# config.py – Central configuration
# All hardware constants and UI limits in one place.
# Values sourced from Slidercontrol_V2_1.ino; deviations are commented.
# =============================================================================

# --- Serial connection --------------------------------------------------------
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 1          # Seconds before a read attempt times out

# --- Motor speed --------------------------------------------------------------
# speed_max in Arduino: 1200 steps/s (without microstepping)
# speed_min: 60 steps/s (lower bound from raise_speed_by / initial value)
SPEED_MIN_STEPS = 60
SPEED_MAX_STEPS = 1200
# 100% in the TFT UI equals speed_set / 12 == 100, i.e. 1200 steps/s
SPEED_PERCENT_DIVISOR = 12  # steps/s divided by this value = percentage

# --- Distance -----------------------------------------------------------------
# slider_length_long / slider_length_short from the .ino
DISTANCE_MIN_STEPS = 0
DISTANCE_MAX_STEPS = 36000
DISTANCE_SHORT_STEPS = 18000  # slider_length_short
DISTANCE_LONG_STEPS = 36000   # slider_length_long

# DUMMY VALUE – must be calibrated with the actual hardware setup!
# Formula: steps_per_mm = (motor full steps/rev * microstep divisor) / (belt pitch mm * drive pulley teeth)
# Example: Nema17, 200 steps/rev, 1/1 microstep, GT2 belt 2mm pitch, 20-tooth pulley: 200 / (2*20) = 5 steps/mm
STEPS_PER_MM = 39.37  # Calibrated: 1000 steps = 25.4 mm (1 inch)

# --- Ramp (acceleration) ------------------------------------------------------
# Upper limit is dynamic: max. distance / 2 (as enforced in the Arduino)
RAMP_MIN_STEPS = 0
RAMP_STEP_INCREMENT = 100   # ramp_steps_by from the .ino

# --- Timelapse ----------------------------------------------------------------
TIME_MIN_S = 0
TIME_MAX_S = 900            # 15 minutes, time_max from the .ino
TIME_INCREMENT_S = 1

SUBDIVISIONS_MIN = 2        # Minimum divisor, safety check also present in Arduino
SUBDIVISIONS_MAX = 1000     # steps_max from the .ino

# --- Presets ------------------------------------------------------------------
PRESETS_DIR = "presets"     # Folder relative to the binary / script
