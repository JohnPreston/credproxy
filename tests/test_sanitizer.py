#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

from __future__ import annotations

from tests.mock_aws import (
    mock_role_arn,
    mock_external_id,
    mock_access_key_id,
    mock_secret_access_key,
)
from credproxy.sanitizer import sanitize_for_logging, sanitize_exception_message


class TestSanitizeForLogging:
    """Test sanitize_for_logging function."""

    def test_dict_with_sensitive_data(self):
        """Test sanitizing dictionaries with sensitive data."""
        mock_secret = mock_secret_access_key()
        data = {
            "username": "john",
            "password": "supersecret123",
            "aws_access_key_id": mock_access_key_id(),
            "region": "us-east-1",
            "aws_secret_access_key": mock_secret,
        }

        result = sanitize_for_logging(data)

        assert result["username"] == "john"
        assert result["password"] == "supe****"
        assert result["aws_access_key_id"] == "AKIA****"
        assert result["region"] == "us-east-1"
        assert result["aws_secret_access_key"] == f"{mock_secret[:4]}****"

    def test_nested_dict(self):
        """Test sanitizing nested dictionaries."""
        mock_secret = mock_secret_access_key()
        data = {
            "service": {
                "auth_token": "verylongtoken123456789",
                "aws": {
                    "aws_access_key_id": mock_access_key_id(),
                    "aws_secret_access_key": mock_secret,
                    "region": "us-west-2",
                },
            },
            "server": {
                "host": "localhost",
                "port": 1338,
            },
        }

        result = sanitize_for_logging(data)

        assert result["service"]["auth_token"] == "very****"
        assert result["service"]["aws"]["aws_access_key_id"] == "AKIA****"
        assert (
            result["service"]["aws"]["aws_secret_access_key"]
            == f"{mock_secret[:4]}****"
        )
        assert result["service"]["aws"]["region"] == "us-west-2"
        assert result["server"]["host"] == "localhost"
        assert result["server"]["port"] == 1338

    def test_list_with_sensitive_data(self):
        """Test sanitizing lists containing sensitive data."""
        data = [
            {"username": "user1", "password": "pass123"},
            {"username": "user2", "password": "pass456"},
            {"region": "eu-west-1"},
        ]

        result = sanitize_for_logging(data)

        assert result[0]["username"] == "user1"
        assert result[0]["password"] == "pass****"
        assert result[1]["username"] == "user2"
        assert result[1]["password"] == "pass****"
        assert result[2]["region"] == "eu-west-1"

    def test_aws_key_patterns(self):
        """Test that AWS key patterns are detected and sanitized."""
        # AWS Access Key ID pattern
        data = {"key": mock_access_key_id()}
        result = sanitize_for_logging(data)
        assert result["key"] == "AKIA****"

        # AWS Secret Access Key pattern (base64-like)
        mock_secret = mock_secret_access_key()
        data = {"key": mock_secret}
        result = sanitize_for_logging(data)
        assert result["key"] == f"{mock_secret[:4]}****"

        # Generic long token
        data = {"key": "verylongtoken123456789012345678901234567890"}
        result = sanitize_for_logging(data)
        assert result["key"] == "very****"

    def test_non_string_values(self):
        """Test handling of non-string values in sensitive fields."""
        data = {
            "password": 123456,  # number
            "auth_token": None,  # None
            "secret_key": ["list", "of", "secrets"],  # list
        }

        result = sanitize_for_logging(data)

        assert result["password"] == "1234****"
        assert result["auth_token"] is None
        # Lists in sensitive fields are now recursively sanitized
        assert result["secret_key"] == ["list", "of", "secrets"]

    def test_empty_and_none_values(self):
        """Test handling of empty and None values."""
        data = {
            "password": "",
            "secret": None,
            "token": "abc",
        }

        result = sanitize_for_logging(data)

        assert result["password"] == ""
        assert result["secret"] is None
        assert result["token"] == "****"


