#!/usr/bin/env python3
"""
CredProxy Configuration Generator

This script generates CredProxy configuration files and Docker Compose snippets
based on a deployed CloudFormation stack.
"""

import os
import sys
import argparse

import yaml
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# Constants for consistent paths and configurations
CREDPROXY_CONFIG_PATH = "/credproxy/config.yaml"
DYNAMIC_DIR_PATH = "/credproxy/dynamic"
TOKENS_DIR_PATH = "./tokens"
SCRIPTS_DIR_PATH = "./scripts"
DEFAULT_TOOLS = ["aws-cli", "python-boto3", "node-aws-sdk", "go-aws-sdk"]
DEFAULT_SDKS = ["python-boto3", "node-aws-sdk", "go-aws-sdk"]  # Actual SDKs only
CREDPROXY_PORT = 1338
CREDPROXY_HOST = "localhost"


def get_caller_identity(region=None):
    """Get AWS caller identity to auto-detect service name."""
    try:
        sts_client = boto3.client("sts", region_name=region)
        response = sts_client.get_caller_identity()

        # Extract account ID and generate service name from it
        account_id = response.get("Account", "")
        if account_id:
            # Generate a service name based on account ID
            # This ensures unique, predictable service names
            service_name = f"aws-service-{account_id[-8:]}"
            print(f"Auto-detected service name: {service_name}")
            return service_name
        else:
            raise ValueError("Could not determine AWS account ID from caller identity")

    except (ClientError, NoCredentialsError) as error:
        raise ValueError(f"Failed to get AWS caller identity: {error}")


def get_stack_outputs(stack_name, region=None):
    """Get CloudFormation stack outputs."""
    try:
        cf_client = boto3.client("cloudformation", region_name=region)
        response = cf_client.describe_stacks(StackName=stack_name)

        if not response["Stacks"]:
            raise ValueError(f"Stack {stack_name} not found")

        stack = response["Stacks"][0]
        if stack["StackStatus"] in ["DELETE_COMPLETE", "DELETE_IN_PROGRESS"]:
            raise ValueError(f"Stack {stack_name} is deleted or being deleted")

        outputs = {}
        for output in stack.get("Outputs", []):
            outputs[output["OutputKey"]] = output["OutputValue"]

        return outputs

    except ClientError as error:
        if error.response["Error"]["Code"] == "ValidationError":
            raise ValueError(f"Stack {stack_name} not found or invalid")
        raise
    except NoCredentialsError:
        raise ValueError(
            "AWS credentials not found. Please configure your AWS credentials."
        )


def generate_credproxy_config(service_names, role_arn, external_id=None, region=None):
    """Generate CredProxy configuration YAML following new schema."""
    # Handle single service name (backward compatibility) or list of service names
    if isinstance(service_names, str):
        service_names = [service_names]

    # Keep AWS-CLI in main config, SDKs go to dynamic files
    services = {}

    # Add AWS-CLI service to main config (it's a tool, not SDK)
    if "aws-cli" in service_names:
        services["aws-cli"] = {
            "auth_token": "${fromFile:/run/secrets/aws-cli-token}",
            "source_credentials": {},
            "assumed_role": {
                "RoleArn": role_arn,
                "RoleSessionName": "credproxy-aws-cli-session",
                "DurationSeconds": 3600,
            },
        }

        if external_id and external_id != "none":
            services["aws-cli"]["assumed_role"]["ExternalId"] = external_id

    # Only actual SDKs go to dynamic files
    dynamic_sdks = [sdk for sdk in service_names if sdk in DEFAULT_SDKS]

    # Configure server based on sidecar mode
    if os.environ.get("SIDECAR_MODE", "false").lower() == "true":
        server_host = "0.0.0.0"  # Listen on all interfaces for Docker networking
    else:
        server_host = CREDPROXY_HOST

    config = {
        "aws_defaults": {
            "region": "${fromEnv:AWS_DEFAULT_REGION}",
        },
        "server": {
            "host": server_host,
            "port": CREDPROXY_PORT,
            "debug": False,
        },
        "credentials": {
            "refresh_buffer_seconds": 300,
            "retry_delay": 60,
            "request_timeout": 30,
        },
        "metrics": {"prometheus": {"enabled": True, "host": "0.0.0.0", "port": 9090}},
        "dynamic_services": {
            "enabled": True,
            "directories": [
                {
                    "path": DYNAMIC_DIR_PATH,
                    "include_patterns": [".*\\.yaml$", ".*\\.yml$"],
                    "exclude_patterns": ["^\\..*", ".*~$", ".*\\.bak$"],
                }
            ],
            "reload_interval": 5,
        },
        "services": services,
    }

    # Generate individual SDK service files (only actual SDKs)
    if dynamic_sdks:
        generate_dynamic_service_files(
            service_name="sdk-services",
            role_arn=role_arn,
            external_id=external_id,
            region=region or "eu-west-1",
            sdks=dynamic_sdks,
            output_dir=".",
        )

    return config


