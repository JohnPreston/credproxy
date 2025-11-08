#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""Prometheus metrics for CredProxy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import prometheus_client
from prometheus_client import (
    Info,
    Gauge,
    Counter,
    Histogram,
    CollectorRegistry,
    generate_latest,
    disable_created_metrics,
)

from credproxy.logger import LOG


if TYPE_CHECKING:
    pass


# Disable default Prometheus collectors to ensure only CredProxy metrics are exposed
# This prevents Python runtime metrics from polluting our output
prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)

# Disable _created metrics to reduce cardinality
disable_created_metrics()

# Custom registry for CredProxy metrics - completely isolated from default registry
REGISTRY = CollectorRegistry()

# Request metrics - keep only what's needed
REQUESTS_TOTAL = Counter(
    "credproxy_requests_total",
    "Total number of credential requests",
    ["result", "service_name"],
    registry=REGISTRY,
)

# Request duration histogram - for tracking latency
REQUEST_DURATION = Histogram(
    "credproxy_request_duration_seconds",
    "Request duration in seconds",
    ["result", "service_name"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

# Service discovery metrics - for tracking managed services over time
ACTIVE_SERVICES = Gauge(
    "credproxy_active_services_total",
    "Number of currently active services",
    registry=REGISTRY,
)

# Application info - minimal version tracking
APP_INFO = Info(
    "credproxy_app_info",
    "CredProxy application information",
    registry=REGISTRY,
)


def init_metrics() -> None:
    """Initialize metrics with default values."""
    LOG.info("Initializing Prometheus metrics with isolated registry")

    # Set application info
    try:
        from credproxy import __version__

        APP_INFO.info(
            {
                "version": __version__,
                "name": "credproxy",
            }
        )
    except ImportError:
        APP_INFO.info(
            {
                "version": "unknown",
                "name": "credproxy",
            }
        )

    LOG.info("Prometheus metrics initialized successfully with isolated registry")


def get_metrics() -> str:
    """Get metrics in Prometheus format."""
    try:
        return generate_latest(REGISTRY).decode("utf-8")
    except Exception as error:
        LOG.error("Failed to generate metrics: %s", error)
        return ""


def record_request(
    result: str,
    service_name: str = "unknown",
    duration: float | None = None,
) -> None:
    """Record a credential request with optional duration."""
    REQUESTS_TOTAL.labels(result=result, service_name=service_name).inc()

    # Record duration if provided
    if duration is not None:
        REQUEST_DURATION.labels(result=result, service_name=service_name).observe(
            duration
        )


def update_active_services(count: int) -> None:
    """Update the active services count."""
    ACTIVE_SERVICES.set(count)
