# =============================================================================
# logic/preset_manager.py – Preset Speichern / Laden
# Schreibt und liest Konfigurationen als .json-Dateien im presets/-Ordner.
# =============================================================================

import json
import os
from config import PRESETS_DIR


def _ensure_dir():
    """Erstellt den Presets-Ordner, falls er noch nicht existiert."""
    os.makedirs(PRESETS_DIR, exist_ok=True)


def save_preset(filepath: str, data: dict):
    """
    Speichert ein Preset als JSON-Datei.
    data-Struktur:
      {
        "name": str,
        "speed_pct": float,       # 0–100
        "distance_steps": int,
        "ramp_steps": int,
        "time_s": int,            # Timelapse-Delay
        "subdivisions": int       # Timelapse-Unterteilungen
      }
    """
    _ensure_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_preset(filepath: str) -> dict:
    """Lädt ein Preset aus einer JSON-Datei und gibt es als dict zurück."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
