# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from tests.mock_aws import mock_role_arn, mock_access_key_id, mock_secret_access_key
from credproxy.config import Config


class TestJSONSchemaValidation:
    """Test JSON schema validation functionality."""

    def test_valid_minimal_config(self):
        """Test validation of a valid minimal configuration."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        # Should not raise any exception
        Config.validate_schema(config_data)

    def test_valid_full_config(self):
        """Test validation of a valid full configuration."""
        mock_access_key_1 = mock_access_key_id()
        mock_secret_key_1 = mock_secret_access_key()
        mock_role_1 = mock_role_arn()
        mock_role_2 = mock_role_arn()

        config_data = {
            "server": {"host": "127.0.0.1", "port": 8080, "debug": True},
            "credentials": {
                "refresh_buffer_seconds": 600,
                "retry_delay": 30,
                "request_timeout": 60,
            },
            "aws_defaults": {
                "region": "us-east-1",
                "iam_profile": {"profile_name": "default-profile"},
            },
            "services": {
                "service1": {
                    "auth_token": "token1",
                    "source_credentials": {
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key_1,
                            "aws_secret_access_key": mock_secret_key_1,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role_1,
                        "RoleSessionName": "service1-session",
                    },
                },
                "service2": {
                    "auth_token": "token2",
                    "source_credentials": {
                        "region": "eu-west-1",
                        "iam_profile": {"profile_name": "my-profile"},
                    },
                    "assumed_role": {
                        "RoleArn": mock_role_2,
                        "RoleSessionName": "service2-session",
                    },
                },
            },
        }

        # Should not raise any exception
        Config.validate_schema(config_data)

    def test_invalid_missing_services(self):
        """Test validation fails when services are missing."""
        config_data = {"server": {"host": "0.0.0.0"}}

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_service_missing_auth_token(self):
        """Test validation fails when service is missing auth_token."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_service_missing_source_credentials(self):
        """Test validation fails when service is missing source_credentials config."""
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_aws_role_arn(self):
        """Test validation fails with invalid role ARN."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": "invalid-arn-format",  # Invalid ARN format
                        "DurationSeconds": 3600,
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_aws_region(self):
        """Test validation fails with invalid region."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "Invalid-Region",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_iam_keys_missing_required(self):
        """Test validation fails when IAM keys missing required fields."""
        mock_access_key = mock_access_key_id()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key
                            # Missing aws_secret_access_key
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_iam_profile_missing_required(self):
        """Test validation fails when IAM profile missing required fields."""
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_profile": {
                            # Missing profile_name
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_server_port_range(self):
        """Test validation fails with invalid server port."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "server": {"port": 70000},  # Invalid port number
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            },
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_service_name_pattern(self):
        """Test validation fails with invalid service name."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "invalid service name!": {  # Invalid characters
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_additional_properties(self):
        """Test validation fails with additional properties."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                        "invalid_property": "should not be allowed",
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_iam_keys_missing_section(self):
        """Test validation fails when iam_keys specified but missing required fields."""
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            # Missing both access_key_id and secret_access_key
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_invalid_iam_profile_missing_section(self):
        """Test validation fails when iam_profile specified but missing fields."""
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_profile": {
                            # Missing profile_name
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.validate_schema(config_data)

    def test_schema_file_missing(self):
        """Test behavior when schema file is missing - should skip validation
        gracefully."""

        # Get the original schema path
        original_schema_path = (
            Path(__file__).parent.parent / "credproxy" / "config-schema.json"
        )

        # Create a temporary backup and remove the original
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_backup = temp_file.name

        try:
            # Backup the original schema file
            if original_schema_path.exists():
                shutil.copy2(original_schema_path, temp_backup)
                original_schema_path.unlink()

            # Test that validation is skipped when schema file is missing
            # This should not raise any exception
            invalid_config_data = {
                "services": {
                    "test-service": {
                        # Missing auth_token and aws - would normally fail schema
                        # validation
                        "invalid": "config"
                    }
                }
            }

            # Should not raise any exception when schema file is missing
            Config.validate_schema(invalid_config_data)

        finally:
            # Restore the original schema file
            if original_schema_path.exists():
                original_schema_path.unlink()
            if Path(temp_backup).exists():
                shutil.copy2(temp_backup, original_schema_path)
            Path(temp_backup).unlink(missing_ok=True)

    def test_valid_assumed_role_with_all_new_properties(self):
        """Test validation of assumed_role with all new boto3-aligned properties."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()
        mock_policy_arn_1 = f"arn:aws:iam::{mock_role.split(':')[4]}:policy/TestPolicy1"
        mock_policy_arn_2 = f"arn:aws:iam::{mock_role.split(':')[4]}:policy/TestPolicy2"

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                        "ExternalId": "test-external-id",
                        "DurationSeconds": 7200,
                        "PolicyArns": [
                            {"arn": mock_policy_arn_1},
                            {"arn": mock_policy_arn_2},
                        ],
                        "Policy": (
                            '{"Version": "2012-10-17","Statement": '
                            '[{"Effect": "Allow","Action": "s3:GetObject",'
                            '"Resource": "*"}]}'
                        ),
                        "Tags": [
                            {"Key": "Environment", "Value": "test"},
                            {"Key": "Application", "Value": "credproxy"},
                        ],
                        "TransitiveTagKeys": ["Environment", "Application"],
                        "SerialNumber": "GAHT12345678",
                        "TokenCode": "123456",
                        "SourceIdentity": "test-source-identity",
                    },
                }
            }
        }

        # Should not raise any exception
        Config.validate_schema(config_data)

    def test_valid_assumed_role_DurationSeconds(self):
        """Test validation of DurationSeconds with valid values."""
        valid_durations = [900, 3600, 7200, 43200]  # Min, default, 2 hours, max

        for duration in valid_durations:
            mock_access_key = mock_access_key_id()
            mock_secret_key = mock_secret_access_key()
            mock_role = mock_role_arn()

            config_data = {
                "services": {
                    "test-service": {
                        "auth_token": "test-token",
                        "source_credentials": {
                            "region": "us-east-1",
                            "iam_keys": {
                                "aws_access_key_id": mock_access_key,
                                "aws_secret_access_key": mock_secret_key,
                            },
                        },
                        "assumed_role": {
                            "RoleArn": mock_role,
                            "DurationSeconds": duration,
                        },
                    }
                }
            }

            # Should not raise any exception
            Config.validate_schema(config_data)

    def test_invalid_assumed_role_DurationSeconds(self):
        """Test validation fails with invalid DurationSeconds values."""
        invalid_durations = [899, 43201]  # Below min, above max

        for duration in invalid_durations:
            mock_access_key = mock_access_key_id()
            mock_secret_key = mock_secret_access_key()
            mock_role = mock_role_arn()

            config_data = {
                "services": {
                    "test-service": {
                        "auth_token": "test-token",
                        "source_credentials": {
                            "region": "us-east-1",
                            "iam_keys": {
                                "aws_access_key_id": mock_access_key,
                                "aws_secret_access_key": mock_secret_key,
                            },
                        },
                        "assumed_role": {
                            "RoleArn": mock_role,
                            "DurationSeconds": duration,
                        },
                    }
                }
            }

            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config.validate_schema(config_data)

    def test_valid_assumed_role_policy_arns(self):
        """Test validation of policy_arns with valid format."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()
        mock_policy_arn_1 = f"arn:aws:iam::{mock_role.split(':')[4]}:policy/TestPolicy1"
        mock_policy_arn_2 = f"arn:aws:iam::{mock_role.split(':')[4]}:policy/TestPolicy2"

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "PolicyArns": [
                            {"arn": mock_policy_arn_1},
                            {"arn": mock_policy_arn_2},
                        ],
                    },
                }
            }
        }

        # Should not raise any exception
        Config.validate_schema(config_data)

    def test_valid_assumed_role_tags(self):
        """Test validation of tags with valid format."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "Tags": [
                            {"Key": "Environment", "Value": "production"},
                            {"Key": "Application", "Value": "my-app"},
                            {"Key": "Team", "Value": "platform"},
                        ],
                    },
                }
            }
        }

        # Should not raise any exception
        Config.validate_schema(config_data)

    def test_valid_assumed_role_mfa_properties(self):
        """Test validation of MFA-related properties."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()
        mock_mfa_arn = f"arn:aws:iam::{mock_role.split(':')[4]}:mfa/user"

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "SerialNumber": mock_mfa_arn,
                        "TokenCode": "123456",
                    },
                }
            }
        }

        # Should not raise any exception
        Config.validate_schema(config_data)

    def test_valid_assumed_role_source_identity(self):
        """Test validation of source_identity property."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "SourceIdentity": "my-app-user",
                    },
                }
            }
        }

        # Should not raise any exception
        Config.validate_schema(config_data)

    def test_backward_compatibility_assumed_role(self):
        """Test that existing configurations without new properties still work."""
        mock_access_key = mock_access_key_id()
        mock_secret_key = mock_secret_access_key()
        mock_role = mock_role_arn()

        config_data = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "region": "us-east-1",
                        "iam_keys": {
                            "aws_access_key_id": mock_access_key,
                            "aws_secret_access_key": mock_secret_key,
                        },
                    },
                    "assumed_role": {
                        "RoleArn": mock_role,
                        "RoleSessionName": "test-session",
                        "ExternalId": "test-external-id",
                    },
                }
            }
        }

        # Should not raise any exception - backward compatibility maintained
        Config.validate_schema(config_data)