def generate_proxy_sidecar_config(sdk_name):
    """Generate configuration for a proxy sidecar service."""
    return {
        "build": {
            "context": ".",
            "dockerfile": "./dockerfiles/socat.Dockerfile",
        },
        "depends_on": {"credproxy": {"condition": "service_healthy"}},
        "restart": "unless-stopped",
        "network_mode": f"service:{sdk_name}",
        "cap_add": ["NET_ADMIN"],
    }


def generate_sdk_service_config(
    sdk_type, role_arn, external_id=None, region="eu-west-1", with_sidecars=False
):
    """Generate configuration for a specific SDK service."""
    # Use simple SDK names as container names
    container_name = sdk_type
    token_file = f"/run/secrets/{container_name}-token"

    # Use relative URL when in sidecar mode (for ECS metadata testing)
    if with_sidecars:
        credentials_uri = "http://169.254.170.2/v1/credentials"
    else:
        credentials_uri = f"http://{CREDPROXY_HOST}:{CREDPROXY_PORT}/v1/credentials"

    environment = {
        "AWS_CONTAINER_CREDENTIALS_FULL_URI": credentials_uri,
        "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE": token_file,
        "AWS_DEFAULT_REGION": f"${{AWS_DEFAULT_REGION:-{region}}}",
        "AWS_REGION": f"${{AWS_DEFAULT_REGION:-{region}}}",
    }

    # SDK-specific configurations using pre-built images
    sdk_configs = {
        "aws-cli": {
            "image": "public.ecr.aws/aws-cli/aws-cli:latest",
            "command": ["sts", "get-caller-identity"],
            "volumes": ["./scripts:/scripts:ro"],
        },
        "python-boto3": {
            "build": {
                "context": ".",
                "dockerfile": "./dockerfiles/python-boto3.Dockerfile",
            },
            "volumes": ["./scripts:/scripts:ro"],
        },
        "node-aws-sdk": {
            "build": {
                "context": ".",
                "dockerfile": "./dockerfiles/node-aws-sdk.Dockerfile",
            },
        },
        "go-aws-sdk": {
            "build": {
                "context": ".",
                "dockerfile": "./dockerfiles/go-aws-sdk.Dockerfile",
            },
        },
    }

    if sdk_type not in sdk_configs:
        raise ValueError(f"Unsupported SDK type: {sdk_type}")

    config = sdk_configs[sdk_type].copy()

    # Set up dependencies based on SDK order and sidecar mode
    # aws-cli -> python-boto3 -> node-aws-sdk -> go-aws-sdk
    if with_sidecars:
        # Proxy sidecar depends on SDK service and uses its network namespace
        dependencies = {"credproxy": {"condition": "service_healthy"}}
        network_mode = None  # SDK service uses default network
    else:
        # Direct dependency on credproxy
        dependencies = {"credproxy": {"condition": "service_healthy"}}
        network_mode = "service:credproxy"

    if sdk_type == "python-boto3":
        dependencies["aws-cli"] = {"condition": "service_completed_successfully"}
    elif sdk_type == "node-aws-sdk":
        dependencies["aws-cli"] = {"condition": "service_completed_successfully"}
        dependencies["python-boto3"] = {"condition": "service_completed_successfully"}
    elif sdk_type == "go-aws-sdk":
        dependencies["aws-cli"] = {"condition": "service_completed_successfully"}
        dependencies["python-boto3"] = {"condition": "service_completed_successfully"}
        dependencies["node-aws-sdk"] = {"condition": "service_completed_successfully"}

    config.update(
        {
            "environment": environment,
            "depends_on": dependencies,
            "secrets": [f"{container_name}-token"],
        }
    )

    # Add network_mode only if specified (for non-sidecar mode)
    if network_mode:
        config["network_mode"] = network_mode

    return config


