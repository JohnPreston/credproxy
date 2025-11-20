Contributing to CredProxy
=========================

.. meta::
    :description: Contributing guide for CredProxy development with setup and testing instructions
    :keywords: CredProxy, contributing, development, Python, Poetry, testing, pull requests=

Thank you for your interest in contributing to CredProxy! This guide will help you get
started with development, testing, and submitting contributions.

Quick Start for Development

Prerequisites

- **Python 3.11+** - Required for development
- **Docker** - For container-based testing
- **Poetry** - Dependency management
- **Git** - Version control

Development Setup

.. code-block:: bash

    1. Clone the repository
    git clone <repository-url>
    cd credproxy

    2. Set up virtual environment and install tools
    python3 -m venv venv
    source venv/bin/activate
    pip install pip poetry -U --user

    3. Install dependencies with Poetry
    poetry install

    4. Activate the virtual environment
    poetry shell

    5. Run initial validation
    make validate

    6. Run the example to verify setup
    docker compose -f docker-compose.example.yaml up --build

Running CredProxy for Development

For development and testing, you can run CredProxy using multiple entry points:

Primary Method (Recommended)

.. code-block:: bash

    Development mode with Flask server
    poetry run credproxy --dev --config config.yaml

    Production mode
    poetry run credproxy --config config.yaml

    Validate configuration
    poetry run credproxy --validate-only --config config.yaml

Alternative Method (Development)

.. code-block:: bash

    Using Python module execution
    python -m credproxy --config config.yaml

    With Poetry
    poetry run python -m credproxy --config config.yaml

**Entry Points Summary:**

    - **``credproxy`` command** - Primary entry point (defined in pyproject.toml)
    - **``python -m credproxy``** - Alternative entry point for development
    - Both provide identical functionality and accept the same arguments
    - Use ``credproxy`` command for testing deployments
    - Use either method for development and testing

**Note**: Development mode requires existing AWS infrastructure (IAM roles/profiles).
For actual usage, see the main README.rst for Docker-based deployment.

Project Structure

.. code-block::

    credproxy/
    ├── credproxy/                 # Main source code
    │   ├── __init__.py           # Version and metadata
    │   ├── __main__.py          # Alternative entry point for python -m credproxy
    │   ├── cli.py                # Command-line interface (primary entry point)
    │   ├── config.py             # Configuration management
    │   ├── credentials_handler.py # AWS credential handling
    │   ├── main.py               # Flask application
    │   ├── substitutions.py      # Variable substitution logic
    │   ├── logging.py            # Logging configuration
    │   └── config-schema.json    # JSON Schema for validation

Testing

Running Tests

.. code-block:: bash

    Run all tests with coverage
    make test-cov

    Run tests without coverage
    make test

    Run specific test file
    poetry run pytest tests/test_config.py -v

    Run with specific pattern
    poetry run pytest tests/ -k "test_config" -v

Test Coverage

.. code-block:: bash

    View coverage report
    make test-cov-view

    Generate coverage summary
    make test-cov-summary

Writing Tests

Follow these guidelines when writing tests:

1. **Use descriptive test names** that explain what is being tested
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Mock external dependencies** (AWS calls, file I/O)
4. **Test both success and failure cases**
5. **Include edge cases and error conditions**

Testing New Features

Prometheus Metrics

When testing metrics functionality:

.. code-block:: python

    def test_metrics_endpoint_returns_prometheus_format():
        """Test that /metrics endpoint returns Prometheus-compatible format."""
        # Arrange
        client = app.test_client()

        # Act
        response = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        assert "text/plain" in response.content_type
        assert "credential_requests_total" in response.data.decode()


    def test_metrics_configuration_validation():
        """Test metrics configuration validation."""
        # Test valid configuration
        config = {"metrics": {"prometheus": {"enabled": True}}}
        assert validate_metrics_config(config) is True

        # Test invalid configuration
        config = {"metrics": {"prometheus": {"invalid_field": True}}}
        assert validate_metrics_config(config) is False

