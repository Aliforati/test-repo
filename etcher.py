#!/usr/bin/env python3
"""
SimpleEtcher - A lightweight disk imaging tool similar to BalenaEtcher.
Flashes OS images (.iso, .img) to SD cards and USB drives.
"""

import sys
import os
import time
import json
import platform
from datetime import timedelta

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QComboBox, QFileDialog, QMessageBox,
        QProgressBar, QFrame, QGraphicsDropShadowEffect
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QIcon, QColor, QPainter, QLinearGradient
    HAS_QT = True
except ImportError:
    HAS_QT = False

try:
    from rich.console import Console
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None

# Translation system
TRANSLATIONS = {}
CURRENT_LANGUAGE = "en"

def load_translations(lang):
    global CURRENT_LANGUAGE, TRANSLATIONS
    try:
        with open(f"translations/{lang}.json", "r", encoding="utf-8") as f:
            TRANSLATIONS = json.load(f)
            CURRENT_LANGUAGE = lang
            return True
    except Exception as e:
        print(f"Error loading translations for {lang}: {e}")
        return False

def t(key, **kwargs):
    """Translate a key with optional string formatting."""
    text = TRANSLATIONS.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text

def get_platform():
    """Detect current platform."""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Linux":
        return "linux"
    elif system == "Darwin":
        return "macos"
    return "unknown"


def list_drives():
    """List available block devices/drives."""
    platform_name = get_platform()
    drives = []

    if platform_name == "windows":
        try:
            import win32api
            for i in range(65, 91):  # A-Z
                drive_letter = chr(i) + ":"
                try:
                    drive_type = win32api.GetDriveType(drive_letter)
                    if drive_type == win32api.DRIVE_REMOVABLE or drive_type == win32api.DRIVE_FIXED:
                        free, total, _ = win32api.GetDiskFreeSpaceEx(drive_letter)
                        drives.append({
                            "device": drive_letter,
                            "type": "removable" if drive_type == win32api.DRIVE_REMOVABLE else "fixed",
                            "size": total
                        })
                except Exception:
                    pass
        except ImportError:
            return drives

    elif platform_name in ["linux", "macos"]:
        import subprocess
        try:
            if platform_name == "linux":
                result = subprocess.run(
                    ["lsblk", "-d", "-o", "NAME,TYPE,SIZE,RM,MOUNTPOINT"],
                    capture_output=True, text=True
                )
                for line in result.stdout.strip().split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 5 and (parts[3] == "1" or parts[1] == "disk"):
                        drives.append({
                            "device": f"/dev/{parts[0]}",
                            "type": "removable" if parts[3] == "1" else "fixed",
                            "size": parse_size(parts[2])
                        })
            else:  # macOS
                result = subprocess.run(
                    ["diskutil", "list"],
                    capture_output=True, text=True
                )
                lines = result.stdout.split("\n")
                for line in lines:
                    if "disk" in line and "external" in line:
                        drives.append({
                            "device": f"/dev/{line.split()[0]}",
                            "type": "removable",
                            "size": 0
                        })
        except Exception as e:
            if console:
                console.print(f"[red]Error listing drives: {e}[/red]")

    return drives


