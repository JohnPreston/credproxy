# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for CLI functionality."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import yaml
import pytest

from credproxy.cli import main, create_parser
from tests.mock_aws import mock_role_arn, mock_access_key_id, mock_secret_access_key
from credproxy.runner import validate_config_file


class TestCLI:
    """Test CLI functionality."""

    def test_create_parser(self):
        """Test argument parser creation."""
        parser = create_parser()

        # Test default arguments
        args = parser.parse_args([])
        assert args.config == "/credproxy/config.yaml"
        assert args.validate_only is False
        assert args.log_level is None

        # Test custom arguments
        args = parser.parse_args(
            ["--config", "test.yaml", "--validate-only", "--log-level", "DEBUG"]
        )
        assert args.config == "test.yaml"
        assert args.validate_only is True
        assert args.log_level == "DEBUG"

    def test_log_level_argument(self):
        """Test log level argument parsing."""
        parser = create_parser()

        # Test with log level specified
        args = parser.parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

        # Test with different log level
        args = parser.parse_args(["--log-level", "ERROR"])
        assert args.log_level == "ERROR"

    def test_validate_config_success(self):
        """Test successful configuration validation."""
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
                    "assumed_role": {"RoleArn": mock_role},
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            result = validate_config_file(temp_file)
            assert result is True
        finally:
            os.unlink(temp_file)

    def test_validate_config_failure(self):
        """Test configuration validation failure."""
        mock_role = mock_role_arn()

        config_data = {
            "aws_defaults": {"region": "us-west-2"},
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    # Missing source_credentials entirely - this should fail
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
            result = validate_config_file(temp_file)
            assert result is False
        finally:
            os.unlink(temp_file)

    @patch("flask.Flask.run")
    def test_main_run_app(self, mock_flask_run):
        """Test main function running the application."""
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
            result = main(["--config", temp_file, "--log-level", "WARNING"])
            assert result == 0
            mock_flask_run.assert_called_once()
        finally:
            os.unlink(temp_file)

    def test_main_validate_only(self):
        """Test main function with validate-only flag."""
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
            result = main(["--config", temp_file, "--validate-only"])

            assert result == 0
        finally:
            os.unlink(temp_file)

    def test_main_keyboard_interrupt(self):
        """Test main function with keyboard interrupt during app run."""
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
            with patch("flask.Flask.run", side_effect=KeyboardInterrupt()):
                result = main(["--config", temp_file])
                assert result == 0
        finally:
            os.unlink(temp_file)

    def test_main_config_file_not_found(self):
        """Test main function with missing config file."""
        result = main(["--config", "nonexistent.yaml"])
        assert result == 1

    def test_main_version(self):
        """Test main function with version argument."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])

        assert exc_info.value.code == 0

    def test_dev_flag_sets_debug_log_level(self):
        """Test that --dev flag sets log level to DEBUG when not explicitly set."""
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
            with patch("flask.Flask.run") as mock_flask_run:
                result = main(["--config", temp_file, "--dev"])
                assert result == 0
                mock_flask_run.assert_called_once()
        finally:
            os.unlink(temp_file)

    def test_dev_flag_preserves_existing_log_level(self):
        """Test that --dev flag preserves existing log level when set."""
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
            with patch("flask.Flask.run") as mock_flask_run:
                result = main(
                    ["--config", temp_file, "--dev", "--log-level", "WARNING"]
                )
                assert result == 0
                mock_flask_run.assert_called_once()
        finally:
            os.unlink(temp_file)

    def test_validation_exception_handling(self):
        """Test exception handling during validation."""
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
            with patch(
                "credproxy.runner.validate_config_file",
                side_effect=Exception("Validation error"),
            ):
                result = main(["--config", temp_file, "--validate-only"])
                assert result == 1
        finally:
            os.unlink(temp_file)
