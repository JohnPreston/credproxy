# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for Flask application initialization and configuration."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from flask import g

from credproxy.app import init_app, set_service_context
from credproxy.config import Config
from credproxy.credentials_handler import CredentialsHandler


class TestAppInitialization:
    """Test Flask application initialization."""

    def test_init_app_minimal_config(self):
        """Test app initialization with minimal configuration."""
        config = Config()
        app = init_app(config)

        # Check basic app setup
        assert app is not None
        assert "credproxy_config" in app.config
        assert app.config["credproxy_config"] is config
        assert "credentials_handler" in app.config
        assert "file_watcher" in app.config

        # Check that blueprint is registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert "api" in blueprint_names

    def test_init_app_with_full_config(self):
        """Test app initialization with complete configuration."""
        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "iam_profile": {"profile_name": "test"},
                        "region": "us-east-1",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            },
            "server": {"host": "0.0.0.0", "port": 1338, "debug": True},
            "dynamic_services": {
                "enabled": True,
                "directories": [
                    {
                        "path": "/tmp/dynamic",
                        "include_patterns": [".*\\.yaml$"],
                        "exclude_patterns": [".*\\.tmp$"],
                    }
                ],
                "reload_interval": 5,
            },
        }
        config = Config.from_dict(config_data)
        app = init_app(config)

        # Verify config is stored
        assert app.config["credproxy_config"] is config

        # Verify credentials handler is created
        credentials_handler = app.config["credentials_handler"]
        assert isinstance(credentials_handler, CredentialsHandler)

        # Verify file watcher is created
        file_watcher = app.config["file_watcher"]
        assert file_watcher is not None

    @patch("credproxy.app.FileWatcherService")
    def test_init_app_file_watcher_failure(self, mock_file_watcher_class):
        """Test graceful degradation when file watcher fails."""
        # Mock file watcher to raise exception on start
        mock_file_watcher = Mock()
        mock_file_watcher.start.side_effect = Exception("File system error")
        mock_file_watcher_class.return_value = mock_file_watcher

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "iam_profile": {"profile_name": "test"},
                        "region": "us-east-1",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            },
            "dynamic_services": {
                "enabled": True,
                "directories": [
                    {
                        "path": "/tmp/dynamic",
                        "include_patterns": [".*\\.yaml$"],
                        "exclude_patterns": [".*\\.tmp$"],
                    }
                ],
                "reload_interval": 5,
            },
        }
        config = Config.from_dict(config_data)

        # Should not raise exception, should continue gracefully
        app = init_app(config)

        # App should still be created
        assert app is not None
        # File watcher start should have been attempted
        mock_file_watcher.start.assert_called_once()

    def test_init_app_request_id_generation(self):
        """Test that request ID generation is set up."""
        config = Config()
        app = init_app(config)

        with app.test_request_context("/"):
            # Check that request_id is set in g context
            with app.test_client() as client:
                response = client.get("/health")
                # Should succeed without error
                assert response.status_code == 200

    def test_init_app_shutdown_middleware(self):
        """Test shutdown middleware functionality."""
        config = Config()
        app = init_app(config)

        # Set shutdown flag
        app.config["_shutdown_requested"] = True

        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 503
            assert "Service shutting down" in response.get_data(as_text=True)


