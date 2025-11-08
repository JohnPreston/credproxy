Changelog
=========

.. meta::
    :description: Version history and changelog for CredProxy releases
    :keywords: CredProxy, changelog, version history, releases, updates

All notable changes to CredProxy will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_, and
this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

[0.2.0] - 2025-01-08

Added

    - **Per-directory pattern filtering** for dynamic services configuration
    - **Multiple directory support** with individual include/exclude patterns
    - **Backward compatibility** for existing dynamic services configurations
    - **Enhanced regex pattern matching** with cross-platform path normalization
    - **Comprehensive pattern examples** and documentation updates

Changed

    - **Dynamic services configuration** now supports array of directory objects
    - **File filtering logic** improved with exclude-first, then include approach
    - **Configuration validation** updated to support new directory object format
    - **Documentation** enhanced with pattern matching examples and migration guide

Features

    - **DirectoryConfig** dataclass for per-directory configuration
    - **Pattern matching functions** with proper error handling for invalid regex
    - **Cross-platform path normalization** for consistent pattern matching
    - **Enhanced logging** for pattern matching decisions
    - **Test coverage** expanded to 277 tests covering all new functionality

Configuration

    - **New format**: ``directories`` array with ``path``, ``include_patterns``, ``exclude_patterns``
    - **Old format**: Still supported via automatic conversion
    - **Pattern flexibility**: Support for complex regex patterns and directory-based filtering
    - **Multiple directories**: Each with independent filtering rules

Migration

    - **No breaking changes** - existing configurations continue to work
    - **Optional upgrade** - new format provides enhanced filtering capabilities
    - **Gradual adoption** - mix old and new formats during transition

[0.1.0] - 2025-01-22

Added

    - Initial release of CredProxy - ECS-compatible AWS credentials proxy
    - ECS-compatible credential provider endpoint (``/v1/credentials``)
    - Support for IAM profiles and IAM keys authentication methods
    - JSON Schema validation for configuration files with comprehensive error reporting
    - Variable substitution with ``${fromEnv:}`` and ``${fromFile:}`` syntax
    - Automatic credential rotation with configurable refresh buffer (default: 5
      minutes)
    - Docker Compose integration examples for various authentication scenarios
    - Comprehensive test suite with 140 tests and 66% code coverage
    - Proper signal handling for graceful container shutdown
    - Health check endpoint (``/health``) with lprobe integration
    - CLI with validation, debug options, and development mode
    - Non-root Docker container execution (UID/GID 1338) for security
    - Dynamic services configuration with file watching capabilities
    - Secure credential storage in memory only (no persistence)
    - Token-based authentication with per-service authorization tokens

Features

Authentication Methods

    - IAM profile support with custom config files
    - IAM keys with optional session tokens
    - Per-service authentication configuration
    - AWS SDK default provider chain fallback

Configuration

    - YAML-based configuration with JSON Schema validation
    - Environment variable substitution
    - File content substitution for secrets
    - Configurable substitution syntax via environment variables
    - Multiple services with different AWS roles/accounts
    - Dynamic services with hot-reloading

Server

    - Flask-based HTTP server
    - Configurable host and port (default: localhost:1338)
    - Health check endpoint at ``/health``
    - Debug mode support
    - Structured JSON logging with service context

Credential Management

    - Background credential refresh
    - Configurable refresh buffer (default: 300 seconds)
    - Retry logic with configurable delays
    - Request timeout handling
    - In-memory caching with expiration

Docker Integration

    - Multi-stage Dockerfile for optimized images
    - Docker Compose examples for all scenarios
    - Network namespace sharing for localhost access
    - Health checks in Docker Compose
    - Non-root user execution

Configuration Options

    - ``aws_defaults`` - Global AWS settings
    - ``services`` - Per-service credential configurations
    - ``server`` - HTTP server settings
    - ``credentials`` - Credential management settings
    - ``dynamic_services`` - Dynamic configuration monitoring

Environment Variables

    - ``CREDPROXY_CONFIG_FILE`` - Path to configuration file
    - ``CREDPROXY_FROM_ENV_TAG`` - Custom environment variable tag
    - ``CREDPROXY_FROM_FILE_TAG`` - Custom file content tag
    - ``CREDPROXY_TAG_SEPARATOR`` - Custom substitution separator

CLI Options

    - ``--config`` - Configuration file path
    - ``--validate-only`` - Validate configuration and exit
    - ``--log-level`` - Set logging level
    - ``--version`` - Show version information
    - ``--dev`` - Enable development mode

Documentation

    - Comprehensive README with quick start guide
    - Detailed USAGE.md with examples
    - Contributing guidelines with development setup
    - Security policy with best practices
    - JSON Schema for IDE auto-completion
    - Architecture diagrams and credential flow

Testing

    - Unit tests for all major components (140 tests)
    - Integration tests with Docker
    - Configuration validation tests
    - Coverage reporting (66% overall)
    - Pre-commit hooks for code quality

Security

    - Non-root container execution (UID/GID 1338)
    - Minimal Alpine Linux base image
    - Token-based authentication per service
    - Memory-only credential storage
    - Network isolation with loopback requirements
    - Role-based access control with least privilege
    - Automatic credential rotation
    - Comprehensive logging with sensitive data sanitization
    - Vulnerability reporting process

Examples Included

    - **docker-compose-profile/** - IAM profile authentication (RECOMMENDED)
    - **docker-compose-basic/** - IAM keys authentication
    - **docker-compose-multi-role/** - Single profile, multiple roles
    - **docker-compose-multi-auth/** - Different auth per service
    - **python-quickstart/** - Development and testing setup
    - **kafka_tiered_storage/** - Real-world Kafka use case
    - **dynamic/** - Dynamic service configuration examples

----

Version History

Version Format

This project follows semantic versioning: ``MAJOR.MINOR.PATCH``

    - **MAJOR**: Breaking changes that require configuration or API changes
    - **MINOR**: New features that are backward compatible
    - **PATCH**: Bug fixes and minor improvements

Release Process

1. Update version in ``pyproject.toml`` and ``credproxy/__init__.py``
2. Update this CHANGELOG.md
3. Create git tag with version number
4. Build and release Docker image

Migration Guide

When upgrading between major versions, check this section for migration instructions.

From 0.0.x to 0.1.0

No migration required - initial release.

----

Support

For questions about specific changes or upgrade assistance:

1. Check the `Documentation <README.rst>`_
2. Review `Usage Examples <USAGE.md>`_
3. Open an `Issue <https://github.com/johnpreston/credproxy/issues>`_
