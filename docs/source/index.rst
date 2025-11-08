CredProxy Documentation
=======================

.. meta::
    :description: CredProxy - ECS-compatible AWS credentials proxy for local development
    :keywords: AWS, ECS, credentials, proxy, Docker, containers, local development, IAM

.. image:: https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg
    :target: https://opensource.org/licenses/MPL-2.0

.. image:: https://img.shields.io/badge/python-3.10+-blue.svg
    :target: https://www.python.org/downloads/

.. image:: https://img.shields.io/badge/docker-ready-blue.svg
    :target: https://www.docker.com/

.. image:: https://img.shields.io/badge/tests-passing-brightgreen.svg
    :target: https://github.com/johnpreston/credproxy/actions

A lightweight sidecar container that provides AWS credentials to applications using the
same interface as ECS credential providers. Designed for local development and testing
to strengthen applications that will later use AWS services like S3.

Quick Start
-----------

.. code-block:: bash

    # Clone and run with Docker in 30 seconds
    git clone https://github.com/johnpreston/credproxy.git && cd credproxy
    docker compose up --build

**Result**: You can expose AWS Credentials to your application as if running on ECS!

Why CredProxy?
--------------

**Problem**: Applications often behave differently in local development vs production
when using AWS SDKs, especially around credential management and AWS service
integration.

**Solution**: CredProxy provides ECS-compatible credential endpoints locally, allowing
you to develop and test with the same credential management patterns that will be used
in production. This strengthens local implementation and helps catch issues early.

Key Features
------------

- **ECS-Compatible** - Drop-in replacement for ECS credential providers
- **Multiple Auth Methods** - IAM profiles, access keys, with secure variable substitution
- **Zero Downtime** - Automatic credential rotation 5 minutes before expiry
- **Development Focused** - Designed for local development with Docker Compose
- **Configurable** - YAML-based configuration with environment variable substitution
- **Built-in Metrics** - Prometheus metrics for credential requests and service health

Authentication Methods
----------------------

- **Default** - AWS SDK default provider chain (EC2, ECS, env vars, profiles)
- **IAM Profiles** - Assume container role from an existing profile
- **IAM Keys** - Assume container role from AWS Keys

Installation
------------

Option 1: Docker (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/johnpreston/credproxy && cd credproxy
    # Build the container
    docker build -t credproxy .

Option 2: From Source (Development)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For development and testing, you can run from source:

.. code-block:: bash

    # Requires Python 3.10+
    # First, ensure pip and poetry are up to date (user-level installation)
    pip install pip poetry -U --user

    # Clone and set up virtual environment
    git clone https://github.com/johnpreston/credproxy && cd credproxy
    python3 -m venv venv
    source venv/bin/activate
    pip install pip poetry -U
    poetry install

    # Development mode (requires existing AWS infrastructure)
    poetry run credproxy --dev --config config.yaml

    # Production mode
    poetry run credproxy --config config.yaml

**Note**: Development requires existing AWS IAM roles/profiles. For most users, Docker
deployment is recommended.

Architecture
------------

**CredProxy runs directly with built-in signal handling** in containerized environments.

- **Docker**: Runs credproxy directly (recommended for production)
- **Direct credproxy**: ``credproxy --config config.yaml``
- **Environment variable**: ``CREDPROXY_CONFIG_FILE=/path/to/config.yaml``

How It Works
------------

Step 1: Configure
~~~~~~~~~~~~~~~~~

Create a YAML configuration file:

.. code-block:: yaml

    aws_defaults:
      region: "us-west-2"

    services:
      my-app:
        auth_token: "secure-token-2025"
        source_credentials:
          region: "us-west-2"
        assumed_role:
          RoleArn: "arn:aws:iam::123456789012:role/MyAppRole"
          RoleSessionName: "my-app-session"

Step 2: Deploy with Docker Compose
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    services:
      credproxy:
        build: .
        deploy:
          resources:
            limits:
              cpus: "0.25"
              memory: 512M
        volumes:
          - ./config.yaml:/credproxy/config.yaml:ro
          - ${HOME}/.aws/:/credproxy/.aws/:ro

      my-app:
        network_mode: service:credproxy # Critical: shares localhost
        environment:
          - AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:1338
          - AWS_CONTAINER_AUTHORIZATION_TOKEN=secure-token-2025

Step 3: Use with Any AWS SDK
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your application automatically gets credentials - no code changes needed!

.. code-block:: python

    import boto3

    # AWS SDK automatically uses CredProxy for credentials
    s3 = boto3.client("s3")
    s3.list_buckets()  # Just works!

API Reference
-------------

CredProxy implements standard AWS ECS credential provider interface:

- **GET** ``/`` - Service information and health status
- **GET** ``/health`` - Health check endpoint
- **GET** ``/metrics`` - Prometheus metrics (if enabled)

Health Check Implementation
---------------------------

CredProxy uses `lprobe <https://github.com/fivexl/lprobe>`_ for container health checks
- a lightweight, secure tool designed specifically for containerized environments.

**Why lprobe?**

- **Security**: Purpose-built for container health checks (replaces curl/wget)
- **Lightweight**: Minimal footprint for containerized deployments
- **Compatible**: Works with Docker, ECS, and Kubernetes
- **Hardened**: Designed to reduce attack surface in breached containers

All Docker Compose examples include proper healthcheck configuration:

.. code-block:: yaml

    healthcheck:
      test: [
        "CMD",
        "/bin/lprobe",
        "-mode=http",
        "-port=1338",
        "-endpoint=/health",
      ]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

See :doc:`installation/healthcheck` for complete health check configuration.

.. toctree::
    :maxdepth: 2
    :caption: Contents:

    installation/index
    configuration/index
    development/index
    troubleshooting/index
    api/index

Indices and tables
==================

- :ref:`genindex`
- :ref:`modindex`
- :ref:`search`
