Installation
============

.. meta::
    :description: Installation guide for CredProxy with Docker and source deployment options
    :keywords: CredProxy, installation, Docker, deployment, setup, containers=

.. toctree::
    :maxdepth: 2

    healthcheck

CredProxy can be deployed via Docker (recommended) or from source for development.

Docker Installation (Recommended)
----------------------------------

Prerequisites
~~~~~~~~~~~~~

- Docker 20.10+
- Docker Compose v2.0+ (optional, for multi-container setups)
- AWS credentials configured (AWS CLI profile or environment variables)

Quick Start
~~~~~~~~~~~

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/johnpreston/credproxy.git
    cd credproxy

    # Build the Docker image
    docker build -t credproxy:latest .

    # Run with docker compose
    docker compose up --build

The service will be available at ``http://localhost:1338``

Docker Image
~~~~~~~~~~~~

The official Docker image is built on Alpine Linux for minimal size and includes:

- Python 3.11+
- lprobe for health checks
- All required dependencies

Health checks are configured using `lprobe <https://github.com/fivexl/lprobe>`_,
a lightweight HTTP health check tool designed for containers.

See :doc:`healthcheck` for complete health check configuration details.

From Source Installation
------------------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.10+
- Poetry 1.5+
- AWS CLI configured

Installation Steps
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/johnpreston/credproxy.git
    cd credproxy

    # Install dependencies with poetry
    poetry install

    # Run in development mode
    poetry run credproxy --dev --config config.yaml

    # Or run in testing mode
    poetry run credproxy --config config.yaml

Development Setup
~~~~~~~~~~~~~~~~~

For development with hot-reload:

.. code-block:: bash

    # Install development dependencies
    poetry install --with dev

    # Run tests
    poetry run pytest

    # Run with coverage
    poetry run pytest --cov=credproxy

    # Format code
    poetry run black credproxy tests
    poetry run isort credproxy tests

Python Requirements
-------------------

Core Dependencies
~~~~~~~~~~~~~~~~~

- Flask - Web framework for API endpoints
- boto3 / botocore - AWS SDK
- PyYAML - Configuration file parsing
- jsonschema - Configuration validation
- watchdog - File monitoring for dynamic services (optional)
- prometheus-client - Metrics export

Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~

- sphinx - Documentation generation
- pytest - Testing framework
- black / isort - Code formatting

Configuration
-------------

After installation, create a configuration file:

.. code-block:: yaml

    # config.yaml
    server:
      host: localhost
      port: 1338

    services:
      my-app:
        auth_token: "your-secure-token"
        source_credentials:
          region: "us-west-2"
        assumed_role:
          RoleArn: "arn:aws:iam::123456789012:role/MyRole"

See :doc:`../configuration/index` for complete configuration options.

Verification
------------

Verify the installation:

.. code-block:: bash

    # Check health endpoint
    curl http://localhost:1338/health

    # Expected response:
    # {"status": "healthy", "services": {"my-app": "active"}}

Next Steps
----------

- Review :doc:`../configuration/index` for configuration options
- Check :doc:`../configuration/environment-variables` for environment variable support
- See :doc:`../configuration/security` for security best practices
- Read :doc:`healthcheck` for health check configuration
- Explore :doc:`../development/index` for development workflows
