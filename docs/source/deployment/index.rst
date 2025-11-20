Deployment
==========

.. meta::
    :description: Deployment guides and configurations for CredProxy in various environments
    :keywords: CredProxy, deployment, Docker, Kubernetes, ECS, CloudFormation, testing

This section provides comprehensive deployment guides for CredProxy across different environments and use cases. Whether you're deploying for local development or testing, you'll find detailed instructions and best practices here.

Deployment Options
------------------

CredProxy supports multiple deployment strategies to fit different needs:

**Local Development**
  Quick setup for local development and testing with Docker Compose

**Multi-SDK Testing**
  Comprehensive testing environment with multiple AWS SDKs and socat proxy

**Production Deployment**
  Production-ready configurations with security and observability

**Cloud-Native Deployment**
  Deployment patterns for ECS, Kubernetes, and other cloud platforms

.. toctree::
    :maxdepth: 2
    :caption: Deployment Guides:

    docker-compose
    advanced-docker-compose
    socat-proxy
    cloudformation

Quick Start
-----------

For most users, the Docker Compose deployment is the recommended starting point:

.. code-block:: bash

    # Clone and run with Docker
    git clone https://github.com/johnpreston/credproxy.git && cd credproxy
    docker compose up --build

**For ECS metadata-style testing**: Use the CloudFormation template for multi-SDK testing with socat proxy:

.. code-block:: bash

    cd tooling/cloudformation
    python3 generate-config.py
    docker compose up --build

Choosing the Right Deployment
-----------------------------

**Local Development**
  Use :doc:`docker-compose` for simple local development and testing

**ECS Metadata Testing**
  Use :doc:`socat-proxy` to simulate ECS credential provider behavior locally

**Multi-SDK Validation**
  Use :doc:`cloudformation` for comprehensive testing across multiple AWS SDKs

**Security Considerations**
  See the security sections in each guide for important security considerations

Security Considerations
-----------------------

All deployment guides include security best practices:

- **Network Isolation**: Proper network namespace sharing and firewall rules
- **Credential Management**: Secure token handling and rotation
- **Access Control**: Proper IAM roles and authentication configuration
- **Monitoring**: Logging and metrics for security observability

Next Steps
----------

- :doc:`docker-compose` - Docker Compose deployment guide
- :doc:`socat-proxy` - Socat proxy sidecar for ECS metadata
- :doc:`cloudformation` - CloudFormation template deployment
- :doc:`../installation/index` - Installation prerequisites
- :doc:`../configuration/index` - Configuration options
- :doc:`../configuration/security` - Security best practices