Dynamic Services

When testing dynamic services functionality:

.. code-block:: python

    def test_dynamic_services_file_watching():
        """Test that file watcher detects configuration changes."""
        # Arrange
        config_file = create_temp_config_file({"services": {}})
        watcher = FileWatcher(config_file)

        # Act
        update_config_file(config_file, {"services": {"new_service": {}}})
        watcher.check_for_changes()

        # Assert
        assert watcher.has_changes() is True


    def test_dynamic_services_validation():
        """Test dynamic service configuration validation."""
        # Test valid service addition
        new_service = {
            "auth_token": "token123",
            "assumed_role": {"RoleArn": "arn:aws:iam::123456789012:role/TestRole"},
        }
        assert validate_dynamic_service(new_service) is True

        # Test invalid service (missing required fields)
        invalid_service = {"auth_token": "token123"}
        assert validate_dynamic_service(invalid_service) is False

Health Check Logging

When testing health check logging:

.. code-block:: python

    def test_health_check_logging_configuration():
        """Test health check logging configuration."""
        # Test with logging enabled
        config = {"health_check": {"log_requests": True}}
        assert validate_health_check_config(config) is True

        # Test with logging disabled
        config = {"health_check": {"log_requests": False}}
        assert validate_health_check_config(config) is True


    def test_health_check_logging_output():
        """Test that health check requests are logged when enabled."""
        # Arrange
        with patch("credproxy.logger.LOG") as mock_log:
            config = {"health_check": {"log_requests": True}}

            # Act
            perform_health_check(config)

            # Assert
            mock_log.info.assert_called_with("Health check requested")

.. code-block:: python

    def test_config_validation_with_valid_iam_keys():
        """Test that valid IAM keys configuration passes validation."""
        # Arrange
        config = {
            "aws_defaults": {
                "region": "us-west-2",
                "auth_method": "iam_keys",
                "iam_keys": {
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                },
            },
            "services": {
                "test": {
                    "auth_token": "token",
                    "assumed_role": {"RoleArn": "arn:aws:iam::123456789012:role/TestRole"},
                }
            },
        }

        # Act
        result = validate_config(config)

        # Assert
        assert result is True

Code Style

Formatting

We use automated formatting tools:

.. code-block:: bash

    # Format code (ruff formatter with import sorting)
    make format

    # Check formatting without making changes
    make lint

Style Guidelines

- **Ruff formatter** with 88-character line length and built-in import sorting
- **Type hints** required for all functions
- **Docstrings** for all public functions and classes
- **No emojis** in code or comments (professional tone)

Import Style

.. code-block:: python

    from __future__ import annotations

    # Standard library
    import json
    import logging
    from typing import TYPE_CHECKING

    # Third-party
    import boto3
    from flask import Flask, request

    Local
    from credproxy.config import Config
    from credproxy.credentials_handler import CredentialsHandler

    if TYPE_CHECKING:
        from credproxy.types import ConfigType

Development Workflow

1. Create a Feature Branch

.. code-block:: bash

    git checkout -b feature/your-feature-name
    or
    git checkout -b fix/issue-description

2. Make Changes

   - Write code following the style guidelines
   - Add tests for new functionality
   - Update documentation if needed
   - Ensure all tests pass

3. Run Validation

.. code-block:: bash

    Run full validation suite
    make validate

    This includes:
       - Code formatting checks
       - Linting
       - Type checking
       - Tests with coverage

4. Commit Changes

Use conventional commit messages:

.. code-block::

    feat: add support for AWS session tokens
    fix: resolve credential refresh timing issue
    docs: update installation instructions
    test: add integration tests for IAM profiles
    refactor: simplify configuration validation

5. Submit Pull Request

   - Push your branch to the repository
   - Create a pull request with a clear description
   - Link any relevant issues
   - Ensure CI checks pass

