# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for variable substitution functionality."""

from __future__ import annotations

import os
import re
import tempfile

import pytest

from credproxy.settings import FROM_ENV_TAG, FROM_FILE_TAG, TAG_SEPARATOR
from credproxy.substitutions import substitute_variables


def env_var(name: str) -> str:
    """Helper to build environment variable pattern."""
    return f"${{{FROM_ENV_TAG}{TAG_SEPARATOR}{name}}}"


def file_var(path: str) -> str:
    """Helper to build file variable pattern."""
    return f"${{{FROM_FILE_TAG}{TAG_SEPARATOR}{path}}}"


class TestSubstituteVariables:
    """Test the main substitute_variables function."""

    def test_substitute_string_with_env_var(self):
        """Test substituting environment variable in a string."""
        os.environ["TEST_VAR"] = "test_value"
        result = substitute_variables(f"prefix_{env_var('TEST_VAR')}_suffix")
        assert result == "prefix_test_value_suffix"
        del os.environ["TEST_VAR"]

    def test_substitute_string_with_file_var(self):
        """Test substituting file contents in a string."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("file_content")
            temp_file = f.name

        try:
            result = substitute_variables(f"prefix_{file_var(temp_file)}_suffix")
            assert result == "prefix_file_content_suffix"
        finally:
            os.unlink(temp_file)

    def test_substitute_dict(self):
        """Test substituting variables in a dictionary."""
        os.environ["TEST_VAR"] = "dict_value"
        input_dict = {
            "key1": f"value_{env_var('TEST_VAR')}",
            "key2": "static_value",
            "nested": {"subkey": f"{env_var('TEST_VAR')}_nested"},
        }
        result = substitute_variables(input_dict)
        expected = {
            "key1": "value_dict_value",
            "key2": "static_value",
            "nested": {"subkey": "dict_value_nested"},
        }
        assert result == expected
        del os.environ["TEST_VAR"]

    def test_substitute_list(self):
        """Test substituting variables in a list."""
        os.environ["TEST_VAR"] = "list_value"
        input_list = [
            f"item_{env_var('TEST_VAR')}",
            "static_item",
            [f"nested_{env_var('TEST_VAR')}"],
        ]
        result = substitute_variables(input_list)
        expected = ["item_list_value", "static_item", ["nested_list_value"]]
        assert result == expected
        del os.environ["TEST_VAR"]

    def test_substitute_multiple_variables(self):
        """Test substituting multiple variables in one string."""
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("file_value")
            temp_file = f.name

        try:
            result = substitute_variables(
                f"{env_var('VAR1')}_{file_var(temp_file)}_{env_var('VAR2')}"
            )
            assert result == "value1_file_value_value2"
        finally:
            os.unlink(temp_file)
            del os.environ["VAR1"]
            del os.environ["VAR2"]

    def test_substitute_nested_variables(self):
        """Test nested variable substitution."""
        os.environ["OUTER_VAR"] = env_var("INNER_VAR")
        os.environ["INNER_VAR"] = "inner_value"

        result = substitute_variables(env_var("OUTER_VAR"))
        assert result == "inner_value"

        del os.environ["OUTER_VAR"]
        del os.environ["INNER_VAR"]


class TestSubstituteEnv:
    """Test environment variable substitution through the public API."""

    def test_substitute_env_existing(self):
        """Test substituting existing environment variable."""
        os.environ["TEST_VAR"] = "test_value"
        result = substitute_variables(env_var("TEST_VAR"))
        assert result == "test_value"
        del os.environ["TEST_VAR"]

    def test_substitute_env_missing(self):
        """Test substituting missing environment variable."""
        with pytest.raises(
            ValueError, match="Environment variable 'MISSING_VAR' not found"
        ):
            substitute_variables(env_var("MISSING_VAR"))

    def test_substitute_env_empty_value(self):
        """Test substituting environment variable with empty value."""
        os.environ["EMPTY_VAR"] = ""
        result = substitute_variables(env_var("EMPTY_VAR"))
        assert result == ""
        del os.environ["EMPTY_VAR"]


class TestSubstituteFile:
    """Test file substitution through the public API."""

    def test_substitute_file_existing(self):
        """Test substituting existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("  file content with whitespace  \n")
            temp_file = f.name

        try:
            result = substitute_variables(file_var(temp_file))
            # New behavior: only strips trailing newline for single-line content,
            # preserves other whitespace
            assert result == "  file content with whitespace  "
        finally:
            os.unlink(temp_file)

    def test_substitute_file_missing(self):
        """Test substituting missing file."""
        with pytest.raises(ValueError, match="File '/nonexistent/file' not found"):
            substitute_variables(file_var("/nonexistent/file"))

    def test_substitute_file_unreadable(self):
        """Test substituting unreadable file."""
        # Create a file and make it unreadable
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("content")
            temp_file = f.name

        try:
            os.chmod(temp_file, 0o000)  # Remove all permissions
            with pytest.raises(ValueError, match=f"Error reading file '{temp_file}'"):
                substitute_variables(file_var(temp_file))
        finally:
            os.chmod(temp_file, 0o644)  # Restore permissions to delete
            os.unlink(temp_file)

    def test_substitute_file_empty(self):
        """Test substituting empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            result = substitute_variables(file_var(temp_file))
            assert result == ""
        finally:
            os.unlink(temp_file)

    def test_substitute_file_with_newlines(self):
        """Test substituting file with newlines."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("line1\nline2\nline3\n")
            temp_file = f.name

        try:
            result = substitute_variables(file_var(temp_file))
            # Multi-line content should preserve trailing newline
            assert result == "line1\nline2\nline3\n"
        finally:
            os.unlink(temp_file)

    def test_substitute_file_single_line_with_trailing_newline(self):
        """Test substituting single line file with trailing newline
        (should be stripped)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("secret_value\n")
            temp_file = f.name

        try:
            result = substitute_variables(file_var(temp_file))
            # Single line with trailing newline should have trailing newline stripped
            assert result == "secret_value"
        finally:
            os.unlink(temp_file)

    def test_substitute_file_single_line_without_trailing_newline(self):
        """Test substituting single line file without trailing newline
        (should remain as-is)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("secret_value")
            temp_file = f.name

        try:
            result = substitute_variables(file_var(temp_file))
            # Single line without trailing newline should remain unchanged
            assert result == "secret_value"
        finally:
            os.unlink(temp_file)

    def test_substitute_file_multi_line_without_trailing_newline(self):
        """Test substituting multi-line file without trailing newline
        (should remain as-is)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("line1\nline2\nline3")
            temp_file = f.name

        try:
            result = substitute_variables(file_var(temp_file))
            # Multi-line without trailing newline should remain unchanged
            assert result == "line1\nline2\nline3"
        finally:
            os.unlink(temp_file)


class TestErrorHandling:
    """Test error handling in substitution functions."""

    def test_unknown_variable_type(self):
        """Test unknown variable type raises ValueError."""
        import credproxy.substitutions as sub_module

        # Temporarily replace the pattern to match any variable type
        original_pattern = sub_module.VARIABLE_PATTERN
        sub_module.VARIABLE_PATTERN = re.compile(r"\$\{([^:}]+):([^}]+)\}")

        try:
            # This should match and trigger the error for unknown variable type
            with pytest.raises(ValueError, match="Unknown variable type: wrong"):
                sub_module._substitute_string("${wrong:VAR}")
        finally:
            # Restore original pattern
            sub_module.VARIABLE_PATTERN = original_pattern

    def test_malformed_variable(self):
        """Test malformed variable patterns."""
        # These should not match the pattern and be returned as-is
        assert substitute_variables("${env") == "${env"
        assert substitute_variables("env:VAR}") == "env:VAR}"
        assert substitute_variables("${VAR}") == "${VAR}"


class TestConfigurableTags:
    """Test configurable substitution tags."""

    def test_settings_module_reads_env_vars(self):
        """Test that settings module correctly reads environment variables."""
        # Test that the settings module responds to environment variables
        original_tag = os.environ.get("CREDPROXY_FROM_ENV_TAG")

        try:
            os.environ["CREDPROXY_FROM_ENV_TAG"] = "testCustomTag"

            # Import settings directly to test environment variable reading
            from credproxy.settings import NAMESPACE, get_from_env_tag

            assert get_from_env_tag(NAMESPACE) == "testCustomTag"

        finally:
            # Restore original value
            if original_tag is not None:
                os.environ["CREDPROXY_FROM_ENV_TAG"] = original_tag
            else:
                os.environ.pop("CREDPROXY_FROM_ENV_TAG", None)

    def test_default_values(self):
        """Test that default values are used when environment variables are not set."""
        from credproxy.settings import (
            NAMESPACE,
            get_from_env_tag,
            get_from_file_tag,
            get_tag_separator,
        )

        # These should be the defaults
        assert get_from_env_tag(NAMESPACE) == "fromEnv"
        assert get_from_file_tag(NAMESPACE) == "fromFile"
        assert get_tag_separator(NAMESPACE) == ":"


class TestRealWorldScenarios:
    """Test real-world configuration scenarios."""

    def test_aws_credentials_config(self):
        """Test typical AWS credentials configuration."""
        from tests.mock_aws import mock_access_key_id, mock_secret_access_key

        # Generate mock values once and reuse them
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()

        os.environ["AWS_ACCESS_KEY_ID"] = mock_access_key
        os.environ["AWS_SECRET_ACCESS_KEY"] = mock_secret_key

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("arn:aws:iam::123456789012:role/MyRole")
            temp_file = f.name

        try:
            config = {
                "aws_defaults": {
                    "region": "us-west-2",
                    "iam_keys": {
                        "aws_access_key_id": env_var("AWS_ACCESS_KEY_ID"),
                        "aws_secret_access_key": env_var("AWS_SECRET_ACCESS_KEY"),
                    },
                },
                "services": {
                    "my-service": {
                        "auth_token": "my-token",
                        "source_credentials": {
                            "region": "us-west-2",
                        },
                        "assumed_role": {
                            "RoleArn": file_var(temp_file),
                            "RoleSessionName": "my-session",
                        },
                    }
                },
            }

            result = substitute_variables(config)
            expected = {
                "aws_defaults": {
                    "region": "us-west-2",
                    "iam_keys": {
                        "aws_access_key_id": mock_access_key,
                        "aws_secret_access_key": mock_secret_key,
                    },
                },
                "services": {
                    "my-service": {
                        "auth_token": "my-token",
                        "source_credentials": {
                            "region": "us-west-2",
                        },
                        "assumed_role": {
                            "RoleArn": "arn:aws:iam::123456789012:role/MyRole",
                            "RoleSessionName": "my-session",
                        },
                    }
                },
            }

            assert result == expected
        finally:
            os.unlink(temp_file)
            del os.environ["AWS_ACCESS_KEY_ID"]
            del os.environ["AWS_SECRET_ACCESS_KEY"]

    def test_aws_environment_substitution(self):
        """Test AWS credential environment variable substitution."""
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["AWS_PROFILE_NAME"] = "dev-profile"
        os.environ["AWS_SESSION_NAME"] = "credproxy-session"

        config = {
            "aws_defaults": {
                "region": env_var("AWS_REGION"),
                "auth_method": "iam_profile",
                "iam_profile": {
                    "profile_name": env_var("AWS_PROFILE_NAME"),
                    "RoleSessionName": env_var("AWS_SESSION_NAME"),
                },
            },
            "services": {
                "web-app": {
                    "auth_token": "web-token",
                    "aws": {
                        "RoleArn": "arn:aws:iam::123456789012:role/WebAppRole",
                        "RoleSessionName": env_var("AWS_SESSION_NAME"),
                    },
                }
            },
        }

        result = substitute_variables(config)
        expected = {
            "aws_defaults": {
                "region": "us-west-2",
                "auth_method": "iam_profile",
                "iam_profile": {
                    "profile_name": "dev-profile",
                    "RoleSessionName": "credproxy-session",
                },
            },
            "services": {
                "web-app": {
                    "auth_token": "web-token",
                    "aws": {
                        "RoleArn": "arn:aws:iam::123456789012:role/WebAppRole",
                        "RoleSessionName": "credproxy-session",
                    },
                }
            },
        }

        assert result == expected
        del os.environ["AWS_REGION"]
        del os.environ["AWS_PROFILE_NAME"]
        del os.environ["AWS_SESSION_NAME"]
