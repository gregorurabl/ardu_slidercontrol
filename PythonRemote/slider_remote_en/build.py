#!/usr/bin/env python3
# build.py – Creates a portable single-file binary via PyInstaller
# Usage: python build.py
# Prerequisite: pip install pyinstaller

import subprocess
import sys

subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onefile",                        # bundle everything into a single .exe / binary
    "--windowed",                       # no console window (Windows / macOS)
    "--name", "SliderRemote",
    # CustomTkinter requires its theme files to be bundled explicitly
    "--collect-data", "customtkinter",
    "main.py"
], check=True)

print("\nBinary is located in dist/SliderRemote")