Bug Reports

When reporting bugs, please include:

1. **Environment information**: - Python version - Docker version (if applicable) -
   Operating system
2. **Configuration**: - Redacted configuration file - Environment variables (without
   secrets)
3. **Steps to reproduce**: - Clear, reproducible steps - Expected vs actual behavior
4. **Logs**: - Relevant log output - Error messages and stack traces

Feature Requests

Feature requests are welcome! Please:

1. **Check existing issues** for similar requests
2. **Describe the use case** clearly
3. **Explain the proposed solution**
4. **Consider implementation complexity**

Documentation

Updating Documentation

    - **README.rst** - Project overview and quick start
    - **USAGE.md** - Detailed usage examples
    - **SECURITY.md** - Security considerations

Documentation Style

    - Use clear, concise language
    - Include code examples for all features
    - Add diagrams where helpful
    - Keep examples up-to-date with code changes

Release Process

Releases are managed using semantic versioning:

    - **MAJOR**: Breaking changes
    - **MINOR**: New features (backward compatible)
    - **PATCH**: Bug fixes (backward compatible)

Version Bumping

.. code-block:: bash

    Bump version (uses tbump)
    tbump patch  # or minor, major

    This updates:
       - pyproject.toml
       - credproxy/__init__.py
       - Creates git tag

Community Guidelines

Code of Conduct

    - Be respectful and inclusive
    - Welcome newcomers and help them learn
    - Focus on constructive feedback
    - Assume good intentions

Getting Help

    - **GitHub Issues** - Bug reports and feature requests
    - **Discussions** - General questions and ideas
    - **Documentation** - Check existing docs first

Development Tools

Make Commands

.. code-block:: bash

    make help           # Show all available commands
    make validate       # Run all checks (lint + test)
    make test           # Run tests
    make test-cov       # Run tests with coverage
    make lint           # Run linting checks (ruff)
    make format         # Format code (ruff formatter)
    make conform        # Format and lint code (ruff)
    make clean          # Clean build artifacts

Poetry Commands

.. code-block:: bash

    poetry install          # Install dependencies
    poetry shell           # Activate virtual environment
    poetry run <command>   # Run command in virtual environment
    poetry add <package>   # Add new dependency
    poetry update          # Update dependencies

Pre-commit Hooks

Pre-commit hooks are automatically configured:

    - **ruff** - Code formatting, linting, and import sorting
    - **pyupgrade** - Python syntax upgrades

These run automatically on commit and help maintain code quality.

Contributing Areas

We welcome contributions in these areas:

    - **Core functionality** - Credential handling, configuration
    - **Authentication methods** - New AWS auth approaches
    - **Performance** - Optimization and caching
    - **Documentation** - Examples, guides, API docs
    - **Testing** - Unit tests, integration tests
    - **Docker** - Multi-arch builds, optimization
    - **CI/CD** - GitHub Actions, workflows

Docker images build

Custom Docker Images

Build custom CredProxy images with specific configurations:

.. code-block:: dockerfile

    FROM public.ecr.aws/compose-x/aws/credproxy:latest
    COPY config.yaml /credproxy/config.yaml

Multi-Stage Builds

Use multi-stage builds for production deployments:

.. code-block:: dockerfile

    FROM python:3.11-slim as builder
    WORKDIR /app
    COPY . .
    RUN poetry install --only=main

    FROM python:3.11-slim
    COPY --from=builder /app /app
    WORKDIR /app
    CMD ["python", "-m", "credproxy.main"]

Questions?

If you have questions about contributing:

1. Check existing `Issues <https://github.com/johnpreston/credproxy/issues>`_
2. Start a `Discussion <https://github.com/johnpreston/credproxy/discussions>`_
3. Read the `Documentation <https://github.com/johnpreston/credproxy/docs>`_

----

Thank you for contributing to CredProxy!
