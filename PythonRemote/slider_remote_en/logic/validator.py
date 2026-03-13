# =============================================================================
# logic/validator.py – Input validation
# Checks all parameters against the limits defined in config.py.
# Returns a human-readable error message on failure, or None on success.
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
    """Validates parameters for Normal mode. Returns an error message or None."""
    if not (SPEED_MIN_STEPS <= speed_steps <= SPEED_MAX_STEPS):
        return f"Speed must be between {SPEED_MIN_STEPS} and {SPEED_MAX_STEPS} steps/s."
    if not (-DISTANCE_MAX_STEPS <= distance_steps <= DISTANCE_MAX_STEPS) or distance_steps == 0:
        return f"Distance must be between -{DISTANCE_MAX_STEPS} and {DISTANCE_MAX_STEPS} steps (non-zero)."
    ramp_max = abs(distance_steps) // 2
    if not (RAMP_MIN_STEPS <= ramp_steps <= ramp_max):
        return f"Ramp must be between {RAMP_MIN_STEPS} and {ramp_max} steps (max. distance / 2)."
    return None


def validate_timelapse(speed_steps: int, distance_steps: int, ramp_steps: int,
                       time_s: int, subdivisions: int) -> Optional[str]:
    """Validates parameters for Timelapse mode. Returns an error message or None."""
    error = validate_normal(speed_steps, distance_steps, ramp_steps)
    if error:
        return error
    if not (TIME_MIN_S <= time_s <= TIME_MAX_S):
        return f"Delay must be between {TIME_MIN_S} and {TIME_MAX_S} seconds."
    if not (SUBDIVISIONS_MIN <= subdivisions <= SUBDIVISIONS_MAX):
        return f"Subdivisions must be between {SUBDIVISIONS_MIN} and {SUBDIVISIONS_MAX}."
    return None
