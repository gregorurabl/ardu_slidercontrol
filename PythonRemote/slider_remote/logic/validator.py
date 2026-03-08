# =============================================================================
# logic/validator.py – Eingabevalidierung
# Prüft alle Parameter gegen die Limits aus config.py.
# Gibt bei Fehler eine lesbare Fehlermeldung zurück, sonst None.
# =============================================================================

from typing import Optional
from config import (
    SPEED_MIN_STEPS, SPEED_MAX_STEPS,
    DISTANCE_MIN_STEPS, DISTANCE_MAX_STEPS,
    RAMP_MIN_STEPS,
    TIME_MIN_S, TIME_MAX_S,
    SUBDIVISIONS_MIN, SUBDIVISIONS_MAX
)


def validate_normal(speed_steps: int, distance_steps: int, ramp_steps: int) -> Optional[str]:
    """Validiert Parameter für den Normal-Modus. Gibt Fehlermeldung oder None zurück."""
    if not (SPEED_MIN_STEPS <= speed_steps <= SPEED_MAX_STEPS):
        return f"Geschwindigkeit muss zwischen {SPEED_MIN_STEPS} und {SPEED_MAX_STEPS} steps/s liegen."
    if not (DISTANCE_MIN_STEPS <= distance_steps <= DISTANCE_MAX_STEPS):
        return f"Distanz muss zwischen {DISTANCE_MIN_STEPS} und {DISTANCE_MAX_STEPS} Steps liegen."
    ramp_max = distance_steps // 2
    if not (RAMP_MIN_STEPS <= ramp_steps <= ramp_max):
        return f"Rampe muss zwischen {RAMP_MIN_STEPS} und {ramp_max} Steps liegen (max. Distanz/2)."
    return None


def validate_timelapse(speed_steps: int, distance_steps: int, ramp_steps: int,
                       time_s: int, subdivisions: int) -> Optional[str]:
    """Validiert Parameter für den Timelapse-Modus. Gibt Fehlermeldung oder None zurück."""
    error = validate_normal(speed_steps, distance_steps, ramp_steps)
    if error:
        return error
    if not (TIME_MIN_S <= time_s <= TIME_MAX_S):
        return f"Delay muss zwischen {TIME_MIN_S} und {TIME_MAX_S} Sekunden liegen."
    if not (SUBDIVISIONS_MIN <= subdivisions <= SUBDIVISIONS_MAX):
        return f"Unterteilungen müssen zwischen {SUBDIVISIONS_MIN} und {SUBDIVISIONS_MAX} liegen."
    return None
