Socat Proxy Sidecar for ECS Metadata
=====================================

.. meta::
    :description: Simple explanation of the socat proxy trick for simulating ECS metadata service with CredProxy
    :keywords: CredProxy, socat proxy, ECS metadata, credential provider, sidecar

The socat proxy sidecar enables CredProxy to simulate the ECS metadata service, allowing applications to use standard ECS credential provider interfaces in local development environments.

The Trick
---------

The socat proxy creates a local ECS metadata service endpoint (``169.254.170.2``) that forwards credential requests to CredProxy. This works by:

1. **IP Configuration**: Socat adds ``169.254.170.2`` to the loopback interface
2. **Port Forwarding**: Forwards requests from port 80 (ECS metadata) to CredProxy port 1338
3. **Network Namespace**: Shares network namespace with CredProxy for loopback access

How It Works
-------------

.. code-block:: text

    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   AWS SDK App   │    │  Socat Proxy    │    │   CredProxy     │
    │                 │    │                 │    │                 │
    │  AWS SDK        │───▶│  169.254.170.2  │───▶│  localhost:1338 │
    │  requests       │    │  forwarding     │    │  credential     │
    │  credentials    │    │  to CredProxy   │    │  provider       │
    └─────────────────┘    └─────────────────┘    └─────────────────┘

Purpose
-------

- **ECS Compatibility**: Applications use the same credential provider code as in ECS containers
- **Local Testing**: Test ECS credential provider behavior without deploying to ECS
- **Multi-SDK Support**: Works with all AWS SDKs that support ECS credential provider
- **Seamless Integration**: No code changes required for applications

Basic Configuration
-------------------

.. code-block:: yaml

    services:
      credproxy:
        image: credproxy:latest
        # ... CredProxy configuration ...

      socat-proxy:
        image: socat-proxy:latest
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

Application Usage
-----------------

Configure your application to use ECS credential provider:

.. code-block:: bash

    # ECS credential provider configuration
    export AWS_CONTAINER_CREDENTIALS_FULL_URI=http://127.0.0.1/v1/credentials
    export AWS_CONTAINER_AUTHORIZATION_TOKEN=your-auth-token

The AWS SDK will automatically use these environment variables to retrieve credentials through the socat proxy.

Demo and Quick Start
--------------------

For a complete working demo showcasing multiple AWS SDKs using the socat proxy, see the :doc:`cloudformation` guide. It includes:

- IAM role setup with CloudFormation
- Multi-SDK testing environment (AWS CLI, Python Boto3, Node.js, Go)
- Complete Docker Compose configuration
- Sequential credential testing across all SDKs

Security Considerations
-----------------------

- The socat proxy requires ``NET_ADMIN`` capability to manage network interfaces
- Only modifies the loopback interface, maintaining network isolation
- Use strong, random tokens for authorization
- Consider using non-root users in testing containers

Next Steps
----------

- :doc:`cloudformation` - Complete CloudFormation demo with multi-SDK testing
- :doc:`docker-compose` - Docker Compose deployment guide
- :doc:`../configuration/index` - Configuration options
- :doc:`../configuration/security` - Security best practices
