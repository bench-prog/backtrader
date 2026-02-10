#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Backtrader dependency installer for beginners
#
# Usage:
#   python tools/install_deps.py              # Interactive mode
#   python tools/install_deps.py --all        # Install everything
#   python tools/install_deps.py --core       # Core libs only
#   python tools/install_deps.py --china      # Core + China market data
#   python tools/install_deps.py --crypto     # Core + Crypto exchange data
#   python tools/install_deps.py --list       # List all dependencies
#
###############################################################################
from __future__ import absolute_import, division, print_function, unicode_literals

import platform
import subprocess
import sys

# ---------------------------------------------------------------------------
# Dependency definitions
# ---------------------------------------------------------------------------
GROUPS = {
    "core": {
        "desc": "Core libraries (plotting, numerical, data processing)",
        "packages": [
            ("numpy", "numpy", "Numerical computation"),
            ("pandas", "pandas", "Data analysis & DataFrames"),
            ("matplotlib", "matplotlib", "Charting & visualization"),
        ],
    },
    "china": {
        "desc": "China market data (A-shares, index, fund, futures via AkShare)",
        "packages": [
            ("akshare", "akshare", "AkShare - Chinese market data"),
        ],
    },
    "yahoo": {
        "desc": "Yahoo Finance data (US & global equities)",
        "packages": [
            ("yfinance", "yfinance", "Yahoo Finance downloader"),
        ],
    },
    "crypto": {
        "desc": "Cryptocurrency exchange integration",
        "packages": [
            ("ccxt", "ccxt", "Unified crypto exchange API"),
        ],
    },
    "talib": {
        "desc": "Technical analysis indicators (requires TA-Lib C library)",
        "packages": [
            ("talib", "TA-Lib", "Technical Analysis Library"),
        ],
    },
    "trading": {
        "desc": "Live trading & broker connectors",
        "packages": [
            ("oandapy", "oandapy", "OANDA forex broker API"),
            ("requests", "requests", "HTTP client (used by oandapy)"),
        ],
    },
    "extras": {
        "desc": "Extra utilities",
        "packages": [
            (
                "pandas_market_calendars",
                "pandas_market_calendars",
                "Exchange trading calendars",
            ),
            ("influxdb", "influxdb", "InfluxDB time-series database client"),
        ],
    },
}

# Preset combinations
PRESETS = {
    "core": ["core"],
    "china": ["core", "china"],
    "yahoo": ["core", "yahoo"],
    "crypto": ["core", "crypto"],
    "all": list(GROUPS.keys()),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def check_installed(import_name):
    """Return True if a package is importable."""
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def pip_install(pip_name):
    """Install a package via pip. Returns True on success."""
    cmd = [sys.executable, "-m", "pip", "install", pip_name]
    print(f"  -> pip install {pip_name} ...", end=" ", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("OK")
        return True
    else:
        print("FAILED")
        print(
            f"     {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'unknown error'}"
        )
        return False


def show_status():
    """Print the install status of every known dependency."""
    print("\n=== Backtrader dependency status ===\n")
    for group_name, group in GROUPS.items():
        print(f"[{group_name}] {group['desc']}")
        for import_name, pip_name, desc in group["packages"]:
            status = "installed" if check_installed(import_name) else "NOT installed"
            print(f"  {pip_name:<28s} {status:<16s} - {desc}")
        print()


def install_groups(group_names):
    """Install all packages in the given groups."""
    success, failed = [], []
    for gname in group_names:
        group = GROUPS[gname]
        print(f"\n--- [{gname}] {group['desc']} ---")
        for import_name, pip_name, desc in group["packages"]:
            if check_installed(import_name):
                print(f"  {pip_name} already installed, skipping.")
                success.append(pip_name)
            else:
                if pip_name == "TA-Lib":
                    print(
                        f"  {pip_name} requires the TA-Lib C library to be installed first."
                    )
                    _print_talib_hint()
                    # Still try pip install; it will fail gracefully if C lib missing
                ok = pip_install(pip_name)
                (success if ok else failed).append(pip_name)

    print("\n=== Summary ===")
    print(f"  Succeeded: {len(success)}  ({', '.join(success) if success else '-'})")
    if failed:
        print(f"  Failed:    {len(failed)}  ({', '.join(failed)})")
    return len(failed) == 0


def _print_talib_hint():
    """Print platform-specific TA-Lib C library installation hints."""
    os_name = platform.system()
    if os_name == "Darwin":
        print("  Hint (macOS): brew install ta-lib")
    elif os_name == "Linux":
        print("  Hint (Linux): sudo apt-get install -y libta-lib0-dev  (Debian/Ubuntu)")
        print("                or build from source: https://ta-lib.org")
    elif os_name == "Windows":
        print("  Hint (Windows): download the .whl from")
        print("    https://github.com/cgohlke/talib-build/releases")
    print()


def interactive_menu():
    """Interactive selection UI."""
    print("=" * 60)
    print("  Backtrader Dependency Installer")
    print("=" * 60)
    print()
    print("Available dependency groups:")
    print()
    for i, (gname, group) in enumerate(GROUPS.items(), 1):
        pkgs = ", ".join(p[1] for p in group["packages"])
        print(f"  {i}. [{gname}] {group['desc']}")
        print(f"     Packages: {pkgs}")
    print()
    print("Presets:")
    print("  a  -> Install ALL groups")
    print("  c  -> Core only  (numpy, pandas, matplotlib)")
    print("  cn -> Core + China market data  (+ akshare)")
    print("  y  -> Core + Yahoo Finance      (+ yfinance)")
    print("  cr -> Core + Crypto             (+ ccxt)")
    print("  q  -> Quit")
    print()
    choice = (
        input("Enter preset letter, or group numbers separated by comma (e.g. 1,2,4): ")
        .strip()
        .lower()
    )

    if choice == "q":
        print("Bye.")
        sys.exit(0)

    preset_map = {
        "a": "all",
        "c": "core",
        "cn": "china",
        "y": "yahoo",
        "cr": "crypto",
    }

    if choice in preset_map:
        return PRESETS[preset_map[choice]]

    # Parse numeric selection
    group_keys = list(GROUPS.keys())
    selected = []
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(group_keys):
                selected.append(group_keys[idx])
            else:
                print(f"Invalid number: {part}")
        elif part in GROUPS:
            selected.append(part)
        else:
            print(f"Unknown selection: {part}")

    if not selected:
        print("No valid selection. Exiting.")
        sys.exit(1)

    return selected


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Install backtrader external dependencies"
    )
    parser.add_argument(
        "--all", action="store_true", help="Install all dependency groups"
    )
    parser.add_argument(
        "--core",
        action="store_true",
        help="Install core libs (numpy, pandas, matplotlib)",
    )
    parser.add_argument(
        "--china",
        action="store_true",
        help="Install core + AkShare (China market data)",
    )
    parser.add_argument(
        "--yahoo", action="store_true", help="Install core + yfinance (Yahoo Finance)"
    )
    parser.add_argument(
        "--crypto", action="store_true", help="Install core + ccxt (crypto exchanges)"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all dependencies and their status"
    )
    args = parser.parse_args()

    if args.list:
        show_status()
        sys.exit(0)

    # Determine which groups to install
    groups_to_install = None
    for preset_name in ("all", "core", "china", "yahoo", "crypto"):
        if getattr(args, preset_name, False):
            groups_to_install = PRESETS[preset_name]
            break

    if groups_to_install is None:
        # No flag given -> interactive mode
        groups_to_install = interactive_menu()

    ok = install_groups(groups_to_install)
    print()
    show_status()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
