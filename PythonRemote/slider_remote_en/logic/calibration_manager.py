# =============================================================================
# logic/calibration_manager.py – Calibration persistence and lookup
# Stores the active calibration in memory; provides save/load and interpolation.
# =============================================================================

import json
import time

_active: dict | None = None


def get_active_calibration() -> dict | None:
    return _active


def set_active_calibration(data: dict):
    global _active
    _active = data


# ---------------------------------------------------------------------------
# Runtime value getters – return calibrated values when loaded, else config
# ---------------------------------------------------------------------------

def get_steps_per_mm() -> float:
    from config import STEPS_PER_MM
    if _active and "steps_per_mm" in _active:
        return float(_active["steps_per_mm"])
    return STEPS_PER_MM


def get_distance_long() -> int:
    from config import DISTANCE_LONG_STEPS
    if _active and "distance_long_steps" in _active:
        return int(_active["distance_long_steps"])
    return DISTANCE_LONG_STEPS


def get_distance_short() -> int:
    from config import DISTANCE_SHORT_STEPS
    if _active and "distance_short_steps" in _active:
        return int(_active["distance_short_steps"])
    return DISTANCE_SHORT_STEPS


def save_calibration(path: str, slider_length_steps: int, speed_table: dict,
                     distance_long: int, distance_short: int,
                     steps_per_mm: float) -> dict:
    data = {
        "slider_length_steps": slider_length_steps,
        "distance_long_steps": distance_long,
        "distance_short_steps": distance_short,
        "steps_per_mm": round(steps_per_mm, 6),
        "calibration_date": time.strftime("%Y-%m-%d"),
        "speed_calibration": {str(k): round(v, 3) for k, v in speed_table.items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def load_calibration(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "slider_length_steps" not in data or "speed_calibration" not in data:
        raise ValueError("Invalid calibration file: missing required keys.")
    return data


def interpolate_travel_time(speed_pct: float) -> float | None:
    """
    Returns the estimated full-length travel time (seconds) for the given speed
    percentage, linearly interpolated from the calibration table.
    Returns None if no calibration is loaded.
    """
    if not _active:
        return None
    table = _active["speed_calibration"]
    speeds = sorted(int(k) for k in table)
    if not speeds:
        return None
    speed_pct = max(speeds[0], min(speeds[-1], speed_pct))
    for i in range(len(speeds) - 1):
        lo, hi = speeds[i], speeds[i + 1]
        if lo <= speed_pct <= hi:
            t_lo = float(table[str(lo)])
            t_hi = float(table[str(hi)])
            ratio = (speed_pct - lo) / (hi - lo)
            return t_lo + ratio * (t_hi - t_lo)
    return float(table[str(speeds[0])])