class TestServiceContext:
    """Test service context setting for logging."""

    def test_set_service_context_function_exists(self):
        """Test that set_service_context function exists and is callable."""

        assert callable(set_service_context)

    def test_set_service_context_handles_no_context(self):
        """Test that set_service_context handles missing Flask context gracefully."""

        # Should raise RuntimeError when called outside Flask context
        with pytest.raises(RuntimeError):
            set_service_context()

    def test_set_service_context_with_valid_token(self):
        """Test set_service_context with valid authorization token."""

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "valid-token",
                    "source_credentials": {
                        "iam_profile": {"profile_name": "test"},
                        "region": "us-east-1",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            }
        }
        config = Config.from_dict(config_data)
        app = init_app(config)

        # Test with proper request context
        with app.test_request_context(
            "/credentials", headers={"Authorization": "valid-token"}
        ):
            # Patch request at module level
            with patch("credproxy.app.request") as mock_request:
                mock_request.endpoint = "api.get_credentials"
                mock_request.headers = Mock()
                mock_request.headers.get.return_value = "valid-token"

                set_service_context()

                # Verify service context was set
                assert hasattr(g, "service_name")
                assert g.service_name == "test-service"

    def test_set_service_context_with_source_file(self):
        """Test set_service_context when service has source_file."""

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "valid-token",
                    "source_credentials": {
                        "iam_profile": {"profile_name": "test"},
                        "region": "us-east-1",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                    "x-source-file": "/path/to/service.yaml",
                }
            }
        }
        config = Config.from_dict(config_data)
        app = init_app(config)

        # Test with proper request context
        with app.test_request_context(
            "/credentials", headers={"Authorization": "valid-token"}
        ):
            # Mock the endpoint to match get_credentials
            with patch("credproxy.app.request") as mock_request:
                mock_request.endpoint = "api.get_credentials"
                mock_request.headers = Mock()
                mock_request.headers.get.return_value = "valid-token"

                set_service_context()

                # Verify both service name and source file were set
                assert hasattr(g, "service_name")
                assert hasattr(g, "service_source_file")
                assert g.service_name == "test-service"
                assert g.service_source_file is not None

    def test_set_service_context_no_auth_header(self):
        """Test set_service_context when no authorization header is provided."""

        config = Config()
        app = init_app(config)

        # Test with proper request context but no auth header
        with app.test_request_context("/credentials"):
            # Mock the endpoint to match get_credentials but no auth header
            with patch("credproxy.app.request") as mock_request:
                mock_request.endpoint = "api.get_credentials"
                mock_request.headers = Mock()
                mock_request.headers.get.return_value = None

                set_service_context()

                # Verify no service context was set
                assert not hasattr(g, "service_name")
                assert not hasattr(g, "service_source_file")

    def test_set_service_context_invalid_token(self):
        """Test set_service_context with invalid authorization token."""

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "valid-token",
                    "source_credentials": {
                        "iam_profile": {"profile_name": "test"},
                        "region": "us-east-1",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            }
        }
        config = Config.from_dict(config_data)
        app = init_app(config)

        # Test with proper request context but invalid token
        with app.test_request_context(
            "/credentials", headers={"Authorization": "invalid-token"}
        ):
            # Mock the endpoint to match get_credentials
            with patch("credproxy.app.request") as mock_request:
                mock_request.endpoint = "api.get_credentials"
                mock_request.headers = Mock()
                mock_request.headers.get.return_value = "invalid-token"

                set_service_context()

                # Verify no service context was set for invalid token
                assert not hasattr(g, "service_name")
                assert not hasattr(g, "service_source_file")

    def test_set_service_context_non_credentials_endpoint(self):
        """Test set_service_context when endpoint is not get_credentials."""

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "valid-token",
                    "source_credentials": {
                        "iam_profile": {"profile_name": "test"},
                        "region": "us-east-1",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole"
                    },
                }
            }
        }
        config = Config.from_dict(config_data)
        app = init_app(config)

        # Test with non-credentials endpoint
        with app.test_request_context(
            "/health", headers={"Authorization": "valid-token"}
        ):
            # Mock the endpoint to be something other than get_credentials
            with patch("credproxy.app.request") as mock_request:
                mock_request.endpoint = "health_check"
                mock_request.headers = Mock()
                mock_request.headers.get.return_value = "valid-token"

                set_service_context()

                # Verify no service context was set for non-credentials endpoint
                assert not hasattr(g, "service_name")
                assert not hasattr(g, "service_source_file")
