Environment Variables Reference
===============================

.. meta::
    :description: Complete reference for CredProxy environment variables and runtime configuration
    :keywords: CredProxy, environment variables, configuration, runtime, Docker, Kubernetes

CredProxy supports configuration via environment variables for operational flexibility
in containerized environments. All environment variables use the ``CREDPROXY_`` namespace
by default.

Core Environment Variables
---------------------------

These variables are defined in ``credproxy/settings.py`` and control CredProxy's runtime behavior.

Configuration File
~~~~~~~~~~~~~~~~~~

``CREDPROXY_CONFIG_FILE``
    Path to the YAML configuration file.

    **Default:** ``/credproxy/config.yaml``

    **Example:** ``CREDPROXY_CONFIG_FILE=/app/config.yaml``

Namespace Configuration
~~~~~~~~~~~~~~~~~~~~~~~

``CREDPROXY_NAMESPACE``
    Custom namespace prefix for all environment variables.

    **Default:** ``CREDPROXY_``

    **Example:** ``CREDPROXY_NAMESPACE=MYAPP_``

    **Note:** Changing this allows you to use a custom prefix like ``MYAPP_CONFIG_FILE``

Variable Substitution Tags
~~~~~~~~~~~~~~~~~~~~~~~~~~

``CREDPROXY_FROM_ENV_TAG``
    Tag name used for environment variable substitution in config files.

    **Default:** ``fromEnv``

    **Usage in config:**

    .. code-block:: yaml

        region: "${fromEnv:AWS_DEFAULT_REGION}"

``CREDPROXY_FROM_FILE_TAG``
    Tag name used for file content substitution in config files.

    **Default:** ``fromFile``

    **Usage in config:**

    .. code-block:: yaml

        auth_token: "${fromFile:/run/secrets/token}"

``CREDPROXY_TAG_SEPARATOR``
    Separator character used between tag name and value.

    **Default:** ``:``

    **Example:** With separator ``|``, you would use ``${fromEnv|AWS_REGION}``

Logging Configuration
~~~~~~~~~~~~~~~~~~~~~

``CREDPROXY_LOG_LEVEL``
    Logging level for the application.

    **Default:** ``warning``

    **Valid values:** ``debug``, ``info``, ``warning``, ``error``, ``critical`` (case-insensitive)

    **Example:** ``CREDPROXY_LOG_LEVEL=info``

``CREDPROXY_LOG_HEALTH_CHECKS``
    Enable logging for health check requests (non-error responses).

    **Default:** ``false``

    **Valid values:** ``true``, ``1``, ``yes``, ``on`` (case-insensitive) enable logging;
    any other value disables it.

    **Example:** ``CREDPROXY_LOG_HEALTH_CHECKS=true``

Configuration Schema Variables
------------------------------

These variables correspond to the JSON schema and allow overriding YAML configuration values.

Server Configuration
~~~~~~~~~~~~~~~~~~~~

``CREDPROXY_HOST``
    Server host address.

    **Default:** ``localhost``

    **From schema:** ``server.host``

``CREDPROXY_PORT``
    Server port number.

    **Default:** ``1338``

    **Range:** 1-65535

    **From schema:** ``server.port``

``CREDPROXY_DEBUG``
    Enable debug mode.

    **Default:** ``false``

    **From schema:** ``server.debug``

Credentials Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

``CREDPROXY_REFRESH_BUFFER_SECONDS``
    Refresh credentials this many seconds before expiry.

    **Default:** ``300`` (5 minutes)

    **Range:** 0-3600

    **From schema:** ``credentials.refresh_buffer_seconds``

``CREDPROXY_RETRY_DELAY``
    Retry delay on errors in seconds.

    **Default:** ``60``

    **Range:** 1-300

    **From schema:** ``credentials.retry_delay``

``CREDPROXY_REQUEST_TIMEOUT``
    Request timeout for external requests in seconds.

    **Default:** ``30``

    **Range:** 1-300

    **From schema:** ``credentials.request_timeout``

Dynamic Services Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``CREDPROXY_DYNAMIC_SERVICES_ENABLED``
    Enable dynamic services monitoring.

    **Default:** ``false``

    **From schema:** ``dynamic_services.enabled``

``CREDPROXY_DYNAMIC_SERVICES_DIRECTORIES``
    List of directories to monitor for service configuration files.
    For new per-directory format, this accepts comma-separated paths only.
    For full per-directory configuration (include/exclude patterns),
    use YAML configuration file.

    **Default:** ``/credproxy/dynamic``

    **From schema:** ``dynamic_services.directories``

    **Note:** Environment variable only supports directory paths. For include/exclude
    patterns, use YAML configuration file.

``CREDPROXY_DYNAMIC_SERVICES_RELOAD_INTERVAL``
    Reload interval in seconds for debouncing file changes.

    **Default:** ``5``

    **Range:** 1-60

    **From schema:** ``dynamic_services.reload_interval``

Metrics Configuration
~~~~~~~~~~~~~~~~~~~~~

``CREDPROXY_METRICS_PROMETHEUS_ENABLED``
    Enable Prometheus metrics endpoint.

    **Default:** ``true``

    **From schema:** ``metrics.prometheus.enabled``

``CREDPROXY_METRICS_PROMETHEUS_HOST``
    Host address for Prometheus metrics server.

    **Default:** ``0.0.0.0``

    **From schema:** ``metrics.prometheus.host``

``CREDPROXY_METRICS_PROMETHEUS_PORT``
    Port for Prometheus metrics server (separate from main API).

    **Default:** ``9090``

    **Range:** 1024-65535

    **From schema:** ``metrics.prometheus.port``

Usage Examples
--------------

Docker Compose
~~~~~~~~~~~~~~

.. code-block:: yaml

    services:
      credproxy:
        image: public.ecr.aws/compose-x/aws/credproxy:latest
        environment:
          - CREDPROXY_LOG_LEVEL=info
          - CREDPROXY_LOG_HEALTH_CHECKS=true
          - CREDPROXY_REFRESH_BUFFER_SECONDS=600
          - CREDPROXY_METRICS_PROMETHEUS_ENABLED=true

Kubernetes
~~~~~~~~~~

.. code-block:: yaml

    apiVersion: v1
    kind: Pod
    metadata:
      name: credproxy
    spec:
      containers:
      - name: credproxy
        image: public.ecr.aws/compose-x/aws/credproxy:latest
        env:
        - name: CREDPROXY_LOG_LEVEL
          value: "info"
        - name: CREDPROXY_CONFIG_FILE
          value: "/config/credproxy.yaml"
        - name: CREDPROXY_DYNAMIC_SERVICES_ENABLED
          value: "true"

ECS Task Definition
~~~~~~~~~~~~~~~~~~~

.. code-block:: json

    {
      "containerDefinitions": [
        {
          "name": "credproxy",
          "image": "public.ecr.aws/compose-x/aws/credproxy:latest",
          "environment": [
            {
              "name": "CREDPROXY_LOG_LEVEL",
              "value": "info"
            },
            {
              "name": "CREDPROXY_METRICS_PROMETHEUS_ENABLED",
              "value": "true"
            }
          ]
        }
      ]
    }
