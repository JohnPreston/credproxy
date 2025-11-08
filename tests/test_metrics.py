#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""Tests for Prometheus metrics functionality."""

from __future__ import annotations

from unittest.mock import patch

import prometheus_client

from credproxy.metrics import (
    REGISTRY,
    get_metrics,
    init_metrics,
    record_request,
    update_active_services,
)


class TestMetricsInitialization:
    """Test metrics initialization."""

    def test_init_metrics_runs_without_error(self):
        """Test that init_metrics runs without error."""
        # Should not raise any exceptions
        init_metrics()


class TestRequestMetrics:
    """Test request-related metrics."""

    def test_record_request_success(self):
        """Test recording a successful request."""
        # Should not raise any exceptions
        record_request(result="success", service_name="test-service", duration=0.5)

    def test_record_request_denied(self):
        """Test recording a denied request."""
        # Should not raise any exceptions
        record_request(result="denied_missing_token", service_name="unknown")

    def test_record_request_without_duration(self):
        """Test recording a request without duration."""
        # Should not raise any exceptions
        record_request(result="success", service_name="test-service")


class TestServiceDiscoveryMetrics:
    """Test service discovery metrics."""

    def test_update_active_services(self):
        """Test updating active services count."""
        update_active_services(5)


class TestMetricsEndpoint:
    """Test metrics endpoint functionality."""

    def test_get_metrics_returns_content(self):
        """Test that get_metrics returns content."""
        # Record some metrics first
        record_request(result="success", service_name="test")

        metrics_content = get_metrics()

        assert isinstance(metrics_content, str)

    @patch("credproxy.metrics.generate_latest")
    def test_get_metrics_handles_exception(self, mock_generate):
        """Test that get_metrics handles exceptions gracefully."""
        mock_generate.side_effect = Exception("Test error")

        metrics_content = get_metrics()

        assert metrics_content == ""

    def test_get_metrics_format(self):
        """Test that metrics are in correct Prometheus format."""
        # Record some metrics
        record_request(result="success", service_name="test-service", duration=0.5)
        update_active_services(2)

        metrics_content = get_metrics()

        # Check for Prometheus format elements
        assert "credproxy_requests_total" in metrics_content
        assert "credproxy_active_services_total" in metrics_content

    def test_get_metrics_contains_only_credproxy_metrics(self):
        """Test that only CredProxy metrics are exposed, no default Python metrics."""
        # Record some metrics
        record_request(result="success", service_name="test-service")
        update_active_services(3)

        metrics_content = get_metrics()

        # Should contain our metrics
        assert "credproxy_requests_total" in metrics_content
        assert "credproxy_active_services_total" in metrics_content
        assert "credproxy_app_info_info" in metrics_content

        # Should NOT contain default Python Prometheus metrics
        assert "python_info" not in metrics_content
        assert "python_gc_objects_collected_total" not in metrics_content
        assert "process_resident_memory_bytes" not in metrics_content
        assert "process_cpu_seconds_total" not in metrics_content

    def test_default_collectors_disabled(self):
        """Test that default Prometheus collectors are disabled."""
        # The global registry should not have the default collectors
        global_registry = prometheus_client.REGISTRY

        # Check that default collectors are not in the global registry
        collector_classes = [
            collector.__class__.__name__
            for collector in global_registry._collector_to_names.keys()
        ]

        assert "ProcessCollector" not in collector_classes
        assert "PlatformCollector" not in collector_classes
        assert "GCCollector" not in collector_classes

    def test_custom_registry_isolation(self):
        """Test that our custom registry only contains our metrics."""
        # Should contain our metric collectors
        metric_name_lists = list(REGISTRY._collector_to_names.values())

        # Flatten the lists and check that only our metrics are present
        all_metric_names = []
        for name_list in metric_name_lists:
            all_metric_names.extend(name_list)

        # Check that only our metrics are present
        for name in all_metric_names:
            assert name.startswith("credproxy_")
