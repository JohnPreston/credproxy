#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""Test mock AWS credential generation utilities."""

from __future__ import annotations

import re

from tests.mock_aws import MockAWSGenerator, mock_role_arn, mock_access_key_id


class TestMockAWSGenerator:
    """Test the MockAWSGenerator class."""

    def test_mock_access_key_id_format(self):
        """Test that mock access key IDs follow AWS format."""
        access_key = MockAWSGenerator.mock_access_key_id()

        # Should start with AKIA
        assert access_key.startswith("AKIA")

        # Should be 20 characters total
        assert len(access_key) == 20

        # Should contain only uppercase letters and digits
        assert access_key[4:].isalnum()

        # Should be different each time (random)
        access_key2 = MockAWSGenerator.mock_access_key_id()
        assert access_key != access_key2

    def test_mock_secret_access_key_format(self):
        """Test that mock secret access keys follow AWS format."""
        secret_key = MockAWSGenerator.mock_secret_access_key()

        # Should be 40 characters
        assert len(secret_key) == 40

        # Should contain only valid characters
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/+"
        )
        assert all(c in valid_chars for c in secret_key)

        # Should be different each time
        secret_key2 = MockAWSGenerator.mock_secret_access_key()
        assert secret_key != secret_key2

    def test_mock_session_token_format(self):
        """Test that mock session tokens follow AWS format."""
        session_token = MockAWSGenerator.mock_session_token()

        # Should be 356 characters (typical AWS session token length)
        assert len(session_token) == 356

        # Should contain only valid characters
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/+="
        )
        assert all(c in valid_chars for c in session_token)

    def test_mock_role_arn_format(self):
        """Test that mock role ARNs follow AWS format."""
        role_arn = MockAWSGenerator.mock_role_arn()

        # Should follow ARN format
        arn_pattern = r"^arn:aws:iam::\d{12}:role/.+/.+$"
        assert re.match(arn_pattern, role_arn), f"Invalid ARN format: {role_arn}"

        # Should use mock account ID
        assert "123456789012" in role_arn

        # Should have proper structure
        parts = role_arn.split(":")
        assert len(parts) == 6  # arn:aws:iam:account-id:role/path/name
        assert parts[0] == "arn"
        assert parts[1] == "aws"
        assert parts[2] == "iam"
        assert parts[4] == "123456789012"
        assert parts[5].startswith("role")

    def test_mock_role_arn_with_custom_values(self):
        """Test mock role ARN with custom role name and path."""
        role_arn = MockAWSGenerator.mock_role_arn(
            role_name="custom-role", path="/custom/path"
        )

        assert "custom-role" in role_arn
        assert "/custom/path" in role_arn
        assert role_arn == "arn:aws:iam::123456789012:role/custom/path/custom-role"

    def test_mock_role_arn_path_normalization(self):
        """Test that paths are properly normalized."""
        # Test path without leading slash
        role_arn1 = MockAWSGenerator.mock_role_arn(path="test/path")
        assert role_arn1.startswith("arn:aws:iam::123456789012:role/test/path/")

        # Test path with trailing slash
        role_arn2 = MockAWSGenerator.mock_role_arn(path="/test/path/")
        assert not role_arn2.endswith("/test/path//")  # Should not have double slash

    def test_mock_user_arn_format(self):
        """Test that mock user ARNs follow AWS format."""
        user_arn = MockAWSGenerator.mock_user_arn()

        # Should follow ARN format
        arn_pattern = r"^arn:aws:iam::\d{12}:user/.+/.+$"
        assert re.match(arn_pattern, user_arn), f"Invalid ARN format: {user_arn}"

        # Should use mock account ID
        assert "123456789012" in user_arn

    def test_mock_aws_credentials_structure(self):
        """Test that mock AWS credentials have correct structure."""
        creds = MockAWSGenerator.mock_aws_credentials()

        # Should have required keys
        assert "aws_access_key_id" in creds
        assert "aws_secret_access_key" in creds
        assert "aws_session_token" in creds

        # Should have correct formats
        assert creds["aws_access_key_id"].startswith("AKIA")
        assert len(creds["aws_secret_access_key"]) == 40
        assert len(creds["aws_session_token"]) == 356

    def test_mock_role_config_structure(self):
        """Test that mock role configuration has correct structure."""
        role_config = MockAWSGenerator.mock_role_config()

        # Should have required keys
        assert "RoleArn" in role_config
        assert "RoleSessionName" in role_config
        assert "ExternalId" in role_config

        # Should have correct formats
        assert role_config["RoleArn"].startswith("arn:aws:iam::123456789012:role/")
        assert role_config["RoleSessionName"].startswith("test-session-")
        assert len(role_config["ExternalId"]) == 32

    def test_generate_test_config_structure(self):
        """Test that generated test config has correct structure."""
        config = MockAWSGenerator.generate_test_config()

        # Should have top-level sections
        assert "aws_defaults" in config
        assert "services" in config

        # Should have AWS defaults
        aws_defaults = config["aws_defaults"]
        assert "region" in aws_defaults
        assert "iam_keys" in aws_defaults

        # Should have services
        services = config["services"]
        assert "test-service" in services

        # Service should have correct structure
        service = services["test-service"]
        assert "auth_token" in service
        assert "source_credentials" in service
        assert "assumed_role" in service

    def test_convenience_functions(self):
        """Test that convenience functions work correctly."""
        # Test mock_access_key_id
        access_key = mock_access_key_id()
        assert access_key.startswith("AKIA")
        assert len(access_key) == 20

        # Test mock_role_arn
        role_arn = mock_role_arn()
        assert role_arn.startswith("arn:aws:iam::123456789012:role/")

    def test_realistic_role_names_and_paths(self):
        """Test that generated role names and paths are realistic."""
        # Generate multiple role ARNs to check variety
        role_arns = [MockAWSGenerator.mock_role_arn() for _ in range(10)]

        # Should have reasonable variety (allowing for some randomness)
        unique_count = len(set(role_arns))
        assert unique_count >= 7, (
            f"Expected at least 7 unique ARNs out of 10, got {unique_count}"
        )

        # Should all be valid
        for role_arn in role_arns:
            arn_pattern = r"^arn:aws:iam::\d{12}:role/.+/.+$"
            assert re.match(arn_pattern, role_arn), f"Invalid ARN format: {role_arn}"

            # Should have realistic path structure
            parts = role_arn.split(":")
            path_part = parts[5]  # role/path/name part
            assert path_part.count("/") >= 1  # At least one slash in path/name

    def test_account_id_customization(self):
        """Test that account ID can be customized."""
        custom_account = "999999999999"
        role_arn = MockAWSGenerator.mock_role_arn(account_id=custom_account)

        assert custom_account in role_arn
        assert "123456789012" not in role_arn
