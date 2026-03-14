# =============================================================================
# ui/calibration_window.py – Calibration modal window
# Section 1: Slider length calibration (manual start/stop)
# Section 2: Automated speed calibration (10 speeds, full sequence)
# =============================================================================

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time

from logic.calibration_manager import save_calibration, set_active_calibration
from logic.converter import speed_pct_to_steps
from config import SPEED_MAX_STEPS, DISTANCE_MAX_STEPS

CAL_SPEEDS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


class CalibrationWindow(ctk.CTkToplevel):
    def __init__(self, parent, serial_handler, log_callback=None, normal_speed_steps=None):
        super().__init__(parent)
        self.title("Slider Calibration")
        self.geometry("700x820")
        self.resizable(True, True)

        self._serial = serial_handler
        self._log = log_callback or (lambda msg: None)
        self._len_speed_steps = normal_speed_steps or speed_pct_to_steps(10)
        self._serial.add_listener(self._on_serial)

        # Length calibration state
        self._len_phase = "idle"
        self._len_start_time = 0.0

        # Speed calibration state
        self._slider_length: int | None = None
        self._zero_confirmed = False
        self._cal_phase = "idle"
        self._speed_table: dict[int, float] = {}
        self._target_event = threading.Event()
        self._target_time = 0.0
        self._current_cal_speed: int | None = None
        self._current_cal_start = 0.0
        self._current_cal_estimated = 0.0

        # Scrollable container – avoids blank-window bug on Linux
        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # Defer grab_set so window is fully rendered first
        self.after(200, self.grab_set)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    def _on_close(self):
        self._serial.remove_listener(self._on_serial)
        self.destroy()

    def _on_serial(self, msg: str):
        """Receives all controller messages; sets events for the cal thread."""
        if "Target Reached" in msg:
            self._target_time = time.time()
            self._target_event.set()
        if "Manual Run stopped after" in msg and self._len_phase == "stopped":
            # Parse: "Manual Run stopped after 18432 Steps."
            try:
                parts = msg.split()
                steps = int([p for p in parts if p.isdigit()][0])
                self.after(0, self._len_steps_received, steps)
            except (IndexError, ValueError):
                pass
        if "Run Completed" in msg and self._len_phase == "stopped":
            self.after(0, self._len_run_finished)

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------
    def _build_ui(self):
        ctk.CTkLabel(self._scroll, text="Slider Calibration",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(12, 4))

        self._build_length_section()
        self._build_speed_section()
        self._build_geometry_section()

    def _build_geometry_section(self):
        """Section 3: Slider geometry parameters saved alongside speed calibration."""
        frame = ctk.CTkFrame(self._scroll)
        frame.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(frame, text="3  –  Slider Geometry",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(
            fill="x", padx=8, pady=(8, 4))

        from config import DISTANCE_LONG_STEPS, DISTANCE_SHORT_STEPS, STEPS_PER_MM

        def _field_row(parent, label, default, tooltip_text):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=label, width=130, anchor="w").pack(side="left")
            var = ctk.StringVar(value=str(default))
            entry = ctk.CTkEntry(row, textvariable=var, width=100)
            entry.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=tooltip_text, text_color="gray60",
                         font=ctk.CTkFont(size=11), anchor="w").pack(side="left")
            return var

        self._geo_long_var  = _field_row(frame, "Long (steps)",
                                          DISTANCE_LONG_STEPS,
                                          "100% of usable rail length")
        self._geo_short_var = _field_row(frame, "Short (steps)",
                                          DISTANCE_SHORT_STEPS,
                                          "Shorter setup (e.g. without extension rails, "
                                          "typically ~50% of Long)")
        self._geo_spm_var   = _field_row(frame, "Steps / mm",
                                          STEPS_PER_MM,
                                          "1000 steps = 25.4 mm on Rollei Shark S1 "
                                          "with Stepperonline PG14")

        ctk.CTkLabel(frame,
                     text="Note: Long and Short Steps apply to serial control only.\n"
                          "The onboard touchscreen uses slider_length_long / slider_length_short\n"
                          "from the Arduino sketch (lines 176–177) and must be updated manually\n"
                          "if your values differ from the defaults (36000 / 18000).",
                     anchor="w", justify="left",
                     text_color="gray60", font=ctk.CTkFont(size=11),
                     ).pack(fill="x", padx=12, pady=(6, 10))

    def _build_length_section(self):
        frame = ctk.CTkFrame(self._scroll)
        frame.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(frame, text="1  –  Slider Length Calibration",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(
            fill="x", padx=8, pady=(8, 2))

        ctk.CTkLabel(
            frame,
            text="Slider must be at the ZERO position (motor end) before starting.\n"
                 "Direction is automatically set to Forward (away from motor).\n"
                 "Press Start to begin a free run at the current speed set on the controller.\n"
                 "Press Record when the slider reaches the physical limit – the controller\n"
                 "stops immediately and reports the exact step count via serial.",
            anchor="w", justify="left", text_color="#c8922a",
            font=ctk.CTkFont(size=11),
        ).pack(fill="x", padx=12, pady=(0, 8))

        ctrl = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl.pack(fill="x", padx=8, pady=2)

        self.len_start_btn = ctk.CTkButton(ctrl, text="Start", width=90,
                                           fg_color="#2d6e2d", command=self._len_start)
        self.len_start_btn.pack(side="left", padx=(0, 6))

        self.len_stop_btn = ctk.CTkButton(ctrl, text="Record", width=90,
                                          fg_color="#1f6aa5", state="disabled",
                                          command=self._len_stop)
        self.len_stop_btn.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(ctrl, text="Status:", anchor="w").pack(side="left")
        self.len_status = ctk.CTkLabel(ctrl, text="Ready", anchor="w", text_color="gray60")
        self.len_status.pack(side="left", padx=6)

        fields = ctk.CTkFrame(frame, fg_color="transparent")
        fields.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(fields, text="Steps:", width=70, anchor="w").pack(side="left")
        self._len_steps_var = ctk.StringVar(value="–")
        self.len_steps_entry = ctk.CTkEntry(fields, textvariable=self._len_steps_var, width=100)
        self.len_steps_entry.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(fields, text="Run Duration:", anchor="w").pack(side="left")
        self.len_duration_lbl = ctk.CTkLabel(fields, text="–", anchor="w", text_color="gray60")
        self.len_duration_lbl.pack(side="left", padx=6)

        self.len_apply_btn = ctk.CTkButton(frame, text="Apply Settings",
                                           state="disabled", command=self._len_apply)
        self.len_apply_btn.pack(anchor="w", padx=8, pady=(4, 10))

    def _build_speed_section(self):
        frame = ctk.CTkFrame(self._scroll)
        frame.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(frame, text="2  –  Speed Calibration",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(
            fill="x", padx=8, pady=(8, 4))

        # Zero confirmation row
        zero_row = ctk.CTkFrame(frame, fg_color="transparent")
        zero_row.pack(fill="x", padx=8, pady=(0, 4))

        self.zero_btn = ctk.CTkButton(zero_row, text="Confirm Zero Position",
                                      width=190, state="disabled",
                                      command=self._confirm_zero)
        self.zero_btn.pack(side="left", padx=(0, 12))

        self.zero_lbl = ctk.CTkLabel(zero_row,
                                     text="Complete slider length calibration first.",
                                     text_color="gray60", font=ctk.CTkFont(size=11))
        self.zero_lbl.pack(side="left")

        # Start button
        self.spd_start_btn = ctk.CTkButton(frame, text="Start Speed Calibration",
                                           state="disabled", fg_color="#1f6aa5",
                                           command=self._start_speed_cal)
        self.spd_start_btn.pack(anchor="w", padx=8, pady=(0, 6))

        # Progress area
        self.progress_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.progress_lbl = ctk.CTkLabel(self.progress_frame, text="", anchor="w")
        self.progress_lbl.pack(fill="x")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=2)
        self.progress_detail = ctk.CTkLabel(self.progress_frame, text="", anchor="w",
                                            text_color="gray60",
                                            font=ctk.CTkFont(size=11))
        self.progress_detail.pack(fill="x")
        # hidden until calibration starts

        # Results table
        tbl = ctk.CTkFrame(frame)
        tbl.pack(fill="x", padx=8, pady=6)

        hdr = ctk.CTkFrame(tbl, fg_color="gray25")
        hdr.pack(fill="x", padx=2, pady=(2, 0))
        ctk.CTkLabel(hdr, text="Speed", width=90, anchor="center",
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(hdr, text="Travel Duration", width=150, anchor="center",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")

        self._table_rows: dict[int, ctk.CTkLabel] = {}
        for spd in CAL_SPEEDS:
            row = ctk.CTkFrame(tbl, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=1)
            ctk.CTkLabel(row, text=f"{spd}%", width=90, anchor="center").pack(side="left", padx=4)
            lbl = ctk.CTkLabel(row, text="–", width=150, anchor="center", text_color="gray60")
            lbl.pack(side="left")
            self._table_rows[spd] = lbl

        # Save button
        self.save_btn = ctk.CTkButton(frame, text="Save Calibration",
                                      state="disabled", fg_color="#2d6e2d",
                                      command=self._save_cal)
        self.save_btn.pack(anchor="w", padx=8, pady=(4, 10))

    # -------------------------------------------------------------------------
    # Length calibration logic
    # -------------------------------------------------------------------------
    def _len_run_finished(self):
        self.len_status.configure(text="Motor stopped – ready for another run",
                                  text_color="gray60")
        self.len_start_btn.configure(state="normal")

    def _len_steps_received(self, steps: int):
        """Called when Arduino confirms stop and reports actual steps traveled."""
        self._len_steps_var.set(str(steps))
        self.len_status.configure(
            text=f"Measured: {steps:,} steps – adjust if needed, then Apply",
            text_color="#6ec06e")
        self.len_apply_btn.configure(state="normal")
        self.len_start_btn.configure(state="normal")

    def _len_start(self):
        if not self._serial.is_connected():
            messagebox.showwarning("Not Connected", "Connect to a port first.", parent=self)
            return
        self._len_phase = "running"
        self._len_start_time = time.time()
        self._len_steps_var.set("–")
        self.len_status.configure(text="Running...", text_color="#c8922a")
        self.len_start_btn.configure(state="disabled")
        self.len_stop_btn.configure(state="normal")
        cmd = self._serial.build_start_command()
        self._serial.send(cmd)
        self._log(f"Sent (calibration): {cmd}")
        self._len_tick()

    def _len_tick(self):
        if self._len_phase != "running":
            return
        elapsed = time.time() - self._len_start_time
        self.len_duration_lbl.configure(text=f"{elapsed:.1f} s")
        self.after(200, self._len_tick)

    def _len_stop(self):
        self._len_phase = "stopped"
        elapsed = time.time() - self._len_start_time
        self.len_duration_lbl.configure(text=f"{elapsed:.1f} s")
        cmd = self._serial.build_stop_command()
        self._serial.send(cmd)
        self._log(f"Sent (calibration): {cmd}")
        self.len_status.configure(
            text="Stop sent – waiting for step count from controller...",
            text_color="gray60")
        self.len_stop_btn.configure(state="disabled")
        # _on_serial will populate steps and enable Apply when "Manual Run stopped after X Steps." arrives

    def _len_apply(self):
        try:
            steps = int(self._len_steps_var.get())
            if steps <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Steps",
                                   "Steps must be a positive integer.", parent=self)
            return
        self._slider_length = steps
        rth_cmd = self._serial.build_rth_command()
        self._serial.send(rth_cmd)
        self._log(f"Sent (calibration): {rth_cmd}")
        self.len_status.configure(text=f"Applied: {steps} steps – returning home",
                                  text_color="#6ec06e")
        self.zero_btn.configure(state="normal")
        self.zero_lbl.configure(
            text="Move slider to zero position (motor end), then confirm.",
            text_color="gray60")

    # -------------------------------------------------------------------------
    # Speed calibration logic
    # -------------------------------------------------------------------------
    def _confirm_zero(self):
        self._zero_confirmed = True
        self.zero_btn.configure(state="disabled", text="Zero Confirmed")
        self.zero_lbl.configure(text="Ready.", text_color="#6ec06e")
        self.spd_start_btn.configure(state="normal")

    def _start_speed_cal(self):
        if not self._serial.is_connected():
            messagebox.showwarning("Not Connected", "Connect to a port first.", parent=self)
            return
        self._cal_phase = "running"
        self._speed_table = {}
        self.spd_start_btn.configure(state="disabled")
        for spd in CAL_SPEEDS:
            self._table_rows[spd].configure(text="–", text_color="gray60")
        self.progress_frame.pack(fill="x", padx=8, pady=4)
        threading.Thread(target=self._cal_sequence, daemon=True).start()
        self._progress_tick()

    def _cal_sequence(self):
        """Automated speed calibration – runs entirely in a background thread."""
        for spd in CAL_SPEEDS:
            self.after(0, self._set_progress_label, spd)
            self.after(0, self._set_table_row, spd, "running...", "#c8922a")

            speed_steps = speed_pct_to_steps(spd)
            # Rough upper-bound estimate for progress bar
            self._current_cal_estimated = (self._slider_length / speed_steps) * 1.3 + 2
            self._current_cal_speed = spd
            self._current_cal_start = time.time()   # set before send for accurate timing

            self._target_event.clear()
            cmd = f"normal,{speed_steps},{self._slider_length},0,0,2"
            self._serial.send(cmd)
            self._log(f"Sent (calibration {spd}%): {cmd}")

            if not self._target_event.wait(timeout=600):
                self.after(0, self._cal_aborted)
                return

            travel_s = self._target_time - self._current_cal_start
            self._speed_table[spd] = travel_s
            self.after(0, self._set_table_row, spd, f"{travel_s:.2f} s", "#6ec06e")

            # RTH and wait for slider to return before next run
            rth_cmd = "rth,0,0,0,0,0"
            self._serial.send(rth_cmd)
            self._log(f"Sent (calibration RTH): {rth_cmd}")
            rth_wait = (self._slider_length / SPEED_MAX_STEPS) * 1.5 + 3
            time.sleep(rth_wait)

        self.after(0, self._cal_done)

    # -------------------------------------------------------------------------
    # UI update helpers (called via after() from background thread)
    # -------------------------------------------------------------------------
    def _set_table_row(self, speed: int, text: str, color: str):
        self._table_rows[speed].configure(text=text, text_color=color)

    def _set_progress_label(self, speed: int):
        done = len(self._speed_table)
        self.progress_lbl.configure(
            text=f"Current Run: {speed}%    ({done} / {len(CAL_SPEEDS)} complete)")
        self.progress_bar.set(0)

    def _progress_tick(self):
        if self._cal_phase != "running":
            return
        if self._current_cal_speed is not None and self._current_cal_estimated > 0:
            elapsed = time.time() - self._current_cal_start
            self.progress_bar.set(min(elapsed / self._current_cal_estimated, 1.0))
            self.progress_detail.configure(
                text=f"Elapsed: {elapsed:.1f} s  /  Est. {self._current_cal_estimated:.1f} s")
        self.after(200, self._progress_tick)

    def _cal_aborted(self):
        self._cal_phase = "idle"
        messagebox.showwarning("Timeout",
                               "A calibration run timed out (> 10 min). Calibration aborted.",
                               parent=self)
        self.spd_start_btn.configure(state="normal")
        self.progress_frame.pack_forget()

    def _cal_done(self):
        self._cal_phase = "done"
        self.progress_lbl.configure(
            text=f"All {len(CAL_SPEEDS)} runs complete. Save the calibration file.")
        self.progress_bar.set(1.0)
        self.progress_detail.configure(text="")
        set_active_calibration(self._build_cal_data())
        self.save_btn.configure(state="normal")

    def _build_cal_data(self) -> dict:
        """Assembles full calibration dict including geometry fields."""
        try:
            d_long  = int(self._geo_long_var.get())
            d_short = int(self._geo_short_var.get())
            spm     = float(self._geo_spm_var.get())
        except ValueError:
            from config import DISTANCE_LONG_STEPS, DISTANCE_SHORT_STEPS, STEPS_PER_MM
            d_long, d_short, spm = DISTANCE_LONG_STEPS, DISTANCE_SHORT_STEPS, STEPS_PER_MM
        return {
            "slider_length_steps": self._slider_length,
            "distance_long_steps": d_long,
            "distance_short_steps": d_short,
            "steps_per_mm": spm,
            "speed_calibration": {str(k): v for k, v in self._speed_table.items()},
        }

    def _save_cal(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Calibration JSON", "*.json")],
            initialfile="slider_calibration.json",
            parent=self)
        if not path:
            return
        try:
            d_long  = int(self._geo_long_var.get())
            d_short = int(self._geo_short_var.get())
            spm     = float(self._geo_spm_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Values",
                                   "Check Long Steps, Short Steps and Steps/mm fields.",
                                   parent=self)
            return
        data = save_calibration(path, self._slider_length, self._speed_table,
                                d_long, d_short, spm)
        set_active_calibration(data)
        messagebox.showinfo("Saved", f"Calibration saved:\n{path}", parent=self)
