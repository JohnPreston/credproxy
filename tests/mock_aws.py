#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""Mock AWS credential generation utilities for testing."""

from __future__ import annotations

import random
import string
from typing import Any


class MockAWSGenerator:
    """Generate mock AWS credentials and identifiers for testing."""

    # Standard mock AWS account ID
    MOCK_ACCOUNT_ID = "123456789012"

    @classmethod
    def mock_access_key_id(cls) -> str:
        """Generate a mock AWS Access Key ID.

        Returns:
            Mock access key ID in AKIA... format (20 characters)
        """
        # AWS Access Key IDs start with AKIA followed by 16 alphanumeric characters
        prefix = "AKIA"
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
        return f"{prefix}{suffix}"

    @classmethod
    def mock_secret_access_key(cls) -> str:
        """Generate a mock AWS Secret Access Key.

        Returns:
            Mock secret access key (40 characters)
        """
        # Generate a realistic-looking secret key
        chars = string.ascii_letters + string.digits + "/+"
        return "".join(random.choices(chars, k=40))

    @classmethod
    def mock_session_token(cls) -> str:
        """Generate a mock AWS Session Token.

        Returns:
            Mock session token (longer string, typically 350+ characters)
        """
        # Generate a realistic-looking session token
        chars = string.ascii_letters + string.digits + "/+="
        return "".join(random.choices(chars, k=356))

    @classmethod
    def mock_role_arn(
        cls,
        role_name: str | None = None,
        path: str | None = None,
        account_id: str | None = None,
    ) -> str:
        """Generate a mock IAM Role ARN.

        Args:
            role_name: Optional role name. If None, generates a random one.
            path: Optional path prefix. If None, uses a realistic path.
            account_id: Optional account ID. If None, uses mock account ID.

        Returns:
            Mock IAM Role ARN in format:
            arn:aws:iam::123456789012:role/path/to/role-name
        """
        if account_id is None:
            account_id = cls.MOCK_ACCOUNT_ID

        if role_name is None:
            # Generate a realistic role name
            role_names = [
                "web-server-role",
                "lambda-execution-role",
                "api-processor-role",
                "batch-job-role",
                "ecs-task-role",
                "rds-access-role",
                "s3-access-role",
                "cloudwatch-logs-role",
            ]
            role_name = random.choice(role_names)

        if path is None:
            # Generate a realistic path
            paths = [
                "applications",
                "services/lambda",
                "infrastructure",
                "data-processing",
                "web-tier",
                "backend-services",
                "monitoring",
                "storage",
            ]
            path = random.choice(paths)

        # Ensure path starts with / but doesn't end with /
        if not path.startswith("/"):
            path = f"/{path}"
        if path.endswith("/"):
            path = path.rstrip("/")

        return f"arn:aws:iam::{account_id}:role{path}/{role_name}"

    @classmethod
    def mock_user_arn(
        cls,
        username: str | None = None,
        path: str | None = None,
        account_id: str | None = None,
    ) -> str:
        """Generate a mock IAM User ARN.

        Args:
            username: Optional username. If None, generates a random one.
            path: Optional path prefix. If None, uses a realistic path.
            account_id: Optional account ID. If None, uses mock account ID.

        Returns:
            Mock IAM User ARN in format: arn:aws:iam::123456789012:user/path/to/username
        """
        if account_id is None:
            account_id = cls.MOCK_ACCOUNT_ID

        if username is None:
            # Generate a realistic username
            usernames = [
                "admin-user",
                "service-account",
                "application-user",
                "readonly-user",
                "backup-user",
                "monitoring-user",
            ]
            username = random.choice(usernames)

        if path is None:
            path = "/users"

        # Ensure path starts with / but doesn't end with /
        if not path.startswith("/"):
            path = f"/{path}"
        if path.endswith("/"):
            path = path.rstrip("/")

        return f"arn:aws:iam::{account_id}:user{path}/{username}"

    @classmethod
    def mock_policy_arn(
        cls,
        policy_name: str | None = None,
        path: str | None = None,
        account_id: str | None = None,
    ) -> str:
        """Generate a mock IAM Policy ARN.

        Args:
            policy_name: Optional policy name. If None, generates a random one.
            path: Optional path prefix. If None, uses a realistic path.
            account_id: Optional account ID. If None, uses mock account ID.

        Returns:
            Mock IAM Policy ARN in format:
            arn:aws:iam::123456789012:policy/path/to/policy-name
        """
        if account_id is None:
            account_id = cls.MOCK_ACCOUNT_ID

        if policy_name is None:
            # Generate a realistic policy name
            policy_names = [
                "s3-read-only-policy",
                "lambda-execution-policy",
                "ec2-full-access-policy",
                "rds-access-policy",
                "cloudwatch-logs-policy",
                "dynamodb-access-policy",
                "sns-publish-policy",
                "sqs-access-policy",
            ]
            policy_name = random.choice(policy_names)

        if path is None:
            path = "/policies"

        # Ensure path starts with / but doesn't end with /
        if not path.startswith("/"):
            path = f"/{path}"
        if path.endswith("/"):
            path = path.rstrip("/")

        return f"arn:aws:iam::{account_id}:policy{path}/{policy_name}"

    @classmethod
    def mock_aws_credentials(cls) -> dict[str, Any]:
        """Generate a complete set of mock AWS credentials.

        Returns:
            Dictionary containing mock AWS credentials
        """
        return {
            "aws_access_key_id": cls.mock_access_key_id(),
            "aws_secret_access_key": cls.mock_secret_access_key(),
            "aws_session_token": cls.mock_session_token(),
        }

    @classmethod
    def mock_role_config(
        cls,
        role_name: str | None = None,
        path: str | None = None,
        external_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a mock IAM role configuration.

        Args:
            role_name: Optional role name
            path: Optional path prefix
            external_id: Optional external ID. If None, generates a random one.

        Returns:
            Dictionary containing mock role configuration
        """
        if external_id is None:
            # Generate a realistic external ID
            chars = string.ascii_letters + string.digits + "-_@"
            external_id = "".join(random.choices(chars, k=32))

        return {
            "RoleArn": cls.mock_role_arn(role_name, path),
            "RoleSessionName": f"test-session-{random.randint(1000, 9999)}",
            "ExternalId": external_id,
        }

    @classmethod
    def generate_test_config(cls) -> dict[str, Any]:
        """Generate a complete test configuration with mock AWS credentials.

        Returns:
            Dictionary containing a complete test configuration
        """
        return {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_keys": cls.mock_aws_credentials(),
            },
            "services": {
                "test-service": {
                    "auth_token": "test-auth-token-12345",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": cls.mock_aws_credentials(),
                    },
                    "assumed_role": cls.mock_role_config(),
                }
            },
        }


# Convenience functions for direct import
def mock_access_key_id() -> str:
    """Generate a mock AWS Access Key ID."""
    return MockAWSGenerator.mock_access_key_id()


def mock_secret_access_key() -> str:
    """Generate a mock AWS Secret Access Key."""
    return MockAWSGenerator.mock_secret_access_key()


def mock_role_arn(role_name: str | None = None, path: str | None = None) -> str:
    """Generate a mock IAM Role ARN."""
    return MockAWSGenerator.mock_role_arn(role_name, path)


def mock_aws_credentials() -> dict[str, Any]:
    """Generate a complete set of mock AWS credentials."""
    return MockAWSGenerator.mock_aws_credentials()


def mock_role_config(
    role_name: str | None = None, path: str | None = None
) -> dict[str, Any]:
    """Generate a mock IAM role configuration."""
    return MockAWSGenerator.mock_role_config(role_name, path)


def mock_policy_arn(policy_name: str | None = None, path: str | None = None) -> str:
    """Generate a mock IAM Policy ARN."""
    return MockAWSGenerator.mock_policy_arn(policy_name, path)


def mock_external_id() -> str:
    """Generate a mock AWS External ID."""
    import random
    import string

    chars = string.ascii_letters + string.digits + "-_@"
    return "".join(random.choices(chars, k=32))