def generate_docker_compose_snippet(
    service_name,
    role_arn,
    external_id=None,
    region="eu-west-1",
    sdks=None,
    with_sidecars=False,
):
    """Generate Docker Compose snippet for testing with multiple SDKs."""
    if sdks is None:
        sdks = ["aws-cli", "python-boto3", "node-aws-sdk", "go-aws-sdk"]

    services = {}
    secrets = {}

    for sdk in sdks:
        if with_sidecars:
            # Generate proxy sidecar for each SDK
            proxy_name = f"{sdk}-proxy"
            services[proxy_name] = generate_proxy_sidecar_config(sdk)

        # Generate SDK service configuration
        services[sdk] = generate_sdk_service_config(
            sdk, role_arn, external_id, region, with_sidecars
        )

        # Each service gets its own secret in tokens directory
        secrets[f"{sdk}-token"] = {"file": f"./tokens/{sdk}-token.txt"}

    snippet = {
        "services": services,
        "secrets": secrets,
    }

    # Add networks if using sidecars
    if with_sidecars:
        snippet["networks"] = {
            "credproxy-net": {
                "driver": "bridge",
            },
        }
        # SDK services need to be on the network when using sidecars
        for sdk in sdks:
            if sdk in services:
                services[sdk]["networks"] = ["credproxy-net"]

    return snippet


def generate_full_docker_compose(
    service_name,
    role_arn,
    external_id=None,
    region="eu-west-1",
    sdks=None,
    with_sidecars=False,
):
    """Generate complete Docker Compose file with multiple SDK test containers."""
    import secrets

    # Get the service configurations from the snippet function
    service_snippet = generate_docker_compose_snippet(
        service_name, role_arn, external_id, region, sdks, with_sidecars
    )

    # Generate unique auth tokens for each SDK service
    auth_tokens = {}
    for sdk_service_name in service_snippet["services"].keys():
        if not sdk_service_name.endswith(
            "-proxy"
        ):  # Only generate tokens for actual SDK services
            auth_tokens[sdk_service_name] = secrets.token_urlsafe(32)

    # Update CredProxy secrets list to include all tokens
    credproxy_secrets = list(service_snippet["secrets"].keys())

    # Choose image based on sidecar mode
    credproxy_image = "public.ecr.aws/compose-x/aws/credproxy:latest"
    compose = {
        "services": {
            "credproxy": {
                "image": credproxy_image,
                "security_opt": ["no-new-privileges:true"],
                "read_only": True,
                "tmpfs": ["/tmp"],
                "ports": [
                    "9090:9090",  # Prometheus metrics port
                ],
                "volumes": [
                    "./config.yaml:/credproxy/config.yaml:ro",
                    "./dynamic:/credproxy/dynamic:ro",
                    "~/.aws:/root/.aws:ro",
                ],
                "user": "0:0",
                "environment": {
                    "AWS_DEFAULT_REGION": f"${{AWS_DEFAULT_REGION:-{region}}}",
                    "AWS_PROFILE": "${AWS_PROFILE:-default}",
                    "CREDPROXY_CONFIG_FILE": CREDPROXY_CONFIG_PATH,
                    "CREDPROXY_LOG_FORMAT": "json",
                    "CREDPROXY_LOG_LEVEL": "info",
                },
                "healthcheck": {
                    "test": [
                        "CMD",
                        "/bin/lprobe",
                        "-mode=http",
                        "-port=1338",
                        "-endpoint=/health",
                    ],
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 3,
                    "start_period": "10s",
                },
                "secrets": credproxy_secrets,
            },
            # Add socat proxy sidecar when in sidecar mode
            "socat-proxy": {
                "build": {
                    "context": ".",
                    "dockerfile": "./dockerfiles/socat.Dockerfile",
                },
                "restart": "unless-stopped",
                "network_mode": "service:credproxy",
                "cap_add": ["NET_ADMIN"],
                "depends_on": {"credproxy": {"condition": "service_healthy"}},
            },
            # Merge the SDK services from snippet
            **service_snippet["services"],
        },
        "secrets": service_snippet["secrets"],
    }

    # Add networks and configure network mode for credproxy if using sidecars
    if with_sidecars:
        compose["networks"] = {
            "credproxy-net": {
                "driver": "bridge",
            },
        }
        compose["services"]["credproxy"]["networks"] = ["credproxy-net"]
    else:
        pass

    return compose, auth_tokens


