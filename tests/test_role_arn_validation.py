"""Unit tests for AWS IAM Role ARN validation."""

import pytest
import jsonschema

from credproxy.config import Config


class TestRoleARNValidation:
    """Test AWS IAM Role ARN validation against the JSON schema."""

    def get_schema(self):
        """Load the JSON schema for validation."""
        import json
        from pathlib import Path

        schema_path = Path(__file__).parent.parent / "credproxy" / "config-schema.json"
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)

    def test_valid_role_arns(self):
        """Test that valid role ARNs pass validation."""
        schema = self.get_schema()

        valid_arns = [
            # Basic role ARN
            "arn:aws:iam::123456789012:role/MyRole",
            # Role with path
            "arn:aws:iam::123456789012:role/credproxy/credproxy-role",
            # Role with nested path
            "arn:aws:iam::123456789012:role/application/component/RDSAccess",
            # Role with service path
            "arn:aws:iam::123456789012:role/service-role/QuickSightAction",
            # Role with AWS service path
            "arn:aws:iam::123456789012:role/aws-service-role/"
            "access-analyzer.amazonaws.com/AWSServiceRoleForAccessAnalyzer",
            # Role with various allowed characters
            "arn:aws:iam::123456789012:role/My-Role_Name@service",
            "arn:aws:iam::123456789012:role/MyRole+Test",
            "arn:aws:iam::123456789012:role/MyRole=Test",
            "arn:aws:iam::123456789012:role/MyRole.Test",
            # Complex path with multiple levels
            "arn:aws:iam::123456789012:role/division_abc/subdivision_xyz/product_1234/"
            "engineering/RoleName",
        ]

        for arn in valid_arns:
            config_data = {
                "services": {
                    "test-service": {
                        "auth_token": "test-token",
                        "source_credentials": {
                            "iam_profile": {"profile_name": "default"},
                            "region": "us-east-1",
                        },
                        "assumed_role": {
                            "RoleArn": arn,
                            "RoleSessionName": "test-session",
                        },
                    }
                }
            }

            # Should not raise any exception
            jsonschema.validate(config_data, schema)

    def test_invalid_role_arns(self):
        """Test that invalid role ARNs fail validation."""
        schema = self.get_schema()

        invalid_arns = [
            # Wrong partition
            "arn:aws-cn:iam::123456789012:role/MyRole",
            # Wrong service
            "arn:aws:s3::123456789012:role/MyRole",
            # Region specified (should be empty for IAM)
            "arn:aws:iam::us-east-1:123456789012:role/MyRole",
            # Invalid account ID (not 12 digits)
            "arn:aws:iam::12345678901:role/MyRole",
            "arn:aws:iam::1234567890123:role/MyRole",
            # Wrong resource type
            "arn:aws:iam::123456789012:user/MyRole",
            "arn:aws:iam::123456789012:group/MyRole",
            # Missing role prefix
            "arn:aws:iam::123456789012:MyRole",
            # Invalid characters in role name
            "arn:aws:iam::123456789012:role/My Role",  # space
            "arn:aws:iam::123456789012:role/My#Role",  # hash
            "arn:aws:iam::123456789012:role/My%Role",  # percent
            "arn:aws:iam::123456789012:role/My&Role",  # ampersand
            "arn:aws:iam::123456789012:role/My(Role",  # parentheses
            # Empty role name
            "arn:aws:iam::123456789012:role/",
            # Trailing slash
            "arn:aws:iam::123456789012:role/MyRole/",
        ]

        for arn in invalid_arns:
            config_data = {
                "services": {
                    "test-service": {
                        "auth_token": "test-token",
                        "source_credentials": {
                            "iam_profile": {"profile_name": "default"},
                            "region": "us-east-1",
                        },
                        "assumed_role": {
                            "RoleArn": arn,
                            "RoleSessionName": "test-session",
                        },
                    }
                }
            }

            # Should raise jsonschema.ValidationError
            with pytest.raises(jsonschema.ValidationError, match="RoleArn"):
                jsonschema.validate(config_data, schema)

    def test_config_from_dict_with_valid_arn(self):
        """Test Config.from_dict with valid role ARNs."""
        valid_configs = [
            {
                "services": {
                    "test-service": {
                        "auth_token": "test-token",
                        "source_credentials": {
                            "iam_profile": {"profile_name": "default"},
                            "region": "us-east-1",
                        },
                        "assumed_role": {
                            "RoleArn": "arn:aws:iam::123456789012:role/MyRole",
                            "RoleSessionName": "test-session",
                        },
                    }
                }
            },
            {
                "services": {
                    "test-service": {
                        "auth_token": "test-token",
                        "source_credentials": {
                            "iam_profile": {"profile_name": "default"},
                            "region": "us-east-1",
                        },
                        "assumed_role": {
                            "RoleArn": (
                                "arn:aws:iam::123456789012:role/"
                                "credproxy/credproxy-role"
                            ),
                            "RoleSessionName": "test-session",
                        },
                    }
                }
            },
        ]

        for config_data in valid_configs:
            # Should not raise any exception
            config = Config.from_dict(config_data)
            assert (
                config.services["test-service"].assumed_role.RoleArn
                == config_data["services"]["test-service"]["assumed_role"]["RoleArn"]
            )

    def test_config_from_dict_with_invalid_arn(self):
        """Test Config.from_dict with invalid role ARNs."""
        invalid_config = {
            "services": {
                "test-service": {
                    "auth_token": "test-token",
                    "source_credentials": {
                        "iam_profile": {"profile_name": "default"},
                        "region": "us-east-1",
                    },
                    "assumed_role": {
                        "RoleArn": (
                            "arn:aws:iam::123456789012:role/Invalid Role"
                        ),  # space in name
                        "RoleSessionName": "test-session",
                    },
                }
            }
        }

        # Should raise ValueError due to schema validation failure
        with pytest.raises(ValueError, match="Configuration validation failed"):
            Config.from_dict(invalid_config)

    def test_real_world_examples(self):
        """Test real-world role ARN examples from AWS documentation."""
        schema = self.get_schema()

        real_world_arns = [
            # From AWS docs examples
            "arn:aws:iam::123456789012:role/S3Access",
            "arn:aws:iam::123456789012:role/application_abc/component_xyz/RDSAccess",
            (
                "arn:aws:iam::123456789012:role/aws-service-role/"
                "access-analyzer.amazonaws.com/AWSServiceRoleForAccessAnalyzer"
            ),
            "arn:aws:iam::123456789012:role/service-role/QuickSightAction",
            # CloudFormation generated roles
            "arn:aws:iam::123456789012:role/credproxy/credproxy-role",
            "arn:aws:iam::123456789012:role/my-app/lambda-execution-role",
            "arn:aws:iam::123456789012:role/ecs-task-role/MyService",
        ]

        for arn in real_world_arns:
            config_data = {
                "services": {
                    "test-service": {
                        "auth_token": "test-token",
                        "source_credentials": {
                            "iam_profile": {"profile_name": "default"},
                            "region": "us-east-1",
                        },
                        "assumed_role": {
                            "RoleArn": arn,
                            "RoleSessionName": "test-session",
                        },
                    }
                }
            }

            # Should not raise any exception
            jsonschema.validate(config_data, schema)
