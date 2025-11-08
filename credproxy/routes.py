#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from credproxy.logger import LOG
from credproxy.metrics import get_metrics


# Create a Blueprint for API routes
api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET", "HEAD"])
def health_check():
    """Health check endpoint."""
    from flask import current_app

    config = current_app.config.get("credproxy_config")

    # Only log health checks if enabled in config or if there's an error
    if config.server.log_health_checks:
        LOG.info(
            "Health check accessed", extra={"services_count": len(config.services)}
        )

    return jsonify({"status": "healthy", "services": len(config.services)})


@api_bp.route("/v1/credentials", methods=["GET"])
def get_credentials():
    """Get AWS credentials for a service."""
    from flask import current_app

    config = current_app.config.get("credproxy_config")
    credentials_handler = current_app.config.get("credentials_handler")

    provided_token = request.headers.get("Authorization")

    # Use simplified logger for structured logging

    if not provided_token:
        LOG.warning("Request missing Authorization header")
        return jsonify({"error": "Authorization header required"}), 401

    try:
        LOG.debug(
            "Attempting token validation",
            extra={
                "token_prefix": provided_token[:8] + "...",
                "total_services": len(config.services),
                "available_services": list(config.services.keys()),
            },
        )

        service_name = config.get_service_name_by_token(provided_token)
        if not service_name:
            LOG.warning(
                "Invalid authorization token",
                extra={
                    "token_prefix": provided_token[:8] + "...",
                    "total_services": len(config.services),
                    "available_services": list(config.services.keys()),
                },
            )
            return jsonify({"error": "Invalid authorization token"}), 401

        # Set service context in Flask g for logging
        service = config.services[service_name]
        g.service_name = service_name
        g.service_source_file = service.source_file

        LOG.info("Providing credentials for service")

        credentials = credentials_handler.get_credentials(service_name)
        return jsonify(credentials)

    except Exception as error:
        LOG.error("Error getting credentials")
        LOG.exception(error)
        return jsonify({"error": "Internal server error"}), 500


def register_metrics_route(app, config):
    """Register metrics endpoint if enabled in configuration."""
    # Register Flask route when metrics are enabled
    # The separate Prometheus server functionality can be added later
    if config.metrics.prometheus.enabled:

        def metrics():
            """Prometheus metrics endpoint."""
            try:
                metrics_data = get_metrics()
                return metrics_data, 200, {"Content-Type": "text/plain; version=0.0.4"}
            except Exception as error:
                LOG.error("Failed to generate metrics: %s", error)
                return jsonify({"error": "Failed to generate metrics"}), 500

        # Register the route directly on the app with static /metrics path
        app.add_url_rule(
            "/metrics", endpoint="metrics", view_func=metrics, methods=["GET"]
        )
