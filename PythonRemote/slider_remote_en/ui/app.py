# =============================================================================
# ui/app.py – Main window
# Builds the entire layout: connection bar, tabs, action buttons, log.
# =============================================================================

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import time

from serial_io.serial_handler import SerialHandler, list_ports
from logic.validator import validate_normal, validate_timelapse
from logic.converter import speed_pct_to_steps, steps_to_cm
from logic.preset_manager import save_preset, load_preset
from logic.calibration_manager import load_calibration, set_active_calibration, get_active_calibration
from ui.tabs import NormalTab, TimelapseTab
from ui.calibration_window import CalibrationWindow
from config import PRESETS_DIR


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Slider Remote Control")
        self.geometry("680x780")
        self.resizable(False, False)

        # Serial handler – on_receive callback writes into the log field
        self.serial = SerialHandler(on_receive=self._log_receive)
        self._last_send_time = 0.0
        self._timestamps_enabled = True
        self._timed_progress_end = 0.0
        self._timelapse_running = False  # triggers auto-reconnect on completion

        self._build_connection_bar()
        self._build_tabs()
        self._build_action_buttons()
        self._build_log()
        self._build_calibration_bar()

    # -------------------------------------------------------------------------
    # Connection bar
    # -------------------------------------------------------------------------
    def _build_connection_bar(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(frame, text="Port:").pack(side="left", padx=(8, 4))

        self.port_var = ctk.StringVar()
        self.port_dropdown = ctk.CTkOptionMenu(frame, variable=self.port_var, width=160)
        self.port_dropdown.pack(side="left", padx=4)
        self._refresh_ports()

        ctk.CTkButton(frame, text="Refresh", width=100,
                      command=self._refresh_ports).pack(side="left", padx=4)

        self.connect_btn = ctk.CTkButton(frame, text="Connect", width=110,
                                         command=self._on_connect_btn)
        self.connect_btn.pack(side="left", padx=4)

        self.status_label = ctk.CTkLabel(frame, text="Disconnected", text_color="tomato")
        self.status_label.pack(side="left", padx=(8, 4))

    def _refresh_ports(self):
        ports = list_ports()
        if ports:
            self.port_dropdown.configure(values=ports)
            self.port_var.set(ports[0])
            if not hasattr(self, "_auto_connected"):
                self._auto_connected = True
                self._autoconnect_remaining = 5
                self.after(100, self._autoconnect_tick)  # defer until UI fully built
        else:
            self.port_dropdown.configure(values=["No port found"])
            self.port_var.set("No port found")

    def _autoconnect_tick(self):
        if self._autoconnect_remaining <= 0:
            self.connect_btn.configure(text="Connect")
            self._toggle_connection()
            return
        self.connect_btn.configure(
            text=f"Cancel ({self._autoconnect_remaining}s)",
            fg_color="#8b2020")
        self._autoconnect_remaining -= 1
        self._autoconnect_after = self.after(1000, self._autoconnect_tick)

    def _cancel_autoconnect(self):
        if hasattr(self, "_autoconnect_after"):
            self.after_cancel(self._autoconnect_after)
        self.connect_btn.configure(text="Connect", fg_color=["#3B8ED0", "#1F6AA5"])
        self._autoconnect_remaining = 0

    def _on_connect_btn(self):
        """Dispatches to cancel-autoconnect or normal toggle depending on state."""
        if getattr(self, "_autoconnect_remaining", 0) > 0:
            self._cancel_autoconnect()
        else:
            self._toggle_connection()

    def _toggle_connection(self):
        if self.serial.is_connected():
            self.serial.disconnect()
            self.connect_btn.configure(text="Connect")
            self.status_label.configure(text="Disconnected", text_color="tomato")
            self._log("Connection closed.")
        else:
            try:
                self.serial.connect(self.port_var.get())
                self.connect_btn.configure(text="Disconnect")
                self.status_label.configure(text="Connected", text_color="lightgreen")
                self._log(f"Connected to {self.port_var.get()} @ 115200 baud.")
            except ConnectionError as e:
                messagebox.showerror("Connection Error", str(e))

    # -------------------------------------------------------------------------
    # Tabs
    # -------------------------------------------------------------------------
    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=4)

        self.tabview.add("Normal")
        self.tabview.add("Timelapse")

        self.normal_tab = NormalTab(self.tabview.tab("Normal"))
        self.normal_tab.set_serial(self.serial)
        self.timelapse_tab = TimelapseTab(self.tabview.tab("Timelapse"))

    # -------------------------------------------------------------------------
    # Action buttons (NORMAL START | TIMELAPSE START | RTH)
    # -------------------------------------------------------------------------
    def _build_action_buttons(self):
        # Progress bar – sits above the action buttons, hidden until a run starts
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_frame.pack(fill="x", padx=12, pady=(4, 0))
        self._progress_bar = ctk.CTkProgressBar(prog_frame)
        self._progress_bar.set(0)
        self._progress_bar.pack(fill="x", padx=4, pady=(2, 0))
        self._progress_lbl = ctk.CTkLabel(prog_frame, text="", anchor="w",
                                          text_color="gray60",
                                          font=ctk.CTkFont(size=11))
        self._progress_lbl.pack(fill="x", padx=4)
        self._progress_total = 0

        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=12, pady=4)

        btn_cfg = {"height": 42, "font": ctk.CTkFont(size=14, weight="bold")}

        ctk.CTkButton(frame, text="NORMAL START", fg_color="#1f6aa5",
                      command=self._send_normal, **btn_cfg).pack(
            side="left", expand=True, fill="x", padx=(8, 4), pady=8)

        self._freerun_active = False
        self.manual_btn = ctk.CTkButton(frame, text="MANUAL START", fg_color="#2d6e2d",
                                        command=self._toggle_manual, **btn_cfg)
        self.manual_btn.pack(side="left", expand=True, fill="x", padx=4, pady=8)

        ctk.CTkButton(frame, text="TIMELAPSE START", fg_color="#b5820a",
                      command=self._send_timelapse, **btn_cfg).pack(
            side="left", expand=True, fill="x", padx=(4, 4), pady=8)

        ctk.CTkButton(frame, text="RTH", fg_color="#8b2020",
                      command=self._send_rth, **btn_cfg).pack(
            side="left", expand=True, fill="x", padx=(0, 8), pady=8)

        # Preset + log utility buttons in a shared row
        preset_row = ctk.CTkFrame(self)
        preset_row.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkButton(preset_row, text="Load Preset", width=130,
                      command=self._load_preset).pack(side="left", padx=(8, 4), pady=4)
        ctk.CTkButton(preset_row, text="Save Preset", width=130,
                      command=self._save_preset).pack(side="left", padx=(0, 4), pady=4)
        self.ts_btn = ctk.CTkButton(preset_row, text="Timestamps: ON", width=130,
                                    fg_color="#2d6e2d",
                                    command=self._toggle_timestamps)
        self.ts_btn.pack(side="left", padx=(0, 4), pady=4)
        ctk.CTkButton(preset_row, text="Export Log", width=110,
                      command=self._export_log).pack(side="left", padx=(0, 4), pady=4)
        ctk.CTkButton(preset_row, text="Clear Log", width=110,
                      command=self._clear_log).pack(side="left", padx=0, pady=4)

    # -------------------------------------------------------------------------
    # Send methods
    # -------------------------------------------------------------------------
    def _send_normal(self):
        if not self._check_connected():
            return
        v = self.normal_tab.get_values()
        speed_steps = speed_pct_to_steps(v["speed_pct"])
        error = validate_normal(speed_steps, v["distance_steps"], v["ramp_steps"])
        if error:
            messagebox.showwarning("Invalid Input", error)
            return
        cmd = self.serial.build_normal_command(speed_steps, v["distance_steps"], v["ramp_steps"])
        self._send(cmd)
        # Normal run sends no serial progress – use time-based estimate
        travel_s = abs(v["distance_steps"]) / max(speed_steps, 1)
        self._start_timed_progress(travel_s, abs(v["distance_steps"]))

    def _send_timelapse(self):
        if not self._check_connected():
            return
        v = self.timelapse_tab.get_values()
        speed_steps = speed_pct_to_steps(v["speed_pct"])
        # Total wait time = user delay + exposure time (motor must not move during exposure)
        total_time_s = int(v["time_s"] + v["exposure_s"])
        error = validate_timelapse(speed_steps, v["distance_steps"], 0,
                                   total_time_s, v["subdivisions"])
        if error:
            messagebox.showwarning("Invalid Input", error)
            return
        cmd = self.serial.build_timelapse_command(
            speed_steps, v["distance_steps"], 0, total_time_s, v["subdivisions"])
        self._send(cmd)
        self._timelapse_running = True

    def _toggle_manual(self):
        self._freerun_active = not self._freerun_active
        if self._freerun_active:
            self.serial.send(self.serial.build_start_command())
            self._log("Sent: start")
            self.manual_btn.configure(text="STOP", fg_color="#8b2020")
        else:
            self.serial.send(self.serial.build_stop_command())
            self._log("Sent: stop")
            self.manual_btn.configure(text="MANUAL START", fg_color="#2d6e2d")

    def _send_rth(self):
        if not self._check_connected():
            return
        self._send(self.serial.build_rth_command())

    def _send(self, cmd: str):
        # Ignore sends within 500 ms of the last one to prevent accidental repeats
        now = time.monotonic()
        if now - self._last_send_time < 0.5:
            return
        self._last_send_time = now
        try:
            self.serial.send(cmd)
            self._log(f"Sent: {cmd}")
        except ConnectionError as e:
            messagebox.showerror("Send Error", str(e))

    # -------------------------------------------------------------------------
    # Preset load / save
    # -------------------------------------------------------------------------
    def _save_preset(self):
        """Reads current values from both tabs and saves them as a .json file."""
        n = self.normal_tab.get_values()
        t = self.timelapse_tab.get_values()
        data = {
            "name": "",
            # Normal tab
            "normal_speed_pct": n["speed_pct"],
            "normal_distance_steps": n["distance_steps"],  # sign encodes direction
            "normal_ramp_steps": n["ramp_steps"],
            # Timelapse tab
            "tl_speed_pct": t["speed_pct"],
            "tl_distance_steps": t["distance_steps"],      # sign encodes direction
            "tl_ramp_steps": t["ramp_steps"],
            "tl_time_s": t["time_s"],
            "tl_subdivisions": t["subdivisions"],
            "tl_exposure_idx": self.timelapse_tab._exp_idx,
        }
        os.makedirs(PRESETS_DIR, exist_ok=True)
        path = filedialog.asksaveasfilename(
            initialdir=PRESETS_DIR, defaultextension=".json",
            filetypes=[("JSON Preset", "*.json")])
        if path:
            data["name"] = os.path.splitext(os.path.basename(path))[0]
            save_preset(path, data)
            self._log(f"Preset saved: {path}")

    def _load_preset(self):
        """Opens a .json file and populates both tabs."""
        path = filedialog.askopenfilename(
            initialdir=PRESETS_DIR, filetypes=[("JSON Preset", "*.json")])
        if not path:
            return
        try:
            data = load_preset(path)
            self.normal_tab.set_values(
                data["normal_speed_pct"],
                data["normal_distance_steps"],
                data["normal_ramp_steps"])
            self.timelapse_tab.set_values(
                data["tl_speed_pct"],
                data["tl_distance_steps"],
                data["tl_ramp_steps"],
                data["tl_time_s"],
                data["tl_subdivisions"],
                data.get("tl_exposure_idx", 12))
            self._log(f"Preset loaded: {data.get('name', path)}")
        except (KeyError, ValueError) as e:
            messagebox.showerror("Preset Error", f"Invalid preset format:\n{e}")

    def _clear_log(self):
        """Clears all content from the log field."""
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _export_log(self):
        """Writes the current log content to a .txt file chosen via file dialog."""
        content = self.log_box.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Export Log", "Log is empty, nothing to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._log(f"Log exported: {path}")

    # -------------------------------------------------------------------------
    # Log
    # -------------------------------------------------------------------------
    def _build_log(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(frame, text="Log", anchor="w").pack(fill="x", padx=8, pady=(4, 0))

        self.log_box = ctk.CTkTextbox(frame, height=120, state="disabled",
                                      font=ctk.CTkFont(family="Courier", size=12))
        self.log_box.pack(fill="x", padx=8, pady=(0, 8))

    def _start_timed_progress(self, travel_s: float, distance_steps: int):
        """Starts a time-based progress bar for Normal runs (no serial step feedback)."""
        self._timed_progress_end = time.monotonic() + travel_s
        self._timed_progress_total = distance_steps
        self._timed_progress_duration = max(travel_s, 0.1)
        self._timed_progress_tick()

    def _timed_progress_tick(self):
        now = time.monotonic()
        elapsed = self._timed_progress_duration - (self._timed_progress_end - now)
        if elapsed < 0:
            return
        ratio = min(elapsed / self._timed_progress_duration, 1.0)
        est_steps = int(ratio * self._timed_progress_total)
        self._update_progress(est_steps, self._timed_progress_total)
        if ratio < 1.0:
            self.after(100, self._timed_progress_tick)

    def _update_progress(self, done: int, total: int):
        ratio = min(done / total, 1.0)
        self._progress_bar.set(ratio)
        self._progress_lbl.configure(
            text=f"{done} / {total} steps  ({ratio * 100:.1f}%)")

    def _reset_progress(self):
        self._progress_bar.set(0)
        self._progress_lbl.configure(text="")

    def _toggle_timestamps(self):
        self._timestamps_enabled = not self._timestamps_enabled
        if self._timestamps_enabled:
            self.ts_btn.configure(text="Timestamps: ON", fg_color="#2d6e2d")
        else:
            self.ts_btn.configure(text="Timestamps: OFF", fg_color="#555555")

    def _log(self, text: str):
        """Appends a line to the log field (thread-safe via after)."""
        if self._timestamps_enabled:
            text = f"[{time.strftime('%H:%M:%S')}] {text}"
        self.after(0, self._log_append, text)

    def _log_append(self, text: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _log_receive(self, text: str):
        """Callback for incoming controller responses (called from background thread)."""
        # Progress messages from Arduino: "steps_done/steps_total"
        if "/" in text and text.replace("/", "").replace(" ", "").isdigit():
            parts = text.split("/")
            if len(parts) == 2:
                try:
                    done, total = int(parts[0].strip()), int(parts[1].strip())
                    if total > 0:
                        self.after(0, self._update_progress, done, total)
                        return  # suppress from log – high-frequency noise
                except ValueError:
                    pass
        if "Run Completed" in text or "Timelapse Complete" in text or "Return to Home" in text:
            self.after(0, self._reset_progress)
        if "Timelapse Complete" in text and self._timelapse_running:
            self._timelapse_running = False
            # RTH takes up to 30s at max speed over full length + 5s Arduino end-delay already elapsed
            # Reconnect after 35s to let RTH finish before resetting the connection
            self.after(0, self._log, "  Auto-reconnect in 35 s (waiting for RTH to complete)...")
            self.after(35000, self._auto_reconnect)
        self._log(f"  Controller: {text}")

    # -------------------------------------------------------------------------
    # Calibration bar
    # -------------------------------------------------------------------------
    def _build_calibration_bar(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkButton(frame, text="Load Calibration", width=140,
                      command=self._load_calibration_file).pack(side="left", padx=(8, 4), pady=4)
        ctk.CTkButton(frame, text="Calibration Run", width=140,
                      command=self._open_calibration_window).pack(side="left", padx=(0, 12), pady=4)

        self.cal_status_lbl = ctk.CTkLabel(frame, text="No calibration loaded",
                                           text_color="gray60",
                                           font=ctk.CTkFont(size=11), anchor="w")
        self.cal_status_lbl.pack(side="left")

    def _load_calibration_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Calibration JSON", "*.json")])
        if not path:
            return
        try:
            data = load_calibration(path)
            set_active_calibration(data)
            self._apply_calibration_to_ui(data)
            name = os.path.basename(path)
            steps = data["slider_length_steps"]
            self.cal_status_lbl.configure(
                text=f"Loaded: {name}  ({steps} steps)", text_color="#6ec06e")
            self._log(f"Calibration loaded: {path}")
        except (ValueError, KeyError, OSError) as e:
            messagebox.showerror("Calibration Error", f"Could not load calibration:\n{e}")

    def _apply_calibration_to_ui(self, data: dict):
        """Updates distance slider limits and shortcuts from calibration geometry."""
        from config import DISTANCE_LONG_STEPS, DISTANCE_SHORT_STEPS
        d_long  = int(data.get("distance_long_steps",  DISTANCE_LONG_STEPS))
        d_short = int(data.get("distance_short_steps", DISTANCE_SHORT_STEPS))
        for tab in (self.normal_tab, self.timelapse_tab):
            tab.distance.set_max(d_long)
            tab.update_shortcuts(d_short, d_long)

    def _open_calibration_window(self):
        if not self.serial.is_connected():
            messagebox.showwarning("Not Connected",
                                   "Connect to the controller before running calibration.")
            return
        win = CalibrationWindow(self, self.serial,
                                log_callback=self._log,
                                normal_speed_steps=speed_pct_to_steps(
                                    self.normal_tab.get_values()["speed_pct"]))
        win.focus()
        # Update status label when window closes if calibration was applied
        def _on_close():
            cal = get_active_calibration()
            if cal:
                steps = cal["slider_length_steps"]
                self.cal_status_lbl.configure(
                    text=f"Calibration active  ({steps} steps)", text_color="#6ec06e")
                self._apply_calibration_to_ui(cal)
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (win._on_close(), _on_close()))

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _auto_reconnect(self):
        """Disconnect and reconnect to force Arduino reset after a completed timelapse."""
        port = self.port_var.get()
        self._log("  Auto-reconnect: disconnecting...")
        try:
            self.serial.disconnect()
        except Exception:
            pass
        self.connect_btn.configure(text="Connect")
        self.status_label.configure(text="Reconnecting...", text_color="#c8922a")
        # Brief pause then reconnect (includes 2s Arduino boot delay in serial_handler)
        self.after(1000, lambda: self._auto_reconnect_complete(port))

    def _auto_reconnect_complete(self, port: str):
        try:
            self.serial.connect(port)
            self.connect_btn.configure(text="Disconnect")
            self.status_label.configure(text="Connected", text_color="lightgreen")
            self._log(f"  Auto-reconnect: connected to {port}. System ready.")
        except ConnectionError as e:
            self.connect_btn.configure(text="Connect")
            self.status_label.configure(text="Disconnected", text_color="tomato")
            self._log(f"  Auto-reconnect failed: {e}")

    def _check_connected(self) -> bool:
        if not self.serial.is_connected():
            messagebox.showwarning("Not Connected", "Please connect to a port first.")
            return False
        return True
