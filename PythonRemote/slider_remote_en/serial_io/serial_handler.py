# =============================================================================
# serial_io/serial_handler.py – Serial communication
# Wraps pyserial. Sends commands and reads responses from the controller.
# Reading runs in a background thread so the UI is never blocked.
# =============================================================================

from typing import List
import threading
import time
import serial
import serial.tools.list_ports
from config import SERIAL_BAUD, SERIAL_TIMEOUT


def list_ports() -> List[str]:
    """Returns all available serial ports as a list."""
    return [port.device for port in serial.tools.list_ports.comports()]


class SerialHandler:
    def __init__(self, on_receive=None):
        # on_receive: primary callback(str) for incoming controller messages
        self._port = None
        self._on_receive = on_receive
        self._extra_listeners = []
        self._read_thread = None
        self._running = False

    def add_listener(self, callback):
        """Registers an additional receive callback (e.g. calibration window)."""
        if callback not in self._extra_listeners:
            self._extra_listeners.append(callback)

    def remove_listener(self, callback):
        """Removes a previously registered extra callback."""
        if callback in self._extra_listeners:
            self._extra_listeners.remove(callback)

    def connect(self, port: str) -> bool:
        """Opens the connection to the selected COM port. Returns True on success."""
        try:
            self._port = serial.Serial(port, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
            # Arduino resets on DTR when the port opens – wait for it to finish booting
            time.sleep(2)
            self._running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            return True
        except serial.SerialException as e:
            self._port = None
            raise ConnectionError(f"Connection to {port} failed: {e}")

    def disconnect(self):
        """Closes the connection cleanly."""
        self._running = False
        if self._port and self._port.is_open:
            self._port.close()
        self._port = None

    def is_connected(self) -> bool:
        return self._port is not None and self._port.is_open

    def send(self, command: str):
        """Sends a command as a line (with \\n terminator) to the controller."""
        if not self.is_connected():
            raise ConnectionError("Not connected.")
        # Arduino parser expects \\n as the terminating character
        self._port.write((command + "\n").encode("utf-8"))
        self._port.flush()

    def build_normal_command(self, speed: int, distance: int, ramp: int) -> str:
        """Builds the serial command string for Normal mode."""
        return f"normal,{speed},{distance},{ramp},0,2"

    def build_timelapse_command(self, speed: int, distance: int, ramp: int,
                                time_s: int, subdivisions: int) -> str:
        """Builds the serial command string for Timelapse mode."""
        return f"timelapse,{speed},{distance},{ramp},{time_s},{subdivisions}"

    def build_rth_command(self) -> str:
        return "rth"

    def build_start_command(self) -> str:
        return "start"

    def build_stop_command(self) -> str:
        return "stop"

    def _read_loop(self):
        """Background thread: continuously reads responses from the controller."""
        while self._running and self._port and self._port.is_open:
            try:
                line = self._port.readline().decode("utf-8", errors="replace").strip()
                if line:
                    if self._on_receive:
                        self._on_receive(line)
                    for cb in list(self._extra_listeners):
                        cb(line)
            except serial.SerialException:
                self._running = False
                if self._on_receive:
                    self._on_receive("[Connection lost]")
