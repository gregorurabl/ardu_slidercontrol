# =============================================================================
# logic/converter.py – Unit conversion
# Converts between UI units (%, cm) and serial raw values (steps, steps/s).
# =============================================================================

from config import (
    SPEED_MIN_STEPS, SPEED_MAX_STEPS, SPEED_PERCENT_DIVISOR,
)


def speed_pct_to_steps(pct: float) -> int:
    """Converts a percentage (0–100) to steps/s for the serial command."""
    steps = pct * SPEED_PERCENT_DIVISOR
    return int(max(SPEED_MIN_STEPS, min(SPEED_MAX_STEPS, steps)))


def speed_steps_to_pct(steps: int) -> float:
    """Converts steps/s to a percentage (0–100) for display."""
    return round(steps / SPEED_PERCENT_DIVISOR, 1)


def steps_to_cm(steps: int) -> float:
    """Converts steps to centimetres using the active calibration or config value."""
    from logic.calibration_manager import get_steps_per_mm
    spm = get_steps_per_mm()
    if spm <= 0:
        return 0.0
    return round(abs(steps) / (spm * 10), 2)


def cm_to_steps(cm: float) -> int:
    """Converts centimetres to steps. Inverse of steps_to_cm."""
    from logic.calibration_manager import get_steps_per_mm
    return int(cm * get_steps_per_mm() * 10)
