# =============================================================================
# ui/tabs.py – Tab contents
# NormalTab and TimelapseTab each encapsulate all parameter widgets for their mode.
# get_values() returns a dict of raw values; set_values() populates the UI.
# =============================================================================

import customtkinter as ctk
import tkinter as tk
from logic.converter import steps_to_cm, cm_to_steps, speed_pct_to_steps
from config import (
    SPEED_MIN_STEPS, SPEED_MAX_STEPS, SPEED_PERCENT_DIVISOR,
    DISTANCE_MIN_STEPS, DISTANCE_MAX_STEPS,
    DISTANCE_SHORT_STEPS, DISTANCE_LONG_STEPS,
    RAMP_MIN_STEPS,
    TIME_MIN_S, TIME_MAX_S,
    SUBDIVISIONS_MIN, SUBDIVISIONS_MAX
)


# =============================================================================
# Tooltip – shows a small popup label on hover
# =============================================================================
class Tooltip:
    def __init__(self, widget, text: str):
        self._widget = widget
        self._text = text
        self._tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self._tip_window:
            return
        x = self._widget.winfo_rootx() + 20
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tip_window = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)  # no window decorations
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self._text, background="#2b2b2b", foreground="white",
                 relief="flat", padx=6, pady=3,
                 font=("Segoe UI", 9)).pack()

    def _hide(self, _event=None):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None


