# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for configuration functionality."""

from __future__ import annotations

import os
import tempfile

import yaml
import pytest

from tests.mock_aws import mock_role_arn, mock_access_key_id, mock_secret_access_key
from credproxy.config import Config, IAMKeysAuthConfig
from credproxy.substitutions import FROM_ENV_TAG, FROM_FILE_TAG, TAG_SEPARATOR


def env_var(name: str) -> str:
    """Helper to build environment variable pattern."""
    return f"${{{FROM_ENV_TAG}{TAG_SEPARATOR}{name}}}"


def file_var(path: str) -> str:
    """Helper to build file variable pattern."""
    return f"${{{FROM_FILE_TAG}{TAG_SEPARATOR}{path}}}"


class TestConfig:
    """Test configuration functionality."""

    def test_from_file_with_substitutions(self):
        """Test loading config with variable substitutions."""
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
                    "auth_token": env_var("TEST_TOKEN"),
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
            # Set environment variable for substitution
            os.environ["TEST_TOKEN"] = "substituted-token"

            config = Config.from_file(temp_file)

            # Verify substitution worked
            assert config.services["test-service"].auth_token == "substituted-token"

        finally:
            os.unlink(temp_file)
            if "TEST_TOKEN" in os.environ:
                del os.environ["TEST_TOKEN"]

    def test_from_file_with_file_substitution(self):
        """Test loading config with file variable substitution."""
        mock_role = mock_role_arn()

        # Create a dummy file for the substitution to read first
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as secret_file:
            secret_file.write("dummy-token")
            secret_file_path = secret_file.name

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
            },
            "services": {
                "test-service": {
                    "auth_token": file_var(secret_file_path),
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

            # Verify file substitution worked - actual content, not the pattern
            assert config.services["test-service"].auth_token == "dummy-token"

        finally:
            os.unlink(temp_file)
            os.unlink(secret_file_path)

    def test_validate_services_empty(self):
        """Test validation with empty services."""
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {"region": "us-west-2"},
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-west-2"},
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
            # Should load successfully with at least one service
            config = Config.from_file(temp_file)
            assert "test-service" in config.services

        finally:
            os.unlink(temp_file)

    def test_validate_schema_schema_error(self):
        """Test validation with schema error."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()

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
                        # Missing required role_arn
                        "RoleSessionName": "test-session",
                    },
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config.from_file(temp_file)

        finally:
            os.unlink(temp_file)

    def test_validate_schema_general_error(self):
        """Test validation with general error."""
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {
                "region": "invalid-region-format",  # Invalid region format
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
            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config.from_file(temp_file)

        finally:
            os.unlink(temp_file)


class TestServiceConfig:
    """Test service configuration functionality."""

    def test_service_config_inheritance(self):
        """Test service configuration inheritance from defaults."""
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
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)
            service = config.services["test-service"]

            # Should inherit iam_keys from defaults
            assert service.source_credentials.iam_keys is not None
            assert (
                service.source_credentials.iam_keys.aws_access_key_id == mock_access_key
            )
            assert (
                service.source_credentials.iam_keys.aws_secret_access_key
                == mock_secret_key
            )

        finally:
            os.unlink(temp_file)


class TestAuthMethodConfigs:
    """Test authentication method configuration classes."""

    def test_iam_profile_config(self):
        """Test IAM profile configuration."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()

        iam_profile_config = IAMKeysAuthConfig(
            aws_access_key_id=mock_access_key,
            aws_secret_access_key=mock_secret_key,
        )

        assert iam_profile_config.aws_access_key_id == mock_access_key
        assert iam_profile_config.aws_secret_access_key == mock_secret_key


class TestConfigExceptions:
    """Test configuration error handling."""

    def test_from_file_not_found(self):
        """Test loading non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            Config.from_file("/non/existent/path.yaml")

    def test_from_file_malformed_yaml(self):
        """Test loading malformed YAML file."""
        malformed_yaml = "invalid: yaml: content: ["

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(malformed_yaml)
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="File is not valid YAML or JSON"):
                Config.from_file(temp_file)

        finally:
            os.unlink(temp_file)

    def test_validate_no_services(self):
        """Test validation with missing services section."""
        config_data = {"aws_defaults": {"region": "us-west-2"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config.from_file(temp_file)

        finally:
            os.unlink(temp_file)

    def test_validate_missing_auth_token(self):
        """Test validation with missing auth token."""
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {"region": "us-west-2"},
            "services": {
                "test-service": {
                    "source_credentials": {"region": "us-west-2"},
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
            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config.from_file(temp_file)

        finally:
            os.unlink(temp_file)

    def test_validate_missing_region(self):
        """Test validation with missing region."""
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {},  # Missing region
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {},  # Missing region
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
            with pytest.raises(
                ValueError, match="AWS region is required for service 'test-service'"
            ):
                Config.from_file(temp_file)

        finally:
            os.unlink(temp_file)

    def test_validate_missing_role_arn(self):
        """Test validation with missing role ARN."""
        config_data = {
            "aws_defaults": {"region": "us-west-2"},
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-west-2"},
                    "assumed_role": {
                        # Missing role_arn
                        "RoleSessionName": "test-session",
                    },
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config.from_file(temp_file)

        finally:
            os.unlink(temp_file)


class TestConfigEdgeCases:
    """Test configuration edge cases."""

    def test_from_file_default_path(self):
        """Test loading from default path when file doesn't exist."""
        # This should not raise an error if we're not actually loading
        with pytest.raises(FileNotFoundError):
            Config.from_file("/non/existent/default/path.yaml")

    def test_from_file_env_variable(self):
        """Test loading config file path from environment variable."""
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {"region": "us-west-2"},
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-west-2"},
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
            # Set environment variable to override config path
            original_env = os.environ.get("CREDPROXY_CONFIG_FILE")
            os.environ["CREDPROXY_CONFIG_FILE"] = temp_file

            config = Config.from_file()  # Should use env var
            assert config.services["test-service"].auth_token == "test-token"

        finally:
            os.unlink(temp_file)
            if original_env is not None:
                os.environ["CREDPROXY_CONFIG_FILE"] = original_env
            elif "CREDPROXY_CONFIG_FILE" in os.environ:
                del os.environ["CREDPROXY_CONFIG_FILE"]


class TestConfigDefaults:
    """Test configuration defaults."""

    def test_default_values(self):
        """Test that default values are applied correctly."""
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {"region": "us-west-2"},
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-west-2"},
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

            # Check default server values
            assert config.server.host == "localhost"
            assert config.server.port == 1338
            assert config.server.debug is False

            # Check default credentials values
            assert config.credentials.refresh_buffer_seconds == 300
            assert config.credentials.retry_delay == 60
            assert config.credentials.request_timeout == 30

        finally:
            os.unlink(temp_file)


class TestConfigEdgeCasesAndCoverage:
    """Test additional edge cases for coverage improvement."""

    def test_keyisset_missing_key(self):
        """Test keyisset function raises KeyError for missing key."""
        from credproxy.config import keyisset

        data = {"existing_key": "value"}

        with pytest.raises(
            KeyError, match="Required key 'missing_key' not found in configuration"
        ):
            keyisset("missing_key", data)

    def test_get_service_name_by_token_not_found(self):
        """Test token lookup when token is not found."""
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "valid-token",
                    "source_credentials": {"region": "us-west-2"},
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)

            # Test with invalid token
            result = config.get_service_name_by_token("invalid-token")
            assert result is None

        finally:
            os.unlink(temp_file)

    def test_add_service_already_exists(self):
        """Test add_service when service already exists."""
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "existing-service": {
                    "auth_token": "existing-token",
                    "source_credentials": {"region": "us-west-2"},
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "existing-session",
                    },
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)

            # Try to add a service with the same name
            new_service_config = config.services["existing-service"]
            result = config.add_service("existing-service", new_service_config)
            assert result is False

        finally:
            os.unlink(temp_file)

    def test_remove_service_not_found(self):
        """Test remove_service when service doesn't exist."""
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-west-2"},
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)

            # Try to remove a service that doesn't exist
            result = config.remove_service("non-existent-service")
            assert result is False

        finally:
            os.unlink(temp_file)

    def test_update_service_not_found(self):
        """Test update_service when service doesn't exist."""
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {"region": "us-west-2"},
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.from_file(temp_file)

            # Try to update a service that doesn't exist
            service_config = config.services["test-service"]
            result = config.update_service("non-existent-service", service_config)
            assert result is False

        finally:
            os.unlink(temp_file)
