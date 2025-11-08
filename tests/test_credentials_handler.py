# This Source Code Form is subject to terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for credentials handler functionality."""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from credproxy.credentials_handler import CredentialsHandler, ServiceCredentialsManager


class TestServiceCredentialsManager:
    """Test ServiceCredentialsManager class."""

    def test_is_expired_false(self):
        """Test is_expired returns False when not expired."""
        future_time = time.time() + 3600  # 1 hour from now
        manager = ServiceCredentialsManager(
            aws_access_key_id="test",
            aws_secret_access_key="test",
            session_token="test",
            expiry=future_time,
        )
        assert manager.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired returns True when expired."""
        past_time = time.time() - 3600  # 1 hour ago
        manager = ServiceCredentialsManager(
            aws_access_key_id="test",
            aws_secret_access_key="test",
            session_token="test",
            expiry=past_time,
        )
        assert manager.is_expired() is True

    def test_to_dict(self):
        """Test to_dict conversion."""
        expiry_time = time.time() + 3600
        manager = ServiceCredentialsManager(
            aws_access_key_id="TESTKEY",
            aws_secret_access_key="testsecret",
            session_token="testtoken",
            expiry=expiry_time,
        )

        result = manager.to_dict()

        assert result["AccessKeyId"] == "TESTKEY"
        assert result["SecretAccessKey"] == "testsecret"
        assert result["Token"] == "testtoken"
        assert "Expiration" in result


class TestCredentialsHandler:
    """Test CredentialsHandler class."""

    def test_init_with_config(self):
        """Test CredentialsHandler initialization with config."""
        mock_config = MagicMock()
        mock_config.services = {}

        handler = CredentialsHandler(mock_config)

        assert handler.config == mock_config
        assert handler.cache == {}

    def test_cleanup_empty_cache(self):
        """Test cleanup with empty cache."""
        mock_config = MagicMock()
        handler = CredentialsHandler(mock_config)

        handler.cleanup()
        # Should not raise any exception

    def test_cleanup_with_cache(self):
        """Test cleanup with cached credentials."""
        mock_config = MagicMock()
        handler = CredentialsHandler(mock_config)

        # Add some cached credentials
        mock_creds = MagicMock()
        handler.cache["service1"] = mock_creds

        handler.cleanup()
        assert handler.cache == {}

    def test_get_credentials_cache_hit(self):
        """Test getting credentials from cache."""
        mock_config = MagicMock()
        mock_config.services = {"test-service": MagicMock()}

        handler = CredentialsHandler(mock_config)

        # Add non-expired cached credentials
        future_time = time.time() + 3600
        cached_creds = ServiceCredentialsManager(
            aws_access_key_id="CACHEDKEY",
            aws_secret_access_key="cachedsecret",
            session_token="cachedtoken",
            expiry=future_time,
        )
        handler.cache["test-service"] = cached_creds

        result = handler.get_credentials("test-service")

        assert result["AccessKeyId"] == "CACHEDKEY"
        assert result["SecretAccessKey"] == "cachedsecret"
        assert result["Token"] == "cachedtoken"

    def test_get_credentials_cache_miss(self):
        """Test getting credentials when cache miss."""
        from credproxy.config import (
            AssumedRoleConfig,
            IAMProfileAuthConfig,
            SourceCredentialsConfig,
        )

        mock_service = MagicMock()
        mock_service.assumed_role = AssumedRoleConfig(
            RoleArn="arn:aws:iam::123456789012:role/TestRole",
            RoleSessionName="test-session",
        )
        mock_service.source_credentials = SourceCredentialsConfig(
            region="us-west-2",
            iam_profile=IAMProfileAuthConfig(profile_name="test-profile"),
        )

        mock_config = MagicMock()
        mock_config.services = {"test-service": mock_service}
        mock_config.aws_defaults = MagicMock()
        mock_config.aws_defaults.iam_profile = None

        handler = CredentialsHandler(mock_config)

        with patch("boto3.Session") as mock_session:
            mock_boto_session = MagicMock()
            mock_session.return_value = mock_boto_session

            mock_sts_client = MagicMock()
            mock_sts_client.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "NEWKEY",
                    "SecretAccessKey": "newsecret",
                    "SessionToken": "newtoken",
                    "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            }
            mock_boto_session.client.return_value = mock_sts_client

            result = handler.get_credentials("test-service")

            assert result["AccessKeyId"] == "NEWKEY"
            assert result["SecretAccessKey"] == "newsecret"
            assert result["Token"] == "newtoken"

    def test_get_credentials_expired_cache(self):
        """Test getting credentials when cached credentials are expired."""
        from credproxy.config import (
            AssumedRoleConfig,
            IAMKeysAuthConfig,
            SourceCredentialsConfig,
        )

        mock_service = MagicMock()
        mock_service.assumed_role = AssumedRoleConfig(
            RoleArn="arn:aws:iam::123456789012:role/TestRole",
            RoleSessionName="test-session",
        )
        mock_service.source_credentials = SourceCredentialsConfig(
            region="us-west-2",
            iam_keys=IAMKeysAuthConfig(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            ),
        )

        mock_config = MagicMock()
        mock_config.services = {"test-service": mock_service}
        mock_config.aws_defaults = None

        handler = CredentialsHandler(mock_config)

        # Add expired cached credentials
        past_time = time.time() - 3600
        expired_creds = ServiceCredentialsManager(
            aws_access_key_id="EXPIREDKEY",
            aws_secret_access_key="expiredsecret",
            session_token="expiredtoken",
            expiry=past_time,
        )
        handler.cache["test-service"] = expired_creds

        with patch("boto3.client") as mock_client:
            mock_sts_client = MagicMock()
            mock_sts_client.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "NEWKEY",
                    "SecretAccessKey": "newsecret",
                    "SessionToken": "newtoken",
                    "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            }
            mock_client.return_value = mock_sts_client

            result = handler.get_credentials("test-service")

            assert result["AccessKeyId"] == "NEWKEY"
            assert result["SecretAccessKey"] == "newsecret"
            assert result["Token"] == "newtoken"

    def test_assume_role_client_error(self):
        """Test _assume_role with ClientError."""
        from credproxy.config import (
            AssumedRoleConfig,
            IAMKeysAuthConfig,
            SourceCredentialsConfig,
        )

        mock_service = MagicMock()
        mock_service.assumed_role = AssumedRoleConfig(
            RoleArn="arn:aws:iam::123456789012:role/TestRole",
            RoleSessionName="test-session",
        )
        mock_service.source_credentials = SourceCredentialsConfig(
            region="us-west-2",
            iam_keys=IAMKeysAuthConfig(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            ),
        )

        mock_config = MagicMock()
        mock_config.services = {"test-service": mock_service}
        mock_config.aws_defaults = None

        handler = CredentialsHandler(mock_config)

        with patch("boto3.client") as mock_client:
            mock_sts_client = MagicMock()
            from botocore.exceptions import ClientError

            mock_sts_client.assume_role.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "AssumeRole",
            )
            mock_client.return_value = mock_sts_client

            with pytest.raises(ClientError):
                handler._assume_role(mock_service)

    def test_assume_role_with_external_id(self):
        """Test _assume_role with external_id."""
        from credproxy.config import (
            AssumedRoleConfig,
            IAMKeysAuthConfig,
            SourceCredentialsConfig,
        )

        mock_service = MagicMock()
        mock_service.assumed_role = AssumedRoleConfig(
            RoleArn="arn:aws:iam::123456789012:role/TestRole",
            RoleSessionName="test-session",
            ExternalId="test-external-id",
        )
        mock_service.source_credentials = SourceCredentialsConfig(
            region="us-west-2",
            iam_keys=IAMKeysAuthConfig(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            ),
        )

        mock_config = MagicMock()
        mock_config.services = {"test-service": mock_service}
        mock_config.aws_defaults = None

        handler = CredentialsHandler(mock_config)

        with patch("boto3.client") as mock_client:
            mock_sts_client = MagicMock()
            mock_sts_client.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "NEWKEY",
                    "SecretAccessKey": "newsecret",
                    "SessionToken": "newtoken",
                    "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            }
            mock_client.return_value = mock_sts_client

            result = handler._assume_role(mock_service)

            # Verify assume_role was called with external_id
            mock_sts_client.assume_role.assert_called_once_with(
                RoleArn="arn:aws:iam::123456789012:role/TestRole",
                RoleSessionName="test-session",
                DurationSeconds=900,  # Default value
                ExternalId="test-external-id",
            )

            assert result["AccessKeyId"] == "NEWKEY"
            assert result["SecretAccessKey"] == "newsecret"
            assert result["SessionToken"] == "newtoken"

    def test_assume_role_without_external_id(self):
        """Test _assume_role without external_id."""
        from credproxy.config import (
            AssumedRoleConfig,
            IAMKeysAuthConfig,
            SourceCredentialsConfig,
        )

        mock_service = MagicMock()
        mock_service.assumed_role = AssumedRoleConfig(
            RoleArn="arn:aws:iam::123456789012:role/TestRole",
            RoleSessionName="test-session",
        )
        mock_service.source_credentials = SourceCredentialsConfig(
            region="us-west-2",
            iam_keys=IAMKeysAuthConfig(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            ),
        )

        mock_config = MagicMock()
        mock_config.services = {"test-service": mock_service}
        mock_config.aws_defaults = None

        handler = CredentialsHandler(mock_config)

        with patch("boto3.client") as mock_client:
            mock_sts_client = MagicMock()
            mock_sts_client.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "NEWKEY",
                    "SecretAccessKey": "newsecret",
                    "SessionToken": "newtoken",
                    "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            }
            mock_client.return_value = mock_sts_client

            result = handler._assume_role(mock_service)

            # Verify assume_role was called without external_id
            mock_sts_client.assume_role.assert_called_once_with(
                RoleArn="arn:aws:iam::123456789012:role/TestRole",
                RoleSessionName="test-session",
                DurationSeconds=900,  # Default value
            )

            assert result["AccessKeyId"] == "NEWKEY"
            assert result["SecretAccessKey"] == "newsecret"
            assert result["SessionToken"] == "newtoken"

    def test_get_aws_config_iam_profile(self):
        """Test _get_aws_config with IAM profile."""
        mock_service = MagicMock()
        mock_service.source_credentials.iam_profile.profile_name = "test-profile"
        mock_service.source_credentials.region = "us-west-2"
        mock_service.source_credentials.iam_keys = None

        mock_config = MagicMock()
        mock_config.aws_defaults = MagicMock()
        mock_config.aws_defaults.iam_profile = None
        mock_config.aws_defaults.iam_keys = None

        handler = CredentialsHandler(mock_config)

        result = handler._get_aws_config(mock_service)

        expected = {"region_name": "us-west-2", "profile_name": "test-profile"}
        assert result == expected

    def test_get_aws_config_iam_keys(self):
        """Test _get_aws_config with IAM keys."""
        mock_service = MagicMock()
        mock_service.source_credentials.iam_keys.aws_access_key_id = "test-key"
        mock_service.source_credentials.iam_keys.aws_secret_access_key = "test-secret"
        mock_service.source_credentials.iam_keys.session_token = "test-token"
        mock_service.source_credentials.region = "us-west-2"
        mock_service.source_credentials.iam_profile = None

        mock_config = MagicMock()
        mock_config.aws_defaults = MagicMock()
        mock_config.aws_defaults.iam_profile = None
        mock_config.aws_defaults.iam_keys = None

        handler = CredentialsHandler(mock_config)

        result = handler._get_aws_config(mock_service)

        expected = {
            "region_name": "us-west-2",
            "aws_access_key_id": "test-key",
            "aws_secret_access_key": "test-secret",
            "aws_session_token": "test-token",
        }
        assert result == expected

    def test_get_aws_config_fallback_to_defaults(self):
        """Test _get_aws_config falls back to defaults."""
        mock_service = MagicMock()
        mock_service.source_credentials = None  # No service-specific AWS config

        mock_default_aws = MagicMock()
        mock_default_aws.iam_keys.aws_access_key_id = "default-key"
        mock_default_aws.iam_keys.aws_secret_access_key = "default-secret"
        mock_default_aws.iam_keys.session_token = None  # Explicitly set to None
        mock_default_aws.region = "us-east-1"
        mock_default_aws.iam_profile = None

        mock_config = MagicMock()
        mock_config.aws_defaults = mock_default_aws

        handler = CredentialsHandler(mock_config)

        result = handler._get_aws_config(mock_service)

        expected = {
            "region_name": "us-east-1",
            "aws_access_key_id": "default-key",
            "aws_secret_access_key": "default-secret",
        }
        assert result == expected

    def test_get_aws_config_default_auth_method(self):
        """Test _get_aws_config with default auth method."""
        mock_service = MagicMock()
        mock_service.source_credentials.iam_keys = None
        mock_service.source_credentials.iam_profile = None
        mock_service.source_credentials.region = "us-west-2"

        mock_config = MagicMock()
        mock_config.aws_defaults = None

        handler = CredentialsHandler(mock_config)

        result = handler._get_aws_config(mock_service)

        expected = {"region_name": "us-west-2"}
        assert result == expected

    def test_assume_role_with_DurationSeconds(self):
        """Test _assume_role with custom DurationSeconds."""
        from credproxy.config import (
            AssumedRoleConfig,
            IAMKeysAuthConfig,
            SourceCredentialsConfig,
        )

        mock_service = MagicMock()
        mock_service.assumed_role = AssumedRoleConfig(
            RoleArn="arn:aws:iam::123456789012:role/TestRole",
            RoleSessionName="test-session",
            DurationSeconds=1800,  # 30 minutes
        )
        mock_service.source_credentials = SourceCredentialsConfig(
            region="us-west-2",
            iam_keys=IAMKeysAuthConfig(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            ),
        )

        mock_config = MagicMock()
        mock_config.services = {"test-service": mock_service}
        mock_config.aws_defaults = None

        handler = CredentialsHandler(mock_config)

        with patch("boto3.client") as mock_client:
            mock_sts_client = MagicMock()
            mock_sts_client.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "NEWKEY",
                    "SecretAccessKey": "newsecret",
                    "SessionToken": "newtoken",
                    "Expiration": datetime.now(timezone.utc) + timedelta(minutes=30),
                }
            }
            mock_client.return_value = mock_sts_client

            result = handler._assume_role(mock_service)

            # Verify assume_role was called with custom duration
            mock_sts_client.assume_role.assert_called_once_with(
                RoleArn="arn:aws:iam::123456789012:role/TestRole",
                RoleSessionName="test-session",
                DurationSeconds=1800,
            )

            assert result["AccessKeyId"] == "NEWKEY"
            assert result["SecretAccessKey"] == "newsecret"
            assert result["SessionToken"] == "newtoken"
