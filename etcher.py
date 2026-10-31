#!/usr/bin/env python3
"""
SimpleEtcher - A lightweight disk imaging tool similar to BalenaEtcher.
Flashes OS images (.iso, .img) to SD cards and USB drives.
"""

import sys
import os
import time
import argparse
import platform
from datetime import timedelta

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None


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
                        # Get size
                        free, total, _ = win32api.GetDiskFreeSpaceEx(drive_letter)
                        drives.append({
                            "device": drive_letter,
                            "type": "removable" if drive_type == win32api.DRIVE_REMOVABLE else "fixed",
                            "size": total
                        })
                except Exception:
                    pass
        except ImportError:
            console.print("[yellow]Install pywin32 for Windows drive detection: pip install pywin32[/yellow]")
            return drives

    elif platform_name in ["linux", "macos"]:
        # Use lsblk or fdisk to find removable drives
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
                # Parse diskutil output (simplified)
                lines = result.stdout.split("\n")
                for i, line in enumerate(lines):
                    if "disk" in line and "external" in line:
                        drives.append({
                            "device": f"/dev/{line.split()[0]}",
                            "type": "removable",
                            "size": 0
                        })
        except Exception as e:
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


def flash_image(image_path, drive_path):
    """Flash an image file to a drive."""
    platform_name = get_platform()

    # Validate image file
    if not os.path.exists(image_path):
        console.print(f"[red]Image file not found: {image_path}[/red]")
        return False

    image_size = os.path.getsize(image_path)
    console.print(f"[bold]Image:[/bold] {image_path}")
    console.print(f"[bold]Size:[/bold] {format_size(image_size)}")
    console.print(f"[bold]Target:[/bold] {drive_path}")

    # Confirm
    if HAS_RICH:
        from rich.prompt import Confirm
        if not Confirm.ask("Continue? This will erase the target drive!", default=False):
            return False
    else:
        response = input("Continue? This will erase the target drive! (y/N): ")
        if response.lower() != 'y':
            return False

    console.print("\n[bold]Flashing...[/bold]")

    try:
        if platform_name == "windows":
            flash_windows(image_path, drive_path, image_size)
        elif platform_name in ["linux", "macos"]:
            flash_unix(image_path, drive_path, image_size)
        else:
            console.print(f"[red]Unsupported platform: {platform_name}[/red]")
            return False
    except KeyboardInterrupt:
        console.print("\n[yellow]Flashing cancelled by user.[/yellow]")
        return False
    except Exception as e:
        console.print(f"\n[red]Error flashing image: {e}[/red]")
        return False

    console.print("\n[green][bold]✓ Flashing complete![/bold][/green]")
    if platform_name in ["linux", "macos"]:
        console.print("[yellow]Syncing drive...[/yellow]")
        import subprocess
        subprocess.run(["sync"])
        console.print("[green][bold]✓ Done![/bold][/green]")

    return True


def flash_windows(image_path, drive_path, image_size):
    """Flash image on Windows using pywin32."""
    try:
        import win32file
        import win32con
    except ImportError:
        console.print("[red]pywin32 required on Windows. Install with: pip install pywin32[/red]")
        return

    # Open drive
    drive_handle = win32file.CreateFile(
        f"\\\\.\\{drive_path.replace(':','')}",
        win32con.GENERIC_WRITE,
        0,
        None,
        win32con.OPEN_EXISTING,
        0,
        None
    )

    try:
        with open(image_path, 'rb') as img:
            written = 0
            chunk_size = 4 * 1024 * 1024  # 4MB chunks

            if HAS_RICH:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    "[{task.completed}/{task.total}]",
                    TimeRemainingColumn()
                ) as progress:
                    task = progress.add_task("Flashing...", total=image_size)

                    while True:
                        chunk = img.read(chunk_size)
                        if not chunk:
                            break

                        result = win32file.WriteFile(drive_handle, chunk)
                        written += len(chunk)
                        progress.update(task, completed=written)
            else:
                # Simple progress without rich
                while True:
                    chunk = img.read(chunk_size)
                    if not chunk:
                        break
                    win32file.WriteFile(drive_handle, chunk)
                    written += len(chunk)
                    pct = (written / image_size) * 100
                    print(f"\r{pct:.1f}% complete", end="")
                print()
    finally:
        win32file.CloseHandle(drive_handle)


def flash_unix(image_path, drive_path, image_size):
    """Flash image on Linux/macOS using dd."""
    import subprocess

    # Use dd with bs=4M for speed
    cmd = ["dd", f"if={image_path}", f"of={drive_path}", "bs=4M", "status=progress"]

    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

    proc = subprocess.Popen(cmd)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        raise

    if proc.returncode != 0:
        raise Exception(f"dd failed with exit code {proc.returncode}")


def main():
    parser = argparse.ArgumentParser(
        description="SimpleEtcher - Flash OS images to SD cards and USB drives"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List available drives")

    # Flash command
    flash_parser = subparsers.add_parser("flash", help="Flash an image to a drive")
    flash_parser.add_argument("--image", "-i", required=True, help="Path to image file (.iso, .img)")
    flash_parser.add_argument("--drive", "-d", required=True, help="Target drive (e.g., /dev/sdb or D:)\")

    args = parser.parse_args()

    if not HAS_RICH:
        console.print("[dim]Tip: Install rich for better output: pip install rich[/dim]")

    if args.command == "list":
        drives = list_drives()
        if not drives:
            console.print("No removable drives found.")
            return

        if HAS_RICH:
            table = Table(title="Available Drives")
            table.add_column("Device")
            table.add_column("Type")
            table.add_column("Size")

            for drive in drives:
                table.add_row(
                    drive["device"],
                    drive["type"],
                    format_size(drive["size"]) if drive["size"] > 0 else "unknown"
                )
            console.print(table)
        else:
            print("Available drives:")
            for drive in drives:
                size = format_size(drive["size"]) if drive["size"] > 0 else "unknown"
                print(f"  {drive['device']} ({drive['type']}, {size})")

    elif args.command == "flash":
        success = flash_image(args.image, args.drive)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
