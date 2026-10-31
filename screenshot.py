#!/usr/bin/env python3
"""Script to take screenshots of SimpleEtcher for documentation."""

import sys
import os
import time

# Ensure we're in the script's directory before importing
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

from PyQt5.QtWidgets import QApplication
from etcher import EtcherWindow, load_translations, t

# Load translations before creating window
ok = load_translations("en")
print(f"Translations loaded: {ok}")
print(f"language_selector key: '{t('language_selector')}'")

def capture_screenshots():
    app = QApplication(sys.argv)
    window = EtcherWindow()
    window.show()
    
    # Give the UI time to fully render
    for _ in range(10):
        app.processEvents()
        time.sleep(0.1)

    # Screenshot 1: Initial state (English)
    take_screenshot(window, "screenshot_initial.png")

    # Simulate selecting an image
    window.selected_image = "raspberry-pi-os-2024.iso"
    window.image_label.setText("raspberry-pi-os-2024.iso (2.1 GB)")
    window.image_label.setStyleSheet("color: #333; font-size: 14px;")
    app.processEvents()

    # Screenshot 2: Image selected (English)
    time.sleep(0.5)
    take_screenshot(window, "screenshot_image_selected.png")

    # Simulate progress
    window.status_label.setText(t("flashing_status", pct=65))
    window.progress_bar.setValue(65)
    app.processEvents()

    # Screenshot 3: During flashing (English)
    time.sleep(0.5)
    take_screenshot(window, "screenshot_flashing.png")

    # Switch to Persian
    window.change_language(1)  # Index 1 = Persian
    app.processEvents()

    # Screenshot 4: Persian language
    time.sleep(0.5)
    take_screenshot(window, "screenshot_persian.png")

    print("Screenshots captured!")
    app.quit()

def take_screenshot(window, filename):
    window.grab().save(filename)
    print(f"Saved: {filename}")

if __name__ == "__main__":
    capture_screenshots()