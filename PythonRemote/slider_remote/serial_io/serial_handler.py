# =============================================================================
# serial_io/serial_handler.py – Serielle Kommunikation
# Kapselt pyserial. Sendet Kommandos und liest Antworten des Controllers.
# Lesen läuft in einem Hintergrund-Thread, damit die UI nicht blockiert.
# =============================================================================

from typing import List
import threading
import serial
import serial.tools.list_ports
from config import SERIAL_BAUD, SERIAL_TIMEOUT


def list_ports() -> List[str]:
    """Gibt alle verfügbaren seriellen Ports als Liste zurück."""
    return [port.device for port in serial.tools.list_ports.comports()]


class SerialHandler:
    def __init__(self, on_receive=None):
        # on_receive: optionaler Callback(str) für eingehende Controller-Nachrichten
        self._port = None
        self._on_receive = on_receive
        self._read_thread = None
        self._running = False

    def connect(self, port: str) -> bool:
        """Öffnet die Verbindung zum gewählten COM-Port. Gibt True bei Erfolg zurück."""
        try:
            self._port = serial.Serial(port, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
            self._running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            return True
        except serial.SerialException as e:
            self._port = None
            raise ConnectionError(f"Verbindung zu {port} fehlgeschlagen: {e}")

    def disconnect(self):
        """Schließt die Verbindung sauber."""
        self._running = False
        if self._port and self._port.is_open:
            self._port.close()
        self._port = None

    def is_connected(self) -> bool:
        return self._port is not None and self._port.is_open

    def send(self, command: str):
        """Sendet einen Befehl als Zeile (mit \\n-Terminator) an den Controller."""
        if not self.is_connected():
            raise ConnectionError("Nicht verbunden.")
        # Arduino-Parser erwartet \\n als Abschluss-Zeichen
        self._port.write((command + "\n").encode("utf-8"))

    def build_normal_command(self, speed: int, distance: int, ramp: int) -> str:
        """Baut den seriellen Befehlsstring für den Normal-Modus."""
        return f"normal,{speed},{distance},{ramp},0,2"

    def build_timelapse_command(self, speed: int, distance: int, ramp: int,
                                time_s: int, subdivisions: int) -> str:
        """Baut den seriellen Befehlsstring für den Timelapse-Modus."""
        return f"timelapse,{speed},{distance},{ramp},{time_s},{subdivisions}"

    def build_rth_command(self) -> str:
        """Baut den seriellen Befehlsstring für Return to Home."""
        return "rth,0,0,0,0,0"

    def _read_loop(self):
        """Hintergrundthread: Liest kontinuierlich Antworten vom Controller."""
        while self._running and self._port and self._port.is_open:
            try:
                line = self._port.readline().decode("utf-8", errors="replace").strip()
                if line and self._on_receive:
                    self._on_receive(line)
            except serial.SerialException:
                # Verbindung unterbrochen (z.B. USB gezogen)
                self._running = False
                if self._on_receive:
                    self._on_receive("[Verbindung unterbrochen]")
