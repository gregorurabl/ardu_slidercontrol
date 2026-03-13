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


def save_calibration(path: str, slider_length_steps: int, speed_table: dict) -> dict:
    data = {
        "slider_length_steps": slider_length_steps,
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
