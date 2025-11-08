#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""Command-line interface for CredProxy."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import argparse

from credproxy import __version__
from credproxy.logger import LOG


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="credproxy",
        description=(
            "AWS container credential provider - CLI for validation and development"
        ),
    )

    _ = parser.add_argument(
        "--config",
        default="/credproxy/config.yaml",
        help="Path to configuration file (default: /credproxy/config.yaml)",
    )

    _ = parser.add_argument(
        "--validate-only", action="store_true", help="Validate configuration and exit"
    )

    _ = parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    _ = parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO)",
    )

    _ = parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode (sets debug=True and log-level=DEBUG)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point - parse arguments and delegate."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle --dev flag: set debug mode and default log level to DEBUG
    if args.dev:
        args.log_level = args.log_level or "DEBUG"

    # Set up logging level from CLI argument if provided
    if args.log_level:
        from credproxy.runner import setup_cli_logging

        setup_cli_logging(args.log_level)

    try:
        # If validation only, validate and exit
        if args.validate_only:
            from credproxy.runner import validate_config_file

            success = validate_config_file(args.config)
            return 0 if success else 1
    except Exception as error:
        LOG.error("Fatal error during validation: %s", str(error))
        return 1

    # Delegate to server runner for normal operation
    from credproxy.runner import run_server

    return run_server(args)


if __name__ == "__main__":
    import sys

    sys.exit(main())