def parse_size(size_str):
    """Parse size string to bytes."""
    units = {'B': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
    for unit in units:
        if size_str.upper().endswith(unit):
            return int(float(size_str[:-1]) * units[unit])
    return int(size_str)


def format_size(size_bytes):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


class FlashWorker(QThread):
    """Background thread for flashing."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, image_path, drive_path):
        super().__init__()
        self.image_path = image_path
        self.drive_path = drive_path
        self.cancelled = False

    def run(self):
        try:
            platform_name = get_platform()
            image_size = os.path.getsize(self.image_path)

            if platform_name == "windows":
                self._flash_windows(image_size)
            elif platform_name in ["linux", "macos"]:
                self._flash_unix(image_size)
            else:
                self.finished.emit(False, f"Unsupported platform: {platform_name}")

            if not self.cancelled:
                self.finished.emit(True, "Flashing complete!")
        except Exception as e:
            self.finished.emit(False, str(e))

    def _flash_windows(self, image_size):
        import win32file
        import win32con

        drive_handle = win32file.CreateFile(
            f"\\\\.\\{self.drive_path.replace(':','')}",
            win32con.GENERIC_WRITE,
            0, None, win32con.OPEN_EXISTING, 0, None
        )

        try:
            with open(self.image_path, 'rb') as img:
                written = 0
                chunk_size = 4 * 1024 * 1024

                while not self.cancelled:
                    chunk = img.read(chunk_size)
                    if not chunk:
                        break
                    win32file.WriteFile(drive_handle, chunk)
                    written += len(chunk)
                    pct = int((written / image_size) * 100)
                    self.progress.emit(pct)
        finally:
            win32file.CloseHandle(drive_handle)

    def _flash_unix(self, image_size):
        import subprocess

        cmd = f"dd if={self.image_path} of={self.drive_path} bs=4M status=progress"
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        while not self.cancelled:
            line = proc.stdout.readline().decode('utf-8', errors='ignore')
            if not line and proc.poll() is not None:
                break

            # Parse dd progress (simplified)
            try:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == 'copied':
                        size_str = parts[i-1]
                        size = parse_size(size_str)
                        pct = int((size / image_size) * 100)
                        self.progress.emit(min(pct, 100))
                        break
            except:
                pass

        proc.wait()
        if proc.returncode != 0 and not self.cancelled:
            raise Exception(f"dd failed with exit code {proc.returncode}")

    def cancel(self):
        self.cancelled = True


class EtcherWindow(QMainWindow):
    """Main GUI window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("app_title"))
        self.setFixedSize(500, 420)

        # State
        self.selected_image = None
        self.worker = None

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 25, 30, 25)

        # Title row with language selector
        title_row = QHBoxLayout()
        
        title_label = QLabel(t("app_title"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(24)
        title_label.setFont(title_font)
        self.title_label = title_label
        title_row.addWidget(title_label, 1)
        
        # Language selector
        lang_row = QHBoxLayout()
        lang_label = QLabel(t("language_selector"))
        lang_label.setStyleSheet("color: #666; font-size: 12px;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "فارسی"])
        self.lang_combo.setCurrentIndex(0 if CURRENT_LANGUAGE == "en" else 1)
        self.lang_combo.setFixedWidth(90)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                padding: 4px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
        """)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_row.addWidget(lang_label)
        lang_row.addWidget(self.lang_combo)
        title_row.addLayout(lang_row)
        
        layout.addLayout(title_row)

        subtitle_label = QLabel(t("subtitle"))
        subtitle_label.setStyleSheet("color: #666;")
        self.subtitle_label = subtitle_label
        layout.addWidget(subtitle_label)

        layout.addSpacing(10)

        # Image selection card
        self.image_card = QFrame()
        self.image_card.setFixedHeight(80)
        self.image_card.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 10px;
                border: 2px solid #e0e0e0;
            }
        """)
        image_layout = QHBoxLayout(self.image_card)
        image_layout.setContentsMargins(15, 10, 15, 10)

        self.image_label = QLabel(t("no_image"))
        self.image_label.setStyleSheet("color: #999; font-size: 14px;")
        image_layout.addWidget(self.image_label, 1)

        self.select_image_btn = QPushButton(t("select_image_btn"))
        self.select_image_btn.setFixedWidth(120)
        self.select_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #3a7bc8;
            }
        """)
        self.select_image_btn.clicked.connect(self.select_image)
        image_layout.addWidget(self.select_image_btn)

        layout.addWidget(self.image_card)

        # Drive selection card
        self.drive_card = QFrame()
        self.drive_card.setFixedHeight(80)
        self.drive_card.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 10px;
                border: 2px solid #e0e0e0;
            }
        """)
        drive_layout = QHBoxLayout(self.drive_card)
        drive_layout.setContentsMargins(15, 10, 15, 10)

        self.drive_combo = QComboBox()
        self.drive_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: white;
                font-size: 14px;
            }
        """)
        self.refresh_drives()
        drive_layout.addWidget(self.drive_combo, 1)

        self.flash_btn = QPushButton(t("flash_btn"))
        self.flash_btn.setFixedWidth(100)
        self.flash_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #43A047;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        self.flash_btn.clicked.connect(self.start_flash)
        drive_layout.addWidget(self.flash_btn)

        layout.addWidget(self.drive_card)

        # Progress section
        self.progress_section = QWidget()
        progress_layout = QVBoxLayout(self.progress_section)
        progress_layout.setSpacing(10)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 14px;")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 10px;
                background-color: #e0e0e0;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4a90d9;
                border-radius: 10px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_section)
        layout.addStretch()

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("select_image_dialog_title"),
            "",
            t("image_files_filter")
        )
        if file_path:
            self.selected_image = file_path
            filename = os.path.basename(file_path)
            size = format_size(os.path.getsize(file_path))
            self.image_label.setText(f"{filename} ({size})")
            self.image_label.setStyleSheet("color: #333; font-size: 14px;")

    def refresh_drives(self):
        current = self.drive_combo.currentText()
        self.drive_combo.clear()

        drives = list_drives()
        if not drives:
            self.drive_combo.addItem(t("no_drives"))
        else:
            for drive in drives:
                size = format_size(drive["size"]) if drive["size"] > 0 else "unknown"
                text = f"{drive['device']} ({drive['type']}, {size})"
                self.drive_combo.addItem(text, drive["device"])

        # Restore selection if possible
        for i in range(self.drive_combo.count()):
            if self.drive_combo.itemText(i) == current:
                self.drive_combo.setCurrentIndex(i)
                break

    def start_flash(self):
        if not self.selected_image:
            QMessageBox.warning(self, "No Image", "Please select an image file first.")
            return

        drive_device = self.drive_combo.currentData()
        if not drive_device or drive_device == "No drives found":
            QMessageBox.warning(self, "No Drive", "Please select a target drive.")
            return

        # Confirm
        reply = QMessageBox.question(
            self, t("confirm_flash_title"),
            t("confirm_flash_msg", image=os.path.basename(self.selected_image), drive=drive_device),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Disable UI during flash
        self.select_image_btn.setEnabled(False)
        self.drive_combo.setEnabled(False)
        self.flash_btn.setEnabled(False)
        self.status_label.setText(t("flashing_status", pct=0))
        self.progress_bar.setValue(0)

        # Start worker
        self.worker = FlashWorker(self.selected_image, drive_device)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.flash_finished)
        self.worker.start()

    def update_progress(self, pct):
        self.progress_bar.setValue(pct)
        if pct < 100:
            self.status_label.setText(t("flashing_status", pct=pct))

    def change_language(self, index):
        lang = "en" if index == 0 else "fa"
        load_translations(lang)
        
        # Update all UI elements
        self.setWindowTitle(t("app_title"))
        self.title_label.setText(t("app_title"))
        self.subtitle_label.setText(t("subtitle"))
        self.select_image_btn.setText(t("select_image_btn"))
        self.flash_btn.setText(t("flash_btn"))
        
        if not self.selected_image:
            self.image_label.setText(t("no_image"))
        
        # Update status label with translated key
        current_pct = self.progress_bar.value()
        if current_pct < 100:
            self.status_label.setText(t("flashing_status", pct=current_pct))
        else:
            self.status_label.setText(t("flashing_complete"))
        
        # Refresh drives to update "No drives found" text
        self.refresh_drives()
        
        # Update language combo display
        if lang == "en":
            self.lang_combo.setCurrentIndex(0)
        else:
            self.lang_combo.setCurrentIndex(1)
        
        # Set RTL layout for Persian
        if lang == "fa":
            self.setLayoutDirection(Qt.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LeftToRight)
    
    def flash_finished(self, success, message):
        # Re-enable UI
        self.select_image_btn.setEnabled(True)
        self.drive_combo.setEnabled(True)
        self.flash_btn.setEnabled(True)

        if success:
            self.status_label.setText(t("flashing_complete"))
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
            QMessageBox.information(self, t("success_dialog_title"), message)
        else:
            self.status_label.setText(t("error_prefix") + message)
            self.status_label.setStyleSheet("color: #f44336; font-size: 14px; font-weight: bold;")
            QMessageBox.critical(self, t("error_dialog_title"), message)

        self.progress_bar.setValue(0)


def main():
    # Load default translations
    load_translations("en")
    
    if HAS_QT:
        app = QApplication(sys.argv)
        window = EtcherWindow()
        window.show()
        sys.exit(app.exec_())
    else:
        print("PyQt5 not installed. Install with: pip install PyQt5")
        sys.exit(1)


if __name__ == "__main__":
    main()
