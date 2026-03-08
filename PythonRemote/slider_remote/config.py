# =============================================================================
# config.py – Zentrale Konfiguration
# Alle Hardware-Konstanten und UI-Grenzen an einem Ort.
# Werte stammen aus Slidercontrol_V2_1.ino, Abweichungen sind kommentiert.
# =============================================================================

# --- Serielle Verbindung -------------------------------------------------------
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 1          # Sekunden, nach denen ein Leseversuch abbricht

# --- Motorgeschwindigkeit -------------------------------------------------------
# speed_max im Arduino: 1200 steps/s (ohne Microstepping)
# speed_min: 60 steps/s (unterer Wert aus raise_speed_by / Startbelegung)
SPEED_MIN_STEPS = 60
SPEED_MAX_STEPS = 1200
# 100% in der TFT-UI entspricht speed_set / 12 == 100, also 1200 steps/s
SPEED_PERCENT_DIVISOR = 12  # steps/s geteilt durch diesen Wert = Prozentwert

# --- Distanz ------------------------------------------------------------------
# slider_length_long / slider_length_short aus der .ino
DISTANCE_MIN_STEPS = 0
DISTANCE_MAX_STEPS = 34000
DISTANCE_SHORT_STEPS = 17000  # slider_length_short
DISTANCE_LONG_STEPS = 34000   # slider_length_long

# DUMMY-WERT – muss mit realem Messaufbau kalibriert werden!
# Formel: steps_per_mm = (Motor-Vollschritte/Umdrehung * Mikroschritt-Teiler) / (Zahnriemen-Pitch_mm * Zahnanzahl_Antriebsrad)
# Beispiel Nema17, 200 steps/rev, 1/1 Mikroschritt, GT2-Riemen 2mm Pitch, 20-Zahn-Rad: 200 / (2*20) = 5 steps/mm
STEPS_PER_MM = 5.0  # DUMMY – bitte kalibrieren!

# --- Rampe (Acceleration) -----------------------------------------------------
# Obergrenze ist dynamisch: max. distance / 2 (wie im Arduino)
RAMP_MIN_STEPS = 0
RAMP_STEP_INCREMENT = 100   # ramp_steps_by aus der .ino

# --- Timelapse ----------------------------------------------------------------
TIME_MIN_S = 0
TIME_MAX_S = 900            # 15 Minuten, time_max aus der .ino
TIME_INCREMENT_S = 1

SUBDIVISIONS_MIN = 2        # Mindest-Teiler, Safety-Check im Arduino
SUBDIVISIONS_MAX = 1000     # steps_max aus der .ino

# --- Presets ------------------------------------------------------------------
PRESETS_DIR = "presets"     # Ordner relativ zum Binary / Skript
