import os
import time
import shutil
import subprocess
import sys
import argparse


class TextColors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"


def print_color(text: str, color: str = TextColors.BLUE, end: bool = True):
    """Helper function to print colored text, optionally without newlines."""
    _text = f"{color}{text}{TextColors.RESET}"
    if end:
        print(_text)
    else:
        print(_text, end="", flush=True)


def breadcrumb(n: int = 5, color: str = TextColors.BLUE) -> None:
    """Helper function to visually wait for an event."""
    for _ in range(n):
        time.sleep(1)
        print_color(".", color=color, end=False)
    print("")


applescript_code = """tell application "System Events"
    try
        set _groups to groups of UI element 1 of scroll area 1 of group 1 of window "Notification Center" of application process "NotificationCenter"
        repeat with _group in _groups
            set temp to value of static text 1 of _group
            if temp contains "Disk Not Ejected Properly" then
                perform (first action of _group where description is "Close")
            end if
        end repeat
    end try
end tell"""


def execute_applescript(code: str):
    devnull = subprocess.DEVNULL
    subprocess.run(["osascript", "-e", code], stdout=devnull, stderr=devnull)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pico Firmware Flasher")
    parser.add_argument(
        "uf2_file_path",
        metavar="PATH",
        type=str,
        help="PATH: location of a uf2 formatted flash file",
    )
    parser.add_argument(
        "-v",
        "--volume_path",
        type=str,
        default="/Volumes/RPI-RP2",
        help="Path to the volume (optional)",
    )
    parser.add_argument(
        "-a",
        "--applescript",
        type=bool,
        default=True,
        help="Whether to auto-dismiss 'Disk Not Ejected Properly' warnings",
    )
    # Parse the command-line arguments
    args = parser.parse_args()

    # Check if the uf2_file_path argument is provided
    if not args.uf2_file_path:
        parser.error("uf2 file location is missing.")

    return args


def update_firmware(args: argparse.Namespace) -> bool:
    """Update a pico's firmware."""
    print_color("Pico detected, attempting to write firmware")
    print_color("DO NOT CTRL+C!", color=TextColors.RED)
    try:
        # Copy the UF2 file to the RP2 drive
        shutil.copy2(args.uf2_file_path, args.volume_path)
        # Wait for the completed copy operation before printing the message
        file_name: str = os.path.basename(args.uf2_file_path)
        copied_path = os.path.join(args.volume_path, file_name)
        with open(copied_path, "rb") as f:
            os.fsync(f.fileno())
        return True
    except PermissionError:
        print_color(
            "Permission Error: Unable to copy firmware to the Pico."
            + " Please reconnect the Pico and try again.",
            color=TextColors.RED,
        )
        return False
    except FileNotFoundError:
        print_color(
            "Error: UF2 file not found. Please check the file location.",
            color=TextColors.RED,
        )
        return False
    except Exception as e:
        expected_file_error = (
            f"[Errno 2] No such file or directory: '{args.volume_path}'"
        )
        if str(e) == expected_file_error:
            print_color(
                "Error: Volume path '{}' not found.".format(args.volume_path)
                + " Please check the volume path.",
                TextColors.RED,
            )
        else:
            print_color(f"Unknown Error: {e}", color=TextColors.RED)
        return False


def copy_build_files() -> None:
    """Copy a build directory."""
    _color = TextColors.CYAN
    _cmd = ["ls", "/dev/tty.usbmodem*"]
    print_color(f"Watching for serial: {_cmd[-1]}", color=_color)
    while True:
        search = subprocess.run(_cmd, capture_output=True)
        file_results = search.stdout.decode().strip().split("\n")
        if search.returncode == 0:
            if len(file_results) == 1:
                print_color(
                    "Serial connection detected, copying files", color=_color
                )
                print_color("DO NOT CTRL+C!", color=TextColors.RED)
                subprocess.run(["sh", "copy.sh"])
            else:
                print_color(
                    "Serial connection was not unique, could not copy files.",
                    color=TextColors.RED,
                )
            return
        else:
            print_color(search.stderr.decode().strip(), color=TextColors.RED)
        breadcrumb(color=_color)


def run(args: argparse.Namespace) -> None:
    """Main event loop listening for mounted drives and serial connections."""
    print_color(f"Watching for volume: {args.volume_path}")
    try:
        while True:
            # Check if the RP2 drive is available
            if os.path.exists(args.volume_path):
                if update_firmware(args=args):
                    if args.applescript:
                        execute_applescript(applescript_code)
                    copy_build_files()
                print_color("SAFE TO CTRL+C!", color=TextColors.GREEN)
            breadcrumb()
    except KeyboardInterrupt:
        print("")
        sys.exit(0)


def print_welcome_message() -> None:
    print("----------------------------------")
    print_color("Press CTRL+C to exit")
    print_color(
        "WARNING: Exiting while updating firmware could damage the Pico!",
        color=TextColors.RED,
    )
    print("----------------------------------")


if __name__ == "__main__":
    print_welcome_message()
    run(args=parse_args())