def generate_dynamic_service_files(
    service_name,
    role_arn,
    external_id=None,
    region="eu-west-1",
    sdks=None,
    output_dir=".",
):
    """Generate individual SDK service configuration files for dynamic directory."""
    if sdks is None:
        sdks = DEFAULT_SDKS

    dynamic_dir = f"{output_dir}/dynamic"
    os.makedirs(dynamic_dir, exist_ok=True)

    service_files = {}

    for sdk in sdks:
        # Generate service configuration for actual SDKs only
        session_name = f"credproxy-{sdk}-session"

        # Create service configuration following exact same schema as main config
        service_config = {
            "auth_token": f"${{fromFile:/run/secrets/{sdk}-token}}",
            "source_credentials": {},
            "assumed_role": {
                "RoleArn": role_arn,
                "RoleSessionName": session_name,
            },
        }

        if external_id and external_id != "none":
            service_config["assumed_role"]["ExternalId"] = external_id

        # Create file with services key - identical schema to main config
        file_content = {"services": {sdk: service_config}}

        # Write to individual file
        filename = f"{sdk}.yaml"
        filepath = f"{dynamic_dir}/{filename}"

        with open(filepath, "w") as f:
            yaml.dump(file_content, f, default_flow_style=False, indent=2)

        service_files[sdk] = filepath
        print(f"Generated dynamic SDK file: {filepath}")

    return service_files


def generate_test_scripts(output_dir="."):
    """Generate test scripts for different SDKs."""
    scripts_dir = f"{output_dir}/scripts"
    os.makedirs(scripts_dir, exist_ok=True)

    # Python Boto3 test script
    boto3_script = '''#!/usr/bin/env python3
"""
Test script for Python Boto3 SDK with CredProxy
"""

import boto3
import os
import sys

def test_boto3_credentials():
    """Test that Boto3 can use CredProxy credentials."""
    try:
        # Create STS client using container credentials
        sts_client = boto3.client('sts')

        # Get caller identity
        response = sts_client.get_caller_identity()

        print("✅ Boto3 test successful!")
        print(f"Account: {response.get('Account', 'Unknown')}")
        print(f"User ID: {response.get('UserId', 'Unknown')}")
        print(f"ARN: {response.get('Arn', 'Unknown')}")

        return True

    except Exception as error:
        print(f"❌ Boto3 test failed: {error}")
        return False

if __name__ == "__main__":
    success = test_boto3_credentials()
    sys.exit(0 if success else 1)
'''

    # Node.js AWS SDK test script
    node_script = """#!/usr/bin/env node
/**
 * Test script for Node.js AWS SDK with CredProxy
 */

const { STSClient, GetCallerIdentityCommand } = require('@aws-sdk/client-sts');

async function testAwsSdkCredentials() {
    try {
        // Create STS client using container credentials
        const stsClient = new STSClient({});

        // Get caller identity
        const command = new GetCallerIdentityCommand({});
        const response = await stsClient.send(command);

        console.log('✅ Node.js AWS SDK test successful!');
        console.log(`Account: ${response.Account || 'Unknown'}`);
        console.log(`User ID: ${response.UserId || 'Unknown'}`);
        console.log(`ARN: ${response.Arn || 'Unknown'}`);

        return true;

    } catch (error) {
        console.error(`❌ Node.js AWS SDK test failed: ${error.message}`);
        return false;
    }
}

testAwsSdkCredentials().then(success => {
    process.exit(success ? 0 : 1);
});
"""

    # Go AWS SDK test script
    go_script = """package main

import (
	"context"
	"fmt"
	"log"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/sts"
)

func main() {
	// Load AWS configuration using container credentials
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		log.Fatalf("❌ Go AWS SDK test failed: unable to load SDK config, %v", err)
	}

	// Create STS client
	stsClient := sts.NewFromConfig(cfg)

	// Get caller identity
	resp, err := stsClient.GetCallerIdentity(
		context.TODO(), &sts.GetCallerIdentityInput{},
	)
	if err != nil {
		log.Fatalf("❌ Go AWS SDK test failed: %v", err)
	}

	fmt.Println("✅ Go AWS SDK test successful!")
	if resp.Account != nil {
		fmt.Printf("Account: %s\\n", *resp.Account)
	}
	if resp.UserId != nil {
		fmt.Printf("User ID: %s\\n", *resp.UserId)
	}
	if resp.Arn != nil {
		fmt.Printf("ARN: %s\\n", *resp.Arn)
	}
}
"""

    # Write scripts
    scripts = {
        "test_boto3.py": boto3_script,
        "test_aws_sdk.js": node_script,
        "test_aws_sdk.go": go_script,
    }

    for filename, content in scripts.items():
        filepath = f"{scripts_dir}/{filename}"
        with open(filepath, "w") as f:
            f.write(content)

        # Make scripts executable
        os.chmod(filepath, 0o755)

    return scripts_dir


