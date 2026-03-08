# =============================================================================
# ui/app.py – Main window
# Builds the entire layout: connection bar, tabs, action buttons, log.
# =============================================================================

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os

from serial_io.serial_handler import SerialHandler, list_ports
from logic.validator import validate_normal, validate_timelapse
from logic.converter import speed_pct_to_steps, steps_to_cm
from logic.preset_manager import save_preset, load_preset
from ui.tabs import NormalTab, TimelapseTab
from config import PRESETS_DIR


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Slider Remote Control")
        self.geometry("680x720")
        self.resizable(False, False)

        # Serial handler – on_receive callback writes into the log field
        self.serial = SerialHandler(on_receive=self._log_receive)

        self._build_connection_bar()
        self._build_tabs()
        self._build_action_buttons()
        self._build_log()

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
                                         command=self._toggle_connection)
        self.connect_btn.pack(side="left", padx=4)

        self.status_label = ctk.CTkLabel(frame, text="Disconnected", text_color="tomato")
        self.status_label.pack(side="left", padx=(8, 4))

    def _refresh_ports(self):
        ports = list_ports()
        if ports:
            self.port_dropdown.configure(values=ports)
            self.port_var.set(ports[0])
        else:
            self.port_dropdown.configure(values=["No port found"])
            self.port_var.set("No port found")

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
        self.timelapse_tab = TimelapseTab(self.tabview.tab("Timelapse"))

    # -------------------------------------------------------------------------
    # Action buttons (NORMAL START | TIMELAPSE START | RTH)
    # -------------------------------------------------------------------------
    def _build_action_buttons(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=12, pady=4)

        btn_cfg = {"height": 42, "font": ctk.CTkFont(size=14, weight="bold")}

        ctk.CTkButton(frame, text="NORMAL START", fg_color="#1f6aa5",
                      command=self._send_normal, **btn_cfg).pack(
            side="left", expand=True, fill="x", padx=(8, 4), pady=8)

        ctk.CTkButton(frame, text="TIMELAPSE START", fg_color="#b5820a",
                      command=self._send_timelapse, **btn_cfg).pack(
            side="left", expand=True, fill="x", padx=4, pady=8)

        ctk.CTkButton(frame, text="RTH", fg_color="#8b2020",
                      command=self._send_rth, **btn_cfg).pack(
            side="left", expand=True, fill="x", padx=(4, 8), pady=8)

        # Preset buttons in a second row
        preset_row = ctk.CTkFrame(self)
        preset_row.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkButton(preset_row, text="Load Preset", width=150,
                      command=self._load_preset).pack(side="left", padx=(8, 4), pady=4)
        ctk.CTkButton(preset_row, text="Save Preset", width=150,
                      command=self._save_preset).pack(side="left", padx=4, pady=4)

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

    def _send_timelapse(self):
        if not self._check_connected():
            return
        v = self.timelapse_tab.get_values()
        speed_steps = speed_pct_to_steps(v["speed_pct"])
        error = validate_timelapse(speed_steps, v["distance_steps"], v["ramp_steps"],
                                   v["time_s"], v["subdivisions"])
        if error:
            messagebox.showwarning("Invalid Input", error)
            return
        cmd = self.serial.build_timelapse_command(
            speed_steps, v["distance_steps"], v["ramp_steps"], v["time_s"], v["subdivisions"])
        self._send(cmd)

    def _send_rth(self):
        if not self._check_connected():
            return
        self._send(self.serial.build_rth_command())

    def _send(self, cmd: str):
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
            "normal_distance_steps": n["distance_steps"],
            "normal_ramp_steps": n["ramp_steps"],
            # Timelapse tab
            "tl_speed_pct": t["speed_pct"],
            "tl_distance_steps": t["distance_steps"],
            "tl_ramp_steps": t["ramp_steps"],
            "tl_time_s": t["time_s"],
            "tl_subdivisions": t["subdivisions"],
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
                data["tl_subdivisions"])
            self._log(f"Preset loaded: {data.get('name', path)}")
        except (KeyError, ValueError) as e:
            messagebox.showerror("Preset Error", f"Invalid preset format:\n{e}")

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

    def _log(self, text: str):
        """Appends a line to the log field (thread-safe via after)."""
        self.after(0, self._log_append, text)

    def _log_append(self, text: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _log_receive(self, text: str):
        """Callback for incoming controller responses (called from background thread)."""
        self._log(f"  Controller: {text}")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _check_connected(self) -> bool:
        if not self.serial.is_connected():
            messagebox.showwarning("Not Connected", "Please connect to a port first.")
            return False
        return True
