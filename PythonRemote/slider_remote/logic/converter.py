# =============================================================================
# logic/converter.py – Einheitenumrechnung
# Wandelt zwischen UI-Einheiten (%, cm) und seriellen Rohwerten (steps, steps/s).
# =============================================================================

from config import (
    SPEED_MIN_STEPS, SPEED_MAX_STEPS, SPEED_PERCENT_DIVISOR,
    STEPS_PER_MM
)


def speed_pct_to_steps(pct: float) -> int:
    """Prozentwert (0–100) → steps/s für den seriellen Befehl."""
    steps = pct * SPEED_PERCENT_DIVISOR
    return int(max(SPEED_MIN_STEPS, min(SPEED_MAX_STEPS, steps)))


def speed_steps_to_pct(steps: int) -> float:
    """steps/s → Prozentwert (0–100) für die Anzeige."""
    return round(steps / SPEED_PERCENT_DIVISOR, 1)


def steps_to_cm(steps: int) -> float:
    """Steps → Zentimeter anhand des konfigurierten STEPS_PER_MM-Werts."""
    if STEPS_PER_MM <= 0:
        return 0.0
    return round(steps / (STEPS_PER_MM * 10), 2)


def cm_to_steps(cm: float) -> int:
    """Zentimeter → Steps. Kehrt steps_to_cm um."""
    return int(cm * STEPS_PER_MM * 10)
