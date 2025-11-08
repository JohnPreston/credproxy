#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from flask import Flask, g, request

from credproxy.config import Config as AppConfig
from credproxy.logger import LOG, setup_json_logging
from credproxy.routes import api_bp, register_metrics_route
from credproxy.metrics import init_metrics, record_request
from credproxy.file_watcher import FileWatcherService
from credproxy.credentials_handler import CredentialsHandler


if TYPE_CHECKING:
    from flask import Flask


def set_service_context():
    """Set service name in Flask's g context for access logging."""
    # Only set service context for credential requests
    if request.endpoint == "api.get_credentials":
        # Get the authorization token from request header
        provided_token = request.headers.get("Authorization")
        if provided_token:
            # Get config from Flask current app
            from flask import current_app

            config = current_app.config.get("credproxy_config")
            if config:
                # Find the service name for this token using instant lookup
                service_name = config.get_service_name_by_token(provided_token)
                if service_name:
                    g.service_name = service_name
                    # Debug logging
                    LOG.debug("Set service context: service_name=%s", service_name)
                    # Also store source_file for logging
                    service = config.services.get(service_name)
                    if service and service.source_file:
                        g.service_source_file = service.source_file
                else:
                    LOG.debug(
                        "No service found for token: %s", provided_token[:10] + "..."
                    )
        else:
            LOG.debug("No authorization token found in request")
    else:
        LOG.debug("Skipping service context: endpoint=%s", request.endpoint)


def init_app(config: AppConfig) -> Flask:
    """Create and configure Flask app."""
    app = Flask(__name__)

    # Disable Flask's default logging handler to prevent duplicate logs
    app.config["LOGGER_HANDLER_POLICY"] = "never"

    # No need to configure LOG_KEYS - SimpleJsonFormatter includes all essential fields

    # Suppress Flask development server warning
    app.config["ENV"] = "production"

    # Store config in app context
    app.config["credproxy_config"] = config

    # Create credentials handler
    credentials_handler = CredentialsHandler(config)
    app.config["credentials_handler"] = credentials_handler

    # Create and start file watcher service
    file_watcher = FileWatcherService(config)
    app.config["file_watcher"] = file_watcher

    # Setup dynamic JSON logging
    setup_json_logging(app)

    # Initialize Prometheus metrics
    init_metrics()

    # Add request ID generation and metrics timing
    @app.before_request
    def make_request_id() -> None:
        # Use timestamp-based ID (microseconds for uniqueness)
        g.request_id = f"{request.remote_addr}-{int(time.time() * 1000000)}"
        # Record request start time for metrics
        g.start_time = time.time()

    # Register before_request handler for service context
    app.before_request(set_service_context)

    # Add shutdown check middleware
    @app.before_request
    def check_shutdown_flag():
        if app.config.get("_shutdown_requested", False):
            LOG.info("=== SHUTDOWN IN PROGRESS - Rejecting new requests ===")
            return "Service shutting down", 503

    # Add metrics recording after each request
    @app.after_request
    def record_metrics(response):
        # Only record metrics for credential requests
        if request.endpoint == "api.get_credentials":
            try:
                # Calculate request duration
                duration = time.time() - g.get("start_time", time.time())
                service_name = g.get("service_name", "unknown")

                # Determine result based on status code
                if response.status_code == 200:
                    result = "success"
                elif response.status_code == 401:
                    result = "denied_missing_token"
                elif response.status_code == 403:
                    result = "denied_invalid_token"
                else:
                    result = "error"

                # Debug logging
                LOG.debug(
                    "Recording metrics: endpoint=%s, service_name=%s, result=%s, "
                    "status_code=%s",
                    request.endpoint,
                    service_name,
                    result,
                    response.status_code,
                )

                # Record the request
                record_request(
                    result=result, service_name=service_name, duration=duration
                )

            except Exception as error:
                LOG.error("Failed to record request metrics: %s", error)
        else:
            # Debug logging for non-credential endpoints
            LOG.debug("Skipping metrics recording: endpoint=%s", request.endpoint)

        return response

    # Register metrics route if enabled
    register_metrics_route(app, config)

    # Register blueprint
    app.register_blueprint(api_bp)

    # Start file watcher service
    try:
        file_watcher.start()
    except Exception as error:
        LOG.error("Failed to start file watcher service: %s", error)
        # Continue without file watcher - not critical for basic operation

    return app
