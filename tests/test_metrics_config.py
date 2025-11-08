#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""Tests for metrics configuration functionality."""

from __future__ import annotations

from credproxy.app import init_app
from credproxy.config import Config, MetricsConfig, PrometheusConfig


class TestMetricsConfig:
    """Test metrics configuration dataclasses."""

    def test_prometheus_config_defaults(self):
        """Test PrometheusConfig default values."""
        config = PrometheusConfig()
        assert config.enabled is True

    def test_prometheus_config_custom_values(self):
        """Test PrometheusConfig with custom values."""
        config = PrometheusConfig(enabled=False)
        assert config.enabled is False

    def test_metrics_config_defaults(self):
        """Test MetricsConfig default values."""
        config = MetricsConfig()
        assert isinstance(config.prometheus, PrometheusConfig)
        assert config.prometheus.enabled is True

    def test_metrics_config_custom_prometheus(self):
        """Test MetricsConfig with custom Prometheus config."""
        prometheus_config = PrometheusConfig(enabled=False)
        config = MetricsConfig(prometheus=prometheus_config)
        assert config.prometheus.enabled is False

    def test_main_config_metrics_defaults(self):
        """Test main Config class includes metrics with defaults."""
        config = Config()
        assert isinstance(config.metrics, MetricsConfig)
        assert config.metrics.prometheus.enabled is True


class TestMetricsConfigFromDict:
    """Test loading metrics configuration from dictionaries."""

    def test_load_config_without_metrics_section(self):
        """Test loading config without metrics section uses defaults."""
        config_dict = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-east-1"},
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            }
        }

        config = Config.from_dict(config_dict)
        assert config.metrics.prometheus.enabled is True

    def test_load_config_with_metrics_enabled(self):
        """Test loading config with metrics explicitly enabled."""
        config_dict = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-east-1"},
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            },
            "metrics": {"prometheus": {"enabled": True}},
        }

        config = Config.from_dict(config_dict)
        assert config.metrics.prometheus.enabled is True

    def test_load_config_with_metrics_disabled(self):
        """Test loading config with metrics disabled."""
        config_dict = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-east-1"},
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            },
            "metrics": {"prometheus": {"enabled": False}},
        }

        config = Config.from_dict(config_dict)
        assert config.metrics.prometheus.enabled is False

    def test_load_config_with_metrics_enabled_explicitly(self):
        """Test loading config with metrics explicitly enabled."""
        config_dict = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-east-1"},
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            },
            "metrics": {"prometheus": {"enabled": True}},
        }

        config = Config.from_dict(config_dict)
        assert config.metrics.prometheus.enabled is True


class TestMetricsEndpointRegistration:
    """Test metrics endpoint registration based on configuration."""

    def test_metrics_endpoint_registered_when_enabled(self):
        """Test that metrics endpoint is registered when enabled."""
        config_dict = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-east-1"},
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            },
            "metrics": {"prometheus": {"enabled": True}},
        }

        config = Config.from_dict(config_dict)
        app = init_app(config)

        with app.test_client() as client:
            # Test that metrics endpoint is accessible
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "text/plain" in response.content_type

    def test_metrics_endpoint_not_registered_when_disabled(self):
        """Test that metrics endpoint is not registered when disabled."""
        config_dict = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-east-1"},
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            },
            "metrics": {"prometheus": {"enabled": False}},
        }

        config = Config.from_dict(config_dict)
        app = init_app(config)

        with app.test_client() as client:
            # Test that metrics endpoint returns 404
            response = client.get("/metrics")
            assert response.status_code == 404

    def test_metrics_endpoint_registration_with_explicit_enabled(self):
        """Test that metrics endpoint is registered when explicitly enabled."""
        config_dict = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-east-1"},
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            },
            "metrics": {"prometheus": {"enabled": True}},
        }

        config = Config.from_dict(config_dict)
        app = init_app(config)

        with app.test_client() as client:
            # Test that metrics endpoint is accessible
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "text/plain" in response.content_type

    def test_default_metrics_endpoint_when_no_config(self):
        """Test that default metrics endpoint works when no metrics config provided."""
        config_dict = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-east-1"},
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            }
        }

        config = Config.from_dict(config_dict)
        app = init_app(config)

        with app.test_client() as client:
            # Test that the default metrics endpoint is accessible
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "text/plain" in response.content_type
