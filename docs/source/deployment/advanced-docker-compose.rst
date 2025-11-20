Advanced Docker Compose Setup
==============================

.. meta::
    :description: Advanced Docker Compose configurations for CredProxy including socat proxy sidecar and multi-SDK testing
    :keywords: CredProxy, Docker Compose, advanced setup, socat proxy, ECS metadata, multi-SDK testing

This guide covers advanced Docker Compose configurations for CredProxy, including the socat proxy sidecar for ECS metadata-style credential forwarding and multi-SDK testing setups.

Socat Proxy Sidecar for ECS Metadata
--------------------------------------

The socat proxy sidecar enables ECS metadata-style credential forwarding in local development environments, allowing applications to use the same credential provider interface as in ECS containers.

Architecture
~~~~~~~~~~~~

.. code-block:: text

    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   AWS SDK App   │    │  Socat Proxy    │    │   CredProxy     │
    │                 │    │                 │    │                 │
    │  AWS SDK        │───▶│  169.254.170.2  │───▶│  localhost:1338 │
    │  requests       │    │  forwarding     │    │  credential     │
    │  credentials    │    │  to CredProxy   │    │  provider       │
    └─────────────────┘    └─────────────────┘    └─────────────────┘

Features
~~~~~~~~

- **ECS Metadata IP**: Adds ``169.254.170.2`` to loopback interface
- **Port Forwarding**: Forwards both port 80 (ECS metadata) and port 1338 (CredProxy API)
- **Network Namespace**: Shares network namespace with CredProxy for loopback access
- **AWS SDK Compatibility**: Enables standard ECS credential provider environment variables

Configuration
~~~~~~~~~~~~~~

.. code-block:: yaml

    services:
      credproxy:
        image: ${REGISTRY:-public.ecr.aws}/${REPOSITORY:-compose-x/aws/credproxy}:${IMAGE_TAG:-latest}
        build:
          context: .
          dockerfile: docker/Dockerfile
        restart: unless-stopped
        environment:
          AWS_PROFILE: ${AWS_PROFILE:-default}
          AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-us-west-1}
        expose:
          - "1338/tcp"
        deploy:
          resources:
            limits:
              cpus: "0.25"
              memory: 256M
        healthcheck:
          test:
            - CMD
            - /bin/lprobe
            - -mode=http
            - -port=1338
            - -endpoint=/health
          interval: 10s
          timeout: 5s
          retries: 3
          start_period: 10s

      socat-proxy:
        image: ${REGISTRY:-public.ecr.aws}/${REPOSITORY:-compose-x/aws/socat-proxy}:${IMAGE_TAG:-latest}
        build:
          context: tooling/cloudformation
          dockerfile: dockerfiles/socat.Dockerfile
        restart: unless-stopped
        network_mode: service:credproxy
        cap_add:
          - NET_ADMIN
        depends_on:
          credproxy:
            condition: service_healthy

      your-application:
        image: your-app-image
        network_mode: service:credproxy
        environment:
          - AWS_CONTAINER_CREDENTIALS_FULL_URI=http://127.0.0.1/v1/credentials
          - AWS_CONTAINER_AUTHORIZATION_TOKEN=your-auth-token
        depends_on:
          credproxy:
            condition: service_healthy

Usage
~~~~~

Applications can now use ECS-style credential configuration:

.. code-block:: bash

    export AWS_CONTAINER_CREDENTIALS_FULL_URI=http://127.0.0.1/v1/credentials
    export AWS_CONTAINER_AUTHORIZATION_TOKEN=your-auth-token

The AWS SDK will automatically retrieve credentials through the socat proxy, which forwards requests to the main CredProxy service.

Security Considerations
~~~~~~~~~~~~~~~~~~~~~~~

- The socat proxy requires ``NET_ADMIN`` capability to manage network interfaces
- Only the loopback interface is modified, maintaining network isolation
- The proxy runs as a minimal Alpine Linux container with only necessary packages
- All traffic is forwarded to the main CredProxy service which handles authentication

Multi-SDK Testing Setup
------------------------

For comprehensive multi-SDK testing with sequential credential testing across different AWS SDKs, see :doc:`cloudformation`. The CloudFormation guide provides a complete testing environment with:

- IAM role deployment and configuration
- Multi-SDK containers (AWS CLI, Python boto3, Node.js, Go)
- Sequential credential testing with metrics collection
- Comprehensive troubleshooting and validation

Use the CloudFormation quickstart for comprehensive multi-SDK testing environments.

Custom Docker Compose Setups
-----------------------------

