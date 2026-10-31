#!/usr/bin/env python3
"""Script to take screenshots of SimpleEtcher for documentation."""

import sys
import os
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtCore import QTimer, Qt
from etcher import EtcherWindow

def capture_screenshots():
    app = QApplication(sys.argv)
    window = EtcherWindow()
    window.show()
    app.processEvents()

    # Screenshot 1: Initial state
    QTimer.singleShot(500, lambda: take_screenshot(window, "screenshot_initial.png"))
    
    # Wait for first screenshot
    app.processEvents()
    import time
    time.sleep(1)

    # Simulate selecting an image (just set the label text)
    window.selected_image = "raspberry-pi-os-2024.iso"
    window.image_label.setText("raspberry-pi-os-2024.iso (2.1 GB)")
    window.image_label.setStyleSheet("color: #333; font-size: 14px;")
    app.processEvents()

    # Screenshot 2: Image selected
    QTimer.singleShot(500, lambda: take_screenshot(window, "screenshot_image_selected.png"))
    time.sleep(1)

    # Simulate progress
    window.status_label.setText("Flashing... 65%")
    window.progress_bar.setValue(65)
    app.processEvents()

    # Screenshot 3: During flashing
    QTimer.singleShot(500, lambda: take_screenshot(window, "screenshot_flashing.png"))
    time.sleep(1)

    # Simulate completion
    window.status_label.setText("✓ Flashing complete!")
    window.status_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
    window.progress_bar.setValue(100)
    app.processEvents()

    # Screenshot 4: Complete
    QTimer.singleShot(500, lambda: take_screenshot(window, "screenshot_complete.png"))
    time.sleep(1)

    print("Screenshots captured!")
    app.quit()

def take_screenshot(window, filename):
    window.grab().save(filename)
    print(f"Saved: {filename}")

if __name__ == "__main__":
    capture_screenshots()