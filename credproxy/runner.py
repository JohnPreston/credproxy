#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""Application runtime logic for CredProxy."""

from __future__ import annotations

import sys
import signal
import logging as logthings
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import argparse

    from flask import Flask


from credproxy.app import init_app
from credproxy.config import Config
from credproxy.logger import LOG


# Global flag for graceful shutdown
shutdown_requested = False


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        global shutdown_requested
        if not shutdown_requested:
            shutdown_requested = True
            LOG.info("Received signal %d, initiating graceful shutdown...", signum)

            # Get access to the Flask app for cleanup
            try:
                from flask import current_app

                if current_app and hasattr(current_app, "config"):
                    credentials_handler = current_app.config.get("credentials_handler")
                    if credentials_handler and hasattr(credentials_handler, "cleanup"):
                        credentials_handler.cleanup()

                    file_watcher = current_app.config.get("file_watcher")
                    if file_watcher and hasattr(file_watcher, "stop"):
                        file_watcher.stop()
            except Exception:
                # Ignore cleanup errors during shutdown
                pass

            LOG.info("Graceful shutdown completed")
            sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def validate_config_file(config_path: str) -> bool:
    """Validate configuration file."""
    try:
        _ = Config.from_file(config_path)
        LOG.info("Configuration is valid")
        return True
    except Exception as error:
        LOG.error("Configuration validation failed: %s", str(error))
        return False


def setup_cli_logging(log_level: str) -> None:
    """Setup logging level from CLI arguments."""
    level = getattr(logthings, log_level.upper())
    # Update the global logger level
    LOG.setLevel(level)
    # Also update all handlers
    for handler in LOG.handlers:
        handler.setLevel(level)


def run_server(args: argparse.Namespace) -> int:
    """Run the CredProxy server with the given arguments."""
    try:
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers()

        # Run the main application
        LOG.info("CredProxy CLI")
        LOG.info("Configuration file: %s", args.config)

        LOG.info("Running CredProxy with Flask server")

        # Load config and create Flask app
        config = Config.from_file(args.config)
        app: Flask = init_app(config)

        # Override debug mode if --dev flag is set
        debug_mode = config.server.debug or args.dev

        # Start metrics server on separate port if enabled
        if config.metrics.prometheus.enabled:
            from prometheus_client import start_http_server

            from credproxy.metrics import REGISTRY as CREDPROXY_REGISTRY

            try:
                start_http_server(
                    port=config.metrics.prometheus.port,
                    addr=config.metrics.prometheus.host,
                    registry=CREDPROXY_REGISTRY,
                )
                LOG.info(
                    "Prometheus metrics server started on %s:%d using CredProxy "
                    "registry",
                    config.metrics.prometheus.host,
                    config.metrics.prometheus.port,
                )
            except Exception as error:
                LOG.error("Failed to start metrics server: %s", error)

        app.run(host=config.server.host, port=config.server.port, debug=debug_mode)

    except KeyboardInterrupt:
        LOG.info("Shutting down gracefully...")
        return 0
    except Exception as error:
        LOG.error("Fatal error: %s", str(error))
        return 1

    return 0
