CredProxy
=========

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

🚀 Quick Start
-------------

.. code-block:: bash

    # Clone and run with Docker in 30 seconds
    git clone https://github.com/johnpreston/credproxy.git && cd credproxy
    docker compose up --build

**Result**: You can expose AWS Credentials to your application as if running on ECS!

✨ Why CredProxy?
----------------

**Problem**: Applications often behave differently in local development vs production
when using AWS SDKs, especially around credential management and AWS service
integration.

**Solution**: CredProxy provides ECS-compatible credential endpoints locally, allowing
you to develop and test with the same credential management patterns that will be used
in production. This strengthens local implementation and helps catch issues early.

🎯 Key Features
--------------

- **🔄 ECS-Compatible** - Drop-in replacement for ECS credential providers
- **🔐 Multiple Auth Methods** - IAM profiles, access keys, with secure variable
  substitution
- **⚡ Zero Downtime** - Automatic credential rotation 5 minutes before expiry
- **🐳 Development Focused** - Designed for local development with Docker Compose
- **📝 Configurable** - YAML-based configuration with environment variable substitution
- **📊 Built-in Metrics** - Prometheus metrics for credential requests and service health

🔧 Authentication Methods
------------------------

================ =============================================================
Method           Description
================ =============================================================
**Default**      AWS SDK default provider chain (EC2, ECS, env vars, profiles)
**IAM Profiles** Assume container role from an existing profile
**IAM Keys**     Assume container role from AWS Keys
================ =============================================================

📦 Installation
--------------

