Configuration Schema Reference
==============================

.. meta::
    :description: JSON schema reference for CredProxy YAML configuration validation
    :keywords: CredProxy, JSON schema, configuration, validation, YAML, AWS roles=

This section provides the complete JSON schema for CredProxy configuration.

The schema is automatically validated when CredProxy starts, ensuring your configuration
is correct before attempting to assume roles or start the service.

Schema Location
---------------

The JSON schema is located at ``credproxy/config-schema.json`` in the repository.

You can view it at: https://github.com/johnpreston/credproxy/blob/main/credproxy/config-schema.json

Schema Overview
---------------

Required Fields
~~~~~~~~~~~~~~~

The only required top-level field is ``services``, which must contain at least one service configuration.

.. code-block:: json

    {
      "required": ["services"]
    }

Top-Level Properties
~~~~~~~~~~~~~~~~~~~~

- ``server`` - Server configuration (host, port, debug, log_health_checks)
- ``credentials`` - Global credential management settings
- ``aws_defaults`` - Default AWS credentials applied to all services
- ``services`` - Service-specific configurations (required)
- ``dynamic_services`` - Dynamic service file monitoring configuration
- ``metrics`` - Prometheus metrics configuration

Service Configuration
~~~~~~~~~~~~~~~~~~~~~

Each service must have:

- ``auth_token`` (string, required) - Unique token for client authentication
- ``source_credentials`` (object, required) - AWS credentials to use for assuming the role
- ``assumed_role`` (object, required) - IAM role configuration including RoleArn

Example service configuration:

.. code-block:: yaml

    services:
      my-app:
        auth_token: "secure-token-here"
        source_credentials:
          region: "us-west-2"
          iam_profile:
            profile_name: "default"
        assumed_role:
          RoleArn: "arn:aws:iam::123456789012:role/MyAppRole"
          RoleSessionName: "my-app-session"
          DurationSeconds: 3600

Source Credentials Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can configure source credentials in three ways:

1. **Default AWS SDK chain**

   Leave source_credentials minimal to use EC2/ECS roles, environment variables, or AWS CLI config:

   .. code-block:: yaml

       source_credentials:
         region: "us-west-2"

2. **IAM Profile**

   Specify a profile from ``~/.aws/config``:

   .. code-block:: yaml

       source_credentials:
         region: "us-west-2"
         iam_profile:
           profile_name: "my-profile"
           config_file: "/path/to/config"  # optional

3. **IAM Keys**

   Provide access key ID and secret access key:

   .. code-block:: yaml

       source_credentials:
         region: "us-west-2"
         iam_keys:
           aws_access_key_id: "AKIAIOSFODNN7EXAMPLE"
           aws_secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
           session_token: "optional-session-token"  # for temporary credentials

Role Assumption Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``assumed_role`` section supports all AWS STS AssumeRole parameters:

- ``RoleArn`` (required) - ARN of the role to assume
- ``RoleSessionName`` - Name for the session (default: "credproxy")
- ``DurationSeconds`` - Session duration 900-43200 seconds (default: 900)
- ``ExternalId`` - External ID for third-party access
- Additional STS parameters as needed

.. code-block:: yaml

    assumed_role:
      RoleArn: "arn:aws:iam::123456789012:role/MyRole"
      RoleSessionName: "my-session"
      DurationSeconds: 3600
      ExternalId: "unique-external-id"

Validation Rules
----------------

Pattern Properties
~~~~~~~~~~~~~~~~~~

Service names must match ``^[a-zA-Z0-9_-]+$`` (alphanumeric, underscore, hyphen).

All configuration objects support ``x-`` prefixed properties for custom extensions
that will be ignored by the validator.

AWS Access Key Format
~~~~~~~~~~~~~~~~~~~~~~

- ``aws_access_key_id`` must match ``^[A-Z0-9]{20}$``
- ``aws_secret_access_key`` must be exactly 40 characters

Role ARN Format
~~~~~~~~~~~~~~~

Role ARNs must match the pattern:

``^arn:aws:iam::[0-9]{12}:role/[a-zA-Z0-9+=,.@_/-]*[a-zA-Z0-9+=,.@_-]$``

Port Ranges
~~~~~~~~~~~

- ``server.port``: 1-65535
- ``metrics.prometheus.port``: 1024-65535

Duration Ranges
~~~~~~~~~~~~~~~

- ``credentials.refresh_buffer_seconds``: 0-3600
- ``credentials.retry_delay``: 1-300
- ``credentials.request_timeout``: 1-300
- ``assumed_role.DurationSeconds``: 900-43200
- ``dynamic_services.reload_interval``: 1-60

Dynamic Services Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``dynamic_services`` section enables automatic monitoring of configuration files
for hot-reloading services without restarting CredProxy.

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

**Directory Configuration Properties:**

- ``path`` (string, required) - Directory path to monitor
- ``include_patterns`` (array, optional) - List of regex patterns to include files. If empty, all non-excluded files are included
- ``exclude_patterns`` (array, optional) - List of regex patterns to exclude files

**Pattern Matching Rules:**

1. **Exclude first, then include** - Files matching exclude patterns are always ignored
2. **Empty include_patterns** means include all files that don't match exclude patterns
3. **Patterns are applied to full file paths** (supports directory-based matching)
4. **Regex patterns** use Python ``re.match()`` (matches from start of string)
5. **Cross-platform** paths are normalized with forward slashes

**Pattern Examples:**

.. code-block:: yaml

    # Include only YAML files, exclude hidden and backup files
    include_patterns: [".*\\.yaml$", ".*\\.yml$"]
    exclude_patterns: ["^\\..*", ".*~$", ".*\\.bak$"]

    # Include only dev-prefixed files
    include_patterns: ["^dev-.*\\.yaml$"]
    exclude_patterns: []

    # Include all files except hidden ones
    include_patterns: []
    exclude_patterns: ["^\\..*"]

    # Include files in specific subdirectories
    include_patterns: [".*/production/.*\\.yaml$", ".*/staging/.*\\.yaml$"]
    exclude_patterns: []

**Backward Compatibility:**

The old format is still supported for existing configurations:

.. code-block:: yaml

    # Old format (still works)
    dynamic_services:
      enabled: true
      directory: "/credproxy/dynamic"
      reload_interval: 5

This is automatically converted to the new format internally.

Environment Variable Substitution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Any string value in the configuration can use substitution:

- ``${fromEnv:VARIABLE_NAME}`` - Replace with environment variable value
- ``${fromFile:/path/to/file}`` - Replace with file contents (trimmed)

The substitution tags themselves can be customized via environment variables.
See :doc:`environment-variables` for details.

Full Schema Reference
---------------------

For the complete JSON schema definition with all properties, types, and constraints,
see the schema file: https://github.com/johnpreston/credproxy/blob/main/credproxy/config-schema.json

Example Configurations
----------------------

See :doc:`index` for complete example configurations demonstrating various features.