def main():
    parser = argparse.ArgumentParser(
        description="Generate CredProxy configuration from CloudFormation stack"
    )
    parser.add_argument(
        "stack_name",
        nargs="?",
        default=os.environ.get("CREDPROXY_QS_STACK_NAME", "credproxy-demo-role"),
        help=(
            "Name of the CloudFormation stack (default: CREDPROXY_QS_STACK_NAME "
            "env var or 'credproxy-demo-role')"
        ),
    )
    parser.add_argument(
        "service_name",
        nargs="?",
        help="Name of service for Docker Compose (auto-detected if not provided)",
    )
    parser.add_argument("--region", help="AWS region (uses default if not specified)")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for generated files (default: current directory)",
    )
    parser.add_argument(
        "--snippet-only",
        action="store_true",
        help="Only generate Docker Compose snippet, not full file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output to stdout instead of writing files",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Test mode - use mock values instead of real stack",
    )
    parser.add_argument(
        "--with-sidecars-example",
        action="store_true",
        help="Generate Docker Compose with proxy sidecar pattern",
    )

    args = parser.parse_args()

    # Set environment variable for sidecar mode
    os.environ["SIDECAR_MODE"] = "true" if args.with_sidecars_example else "false"

    try:
        # Get stack outputs
        if args.test_mode:
            print(f"Test mode: Using mock values for stack: {args.stack_name}")
            outputs = {
                "RoleArn": "arn:aws:iam::123456789012:role/credproxy/credproxy-role",
                "ExternalId": "none",
            }
        else:
            print(f"Getting outputs from stack: {args.stack_name}")
            outputs = get_stack_outputs(args.stack_name, args.region)

        role_arn = outputs.get("RoleArn")
        if not role_arn:
            raise ValueError("RoleArn not found in stack outputs")

        external_id = outputs.get("ExternalId", "none")

        print(f"Found role ARN: {role_arn}")

        # Determine service name (use provided or auto-detect)
        if args.service_name:
            service_name = args.service_name
            print(f"Using provided service name: {service_name}")
        else:
            service_name = get_caller_identity(args.region or "eu-west-1")
            print(f"Auto-detected service name: {service_name}")

        # Determine region (use stack region or default)
        stack_region = args.region or "eu-west-1"

        # Generate Docker Compose content first to get auth tokens
        auth_tokens = None
        # Default tools - always generate all 4 (1 CLI + 3 SDKs)
        default_tools = DEFAULT_TOOLS

        if args.snippet_only:
            compose_dict = generate_docker_compose_snippet(
                service_name,
                role_arn,
                external_id,
                stack_region,
                default_tools,
                args.with_sidecars_example,
            )
            import yaml

            compose_content = yaml.dump(
                compose_dict, default_flow_style=False, sort_keys=False
            )

            # Add appropriate header based on mode
            if args.with_sidecars_example:
                compose_content = (
                    "# Docker Compose Snippet for CredProxy Demo with Sidecar Pattern\n"
                    f"# Generated from CloudFormation stack: {args.stack_name}\n"
                    f"# Tool containers: {', '.join(default_tools)}\n"
                    "# Each SDK container uses a proxy "
                    "sidecar for localhost forwarding\n\n"
                    f"{compose_content}"
                )
            else:
                compose_content = (
                    "# Docker Compose Snippet for CredProxy Demo\n"
                    f"# Generated from CloudFormation stack: {args.stack_name}\n"
                    f"# Tool containers: {', '.join(default_tools)}\n\n"
                    f"{compose_content}"
                )
        else:
            compose_dict, auth_tokens = generate_full_docker_compose(
                service_name,
                role_arn,
                external_id,
                stack_region,
                default_tools,
                args.with_sidecars_example,
            )
            import yaml

            compose_content = yaml.dump(
                compose_dict, default_flow_style=False, sort_keys=False
            )

            # Add appropriate header based on mode
            if args.with_sidecars_example:
                compose_content = (
                    "# Docker Compose for CredProxy Demo with Sidecar Pattern\n"
                    f"# Generated from CloudFormation stack: {args.stack_name}\n"
                    f"# Tool containers: {', '.join(default_tools)}\n"
                    "# Each SDK container uses a proxy "
                    "sidecar for localhost forwarding\n\n"
                    f"{compose_content}"
                )
            else:
                compose_content = (
                    "# Docker Compose for CredProxy Demo\n"
                    f"# Generated from CloudFormation stack: {args.stack_name}\n"
                    f"# Tool containers: {', '.join(default_tools)}\n\n"
                    f"{compose_content}"
                )

        # Generate CredProxy config with all tool service names
        tool_service_names = default_tools
        credproxy_config = generate_credproxy_config(
            tool_service_names, role_arn, external_id, args.region
        )
        import yaml

        config_yaml = (
            "# CredProxy Configuration\n"
            f"# Generated from CloudFormation stack: {args.stack_name}\n"
            f"# Tool services: {', '.join(tool_service_names)}\n"
        )
        if args.with_sidecars_example:
            config_yaml += "# Mode: Sidecar proxy pattern\n"
        config_yaml += "\n"
        config_yaml += yaml.dump(
            credproxy_config, default_flow_style=False, sort_keys=False
        )

        # Output results
        if args.dry_run:
            print("\n" + "=" * 50)
            print("CREDPROXY CONFIG (config.yaml):")
            print("=" * 50)
            print(config_yaml)

            print("\n" + "=" * 50)
            print("DOCKER COMPOSE:")
            print("=" * 50)
            print(compose_content)

            if auth_tokens:
                print("\n" + "=" * 50)
                print("AUTH TOKENS:")
                print("=" * 50)
                for service_name, token in auth_tokens.items():
                    print(f"tokens/{service_name}-token.txt: {token}")
        else:
            # Write config.yaml
            config_path = f"{args.output_dir}/config.yaml"
            with open(config_path, "w") as f:
                f.write(config_yaml)
            print(f"Generated config.yaml: {config_path}")

            # Write Docker Compose
            if args.snippet_only:
                compose_path = f"{args.output_dir}/docker-compose-snippet.yaml"
            else:
                compose_path = f"{args.output_dir}/docker-compose.yaml"

            with open(compose_path, "w") as f:
                f.write(compose_content)
            file_type = "snippet" if args.snippet_only else "Docker Compose"
            print(f"Generated {file_type}: {compose_path}")

            # Generate test scripts if needed
            scripts_dir = None
            if not args.snippet_only and any(
                sdk in default_tools
                for sdk in ["python-boto3", "node-aws-sdk", "go-aws-sdk"]
            ):
                scripts_dir = generate_test_scripts(args.output_dir)
                print(f"Generated test scripts: {scripts_dir}")

            # Create tokens directory and write auth token secret files
            if auth_tokens:
                tokens_dir = f"{args.output_dir}/tokens"
                os.makedirs(tokens_dir, exist_ok=True)

                for service_name, token in auth_tokens.items():
                    token_path = f"{tokens_dir}/{service_name}-token.txt"
                    with open(token_path, "w") as f:
                        f.write(token)
                    print(f"Generated auth token: {token_path}")

            print("\nTo test CredProxy:")
            print("   1. Copy config.yaml to your CredProxy directory")
            print("   2. Run: docker compose up")
            print("   3. The following tool containers will test AWS credentials:")

            for sdk in default_tools:
                if args.with_sidecars_example:
                    print(f"      - {sdk} (via {sdk}-proxy sidecar)")
                else:
                    print(f"      - {sdk}")

            if scripts_dir:
                print(f"   4. Test scripts are available in: {scripts_dir}")

    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