Sidecar Mode with Multiple Services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For complex applications with multiple services:

.. code-block:: yaml

    services:
      credproxy:
        image: credproxy:latest
        # ... base configuration ...

      socat-proxy:
        image: socat-proxy:latest
        build:
          context: tooling/cloudformation
          dockerfile: dockerfiles/socat.Dockerfile
        network_mode: service:credproxy
        cap_add:
          - NET_ADMIN
        depends_on:
          credproxy:
            condition: service_healthy

      service-a:
        image: service-a:latest
        network_mode: service:credproxy
        environment:
          - AWS_CONTAINER_CREDENTIALS_FULL_URI=http://127.0.0.1/v1/credentials
          - AWS_CONTAINER_AUTHORIZATION_TOKEN=token-a
        depends_on:
          credproxy:
            condition: service_healthy

      service-b:
        image: service-b:latest
        network_mode: service:credproxy
        environment:
          - AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:1338/v1/credentials
          - AWS_CONTAINER_AUTHORIZATION_TOKEN=token-b
        depends_on:
          credproxy:
            condition: service_healthy

External Network Access
~~~~~~~~~~~~~~~~~~~~~~~~

**WARNING**: Never expose port 1338 externally without proper TLS termination and authentication. The credentials endpoint transmits sensitive AWS credentials in clear text.

For development scenarios requiring external access:

.. code-block:: yaml

    services:
      credproxy:
        image: credproxy:latest
        ports:
          - "9090:9090"  # Expose metrics externally only
        # ... other configuration ...

      socat-proxy:
        image: socat-proxy:latest
        network_mode: service:credproxy
        cap_add:
          - NET_ADMIN
        depends_on:
          credproxy:
            condition: service_healthy

      monitoring:
        image: prom/prometheus:latest
        ports:
          - "9091:9090"
        volumes:
          - ./prometheus.yml:/etc/prometheus/prometheus.yml
        command:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--web.console.libraries=/etc/prometheus/console_libraries'
          - '--web.console.templates=/etc/prometheus/consoles'
        depends_on:
          - credproxy

Development with Hot Reload
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For development with automatic configuration reloading:

.. code-block:: yaml

    services:
      credproxy:
        image: credproxy:latest
        build:
          context: .
          dockerfile: docker/Dockerfile
        volumes:
          - ./config.yaml:/credproxy/config.yaml:ro
          - ./dynamic:/credproxy/dynamic:ro  # For dynamic services
          - ${HOME}/.aws/:/credproxy/.aws/:ro
        environment:
          - CREDPROXY_LOG_HEALTH_CHECKS=true
          - CREDPROXY_DYNAMIC_SERVICES_ENABLED=true
        # ... other configuration ...

      socat-proxy:
        image: socat-proxy:latest
        build:
          context: tooling/cloudformation
          dockerfile: dockerfiles/socat.Dockerfile
        network_mode: service:credproxy
        cap_add:
          - NET_ADMIN
        depends_on:
          credproxy:
            condition: service_healthy

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Socat Proxy Fails to Start**
  Ensure the ``NET_ADMIN`` capability is available and the Docker daemon has sufficient permissions.

**Network Namespace Issues**
  Verify that ``network_mode: service:credproxy`` is properly configured for all services that need to share the network namespace.

**Credential Retrieval Fails**
  Check that the ``AWS_CONTAINER_AUTHORIZATION_TOKEN`` environment variable matches a valid token in your CredProxy configuration.

**Port Conflicts**
  Ensure no other services are using ports 1338 or 80 on the shared network namespace.

Debug Commands
~~~~~~~~~~~~~~

.. code-block:: bash

    # Check container status
    docker compose ps

    # View CredProxy logs
    docker compose logs credproxy

    # View socat proxy logs
    docker compose logs socat-proxy

    # Test network connectivity
    docker compose exec credproxy curl http://localhost:1338/health

    # Test socat proxy forwarding
    docker compose exec credproxy curl -H "Authorization: your-token" http://169.254.170.2/v1/credentials

    # Check IP address configuration
    docker compose exec credproxy ip addr show

Cleanup
~~~~~~~

.. code-block:: bash

    # Stop and remove containers
    docker compose down

    # Remove generated files
    rm -rf tokens/ config.yaml docker-compose.yaml

    # Clean up Docker images
    docker image prune -f

Next Steps
----------

- Review :doc:`../configuration/index` for detailed configuration options
- Explore :doc:`cloudformation` for CloudFormation template details
- Read :doc:`../configuration/security` for security best practices
