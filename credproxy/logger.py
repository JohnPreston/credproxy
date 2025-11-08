#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

from __future__ import annotations

import json
import logging as logthings

from flask import g, request

from . import __version__, __git_commit__
from .settings import LOG_LEVEL


class SimpleJsonFormatter(logthings.Formatter):
    """Simple JSON formatter that always includes essential fields."""

    def format(self, record: logthings.LogRecord) -> str:
        # Sanitize the message before processing
        from credproxy.sanitizer import sanitize_string

        sanitized_message = sanitize_string(record.getMessage())

        data = {
            "timestamp": record.created,  # Always include
            "levelname": record.levelname,  # Always include
            "message": sanitized_message,  # Always include (sanitized)
            "name": record.name.split(".")[0],  # Always include
        }

        # Add version info only for INFO level logs (exclude unknown/development values)
        if record.levelname == "INFO":
            if __version__ and __version__ not in ("unknown", "development", "none"):
                data["credproxy.version"] = __version__
            if __git_commit__ and __git_commit__ not in (
                "unknown",
                "development",
                "none",
            ):
                data["credproxy.git_commit"] = __git_commit__

        # Add request context if present
        if hasattr(record, "request") and record.request:
            data["request"] = record.request

        # Add service context if present
        if hasattr(record, "service") and record.service:
            data["service"] = record.service

        # Always include exception information if present (sanitized)
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
            data["exception"] = sanitize_string(exception_text)
        elif record.exc_text:
            data["exception"] = sanitize_string(record.exc_text)

        return json.dumps(data, separators=(",", ":"), default=str)


class RequestContextFilter(logthings.Filter):
    """Adds request and service context to each LogRecord."""

    def filter(self, record: logthings.LogRecord) -> bool:
        # Add request context
        try:
            record.request = {
                "method": request.method,
                "path": request.path,
                "remote": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", ""),
                "request_id": getattr(g, "request_id", None),
            }
        except RuntimeError:
            # Not in a request context
            record.request = {}

        # Add service context if available
        try:
            if hasattr(g, "service_name") and g.service_name:
                service_data = {"name": g.service_name}
                if hasattr(g, "service_source_file") and g.service_source_file:
                    service_data["source_file"] = g.service_source_file
                record.service = service_data
        except (RuntimeError, AttributeError):
            record.service = {}

        # If flat source_file exists as record attribute, create service structure
        if hasattr(record, "source_file"):
            source_file = getattr(record, "source_file")
            if not hasattr(record, "service") or not record.service:
                record.service = {"source_file": source_file}
            else:
                # Preserve existing service data (like name) when adding source_file
                if isinstance(record.service, dict):
                    record.service["source_file"] = source_file
                else:
                    record.service = {"source_file": source_file}
            # Remove flat source_file to prevent duplicate output
            delattr(record, "source_file")

        return True


class WerkzeugAccessLogFilter(logthings.Filter):
    """Filter to exclude all Werkzeug access logs to prevent duplicate logging."""

    def filter(self, record: logthings.LogRecord) -> bool:
        """Filter out all Werkzeug access logs."""
        if record.name != "werkzeug":
            return True

        message = record.getMessage()
        # Filter out all HTTP access logs (patterns like "GET /path HTTP/1.1" 200 -)
        # This matches the standard Werkzeug access log format
        if any(
            method in message
            for method in [
                "GET /",
                "POST /",
                "PUT /",
                "DELETE /",
                "PATCH /",
                "HEAD /",
                "OPTIONS /",
            ]
        ):
            return False

        # Allow all other Werkzeug messages (warnings, errors, etc.)
        return True


class HealthCheckFilter(logthings.Filter):
    """Filter to exclude health check logs from access logs unless there's an error."""

    def filter(self, record: logthings.LogRecord) -> bool:
        """Filter out health check requests unless they result in errors."""
        if record.name != "werkzeug":
            return True

        message = record.getMessage()
        # Check if this is a health check request
        if "GET /health " in message or "HEAD /health " in message:
            # Only allow health check logs if they contain error status codes
            # HTTP status codes 4xx and 5xx indicate errors
            return any(
                f" {status_code} " in message
                for status_code in [str(code) for code in range(400, 600)]
            )

        # Allow all non-health check requests
        return True


class FlaskDevelopmentWarningFilter(logthings.Filter):
    """Filter to exclude Flask development server warnings."""

    def filter(self, record: logthings.LogRecord) -> bool:
        """Filter out Flask development server warnings."""
        if record.name != "werkzeug":
            return True

        message = record.getMessage()
        # Filter out the development server warning
        if "WARNING: This is a development server" in message:
            return False

        # Filter out the "Press CTRL+C to quit" message
        if "Press CTRL+C to quit" in message:
            return False

        return True


def setup_logging():
    """Setup simple JSON logging."""
    formatter = SimpleJsonFormatter()

    handler = logthings.StreamHandler()
    handler.setFormatter(formatter)

    logger = logthings.getLogger("credproxy")
    logger.addHandler(handler)
    logger.setLevel(getattr(logthings, LOG_LEVEL.upper(), logthings.INFO))
    logger.propagate = False

    logger.addFilter(RequestContextFilter())

    # Configure werkzeug logger with filters
    werkzeug_logger = logthings.getLogger("werkzeug")
    werkzeug_logger.addFilter(FlaskDevelopmentWarningFilter())
    werkzeug_logger.addFilter(WerkzeugAccessLogFilter())

    return logger


def setup_json_logging(app, *, level: int = logthings.INFO) -> None:
    """Setup JSON logging for Flask app."""
    # Flush any automatically added handlers
    app.logger.handlers = []

    # Use provided level or get from environment
    if level is None:
        log_level_name = LOG_LEVEL.upper()
        level = getattr(logthings, log_level_name, logthings.INFO)

    formatter = SimpleJsonFormatter()

    handler = logthings.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)

    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    app.logger.propagate = False  # Prevent propagation to root logger

    # Add the request-context filter
    app.logger.addFilter(RequestContextFilter())

    # Configure werkzeug logger with filters to prevent access logs
    werkzeug_logger = logthings.getLogger("werkzeug")
    werkzeug_logger.addFilter(FlaskDevelopmentWarningFilter())
    werkzeug_logger.addFilter(WerkzeugAccessLogFilter())


# Create logger instance
LOG = setup_logging()
