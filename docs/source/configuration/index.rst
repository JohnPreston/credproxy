Configuration
=============

.. meta::
    :description: CredProxy configuration guide with YAML schema and environment variables
    :keywords: CredProxy, configuration, YAML, schema, environment variables, AWS IAM

.. toctree::
    :maxdepth: 2

    schema-reference
    environment-variables
    security
    schema_model

CredProxy uses YAML-based configuration with support for environment variable
substitution and file content injection. This makes it flexible for various
deployment scenarios from local development to production environments.

Authentication Methods
----------------------

- **Default** - AWS SDK default provider chain (EC2 instance profiles, ECS task roles, environment variables, AWS CLI profiles)
- **IAM Profiles** - Use AWS CLI profiles to assume target roles
- **IAM Keys** - Use AWS access keys to assume target roles

Configuration Structure
=======================

Basic Example
-------------

.. code-block:: yaml

    server:
      host: localhost
      port: 1338
      debug: false

    credentials:
      refresh_buffer_seconds: 300
      retry_delay: 60

    services:
      my-app:
        auth_token: "secure-token-here"
        source_credentials:
          region: "us-west-2"
        assumed_role:
          RoleArn: "arn:aws:iam::123456789012:role/MyAppRole"
          RoleSessionName: "my-app-session"
          DurationSeconds: 3600

With Environment Variable Substitution
---------------------------------------

.. code-block:: yaml

    services:
      my-app:
        auth_token: "${fromEnv:APP_AUTH_TOKEN}"
        source_credentials:
          region: "${fromEnv:AWS_DEFAULT_REGION}"
        assumed_role:
          RoleArn: "${fromEnv:APP_ROLE_ARN}"

With File Content Injection
----------------------------

Useful for reading secrets from files (Docker secrets, Kubernetes secrets, etc.):

.. code-block:: yaml

    services:
      my-app:
        auth_token: "${fromFile:/run/secrets/app_token}"
        source_credentials:
          region: "us-west-2"
        assumed_role:
          RoleArn: "arn:aws:iam::123456789012:role/MyAppRole"

Dynamic Services
----------------

CredProxy can monitor directories for service configuration files and dynamically
reload them without restarting. The new per-directory format provides flexible
file filtering with include/exclude patterns.

**New Per-Directory Format (Recommended):**

.. code-block:: yaml

    dynamic_services:
      enabled: true
      directories:
        - path: "/credproxy/dynamic"
          include_patterns: [".*\\.yaml$", ".*\\.yml$"]
          exclude_patterns: ["^\\..*", ".*~$", ".*\\.bak$"]
        - path: "/credproxy/dynamic-dev"
          include_patterns: ["^dev-.*\\.yaml$"]
          exclude_patterns: ["^\\..*"]
      reload_interval: 5

**Multiple Directories with Different Patterns:**

.. code-block:: yaml

    dynamic_services:
      enabled: true
      directories:
        # Production services - only YAML files, no hidden/backup files
        - path: "/credproxy/dynamic"
          include_patterns: [".*\\.yaml$", ".*\\.yml$"]
          exclude_patterns: ["^\\..*", ".*~$", ".*\\.bak$"]

        # Development services - only dev-prefixed files
        - path: "/credproxy/dynamic-dev"
          include_patterns: ["^dev-.*\\.yaml$"]
          exclude_patterns: ["^\\..*"]

        # JSON configurations (if needed)
        - path: "/credproxy/dynamic-json"
          include_patterns: [".*\\.json$"]
          exclude_patterns: ["^\\..*"]

        # Unfiltered directory - include all files
        - path: "/credproxy/dynamic-unfiltered"
          include_patterns: []
          exclude_patterns: []
      reload_interval: 5

**Pattern Matching Examples:**

- ``".*\\.yaml$"`` - Include files ending with .yaml
- ``"^dev-.*\\.yaml$"`` - Include files starting with dev- and ending with .yaml
- ``"^\\..*"`` - Exclude hidden files (starting with .)
- ``".*/production/.*\\.yaml$"`` - Include YAML files in production subdirectories
- ``[""]`` - Empty list means include all (for include_patterns) or exclude none (for exclude_patterns)

Each file in the monitored directories should contain a single service configuration:

.. code-block:: yaml

    # /credproxy/dynamic/service1.yaml
    auth_token: "service1-token"
    source_credentials:
      region: "us-west-2"
    assumed_role:
      RoleArn: "arn:aws:iam::123456789012:role/Service1Role"

**Backward Compatibility:**

The old format is still supported and automatically converted:

.. code-block:: yaml

    # Old format (still works)
    dynamic_services:
      enabled: true
      directory: "/credproxy/dynamic"
      reload_interval: 5