Option 1: Docker (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/johnpreston/credproxy && cd credproxy
    # Build the container
    docker build -t credproxy .

Option 2: From Source (Development)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

🏗️ Architecture
---------------

**CredProxy runs directly with built-in signal handling** in containerized environments.

- **Docker**: Runs credproxy directly (recommended for production)
- **Direct credproxy**: ``credproxy --config config.yaml``
- **Environment variable**: ``CREDPROXY_CONFIG_FILE=/path/to/config.yaml``

For development and testing, see :doc:`development/contributing`.

🎯 How It Works
--------------

Step 1: Configure
~~~~~~~~~~~~~~~~~

Create a YAML configuration file (see ``examples/docker-compose-profile/config.yaml``):

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your application automatically gets credentials - no code changes needed!

.. code-block:: python

    import boto3

    # AWS SDK automatically uses CredProxy for credentials
    s3 = boto3.client("s3")
    s3.list_buckets()  # Just works!

🔍 Health Check Implementation
-----------------------------

CredProxy uses `lprobe <https://github.com/fivexl/lprobe>`_ for container health checks
- a lightweight, secure tool designed specifically for containerized environments.

**Why lprobe?**

- **🔒 Security**: Purpose-built for container health checks (replaces curl/wget)
- **⚡ Lightweight**: Minimal footprint for containerized deployments
- **🐳 Compatible**: Works with Docker, ECS, and Kubernetes
- **🛡️ Hardened**: Designed to reduce attack surface in breached containers

All Docker Compose examples include proper healthcheck configuration:

.. code-block:: yaml

    healthcheck:
      test: ["CMD", "/bin/lprobe", "http://localhost:1338/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

📡 API Reference
---------------

CredProxy implements standard AWS ECS credential provider interface:

Endpoints
~~~~~~~~~

- **Health Check**: ``GET /health`` - Service status (monitored by lprobe)
- **Credentials**: ``GET /v1/credentials`` - AWS credentials (requires ``Authorization``
  header)
- **Metrics**: ``GET /metrics`` - Prometheus metrics (when enabled)

Example Usage
~~~~~~~~~~~~~

.. code-block:: bash

    # Health check
    curl http://localhost:1338/health

    # Get credentials (with auth token)
    curl -H "Authorization: your-token" http://localhost:1338/v1/credentials

    # Get Prometheus metrics (when enabled)
    curl http://localhost:9090/metrics

**Response Format** (standard AWS ECS format):

.. code-block:: json

    {
      "AccessKeyId": "ASIA...",
      "SecretAccessKey": "...",
      "Token": "...",
      "Expiration": "2025-01-01T12:00:00Z"
    }

⚠️ Critical: Loopback Address Requirement
-----------------------------------------

The AWS SDK only accepts credential requests from loopback addresses for security
reasons:

- ✅ ``localhost``, ``127.0.0.1``
- ✅ ECS metadata IPs: ``169.254.170.2``, ``169.254.170.23``, ``fd00:ec2::23``
- ❌ Container names, custom hostnames

**Solution**: Use ``network_mode: service:credproxy`` in Docker Compose to share the
network namespace, making all containers see the same ``localhost:1338``. This satisfies
the AWS SDK's security requirement.

🛠️ Advanced Features
--------------------

🔒 Variable Substitution
~~~~~~~~~~~~~~~~~~~~~~~

Keep secrets out of your configuration files:

.. code-block:: yaml

    aws_defaults:
      iam_keys:
        aws_access_key_id: "${fromEnv:AWS_ACCESS_KEY_ID}"
        aws_secret_access_key: "${fromFile:/run/secrets/aws-secret}"

    services:
      app:
        auth_token: "${fromFile:/run/secrets/app-token}"

✅ JSON Schema Validation
~~~~~~~~~~~~~~~~~~~~~~~~

Every configuration is automatically validated with comprehensive error reporting:

- **Structure validation** - Required fields and proper nesting
- **Type checking** - Data types and formats
- **Pattern validation** - AWS ARNs, regions, credential formats
- **Range validation** - Port numbers, timeouts, buffer sizes
- **IDE support** - Use ``credproxy/config-schema.json`` for auto-completion

🎛️ Configuration Options
~~~~~~~~~~~~~~~~~~~~~~~~

- **Multiple services** - Different credentials per application
- **Environment overrides** - ``CREDPROXY_CONFIG_FILE`` environment variable
- **Sensible defaults** - Ready to use with minimal configuration
- **Flexible auth** - Mix IAM profiles and keys in same config

📊 Prometheus Metrics
~~~~~~~~~~~~~~~~~~~~

CredProxy includes built-in Prometheus metrics for observability:

.. code-block:: yaml

    metrics:
      prometheus:
        enabled: true # Enable metrics endpoint
        host: 0.0.0.0 # Expose metrics on all interfaces
        port: 9090 # Separate port for metrics

**Available Metrics:**

- ``credproxy_requests_total`` - Credential requests per service (success/error)
- ``credproxy_active_services_total`` - Number of active services
- ``credproxy_info`` - Application version information

**Access Metrics:**

.. code-block:: bash

    curl http://localhost:9090/metrics

**Configuration Options:**

.. code-block:: yaml

    metrics:
      prometheus:
        enabled: true # Enable/disable metrics (default: true)
        host: 0.0.0.0 # Metrics server host (default: 0.0.0.0)
        port: 9090 # Metrics server port (default: 9090)

**Docker Compose with Metrics:**

.. code-block:: yaml

    services:
      credproxy:
        ports:
          - "1338:1338" # API port (localhost only)
          - "9090:9090" # Metrics port (0.0.0.0)

🔄 Dynamic Services
~~~~~~~~~~~~~~~~~~

CredProxy supports dynamic service configuration with hot-reloading - add, remove, or
update services without restarting:

.. code-block:: yaml

    dynamic_services:
      enabled: true # Enable dynamic services monitoring
      directory: /credproxy/dynamic # Directory to monitor
      file_pattern: "*.yaml" # File pattern for service configs
      reload_interval: 5 # Debounce interval in seconds

**How It Works:**

1. **File Watching**: Monitors specified directory for YAML configuration files
2. **Hot Reloading**: Automatically loads new/updated service configurations
3. **Debouncing**: Prevents rapid reloads with configurable interval
4. **Service Management**: Add, update, or remove services dynamically

**Dynamic Service File Format:**

.. code-block:: yaml

    # /credproxy/dynamic/new-service.yaml
    auth_token: "dynamic-service-token"
    source_credentials:
      region: "us-west-2"
      iam_profile:
        profile_name: default
    assumed_role:
      RoleArn: "arn:aws:iam::123456789012:role/DynamicServiceRole"
      RoleSessionName: "dynamic-service-session"

**Docker Compose with Dynamic Services:**

.. code-block:: yaml

    services:
      credproxy:
        volumes:
          - ./config.yaml:/credproxy/config.yaml:ro
          - ./dynamic:/credproxy/dynamic:ro # Mount dynamic services directory
          - ${HOME}/.aws/:/credproxy/.aws/:ro

**Use Cases:**

- **Multi-tenant environments**: Add/remove tenant services on demand
- **CI/CD pipelines**: Dynamically configure services during deployment
- **Development**: Test new service configurations without restart
- **Microservices**: Manage multiple service credentials centrally

📝 Health Check Logging
~~~~~~~~~~~~~~~~~~~~~~

Control health check request logging to reduce log noise in production environments:

.. code-block:: yaml

    server:
      host: localhost
      port: 1338
      log_health_checks: false # Disable health check logging (default)

**Configuration Options:**

- **Configuration File**: Set ``server.log_health_checks: true``
- **Environment Variable**: Set ``CREDPROXY_LOG_HEALTH_CHECKS=true``
- **OR Logic**: Either method can enable logging

**Environment Variable Values:**

.. code-block:: bash

    # Any of these values enable health check logging
    export CREDPROXY_LOG_HEALTH_CHECKS=true
    export CREDPROXY_LOG_HEALTH_CHECKS=1
    export CREDPROXY_LOG_HEALTH_CHECKS=yes
    export CREDPROXY_LOG_HEALTH_CHECKS=on

**Docker Compose Example:**

.. code-block:: yaml

    services:
      credproxy:
        environment:
          CREDPROXY_LOG_HEALTH_CHECKS: "true" # Enable health check logging

**Behavior:**

- **Default**: Health check logging is **disabled** (reduces noise)
- **When disabled**: No logs for successful health check requests (200 OK)
- **When enabled**: Logs every health check access with service count
- **Error logging**: Health check errors are always logged regardless of setting

**When to Enable:**

- ✅ Debugging health check issues
- ✅ Monitoring health check patterns
- ✅ Development and testing environments
- ❌ Production (unless needed for specific monitoring)

🖥️ CLI Reference
----------------

Command-Line Options
~~~~~~~~~~~~~~~~~~~~

CLI Options

- ``--config``: Path to configuration file (default: ``/credproxy/config.yaml``)
  Example: ``./my-config.yaml``
- ``--validate-only``: Validate configuration and exit (default: ``False``) Example:
  ``--validate-only``
- ``--log-level``: Set logging level (default: ``INFO``) Example: ``--log-level DEBUG``
- ``--version``: Show version information (default: ``-``) Example: ``--version``
- ``--dev``: Enable development mode (default: ``False``) Example: ``--dev``

Development Mode
~~~~~~~~~~~~~~~~

The ``--dev`` flag enables development-friendly settings:

.. code-block:: bash

    # Development mode (sets debug=True and log-level=DEBUG)
    poetry run credproxy --dev --config config.yaml

    # Equivalent to:
    poetry run credproxy --config config.yaml --log-level DEBUG

**Development Mode Features:**

- **Debug logging**: Detailed output for troubleshooting
- **Debug server**: Flask debug mode enabled
- **Verbose output**: More detailed request/response logging

Common Usage Patterns
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Validate configuration
    poetry run credproxy --validate-only --config config.yaml

    # Production mode
    poetry run credproxy --config config.yaml

    # Development with custom config
    poetry run credproxy --dev --config ./dev-config.yaml

    # Check version
    poetry run credproxy --version

Testing
-------

.. code-block:: bash

    make coverage

📚 Documentation
---------------

**📖 Full Documentation**: docs/build/html/index.html

- **README.rst**: Main documentation (this file)
- **API Reference**: Complete API documentation
- **Configuration Reference**: All configuration options
- **Examples**: Docker Compose examples
- **Development**: Development setup and contribution guide
- **Troubleshooting**: Common issues and solutions

**Legacy Documentation**:

- **USAGE.md**: Detailed CLI and Docker Compose examples
- **CONTRIBUTING.md**: Development setup and contribution guide
- **SECURITY.md**: Security considerations and best practices
- **CHANGELOG.md**: Version history and release notes

🚀 Quick Examples
----------------

Basic Setup
~~~~~~~~~~~

.. code-block:: bash

    cd examples/docker-compose-basic/
    docker compose up -d
    curl http://localhost:1338/health

Production Deployment
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    cd examples/docker-compose-profile/
    # Configure your environment
    docker compose up -d

Multi-Account Management
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    cd examples/docker-compose-multi-role/
    # Set up multiple AWS accounts
    docker compose up -d
    curl http://localhost:1338/health

**👉 See `examples/ <examples/>`_ for complete setup instructions**

External References
~~~~~~~~~~~~~~~~~~~

- **`AWS Container Credential Provider
  <https://docs.aws.amazon.com/sdkref/latest/guide/feature-container-credentials.html>`_**
  - Official AWS documentation
- **`AWS CLI Environment Variables
  <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html>`_** -
  Complete reference

🏗️ Architecture
---------------

Network Namespace Sharing
~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: docs/network-namespace.svg
    :alt: Network Namespace Sharing

**Key Insight**: All containers share the same network namespace, so they all see
``localhost:1338``. This satisfies the AWS SDK's security requirement for loopback
addresses.

Credential Flow Timeline
~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: docs/credential-flow.svg
    :alt: Credential Flow Timeline

**Zero Downtime**: Credentials refresh 5 minutes before expiry in the background,
ensuring your applications never experience credential rotation interruptions.

📄 License
---------

Mozilla Public License 2.0 - see LICENSE file for details.

---

🤝 Contributing
--------------

Contributions welcome! Please see CONTRIBUTING.md for development setup and guidelines.
