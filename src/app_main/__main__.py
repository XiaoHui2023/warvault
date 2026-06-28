from __future__ import annotations

import argparse

from app_main.runtime import run_server


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warvault",
        description="warvault local asset library service.",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=None,
        help="Listening port. Uses config.yaml when omitted; 0 selects a free port.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="YAML config file path.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="warvault 0.0.0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _make_parser().parse_args(argv)
    run_server(args.port, config_path=args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
