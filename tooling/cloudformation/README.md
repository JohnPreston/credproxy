# CredProxy IAM Role CloudFormation Template

Creates IAM roles for CredProxy demonstrations with multi-SDK testing.

## Quick Start

```bash
# Set stack name once, use everywhere
export CREDPROXY_QS_STACK_NAME=credproxy-demo-role

# Deploy IAM Role
aws cloudformation deploy \
  --template-file credproxy-iam-role.yaml \
  --stack-name $CREDPROXY_QS_STACK_NAME \
  --capabilities CAPABILITY_NAMED_IAM

# Generate config files (uses env var automatically)
python3 generate-config.py ${CREDPROXY_QS_STACK_NAME}

# Start all SDK containers sequentially with metrics
docker compose up --force-recreate --remove-orphans --build
```

**Result**: Watch each SDK container get AWS credentials one by one through
CredProxy with metrics collection enabled.

## Socat Proxy Sidecar

The generated Docker Compose configuration includes a socat proxy sidecar that
enables ECS metadata-style credential forwarding:

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AWS SDK App   │    │  Socat Proxy    │    │   CredProxy     │
│                 │    │                 │    │                 │
│  AWS SDK        │───▶│  169.254.170.2  │───▶│  localhost:1338 │
│  requests       │    │  forwarding     │    │  credential     │
│  credentials    │    │  to CredProxy   │    │  provider       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Features

- **ECS Metadata IP**: Adds `169.254.170.2` to loopback interface
- **Port Forwarding**: Forwards both port 80 (ECS metadata) and port 1338
  (CredProxy API)
- **Network Namespace**: Shares network namespace with CredProxy for loopback
  access
- **AWS SDK Compatibility**: Enables standard ECS credential provider
  environment variables

### Usage

Applications can now use ECS-style credential configuration:

```bash
AWS_CONTAINER_CREDENTIALS_FULL_URI=http://127.0.0.1/v1/credentials
AWS_CONTAINER_AUTHORIZATION_TOKEN=your-auth-token
```

### Files

- `dockerfiles/socat.Dockerfile` - Docker image for the socat proxy
- `scripts/socat.sh` - Startup script for IP setup and port forwarding
- `socat.README.md` - Detailed documentation for the socat proxy

## Metrics & Observability

### Prometheus Metrics

- **CredProxy API**: `http://localhost:1338` - Main credential service
- **CredProxy metrics**: `http://localhost:9090/metrics` - Prometheus metrics
  endpoint

### Available Metrics

- `credproxy_requests_total` - Credential requests per service (success/error)
- `credproxy_active_services` - Number of active services
- `credproxy_info` - Application version information

## Files Generated

- `config.yaml` - CredProxy configuration with SDK-specific session names and
  metrics enabled
- `docker-compose.yaml` - Multi-SDK containers (aws-cli → python-boto3 →
  node-aws-sdk → go-aws-sdk)
- `tokens/` - Directory with auth tokens (add to `.gitignore`)

## Environment Variables

- `CREDPROXY_QS_STACK_NAME` - Default CloudFormation stack name (default:
  `credproxy-demo-role`)

## Git Ignore

```gitignore
tokens/
*.token.txt
config.yaml
docker-compose.yaml
```

## What Happens

Each SDK container:

1. Waits for CredProxy to be healthy
2. Uses its own auth token from `tokens/` directory
3. Gets AWS credentials with unique session name (`credproxy-{sdk}-session`)
4. Tests AWS API call (STS GetCallerIdentity)
5. Passes credentials to next SDK in sequence

**Session Names**: `credproxy-aws-cli-session`,
`credproxy-python-boto3-session`, `credproxy-node-aws-sdk-session`,
`credproxy-go-aws-sdk-session`

## SDK-Specific Details

### Node.js AWS SDK v3

- **Node.js Version**: 22 (latest LTS)
- **SDK Version**: AWS SDK v3 for JavaScript
- **Credentials Provider**: Demonstrates simple async credentials provider
  pattern
- **Key Feature**: Shows how easy it is to integrate CredProxy with AWS SDK v3
  using a simple async function that returns credentials with automatic refresh
  support

## Cleanup

```bash
aws cloudformation delete-stack --stack-name $CREDPROXY_QS_STACK_NAME
rm -rf tokens/ config.yaml docker-compose.yaml
```
