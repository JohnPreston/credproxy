Troubleshooting
===============

.. meta::
    :description: Troubleshooting guide for common CredProxy issues and solutions
    :keywords: CredProxy, troubleshooting, debugging, issues, solutions, Docker

.. figure:: /_static/network-namespace.svg
    :alt: CredProxy Network Namespace
    :align: center

    CredProxy Network Namespace Architecture



Common Issues
-------------

Port Conflicts
~~~~~~~~~~~~~~

.. code-block:: bash

    # Check port usage
    netstat -tulpn | grep 1338

    # Change port in configuration
    server:
      port: 1339

Credential Errors
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Check AWS credentials
    aws sts get-caller-identity

    # Verify environment variables
    docker compose exec credproxy env | grep AWS

Network Issues
~~~~~~~~~~~~~~

.. code-block:: bash

    # Check container networking
    docker network ls
    docker compose ps

    # Test connectivity
    docker compose exec credproxy curl http://localhost:1338/health

Configuration Errors
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Validate configuration
    poetry run credproxy --validate-only --config config.yaml

    # Check logs
    docker compose logs credproxy

Debug Mode
----------

Enable debug logging for detailed troubleshooting:

.. code-block:: yaml

    # config.yaml
    server:
      debug: true

.. code-block:: bash

    # Or via CLI
    poetry run credproxy --dev --log-level DEBUG
