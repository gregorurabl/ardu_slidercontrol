#!/usr/bin/env python3
# build.py – Erzeugt ein portables Single-File-Binary via PyInstaller
# Aufruf: python build.py
# Voraussetzung: pip install pyinstaller

import subprocess
import sys

subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onefile",                        # alles in eine einzige .exe / Binary
    "--windowed",                       # kein Konsolenfenster (Windows/macOS)
    "--name", "SliderRemote",
    # CustomTkinter benötigt seine Theme-Dateien, die explizit eingebunden werden müssen
    "--collect-data", "customtkinter",
    "main.py"
], check=True)

print("\nBinary liegt in dist/SliderRemote")