class TestSanitizeExceptionMessage:
    """Test sanitize_exception_message function."""

    def test_jsonschema_validation_error(self):
        """Test sanitizing JSON schema validation errors."""
        mock_secret = mock_secret_access_key()
        mock_external = mock_external_id()
        mock_role = mock_role_arn("test", "")
        message = f"""Additional properties are not allowed ('iam_keys' was unexpected)

On instance['services']['open_webui']:
    {{'auth_token': 'xaGPrbLqO2NqHPBU7MjPX0i6E4xzvLMQqAQWfp3HHHH',
     'iam_keys': {{'aws_access_key_id': '{mock_access_key_id()}',
                  'aws_secret_access_key': '{mock_secret}'}}}},
     'aws': {{'role_arn': '{mock_role}',
              'external_id': '{mock_external}'}}}}"""

        result = sanitize_exception_message(message)

        # Check that sensitive values are sanitized
        assert "xaGP****" in result
        assert "AKIA****" in result
        assert f"{mock_secret[:4]}****" in result
        assert f"{mock_external[:4]}****" in result

        # Check that non-sensitive values are preserved
        assert mock_role in result
        assert "open_webui" in result

    def test_various_sensitive_patterns(self):
        """Test various patterns of sensitive data in exception messages."""
        mock_secret = mock_secret_access_key()
        test_cases = [
            (
                f"'aws_access_key_id': '{mock_access_key_id()}'",
                "'aws_access_key_id': 'AKIA****'",
            ),
            (
                f"'aws_secret_access_key': '{mock_secret}'",
                f"'aws_secret_access_key': '{mock_secret[:4]}****'",
            ),
            ("'auth_token': 'token123456789'", "'auth_token': 'toke****'"),
            ("'password': 'mypassword'", "'password': 'mypa****'"),
            ("'session_token': 'session123'", "'session_token': 'sess****'"),
            ("'external_id': 'external123'", "'external_id': 'exte****'"),
        ]

        for input_msg, expected_output in test_cases:
            result = sanitize_exception_message(input_msg)
            assert expected_output in result

    def test_case_insensitive_patterns(self):
        """Test that pattern matching is case insensitive."""
        message = "'ACCESS_KEY_ID': 'AKIA1234567890123456', 'SECRET': 'mysecret'"
        result = sanitize_exception_message(message)

        assert "'ACCESS_KEY_ID': 'AKIA****'" in result
        assert "'SECRET': 'myse****'" in result

    def test_no_sensitive_data(self):
        """Test messages without sensitive data are unchanged."""
        message = (
            "Configuration validation failed at services -> missing required field"
        )
        result = sanitize_exception_message(message)

        assert result == message

    def test_multiple_occurrences(self):
        """Test sanitizing multiple occurrences of sensitive data."""
        message = (
            f"""'aws_access_key_id': '{mock_access_key_id()}' and """
            f"""'aws_access_key_id': '{mock_access_key_id()}'
        'secret': 'firstsecret' and 'secret': 'secondsecret'"""
        )

        result = sanitize_exception_message(message)

        assert "'aws_access_key_id': 'AKIA****'" in result
        assert "'secret': 'firs****'" in result
        # Should not contain the original sensitive values
        assert "AKIA1111111111111111" not in result
        assert "AKIA2222222222222222" not in result
        assert "firstsecret" not in result
        assert "secondsecret" not in result


class TestRealWorldScenarios:
    """Test real-world scenarios from logs."""

    def test_actual_log_scenario(self):
        """Test the actual scenario from logs_with_secrets.txt file."""
        # Generate mock values to use consistently
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_external = mock_external_id()
        mock_role = mock_role_arn("traefik-acme", "/ikigai/route53")

        # This simulates the actual error that was logged
        message = f"""Additional properties are not allowed ('iam_keys' was unexpected)

Failed validating 'additionalProperties' in schema:
        ['properties']['services']['patternProperties']['^[a-zA-Z0-9_-]+$']:
    {{'type': 'object',
     'description': 'Service configuration',
     'required': ['auth_token', 'aws'],
     'properties': {{'auth_token': {{'type': 'string',
                                   'description': 'Authorization token for '
                                                  'this service',
                                   'minLength': 1}},
                    'aws': {{'$ref': '#/definitions/aws_config'}}}},
     'additionalProperties': False}}

On instance['services']['open_webui']:
    {{'auth_token': 'xaGPrbLqO2NqHPBU7MjPX0i6E4xzvLMQqAQWfp3HHHH',
     'iam_keys': {{'aws_access_key_id': '{mock_access_key}',
                  'aws_secret_access_key': '{mock_secret_key}'}}}},
     'aws': {{'role_arn': '{mock_role}',
              'external_id': '{mock_external}'}}}}"""

        result = sanitize_exception_message(message)

        # Verify all sensitive data is sanitized
        sensitive_values = [
            "xaGPrbLqO2NqHPBU7MjPX0i6E4xzvLMQqAQWfp3HHHH",
            mock_access_key,
            mock_secret_key,
            mock_external,
        ]

        for sensitive_value in sensitive_values:
            msg = f"Sensitive value '{sensitive_value}' was not sanitized"
            assert sensitive_value not in result, msg

        # Verify non-sensitive data is preserved
        non_sensitive_values = [
            "open_webui",
            mock_role,
            "Additional properties are not allowed",
            "iam_keys",
        ]

        for non_sensitive_value in non_sensitive_values:
            msg = (
                f"Non-sensitive value '{non_sensitive_value}' was incorrectly modified"
            )
            assert non_sensitive_value in result, msg

    def test_config_data_sanitization(self):
        """Test sanitizing actual configuration data."""
        # Generate mock values for testing
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_external = mock_external_id()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "open_webui": {
                    "auth_token": "xaGPrbLqO2NqHPBU7MjPX0i6E4xzvLMQqAQWfp3HHHH",
                    "source_credentials": {
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "ExternalId": mock_external,
                    },
                }
            },
        }

        result = sanitize_for_logging(config_data)

        # Verify sensitive data is sanitized
        service = result["services"]["open_webui"]
        assert service["auth_token"] == "xaGP****"
        assert (
            service["source_credentials"]["iam_keys"]["aws_access_key_id"] == "AKIA****"
        )
        assert (
            service["source_credentials"]["iam_keys"]["aws_secret_access_key"]
            == f"{mock_secret_key[:4]}****"
        )
        assert service["assumed_role"]["ExternalId"] == f"{mock_external[:4]}****"

        # Verify non-sensitive data is preserved
        assert service["assumed_role"]["RoleArn"] == mock_role
        assert "open_webui" in result["services"]
