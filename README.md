# SimpleEtcher

A lightweight cross-platform disk imaging tool similar to BalenaEtcher.

## Features
- Flash OS images (.iso, .img) to SD cards and USB drives
- Cross-platform (Windows, Linux, macOS)
- Progress bar with ETA
- Drive detection and validation
- Simple CLI interface

## Installation

```bash
pip install pywin32  # Windows only
```

## Usage

```bash
# List available drives
python etcher.py list

# Flash an image to a drive
python etcher.py flash --image path/to/image.iso --drive /dev/sdb

# On Windows, use the drive letter
python etcher.py flash --image path/to/image.iso --drive D:
```

## How it works

1. Detects available block devices/drives
2. Validates image file and target drive
3. Writes image to drive using platform-specific methods
4. Shows progress with ETA
5. Syncs/flushes writes to ensure data is written
