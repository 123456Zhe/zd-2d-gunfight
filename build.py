"""
Unified Nuitka build script for ZD 2D Gunfight.

This helper automatically adjusts compiler flags per operating system,
ensures third-party packages such as pygame and pathfinding are bundled,
and provides a single entry point for producing distributable binaries.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.resolve()
DEFAULT_TARGET = PROJECT_ROOT / "main.py"
THIRD_PARTY_PACKAGES = ("pygame", "pathfinding")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build standalone binaries with Nuitka (auto-configured per OS)."
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="Entry point Python file (default: main.py).",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "windows", "linux", "mac"),
        default="auto",
        help="Force a specific platform profile instead of using the host OS.",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Bundle into a single executable (supported on Windows/macOS/Linux).",
    )
    parser.add_argument(
        "--disable-console",
        action="store_true",
        help="Disable console window on Windows builds.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=max(1, (os.cpu_count() or 2) - 1),
        help="Number of parallel compile jobs to pass to Nuitka.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous Nuitka outputs before building.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the computed Nuitka command without executing it.",
    )
    parser.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help="Additional raw arguments forwarded to Nuitka (can be repeated).",
    )
    return parser.parse_args()


def ensure_nuitka_available() -> None:
    try:
        import nuitka  # type: ignore  # noqa: F401
    except ImportError:
        print("[build] Nuitka is not installed. Installing latest stable release...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "nuitka"])


def resolve_profile(mode: str) -> dict[str, str | Path | list[str]]:
    system = platform.system().lower()
    release = platform.release()

    if mode != "auto":
        mode = mode.lower()
        if mode == "windows":
            system = "windows"
        elif mode == "linux":
            system = "linux"
        elif mode == "mac":
            system = "darwin"
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    profile: dict[str, str | Path | list[str]] = {
        "system": system,
        "release": release,
        "output_dir": PROJECT_ROOT / "dist" / system,
        "binary_name": "ZD-2D-Gunfight",
        "flags": [],
    }

    if system == "windows":
        profile["binary_name"] = "ZD-2D-Gunfight.exe"
    elif system == "darwin":
        profile["binary_name"] = "ZD-2D-Gunfight.app"
        profile["flags"] = ["--macos-create-app-bundle"]

    return profile


def build_command(args: argparse.Namespace, profile: dict[str, str | Path | list[str]]) -> list[str]:
    target = (PROJECT_ROOT / args.target).resolve() if not args.target.is_absolute() else args.target
    if not target.exists():
        raise FileNotFoundError(f"Target file '{target}' does not exist.")

    output_dir = profile["output_dir"]
    binary_name = profile["binary_name"]
    system = profile["system"]
    base_flags = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--follow-imports",
        "--show-progress",
        "--remove-output",
        f"--output-dir={output_dir}",
        f"--output-filename={binary_name}",
        f"--jobs={args.jobs}",
    ]

    for package in THIRD_PARTY_PACKAGES:
        base_flags.append(f"--include-package={package}")

    base_flags.append("--enable-plugin=pygame")

    if args.onefile:
        base_flags.append("--onefile")

    if args.disable_console and system == "windows":
        base_flags.append("--windows-console-mode=disable")

    base_flags.extend(profile["flags"])
    base_flags.extend(args.extra_arg)
    base_flags.append(str(target))
    return [flag for flag in base_flags if flag]  # remove empty strings


def clean_previous_outputs(output_dir: Path) -> None:
    if output_dir.exists():
        print(f"[build] Removing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)


def main() -> None:
    args = parse_args()
    profile = resolve_profile(args.mode)

    ensure_nuitka_available()

    output_dir: Path = profile["output_dir"]
    if args.clean:
        clean_previous_outputs(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"[build] Platform profile: system={profile['system']} "
        f"release={profile['release']} output_dir={output_dir}"
    )

    cmd = build_command(args, profile)
    print("[build] Running Nuitka command:")
    print(" ".join(str(part) for part in cmd))

    if args.dry_run:
        print("[build] Dry run mode enabled. Exiting without executing Nuitka.")
        return

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    final_hint = (
        output_dir / ("ZD-2D-Gunfight.exe" if profile["system"] == "windows" else profile["binary_name"])
    )
    print(f"[build] Build finished. Output located in: {output_dir}")
    print(f"[build] Executable name: {final_hint.name}")


if __name__ == "__main__":
    main()

