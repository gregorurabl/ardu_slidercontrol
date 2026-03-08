# =============================================================================
# ui/tabs.py – Tab-Inhalte
# NormalTab und TimelapseTab kapseln je alle Parameter-Widgets ihres Modus.
# get_values() gibt ein dict mit Rohwerten zurück, set_values() befüllt die UI.
# =============================================================================

import customtkinter as ctk
from logic.converter import steps_to_cm, cm_to_steps
from config import (
    SPEED_MIN_STEPS, SPEED_MAX_STEPS, SPEED_PERCENT_DIVISOR,
    DISTANCE_MIN_STEPS, DISTANCE_MAX_STEPS,
    DISTANCE_SHORT_STEPS, DISTANCE_LONG_STEPS,
    RAMP_MIN_STEPS,
    TIME_MIN_S, TIME_MAX_S,
    SUBDIVISIONS_MIN, SUBDIVISIONS_MAX
)


# =============================================================================
# Wiederverwendbarer Slider mit Label, Slider und Zahleneingabe
# =============================================================================
class LabeledSlider(ctk.CTkFrame):
    def __init__(self, parent, label: str, from_: float, to: float,
                 unit: str = "", steps: int = 0, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._from = from_
        self._to = to
        self._unit = unit
        self._callback = None  # externer on_change-Callback

        # Label (linksbündig)
        ctk.CTkLabel(self, text=label, width=130, anchor="w").grid(
            row=0, column=0, padx=(0, 8), sticky="w")

        # Slider
        self.slider = ctk.CTkSlider(self, from_=from_, to=to,
                                    number_of_steps=steps if steps else int(to - from_),
                                    command=self._on_slider)
        self.slider.grid(row=0, column=1, sticky="ew", padx=4)

        # Numerisches Eingabefeld
        self.entry_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, width=72)
        self.entry.grid(row=0, column=2, padx=(4, 0))
        self.entry.bind("<Return>", self._on_entry)
        self.entry.bind("<FocusOut>", self._on_entry)

        # Einheit-Label
        ctk.CTkLabel(self, text=unit, width=40, anchor="w").grid(
            row=0, column=3, padx=(2, 0))

        self.columnconfigure(1, weight=1)

    def _on_slider(self, value):
        self.entry_var.set(str(round(value, 1) if isinstance(value, float) else int(value)))
        if self._callback:
            self._callback(value)

    def _on_entry(self, _event=None):
        try:
            value = float(self.entry_var.get())
            value = max(self._from, min(self._to, value))
            self.slider.set(value)
            self.entry_var.set(str(round(value, 1) if isinstance(value, float) else int(value)))
            if self._callback:
                self._callback(value)
        except ValueError:
            pass  # Ungültige Eingabe ignorieren

    def get(self) -> float:
        return self.slider.get()

    def set(self, value: float):
        self.slider.set(value)
        self.entry_var.set(str(round(value, 1) if isinstance(value, float) else int(value)))

    def set_max(self, new_max: float):
        """Aktualisiert das Slider-Maximum dynamisch (z.B. Ramp abhängig von Distance)."""
        self._to = new_max
        self.slider.configure(to=new_max)
        if self.get() > new_max:
            self.set(new_max)

    def on_change(self, callback):
        """Registriert einen Callback, der bei jeder Wertänderung aufgerufen wird."""
        self._callback = callback


