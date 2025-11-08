=============================
Docker Build Documentation
=============================

Overview
========

The CredProxy Docker image is optimized for size, security, and build caching. It uses multi-stage builds and includes build-time metadata for version tracking in logs.

Build Arguments
===============

The Dockerfile supports the following build arguments:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Argument
     - Default
     - Description
   * - ``PYTHON_VERSION``
     - ``3.13``
     - Python version to use (e.g., 3.11, 3.12, 3.13)
   * - ``GIT_COMMIT``
     - ``unknown``
     - Git commit hash for build tracking
   * - ``BUILD_DATE``
     - ``unknown``
     - ISO 8601 build timestamp
   * - ``LPROBE_VERSION``
     - ``v0.1.6``
     - Version of lprobe health check binary

Building the Image
==================

Using Make (Recommended)
------------------------

The simplest way to build with all metadata included:

.. code-block:: bash

   make docker-build

This automatically:

- Generates the SBOM (Software Bill of Materials)
- Extracts the current git commit hash
- Sets the build date to current UTC time
- Passes all build arguments to docker compose

Using Docker Compose
--------------------

When using docker compose directly, you can set environment variables:

.. code-block:: bash

   # Let docker-compose use defaults (unknown)
   docker compose build

   # Or set build args via environment variables
   GIT_COMMIT=$(git rev-parse --short HEAD) \
   BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
   docker compose build

Using Docker CLI Directly
-------------------------

For direct docker builds:

.. code-block:: bash

   docker build \
     --build-arg PYTHON_VERSION=3.13 \
     --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) \
     --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
     -f docker/Dockerfile \
     -t credproxy:latest \
     .

Building with Different Python Versions
----------------------------------------

.. code-block:: bash

   # Python 3.11
   docker build --build-arg PYTHON_VERSION=3.11 -f docker/Dockerfile -t credproxy:py311 .

   # Python 3.12
   docker build --build-arg PYTHON_VERSION=3.12 -f docker/Dockerfile -t credproxy:py312 .

Version Tracking in Logs
=========================

Build-Time Information
----------------------

During the Docker build, a ``_build_info.py`` file is generated with:

.. code-block:: python

   """Build-time information."""

   __version__ = "0.1.0"
   __git_commit__ = "abc1234"  # From GIT_COMMIT build arg
   __build_date__ = "2025-01-01T12:00:00Z"  # From BUILD_DATE build arg

This file is imported by ``credproxy/__init__.py`` and used by the logging system.

Log Output
----------

Version information appears in **INFO level logs only** as structured JSON:

.. code-block:: json

   {
     "timestamp": 1234567890.123,
     "levelname": "INFO",
     "message": "Starting CredProxy...",
     "name": "credproxy",
     "credproxy.version": "0.1.0",
     "credproxy.git_commit": "abc1234"
   }

**Important Notes:**

- Version fields only appear in ``INFO`` level logs
- Fields are **excluded** if values are ``unknown``, ``development``, ``none``, or empty
- This keeps logs clean during development while providing tracking in production

Development vs Production
-------------------------

**Local Development:**

- ``__git_commit__`` defaults to ``"development"``
- Version fields won't appear in logs (filtered out)

**Docker Build (with make docker-build):**

- ``__git_commit__`` will be actual git hash (e.g., ``"0c83fca"``)
- ``__build_date__`` will be build timestamp
- Version fields appear in INFO logs

**Docker Build (without build args):**

- ``__git_commit__`` will be ``"unknown"``
- Version fields won't appear in logs (filtered out)

Multi-Stage Build Process
==========================

The Dockerfile uses three stages:

1. **deps-export**: Exports Poetry dependencies to requirements.txt
2. **builder**: Installs dependencies in a Python virtual environment
3. **final**: Minimal runtime image with only application code and venv

This approach:

- Reduces final image size by ~20-30%
- Improves build caching
- Separates build-time tools from runtime

Image Optimization Features
============================

- **Virtual environment isolation**: Dependencies in ``/opt/venv`` instead of global
- **Multi-stage builds**: Only runtime dependencies in final image
- **Build caching**: Separate layers for dependencies vs code
- **Non-root user**: Runs as ``credproxy`` user (UID/GID 1338)
- **Health checks**: lprobe binary for container health monitoring
- **Minimal base**: Alpine Linux for small image size
- **Security**: No unnecessary packages or files in final image

Health Checks
=============

The image includes lprobe for health checking:

.. code-block:: bash

   # Default health check (configured in Dockerfile)
   /bin/lprobe --port 8080

   # Custom health check in docker-compose
   healthcheck:
     test: ["/bin/lprobe", "-mode=http", "-port=1338", "-endpoint=/health"]

Troubleshooting
===============

Git commit shows as "unknown"
------------------------------

Check that:

1. You're in a git repository
2. Git is installed on the build machine
3. You're using ``make docker-build`` or setting ``GIT_COMMIT`` manually

Version info not appearing in logs
-----------------------------------

This is expected if:

- Log level is not ``INFO``
- Git commit is "unknown" or "development"
- Running locally without Docker build

Build fails with "Unsupported platform"
----------------------------------------

The image supports ``linux/amd64`` and ``linux/arm64``. Set ``TARGETPLATFORM`` build arg if needed.

Best Practices
==============

1. **Always use** ``make docker-build`` for consistent builds with metadata
2. **Pin Python version** in production builds for reproducibility
3. **Use multi-platform builds** for production: ``docker buildx build --platform linux/amd64,linux/arm64``
4. **Keep config.yaml separate** - mount as volume, don't bake into image
5. **Use secrets management** - leverage ``init_secrets.sh`` for Docker secrets
