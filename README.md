# EMSYS Flasher

A lightweight cross-platform disk imaging tool for flashing OS images to SD cards and USB drives. Built by [EMSYS](https://emsys.ir).

🌍 **Available in:** [English](README.md) | [فارسی](README_fa.md)

![SimpleEtcher - Flashing Complete](screenshot_flashing_v2.png)

## Features
- 🖥️ Modern PyQt5 GUI interface with EMSYS branding
- 🌍 Multi-language support (English & Persian)
- 🔍 Automatic drive detection
- 📊 Real-time progress bar
- 🔄 Background flashing (doesn't block UI)
- 💾 Flash OS images (.iso, .img) to SD cards and USB drives
- 🌐 Cross-platform (Windows, Linux, macOS)

## Installation

```bash
pip install PyQt5 pywin32  # Windows: pip install PyQt5 pywin32
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Launch the GUI:
```bash
python etcher.py
```

### Steps:
1. Click **Select Image** and choose your .iso or .img file
2. Select the target drive from the dropdown
3. Click **Flash** to begin
4. Wait for the progress bar to complete

## Screenshots

### Initial State
![Initial State](screenshot_initial_v2.png)

### Image Selected, Ready to Flash
![Image Selected](screenshot_image_selected_v2.png)

### During Flashing
![Flashing Progress](screenshot_flashing_v2.png)

### Persian Language Support
![Persian Interface](screenshot_persian_v2.png)

## Platform Support
- **Windows**: Uses pywin32 for direct drive access
- **Linux**: Uses `dd` command with progress reporting
- **macOS**: Uses `dd` command with progress reporting

## How it works

1. Detects available block devices/drives on your system
2. Validates image file and target drive selection
3. Writes image to drive using platform-specific methods in a background thread
4. Shows real-time progress with percentage
5. Reports success or errors via dialog boxes

---

© EMSYS - Data Recovery & Digital Forensics Center | [emsys.ir](https://emsys.ir)