# =============================================================================
# Normal-Tab
# =============================================================================
class NormalTab:
    def __init__(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Speed (0–100%)
        self.speed = LabeledSlider(frame, "Geschwindigkeit", 0, 100, unit="%", steps=100)
        self.speed.set(50)
        self.speed.pack(fill="x", pady=6)

        # Distance (Steps + cm-Anzeige)
        dist_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dist_frame.pack(fill="x", pady=6)

        self.distance = LabeledSlider(dist_frame, "Distanz", DISTANCE_MIN_STEPS,
                                      DISTANCE_MAX_STEPS, unit="steps", steps=340)
        self.distance.pack(fill="x")
        self.distance.on_change(self._on_distance_change)

        # cm-Anzeige unter dem Distanz-Slider
        cm_row = ctk.CTkFrame(dist_frame, fg_color="transparent")
        cm_row.pack(fill="x")
        ctk.CTkLabel(cm_row, text="", width=130).pack(side="left")  # Abstandshalter
        self.cm_label = ctk.CTkLabel(cm_row, text="= 0.00 cm", anchor="w")
        self.cm_label.pack(side="left", padx=4)

        # Shortcuts: Short / Long Slider-Länge
        shortcut_row = ctk.CTkFrame(frame, fg_color="transparent")
        shortcut_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(shortcut_row, text="", width=130).pack(side="left")
        ctk.CTkButton(shortcut_row, text="Short", width=80,
                      command=lambda: self.distance.set(DISTANCE_SHORT_STEPS)).pack(
            side="left", padx=(4, 2))
        ctk.CTkButton(shortcut_row, text="Long", width=80,
                      command=lambda: self.distance.set(DISTANCE_LONG_STEPS)).pack(
            side="left", padx=2)

        # Ramp (0 – distance/2, dynamisch)
        self.ramp = LabeledSlider(frame, "Rampe", 0, DISTANCE_MAX_STEPS // 2, unit="steps")
        self.ramp.set(0)
        self.ramp.pack(fill="x", pady=6)

        # Initiale cm-Anzeige setzen
        self._on_distance_change(self.distance.get())

    def _on_distance_change(self, value):
        """Aktualisiert cm-Label und Ramp-Maximum wenn Distanz geändert wird."""
        steps = int(value)
        self.cm_label.configure(text=f"= {steps_to_cm(steps):.2f} cm")
        new_ramp_max = max(1, steps // 2)
        self.ramp.set_max(new_ramp_max)

    def get_values(self) -> dict:
        """Gibt aktuelle UI-Werte zurück. Steps werden direkt übergeben; % bleibt für den Logic Layer."""
        return {
            "speed_pct": self.speed.get(),
            "distance_steps": int(self.distance.get()),
            "ramp_steps": int(self.ramp.get()),
        }

    def set_values(self, speed_pct: float, distance_steps: int, ramp_steps: int):
        """Befüllt alle Widgets (z.B. beim Laden eines Presets)."""
        self.speed.set(speed_pct)
        self.distance.set(distance_steps)
        self._on_distance_change(distance_steps)
        self.ramp.set(ramp_steps)


# =============================================================================
# Timelapse-Tab
# =============================================================================
class TimelapseTab:
    def __init__(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Speed (0–100%)
        self.speed = LabeledSlider(frame, "Geschwindigkeit", 0, 100, unit="%", steps=100)
        self.speed.set(30)
        self.speed.pack(fill="x", pady=6)

        # Distance (Steps + cm)
        dist_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dist_frame.pack(fill="x", pady=6)

        self.distance = LabeledSlider(dist_frame, "Distanz", DISTANCE_MIN_STEPS,
                                      DISTANCE_MAX_STEPS, unit="steps", steps=340)
        self.distance.pack(fill="x")
        self.distance.on_change(self._on_distance_change)

        cm_row = ctk.CTkFrame(dist_frame, fg_color="transparent")
        cm_row.pack(fill="x")
        ctk.CTkLabel(cm_row, text="", width=130).pack(side="left")
        self.cm_label = ctk.CTkLabel(cm_row, text="= 0.00 cm", anchor="w")
        self.cm_label.pack(side="left", padx=4)

        shortcut_row = ctk.CTkFrame(frame, fg_color="transparent")
        shortcut_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(shortcut_row, text="", width=130).pack(side="left")
        ctk.CTkButton(shortcut_row, text="Short", width=80,
                      command=lambda: self.distance.set(DISTANCE_SHORT_STEPS)).pack(
            side="left", padx=(4, 2))
        ctk.CTkButton(shortcut_row, text="Long", width=80,
                      command=lambda: self.distance.set(DISTANCE_LONG_STEPS)).pack(
            side="left", padx=2)

        # Ramp
        self.ramp = LabeledSlider(frame, "Rampe", 0, DISTANCE_MAX_STEPS // 2, unit="steps")
        self.ramp.set(0)
        self.ramp.pack(fill="x", pady=6)

        # Delay (Sekunden zwischen Timelapse-Stops)
        self.delay = LabeledSlider(frame, "Delay", TIME_MIN_S, TIME_MAX_S, unit="s",
                                   steps=TIME_MAX_S)
        self.delay.set(30)
        self.delay.pack(fill="x", pady=6)

        # Subdivisions (Unterteilungen)
        self.subdivisions = LabeledSlider(frame, "Unterteilungen", SUBDIVISIONS_MIN,
                                          SUBDIVISIONS_MAX, unit="", steps=SUBDIVISIONS_MAX - 2)
        self.subdivisions.set(10)
        self.subdivisions.pack(fill="x", pady=6)

        self._on_distance_change(self.distance.get())

    def _on_distance_change(self, value):
        steps = int(value)
        self.cm_label.configure(text=f"= {steps_to_cm(steps):.2f} cm")
        new_ramp_max = max(1, steps // 2)
        self.ramp.set_max(new_ramp_max)

    def get_values(self) -> dict:
        return {
            "speed_pct": self.speed.get(),
            "distance_steps": int(self.distance.get()),
            "ramp_steps": int(self.ramp.get()),
            "time_s": int(self.delay.get()),
            "subdivisions": int(self.subdivisions.get()),
        }

    def set_values(self, speed_pct: float, distance_steps: int, ramp_steps: int,
                   time_s: int, subdivisions: int):
        self.speed.set(speed_pct)
        self.distance.set(distance_steps)
        self._on_distance_change(distance_steps)
        self.ramp.set(ramp_steps)
        self.delay.set(time_s)
        self.subdivisions.set(subdivisions)