# =============================================================================
# Reusable slider widget: label, slider, and numeric entry field
# =============================================================================
class LabeledSlider(ctk.CTkFrame):
    def __init__(self, parent, label: str, from_: float, to: float,
                 unit: str = "", steps: int = 0, integer: bool = False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._from = from_
        self._to = to
        self._unit = unit
        self._integer = integer
        self._callback = None

        ctk.CTkLabel(self, text=label, width=130, anchor="w").grid(
            row=0, column=0, padx=(0, 8), sticky="w")

        self.slider = ctk.CTkSlider(self, from_=from_, to=to,
                                    number_of_steps=steps if steps else int(to - from_),
                                    command=self._on_slider)
        self.slider.grid(row=0, column=1, sticky="ew", padx=4)

        self.entry_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, width=72)
        self.entry.grid(row=0, column=2, padx=(4, 0))
        self.entry.bind("<Return>", self._on_entry)
        self.entry.bind("<FocusOut>", self._on_entry)

        ctk.CTkLabel(self, text=unit, width=40, anchor="w").grid(
            row=0, column=3, padx=(2, 0))

        self.columnconfigure(1, weight=1)
        self.set(from_)

    def _fmt(self, value: float) -> str:
        if self._integer:
            return str(int(round(value)))
        rounded = round(value)
        if abs(value - rounded) < 0.05:
            return str(rounded)
        return str(round(value, 1))

    def _on_slider(self, value):
        self.entry_var.set(self._fmt(value))
        if self._callback:
            self._callback(value)

    def _on_entry(self, _event=None):
        try:
            value = float(self.entry_var.get())
            if self._integer:
                value = int(round(value))
            value = max(self._from, min(self._to, value))
            self.slider.set(value)
            self.entry_var.set(self._fmt(value))
            if self._callback:
                self._callback(value)
        except ValueError:
            pass

    def get(self) -> float:
        """Returns the entry field value (authoritative) rather than the quantized slider."""
        try:
            return float(self.entry_var.get())
        except ValueError:
            return self.slider.get()

    def set(self, value: float):
        self.slider.set(value)
        self.entry_var.set(self._fmt(value))
        if self._callback:
            self._callback(value)

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

        # Speed (10–100%)
        self.speed = LabeledSlider(frame, "Speed", 10, 100, unit="%", steps=90)
        self.speed.set(50)
        self.speed.pack(fill="x", pady=6)

        # Distance (steps + cm display)
        dist_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dist_frame.pack(fill="x", pady=6)

        self.distance = LabeledSlider(dist_frame, "Distance", DISTANCE_MIN_STEPS,
                                      DISTANCE_MAX_STEPS, unit="steps", steps=340, integer=True)
        self.distance.set(DISTANCE_SHORT_STEPS)
        self.distance.pack(fill="x")
        self.distance.on_change(self._on_distance_change)

        # cm readout below the distance slider
        cm_row = ctk.CTkFrame(dist_frame, fg_color="transparent")
        cm_row.pack(fill="x")
        ctk.CTkLabel(cm_row, text="", width=130).pack(side="left")  # spacer
        self.cm_label = ctk.CTkLabel(cm_row, text="= 0.00 cm", anchor="w")
        self.cm_label.pack(side="left", padx=4)

        # Shortcuts: short / full slider length + direction toggle + RTH
        shortcut_row = ctk.CTkFrame(frame, fg_color="transparent")
        shortcut_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(shortcut_row, text="", width=130).pack(side="left")
        ctk.CTkButton(shortcut_row, text="Short", width=80,
                      command=lambda: self.distance.set(DISTANCE_SHORT_STEPS)).pack(
            side="left", padx=(4, 2))
        ctk.CTkButton(shortcut_row, text="Long", width=80,
                      command=lambda: self.distance.set(DISTANCE_LONG_STEPS)).pack(
            side="left", padx=2)

        # Direction toggle
        self._direction = 1  # 1 = forward, -1 = reverse
        self.dir_btn = ctk.CTkButton(shortcut_row, text="Forward", width=90,
                                     fg_color="#2d6e2d",
                                     command=self._toggle_direction)
        self.dir_btn.pack(side="left", padx=(8, 0))
        self._dir_tooltip = Tooltip(self.dir_btn, "Motor moves away from its mounted end")

        # Ramp (0 – distance/2, updated dynamically)
        self.ramp = LabeledSlider(frame, "Ramp", 0, DISTANCE_MAX_STEPS // 2, unit="steps", integer=True)
        self.ramp.set(0)
        self.ramp.pack(fill="x", pady=6)

        # Set initial cm display
        self._on_distance_change(self.distance.get())

    def set_serial(self, serial_handler):
        """Called by App after construction so Free Run and RTH can send commands directly."""
        self._serial = serial_handler

    def _send_rth(self):
        if not hasattr(self, "_serial") or self._serial is None:
            return
        self._serial.send(self._serial.build_rth_command())

    def _toggle_freerun(self):
        if not hasattr(self, "_serial") or self._serial is None:
            return
        self._freerun_active = not self._freerun_active
        if self._freerun_active:
            self._serial.send(self._serial.build_start_command())
            self.freerun_btn.configure(text="Stop Free Run", fg_color="#8b2020")
        else:
            self._serial.send(self._serial.build_stop_command())
            self.freerun_btn.configure(text="Start Free Run", fg_color="#2d6e2d")

    def _toggle_direction(self):
        """Toggles between Forward (positive steps) and Reverse (negative steps)."""
        self._direction *= -1
        if self._direction == 1:
            self.dir_btn.configure(text="Forward", fg_color="#2d6e2d")
            self._dir_tooltip._text = "Motor moves away from its mounted end"
        else:
            self.dir_btn.configure(text="Reverse", fg_color="#8b2020")
            self._dir_tooltip._text = "Motor moves toward its mounted end"

    def _on_distance_change(self, value):
        """Updates the cm label and ramp maximum when distance changes."""
        steps = int(value)
        self.cm_label.configure(text=f"= {steps_to_cm(steps):.2f} cm")
        new_ramp_max = max(1, steps // 2)
        self.ramp.set_max(new_ramp_max)

    def get_values(self) -> dict:
        """Returns current UI values. distance_steps carries the direction sign."""
        return {
            "speed_pct": self.speed.get(),
            "distance_steps": int(self.distance.get()) * self._direction,
            "ramp_steps": int(self.ramp.get()),
        }

    def set_values(self, speed_pct: float, distance_steps: int, ramp_steps: int):
        """Populates all widgets (e.g. when loading a preset)."""
        self.speed.set(speed_pct)
        self.distance.set(abs(distance_steps))
        self._on_distance_change(abs(distance_steps))
        self.ramp.set(ramp_steps)
        # Restore direction from sign
        if distance_steps < 0:
            self._direction = -1
            self.dir_btn.configure(text="Reverse", fg_color="#8b2020")
        else:
            self._direction = 1
            self.dir_btn.configure(text="Forward", fg_color="#2d6e2d")


# =============================================================================
# Timelapse tab
# =============================================================================

# Exposure times: tn = 1/(2^n), n from -5 to 13
# Displayed as standard photography shutter speed labels
EXPOSURE_VALUES = [
    ("30",     30.0),
    ("25",     25.0),
    ("20",     20.0),
    ("15",     15.0),
    ("13",     13.0),
    ("10",     10.0),
    ("8",       8.0),
    ("6",       6.0),
    ("5",       5.0),
    ("4",       4.0),
    ("3.2",     3.2),
    ("2.5",     2.5),
    ("2",       2.0),
    ("1.6",     1.6),
    ("1.3",     1.3),
    ("1",       1.0),
    ("0.8",     0.8),
    ("0.6",     0.6),
    ("0.5",     0.5),
    ("0.4",     0.4),
    ("0.3",     0.3),
    ("1/4",     1/4),
    ("1/5",     1/5),
    ("1/6",     1/6),
    ("1/8",     1/8),
    ("1/10",    1/10),
    ("1/13",    1/13),
    ("1/15",    1/15),
    ("1/20",    1/20),
    ("1/25",    1/25),
    ("1/30",    1/30),
    ("1/40",    1/40),
    ("1/50",    1/50),
    ("1/60",    1/60),
    ("1/80",    1/80),
    ("1/100",   1/100),
    ("1/125",   1/125),
    ("1/160",   1/160),
    ("1/200",   1/200),
    ("1/250",   1/250),
    ("1/320",   1/320),
    ("1/400",   1/400),
    ("1/500",   1/500),
    ("1/640",   1/640),
    ("1/800",   1/800),
    ("1/1000",  1/1000),
    ("1/1250",  1/1250),
    ("1/1600",  1/1600),
    ("1/2000",  1/2000),
    ("1/2500",  1/2500),
    ("1/3200",  1/3200),
    ("1/4000",  1/4000),
    ("1/5000",  1/5000),
    ("1/6400",  1/6400),
    ("1/8000",  1/8000),
]
_EXPOSURE_LABELS = [e[0] for e in EXPOSURE_VALUES]
_EXPOSURE_SECONDS = [e[1] for e in EXPOSURE_VALUES]
_EXPOSURE_DEFAULT_IDX = 36  # "1/125"


class TimelapseTab:
    def __init__(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=False, padx=8, pady=8)

        # Speed (0–100%)
        self.speed = LabeledSlider(frame, "Speed", 10, 100, unit="%", steps=90)
        self.speed.set(30)
        self.speed.on_change(lambda _: self._update_runtime())
        self.speed.pack(fill="x", pady=6)

        # Distance (steps + cm)
        dist_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dist_frame.pack(fill="x", pady=6)

        self.distance = LabeledSlider(dist_frame, "Distance", DISTANCE_MIN_STEPS,
                                      DISTANCE_MAX_STEPS, unit="steps", steps=340, integer=True)
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

        # Direction toggle
        self._direction = 1
        self.dir_btn = ctk.CTkButton(shortcut_row, text="Forward", width=90,
                                     fg_color="#2d6e2d",
                                     command=self._toggle_direction)
        self.dir_btn.pack(side="left", padx=(8, 0))
        self._dir_tooltip = Tooltip(self.dir_btn, "Motor moves away from its mounted end")

        # Delay (seconds between timelapse stops, excluding exposure time)
        self.delay = LabeledSlider(frame, "Delay", TIME_MIN_S, TIME_MAX_S, unit="s", integer=True,
                                   steps=TIME_MAX_S)
        self.delay.set(30)
        self.delay.pack(fill="x", pady=6)

        # Exposure time: slider (index) + linked dropdown
        # Dropdown width matches LabeledSlider right side: entry(72) + unit(40) = 112px
        exp_row = ctk.CTkFrame(frame, fg_color="transparent")
        exp_row.pack(fill="x", pady=6)

        ctk.CTkLabel(exp_row, text="Exposure", width=130, anchor="w").pack(side="left")

        self._exp_idx = _EXPOSURE_DEFAULT_IDX

        self.exp_slider = ctk.CTkSlider(exp_row, from_=0, to=len(EXPOSURE_VALUES) - 1,
                                        number_of_steps=len(EXPOSURE_VALUES) - 1,
                                        command=self._on_exp_slider)
        self.exp_slider.set(self._exp_idx)
        self.exp_slider.pack(side="left", fill="x", expand=True, padx=4)

        self.exp_var = ctk.StringVar(value=_EXPOSURE_LABELS[self._exp_idx])
        self.exp_dropdown = ctk.CTkOptionMenu(exp_row, variable=self.exp_var,
                                              values=_EXPOSURE_LABELS, width=112,
                                              command=self._on_exp_dropdown)
        self.exp_dropdown.pack(side="left", padx=(4, 0))

        # Subdivisions
        self.subdivisions = LabeledSlider(frame, "Subdivisions", SUBDIVISIONS_MIN,
                                          SUBDIVISIONS_MAX, unit="", integer=True,
                                          steps=SUBDIVISIONS_MAX - 2)
        self.subdivisions.set(10)
        self.subdivisions.on_change(lambda _: self._update_runtime())
        self.subdivisions.pack(fill="x", pady=6)

        # Runtime estimate – editable entry that also back-calculates delay from a typed duration
        runtime_row = ctk.CTkFrame(frame, fg_color="transparent")
        runtime_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(runtime_row, text="Est. duration", width=130, anchor="w").pack(side="left")
        self._runtime_var = ctk.StringVar(value="–")
        self._runtime_entry = ctk.CTkEntry(runtime_row, textvariable=self._runtime_var, width=120)
        self._runtime_entry.pack(side="left", padx=(4, 4))
        ctk.CTkLabel(runtime_row, text="(h:mm:ss – edit to set delay)",
                     anchor="w", text_color="gray60",
                     font=ctk.CTkFont(size=11)).pack(side="left")
        self._runtime_entry.bind("<Return>", self._on_runtime_entry)
        self._runtime_entry.bind("<FocusOut>", self._on_runtime_entry)

        self._on_distance_change(self.distance.get())
        self.delay.on_change(lambda _: self._update_runtime())
        self._update_runtime()

    def _on_exp_slider(self, value):
        """Slider moved → update dropdown to matching label."""
        self._exp_idx = round(value)
        self.exp_var.set(_EXPOSURE_LABELS[self._exp_idx])
        self._update_runtime()

    def _on_exp_dropdown(self, label):
        """Dropdown changed → update slider to matching index."""
        self._exp_idx = _EXPOSURE_LABELS.index(label)
        self.exp_slider.set(self._exp_idx)
        self._update_runtime()

    def _update_runtime(self):
        """Recalculates and displays the estimated total timelapse duration."""
        try:
            from logic.calibration_manager import get_active_calibration, interpolate_travel_time
            subdivisions = int(self.subdivisions.get())
            delay_s = self.delay.get()
            exposure_s = _EXPOSURE_SECONDS[self._exp_idx]
            speed_pct = self.speed.get()
            distance_steps = int(self.distance.get())
            substep_steps = distance_steps / max(subdivisions, 1)

            cal = get_active_calibration()
            if cal and cal.get("slider_length_steps", 0) > 0:
                full_travel_s = interpolate_travel_time(speed_pct) or 0
                travel_s = full_travel_s * (substep_steps / cal["slider_length_steps"])
            else:
                travel_s = substep_steps / max(speed_pct_to_steps(speed_pct), 1)

            wait_s = 0.05 + exposure_s + delay_s
            total_s = int(subdivisions * (travel_s + wait_s) + 5)  # +5s end wait before RTH
            h, rem = divmod(total_s, 3600)
            m, s = divmod(rem, 60)
            self._runtime_var.set(f"{h}:{m:02d}:{s:02d}" if h > 0 else f"0:{m:02d}:{s:02d}")
        except Exception:
            self._runtime_var.set("–")

    def _on_runtime_entry(self, _event=None):
        """
        User typed a duration → back-calculate the required delay.
        Accepted formats: h:mm:ss or m:ss or plain seconds.
        """
        raw = self._runtime_var.get().strip()
        try:
            parts = raw.split(":")
            if len(parts) == 3:
                target_s = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                target_s = int(parts[0]) * 60 + int(parts[1])
            else:
                target_s = int(raw)

            from logic.calibration_manager import get_active_calibration, interpolate_travel_time
            subdivisions = int(self.subdivisions.get())
            exposure_s = _EXPOSURE_SECONDS[self._exp_idx]
            speed_pct = self.speed.get()
            distance_steps = int(self.distance.get())
            substep_steps = distance_steps / max(subdivisions, 1)

            cal = get_active_calibration()
            if cal and cal.get("slider_length_steps", 0) > 0:
                full_travel_s = interpolate_travel_time(speed_pct) or 0
                travel_s = full_travel_s * (substep_steps / cal["slider_length_steps"])
            else:
                travel_s = substep_steps / max(speed_pct_to_steps(speed_pct), 1)

            # Solve: target_s = subdivisions * (travel_s + 0.05 + exposure_s + delay_s) + 5
            delay_s = ((target_s - 5) / max(subdivisions, 1)) - travel_s - 0.05 - exposure_s
            delay_s = max(0.0, delay_s)

            if delay_s > TIME_MAX_S:
                delay_s = TIME_MAX_S
                from tkinter import messagebox
                messagebox.showwarning(
                    "Delay capped at 15 min",
                    f"The requested duration exceeds the maximum delay of {TIME_MAX_S}s.\n"
                    "Delay has been set to 15 min. Use more subdivisions for a longer run.")

            self.delay.set(int(delay_s))
            self._update_runtime()
        except (ValueError, ZeroDivisionError):
            self._update_runtime()

    def get_exposure_s(self) -> float:
        """Returns the selected exposure time in seconds."""
        return _EXPOSURE_SECONDS[self._exp_idx]

    def _toggle_direction(self):
        """Toggles between Forward (positive steps) and Reverse (negative steps)."""
        self._direction *= -1
        if self._direction == 1:
            self.dir_btn.configure(text="Forward", fg_color="#2d6e2d")
            self._dir_tooltip._text = "Motor moves away from its mounted end"
        else:
            self.dir_btn.configure(text="Reverse", fg_color="#8b2020")
            self._dir_tooltip._text = "Motor moves toward its mounted end"

    def _on_distance_change(self, value):
        steps = int(value)
        self.cm_label.configure(text=f"= {steps_to_cm(steps):.2f} cm")
        self._update_runtime()

    def get_values(self) -> dict:
        """Returns current UI values. Ramp is always 0 for timelapse (enforced by Arduino)."""
        return {
            "speed_pct": self.speed.get(),
            "distance_steps": int(self.distance.get()) * self._direction,
            "ramp_steps": 0,
            "time_s": int(self.delay.get()),
            "subdivisions": int(self.subdivisions.get()),
            "exposure_s": self.get_exposure_s(),
        }

    def set_values(self, speed_pct: float, distance_steps: int, ramp_steps: int,
                   time_s: int, subdivisions: int, exposure_idx: int = _EXPOSURE_DEFAULT_IDX):
        self.speed.set(speed_pct)
        self.distance.set(abs(distance_steps))
        self._on_distance_change(abs(distance_steps))
        self.delay.set(time_s)
        self.subdivisions.set(subdivisions)
        # Restore exposure
        self._exp_idx = max(0, min(len(EXPOSURE_VALUES) - 1, exposure_idx))
        self.exp_slider.set(self._exp_idx)
        self.exp_var.set(_EXPOSURE_LABELS[self._exp_idx])
        # Restore direction from sign
        if distance_steps < 0:
            self._direction = -1
            self.dir_btn.configure(text="Reverse", fg_color="#8b2020")
        else:
            self._direction = 1
            self.dir_btn.configure(text="Forward", fg_color="#2d6e2d")
