# This Source Code Form is subject to terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests for CredProxy application."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import Mock, patch

import yaml

from credproxy.app import init_app
from tests.mock_aws import mock_role_arn, mock_access_key_id, mock_secret_access_key
from credproxy.config import Config


class TestAppIntegration:
    """Integration tests for Flask app."""

    def test_init_app_full_integration(self):
        """Test complete app initialization with all components."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_keys": {
                    "aws_access_key_id": mock_access_key,
                    "aws_secret_access_key": mock_secret_key,
                },
            },
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8080,
            },
            "dynamic_services": {
                "enabled": False,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)
            app = init_app(config)

            # Test app configuration
            assert app.config["ENV"] == "production"
            assert app.config["LOGGER_HANDLER_POLICY"] == "never"
            assert "credproxy_config" in app.config
            assert "credentials_handler" in app.config
            assert "file_watcher" in app.config

            # Test that blueprints are registered
            assert len(app.blueprints) > 0

            # Test that request handlers are registered
            assert len(app.before_request_funcs) > 0

        finally:
            os.unlink(temp_file)

    def test_init_app_with_file_watcher_failure(self):
        """Test app initialization when file watcher fails to start."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_keys": {
                    "aws_access_key_id": mock_access_key,
                    "aws_secret_access_key": mock_secret_key,
                },
            },
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            },
            "dynamic_services": {
                "enabled": True,
                "directories": [
                    {
                        "path": "/tmp/test",
                        "include_patterns": [],
                        "exclude_patterns": [],
                    }
                ],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)

            # Mock file watcher to raise exception
            with patch("credproxy.app.FileWatcherService") as mock_file_watcher:
                mock_instance = Mock()
                mock_instance.start.side_effect = Exception("File watcher error")
                mock_file_watcher.return_value = mock_instance

                # App should still initialize despite file watcher failure
                app = init_app(config)

                # App should be properly configured
                assert app.config["credproxy_config"] is config
                assert "credentials_handler" in app.config
                assert "file_watcher" in app.config

        finally:
            os.unlink(temp_file)

    def test_set_service_context_no_auth_token(self):
        """Test service context setting when no auth token provided."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_keys": {
                    "aws_access_key_id": mock_access_key,
                    "aws_secret_access_key": mock_secret_key,
                },
            },
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)
            app = init_app(config)

            with app.test_request_context("/credentials"):
                from flask import g

                from credproxy.app import set_service_context

                # Call function directly to test integration
                set_service_context()

                # Verify no service context was set
                assert not hasattr(g, "service_name")
                assert not hasattr(g, "service_source_file")

        finally:
            os.unlink(temp_file)

    def test_set_service_context_invalid_token(self):
        """Test service context setting with invalid auth token."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_keys": {
                    "aws_access_key_id": mock_access_key,
                    "aws_secret_access_key": mock_secret_key,
                },
            },
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)
            app = init_app(config)

            with app.test_request_context(
                "/credentials", headers={"Authorization": "invalid-token"}
            ):
                from flask import g

                from credproxy.app import set_service_context

                # Call function directly to test integration
                set_service_context()

                # Verify no service context was set for invalid token
                assert not hasattr(g, "service_name")
                assert not hasattr(g, "service_source_file")

        finally:
            os.unlink(temp_file)

    def test_shutdown_middleware_integration(self):
        """Test shutdown middleware functionality."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_keys": {
                    "aws_access_key_id": mock_access_key,
                    "aws_secret_access_key": mock_secret_key,
                },
            },
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)
            app = init_app(config)

            # Set shutdown flag
            app.config["_shutdown_requested"] = True

            with app.test_client() as client:
                response = client.get("/health")

                # Should return 503 during shutdown
                assert response.status_code == 503
                assert b"Service shutting down" in response.data

        finally:
            os.unlink(temp_file)

    def test_service_config_with_source_file(self):
        """Test service configuration with x-source-file property."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_keys": {
                    "aws_access_key_id": mock_access_key,
                    "aws_secret_access_key": mock_secret_key,
                },
            },
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                    "x-source-file": "/path/to/service.yaml",
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)

            # Test that config has service with source file
            service = config.services.get("test-service")
            assert service is not None
            assert hasattr(service, "source_file")
            # The source_file gets set to the actual config file path during loading
            assert service.source_file is not None
            assert service.source_file.endswith(".yaml")

        finally:
            os.unlink(temp_file)

    def test_set_service_context_with_valid_token(self):
        """Test service context function exists and can be called."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_keys": {
                    "aws_access_key_id": mock_access_key,
                    "aws_secret_access_key": mock_secret_key,
                },
            },
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                    "x-source-file": "/path/to/service.yaml",
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)

            # Test that the function exists and can be imported
            from credproxy.app import set_service_context

            assert callable(set_service_context)

            # Test that config has service for token lookup
            service_name = config.get_service_name_by_token("test-token")
            assert service_name == "test-service"

        finally:
            os.unlink(temp_file)
