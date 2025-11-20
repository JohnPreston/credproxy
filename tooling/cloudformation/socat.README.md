# Socat Proxy Sidecar for ECS Metadata Forwarding

This directory contains the Dockerfile and scripts for the socat proxy sidecar
that enables ECS metadata-style credential forwarding in local development
environments.

## Overview

The socat proxy sidecar is a lightweight container that:

- Adds the ECS metadata IP address (169.254.170.2) to the loopback interface
- Forwards both CredProxy traffic (port 1338) and ECS metadata traffic (port 80)
  to the main CredProxy service
- Enables AWS SDKs to retrieve credentials using the same interface as in ECS
  environments

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AWS SDK App   │    │  Socat Proxy    │    │   CredProxy     │
│                 │    │                 │    │                 │
│  AWS SDK        │───▶│  169.254.170.2  │───▶│  localhost:1338 │
│  requests       │    │  forwarding     │    │  credential     │
│  credentials    │    │  to CredProxy   │    │  provider       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Files

- `socat.Dockerfile` - Docker image definition for the socat proxy
- `../tooling/cloudformation/scripts/socat.sh` - Startup script for the proxy

## Usage

The socat proxy is automatically included in the main `docker-compose.yaml` file
and runs as a sidecar to the main CredProxy service.

### Docker Compose Integration

```yaml
services:
  credproxy:
    # Main CredProxy service
    image: ${REGISTRY:-public.ecr.aws}/${REPOSITORY:-compose-x/aws/credproxy}:${IMAGE_TAG:-latest}
    # ... other configuration ...

  socat-proxy:
    image: ${REGISTRY:-public.ecr.aws}/${REPOSITORY:-compose-x/aws/socat-proxy}:${IMAGE_TAG:-latest}
    build:
      context: .
      dockerfile: docker/socat.Dockerfile
    restart: unless-stopped
    network_mode: service:credproxy
    cap_add:
      - NET_ADMIN
    depends_on:
      credproxy:
        condition: service_healthy
```

### How It Works

1. **Network Namespace Sharing**: The socat proxy uses
   `network_mode: service:credproxy` to share the network namespace with the
   main CredProxy service.

2. **IP Address Setup**: The proxy adds the ECS metadata IP address
   `169.254.170.2` to the loopback interface using `ip addr add`.

3. **Port Forwarding**: Two socat processes run:
   - One forwards port 1338 (CredProxy API) to the main service
   - One forwards port 80 (ECS metadata) to the main service

4. **AWS SDK Compatibility**: Applications can now use standard ECS credential
   provider environment variables:
   ```bash
   AWS_CONTAINER_CREDENTIALS_FULL_URI=http://127.0.0.1/v1/credentials
   AWS_CONTAINER_AUTHORIZATION_TOKEN=your-auth-token
   ```

## Building the Image

```bash
# Build the socat proxy image
docker build -f docker/socat.Dockerfile -t socat-proxy .

# Or build with the main compose file
docker compose build socat-proxy
```

## Security Considerations

- The proxy requires `NET_ADMIN` capability to manage network interfaces
- Only the loopback interface is modified, maintaining network isolation
- The proxy runs as a minimal Alpine Linux container with only necessary
  packages
- All traffic is forwarded to the main CredProxy service which handles
  authentication

## Testing

To test the socat proxy setup:

```bash
# Start the services
docker compose up -d

# Test the ECS metadata endpoint
curl -H "Authorization: your-token" http://localhost:80/v1/credentials

# Test direct CredProxy access
curl -H "Authorization: your-token" http://localhost:1338/v1/credentials
```

Both should return the same AWS credentials, demonstrating that the forwarding
is working correctly.
