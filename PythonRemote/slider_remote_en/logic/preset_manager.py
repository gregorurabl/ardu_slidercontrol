# =============================================================================
# logic/preset_manager.py – Preset save / load
# Writes and reads configurations as .json files in the presets/ folder.
# =============================================================================

import json
import os
from config import PRESETS_DIR


def _ensure_dir():
    """Creates the presets folder if it does not yet exist."""
    os.makedirs(PRESETS_DIR, exist_ok=True)


def save_preset(filepath: str, data: dict):
    """
    Saves a preset as a JSON file.
    Expected data structure:
      {
        "name": str,
        "normal_speed_pct": float,        # 0–100
        "normal_distance_steps": int,
        "normal_ramp_steps": int,
        "tl_speed_pct": float,
        "tl_distance_steps": int,
        "tl_ramp_steps": int,
        "tl_time_s": int,
        "tl_subdivisions": int
      }
    """
    _ensure_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_preset(filepath: str) -> dict:
    """Loads a preset from a JSON file and returns it as a dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
