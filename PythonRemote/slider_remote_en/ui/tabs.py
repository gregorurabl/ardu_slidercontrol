# =============================================================================
# ui/tabs.py – Tab contents
# NormalTab and TimelapseTab each encapsulate all parameter widgets for their mode.
# get_values() returns a dict of raw values; set_values() populates the UI.
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
# Reusable slider widget: label, slider, and numeric entry field
# =============================================================================
class LabeledSlider(ctk.CTkFrame):
    def __init__(self, parent, label: str, from_: float, to: float,
                 unit: str = "", steps: int = 0, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._from = from_
        self._to = to
        self._unit = unit
        self._callback = None  # external on_change callback

        # Label (left-aligned)
        ctk.CTkLabel(self, text=label, width=130, anchor="w").grid(
            row=0, column=0, padx=(0, 8), sticky="w")

        # Slider
        self.slider = ctk.CTkSlider(self, from_=from_, to=to,
                                    number_of_steps=steps if steps else int(to - from_),
                                    command=self._on_slider)
        self.slider.grid(row=0, column=1, sticky="ew", padx=4)

        # Numeric entry field
        self.entry_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, width=72)
        self.entry.grid(row=0, column=2, padx=(4, 0))
        self.entry.bind("<Return>", self._on_entry)
        self.entry.bind("<FocusOut>", self._on_entry)

        # Unit label
        ctk.CTkLabel(self, text=unit, width=40, anchor="w").grid(
            row=0, column=3, padx=(2, 0))

        self.columnconfigure(1, weight=1)

        # Populate the entry field immediately so it is never blank on startup
        self.set(from_)

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
            pass  # Ignore invalid input

    def get(self) -> float:
        return self.slider.get()

    def set(self, value: float):
        self.slider.set(value)
        self.entry_var.set(str(round(value, 1) if isinstance(value, float) else int(value)))

    def set_max(self, new_max: float):
        """Updates the slider maximum dynamically (e.g. ramp depends on distance)."""
        self._to = new_max
        self.slider.configure(to=new_max)
        if self.get() > new_max:
            self.set(new_max)

    def on_change(self, callback):
        """Registers a callback that is called on every value change."""
        self._callback = callback


# =============================================================================
# Normal tab
# =============================================================================
class NormalTab:
    def __init__(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=False, padx=8, pady=8)

        # Speed (0–100%)
        self.speed = LabeledSlider(frame, "Speed", 0, 100, unit="%", steps=100)
        self.speed.set(50)
        self.speed.pack(fill="x", pady=6)

        # Distance (steps + cm display)
        dist_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dist_frame.pack(fill="x", pady=6)

        self.distance = LabeledSlider(dist_frame, "Distance", DISTANCE_MIN_STEPS,
                                      DISTANCE_MAX_STEPS, unit="steps", steps=340)
        self.distance.set(DISTANCE_SHORT_STEPS)
        self.distance.pack(fill="x")
        self.distance.on_change(self._on_distance_change)

        # cm readout below the distance slider
        cm_row = ctk.CTkFrame(dist_frame, fg_color="transparent")
        cm_row.pack(fill="x")
        ctk.CTkLabel(cm_row, text="", width=130).pack(side="left")  # spacer
        self.cm_label = ctk.CTkLabel(cm_row, text="= 0.00 cm", anchor="w")
        self.cm_label.pack(side="left", padx=4)

        # Shortcuts: short / full slider length
        shortcut_row = ctk.CTkFrame(frame, fg_color="transparent")
        shortcut_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(shortcut_row, text="", width=130).pack(side="left")
        ctk.CTkButton(shortcut_row, text="Short", width=80,
                      command=lambda: self.distance.set(DISTANCE_SHORT_STEPS)).pack(
            side="left", padx=(4, 2))
        ctk.CTkButton(shortcut_row, text="Long", width=80,
                      command=lambda: self.distance.set(DISTANCE_LONG_STEPS)).pack(
            side="left", padx=2)

        # Ramp (0 – distance/2, updated dynamically)
        self.ramp = LabeledSlider(frame, "Ramp", 0, DISTANCE_MAX_STEPS // 2, unit="steps")
        self.ramp.set(0)
        self.ramp.pack(fill="x", pady=6)

        # Set initial cm display
        self._on_distance_change(self.distance.get())

    def _on_distance_change(self, value):
        """Updates the cm label and ramp maximum when distance changes."""
        steps = int(value)
        self.cm_label.configure(text=f"= {steps_to_cm(steps):.2f} cm")
        new_ramp_max = max(1, steps // 2)
        self.ramp.set_max(new_ramp_max)

    def get_values(self) -> dict:
        """Returns current UI values. Steps are passed through; % stays for the logic layer."""
        return {
            "speed_pct": self.speed.get(),
            "distance_steps": int(self.distance.get()),
            "ramp_steps": int(self.ramp.get()),
        }

    def set_values(self, speed_pct: float, distance_steps: int, ramp_steps: int):
        """Populates all widgets (e.g. when loading a preset)."""
        self.speed.set(speed_pct)
        self.distance.set(distance_steps)
        self._on_distance_change(distance_steps)
        self.ramp.set(ramp_steps)


# =============================================================================
# Timelapse tab
# =============================================================================
class TimelapseTab:
    def __init__(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=False, padx=8, pady=8)

        # Speed (0–100%)
        self.speed = LabeledSlider(frame, "Speed", 0, 100, unit="%", steps=100)
        self.speed.set(30)
        self.speed.pack(fill="x", pady=6)

        # Distance (steps + cm)
        dist_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dist_frame.pack(fill="x", pady=6)

        self.distance = LabeledSlider(dist_frame, "Distance", DISTANCE_MIN_STEPS,
                                      DISTANCE_MAX_STEPS, unit="steps", steps=340)
        self.distance.set(DISTANCE_SHORT_STEPS)
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
        self.ramp = LabeledSlider(frame, "Ramp", 0, DISTANCE_MAX_STEPS // 2, unit="steps")
        self.ramp.set(0)
        self.ramp.pack(fill="x", pady=6)

        # Delay (seconds between timelapse stops)
        self.delay = LabeledSlider(frame, "Delay", TIME_MIN_S, TIME_MAX_S, unit="s",
                                   steps=TIME_MAX_S)
        self.delay.set(30)
        self.delay.pack(fill="x", pady=6)

        # Subdivisions
        self.subdivisions = LabeledSlider(frame, "Subdivisions", SUBDIVISIONS_MIN,
                                          SUBDIVISIONS_MAX, unit="",
                                          steps=SUBDIVISIONS_MAX - 2)
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
