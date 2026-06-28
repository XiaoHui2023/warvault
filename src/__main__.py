from __future__ import annotations

import argparse
import sys


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warvault",
        description="Warvault 命令行工具。",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="warvault 0.0.0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _make_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
