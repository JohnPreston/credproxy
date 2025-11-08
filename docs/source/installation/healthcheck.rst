Health Check Configuration
===========================

.. meta::
    :description: Health check configuration for CredProxy using lprobe in containerized environments
    :keywords: CredProxy, health check, lprobe, Docker, Kubernetes, monitoring=

Health Check Endpoint
---------------------

CredProxy provides a ``/health`` endpoint that returns service status.

.. code-block:: json

    {
      "status": "healthy",
      "services": {
        "service1": "active",
        "service2": "active"
      },
      "timestamp": "2025-01-15T10:30:00Z"
    }

HTTP Status: ``200 OK`` for healthy, ``503 Service Unavailable`` for degraded.


CredProxy uses `lprobe <https://github.com/fivexl/lprobe>`_ for container health checks.

Docker Health Check Configuration
----------------------------------

Docker Compose
~~~~~~~~~~~~~~

.. code-block:: yaml

    services:
      credproxy:
        build: .
        healthcheck:
          test: [
            "CMD",
            "/bin/lprobe",
            "-mode=http",
            "-port=1338",
            "-endpoint=/health",
          ]
          interval: 30s
          timeout: 10s
          retries: 3
          start_period: 10s

.. lprobe: https://github.com/fivexl/lprobe
