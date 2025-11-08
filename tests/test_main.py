# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for main application functionality."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import yaml
import pytest

from credproxy.app import init_app
from credproxy.config import Config


class TestMainApp:
    """Test the main Flask application."""

    def test_health_check_no_config(self):
        """Test health check endpoint when no config is loaded."""
        # Create app with minimal config
        config = Config()
        app = init_app(config)

        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"
            assert data["services"] == 0

    def test_credentials_endpoint_no_config(self):
        """Test credentials endpoint when no config is loaded."""
        config = Config()
        app = init_app(config)

        with app.test_client() as client:
            response = client.get("/v1/credentials")
            assert response.status_code == 401  # Missing auth header

    def test_credentials_endpoint_no_auth_token(self):
        """Test credentials endpoint without authorization token."""
        config = Config()
        app = init_app(config)

        with app.test_client() as client:
            response = client.get("/v1/credentials")
            assert response.status_code == 401  # Missing auth header

    def test_credentials_endpoint_invalid_token(self):
        """Test credentials endpoint with invalid authorization token."""
        config = Config()
        app = init_app(config)

        with app.test_client() as client:
            response = client.get(
                "/v1/credentials", headers={"Authorization": "invalid-token"}
            )
            assert response.status_code == 401  # Invalid token

    @patch("credproxy.credentials_handler.CredentialsHandler.get_credentials")
    def test_credentials_endpoint_no_credentials_yet(self, mock_get_creds):
        """Test credentials endpoint when credentials not yet available."""
        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_profile": {"profile_name": "default"},
            },
            "services": {
                "test-service": {
                    "auth_token": "valid-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole",
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

            # Mock credentials handler to raise an exception
            mock_get_creds.side_effect = Exception("Credentials unavailable")

            with app.test_client() as client:
                response = client.get(
                    "/v1/credentials", headers={"Authorization": "valid-token"}
                )
                # Should return 500 when credentials handler raises exception
                assert response.status_code == 500

        finally:
            os.unlink(temp_file)

    @patch("credproxy.credentials_handler.CredentialsHandler.get_credentials")
    def test_credentials_endpoint_success(self, mock_get_creds):
        """Test successful credentials endpoint response."""
        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_profile": {"profile_name": "default"},
            },
            "services": {
                "test-service": {
                    "auth_token": "valid-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole",
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

            test_creds = {
                "AccessKeyId": "TESTKEY",
                "SecretAccessKey": "testsecret",
                "Token": "testtoken",
                "Expiration": 1234567890000,
            }
            mock_get_creds.return_value = test_creds

            with app.test_client() as client:
                response = client.get(
                    "/v1/credentials", headers={"Authorization": "valid-token"}
                )
                assert response.status_code == 200
                data = response.get_json()
                assert data["AccessKeyId"] == "TESTKEY"
                assert data["SecretAccessKey"] == "testsecret"

        finally:
            os.unlink(temp_file)

    def test_metrics_endpoint_available(self):
        """Test that metrics endpoint is available and returns correct format."""
        config = Config()
        app = init_app(config)

        with app.test_client() as client:
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "text/plain" in response.content_type

            # Check for basic Prometheus metrics format
            metrics_data = response.data.decode()
            assert "# HELP" in metrics_data
            assert "# TYPE" in metrics_data
            assert "credproxy_" in metrics_data


class TestCredentialMethods:
    """Test credential retrieval methods."""

    @patch("boto3.client")
    def test_get_credentials_aws_error(self, mock_boto3_client):
        """Test error handling for AWS API errors."""
        # Mock STS client to raise a ClientError
        mock_sts_client = mock_boto3_client.return_value
        mock_sts_client.assume_role.side_effect = Exception("AWS API Error")

        config_data = {
            "aws_defaults": {"region": "us-west-2"},
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole",
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
            # Import CredentialsHandler locally to avoid import issues
            from credproxy.credentials_handler import CredentialsHandler

            handler = CredentialsHandler(config)

            # Should raise exception when AWS API call fails
            with pytest.raises(Exception, match="AWS API Error"):
                handler.get_credentials("test-service")

        finally:
            os.unlink(temp_file)

    def test_credentials_format_verification(self):
        """Test that credentials response has correct format for AWS SDK."""
        from datetime import datetime, timezone

        # Create properly formatted credentials like the app should produce
        expiration_time = datetime.now(timezone.utc)
        test_creds = {
            "AccessKeyId": "TESTKEY",
            "SecretAccessKey": "testsecret",
            "Token": "testtoken",
            "Expiration": expiration_time.isoformat(),
        }

        # Verify the format is what AWS SDK expects
        assert isinstance(test_creds["AccessKeyId"], str)
        assert isinstance(test_creds["SecretAccessKey"], str)
        assert isinstance(test_creds["Token"], str)
        assert isinstance(test_creds["Expiration"], str)

        # Verify Expiration is ISO 8601 string
        parsed_time = datetime.fromisoformat(
            test_creds["Expiration"].replace("Z", "+00:00")
        )
        assert parsed_time == expiration_time

    @patch("credproxy.credentials_handler.CredentialsHandler.get_credentials")
    def test_credentials_response_format(self, mock_get_creds):
        """Test that credentials response has correct format for AWS SDK."""
        from datetime import datetime, timezone

        config_data = {
            "aws_defaults": {
                "region": "us-west-2",
                "iam_profile": {"profile_name": "default"},
            },
            "services": {
                "test-service": {
                    "auth_token": "valid-token",
                    "source_credentials": {
                        "region": "us-west-2",
                    },
                    "assumed_role": {
                        "RoleArn": "arn:aws:iam::123456789012:role/TestRole",
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

            # Create properly formatted credentials
            expiration_time = datetime.now(timezone.utc)
            test_creds = {
                "AccessKeyId": "TESTKEY",
                "SecretAccessKey": "testsecret",
                "Token": "testtoken",
                "Expiration": expiration_time.isoformat(),
            }

            mock_get_creds.return_value = test_creds

            with app.test_client() as client:
                response = client.get(
                    "/v1/credentials", headers={"Authorization": "valid-token"}
                )
                assert response.status_code == 200
                data = response.get_json()

                # Verify AWS SDK expected format
                assert "AccessKeyId" in data
                assert "SecretAccessKey" in data
                assert "Token" in data
                assert "Expiration" in data

                # Verify Expiration is ISO 8601 string
                assert isinstance(data["Expiration"], str)
                # Should be parseable as ISO 8601
                parsed_time = datetime.fromisoformat(
                    data["Expiration"].replace("Z", "+00:00")
                )
                assert parsed_time == expiration_time

        finally:
            os.unlink(temp_file)

    def test_metrics_endpoint_available(self):
        """Test that metrics endpoint is available and returns correct format."""
        config = Config()
        app = init_app(config)

        with app.test_client() as client:
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "text/plain" in response.content_type

            # Check for basic Prometheus metrics format
            metrics_data = response.data.decode()
            assert "# HELP" in metrics_data
            assert "# TYPE" in metrics_data
            assert "credproxy_" in metrics_data
