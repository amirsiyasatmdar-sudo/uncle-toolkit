"""Command-line entry point."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from core import __version__
from core.plugin_loader import PluginLoader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uncle-toolkit",
        description="Local-first modular toolkit for Linux and Termux.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subs = parser.add_subparsers(dest="command")
    subs.add_parser("check", help="Check the basic runtime environment")
    plugins = subs.add_parser("plugins", help="List trusted local plugins")
    plugins.add_argument("--directory", default="plugins")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        print(f"Python: {sys.version.split()[0]}")
        print(f"Platform: {sys.platform}")
        print("Core: OK")
        return 0
    if args.command == "plugins":
        print(
            "WARNING: loading plugins executes their Python code; load trusted plugins only."
        )
        try:
            loader = PluginLoader(Path(args.directory))
            found = loader.load_all()
        except (OSError, ValueError, ImportError, TypeError) as exc:
            print(f"Plugin loading failed: {exc}")
            return 1
        if not found:
            print("No plugins found.")
        for name in sorted(found):
            version = loader.metadata.get(name, {}).get("version", "unknown")
            print(f"{name} {version}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
