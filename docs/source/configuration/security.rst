Security Policy
===============

.. meta::
    :description: Security considerations and best practices for CredProxy deployment
    :keywords: CredProxy, security, AWS IAM, best practices, containers, credentials=

This document outlines security considerations and best practices for using CredProxy.

.. contents::
    :depth: 2
    :local:

Security Model

CredProxy is designed to provide AWS credentials to applications in a secure manner,
following AWS security best practices for container environments.

Important: Credential Purpose Clarification

Unlike ``aws ecs-local-endpoints``, CredProxy is designed to provide specific AWS
credentials to the applications, ensuring that each application receives the necessary
permissions for its specific tasks.

**Security Model**:

1. **CredProxy credentials** → Used to assume service-specific IAM roles
2. **Assumed role credentials** → Provided to your applications
3. **Applications** → Use assumed role credentials for AWS operations

This separation ensures:

    - CredProxy only needs permission to assume specific roles
    - Applications get least-privilege credentials for their specific tasks
    - Clear audit trail through role session names
    - No direct exposure of CredProxy's base credentials

Security Boundaries

    - **Network isolation**: Works with AWS SDK loopback address requirements
    - **Token-based authentication**: Each service requires unique auth tokens
    - **Credential isolation**: Services can only access their own credentials
    - **Secure storage**: Credentials are stored in memory only, not persisted

Secure Configuration

Authentication Tokens

Use strong, unique authorization tokens for each service:

.. code-block:: yaml

    services:
      web-app:
        auth_token: "web-app-secure-token-2025-abc123def456"
      worker:
        auth_token: "worker-secure-token-2025-xyz789uvw012"

**Best practices:**

    - Use cryptographically random tokens (32+ characters)
    - Rotate tokens regularly
    - Don't use predictable patterns
    - Store tokens securely (environment variables, secrets management)

Generating Secure Tokens

Python Method (Recommended)

.. code-block:: bash

    Generate 32-character random token
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"

Docker Method

.. code-block:: bash

    Generate token using Docker (no Python installation needed)
    docker run --rm python:3-alpine python3 -c "import secrets; print(secrets.token_urlsafe(32))"

Linux Command Line Alternative

.. code-block:: bash

    Generate 32-character random token (requires openssl)
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32

**Example output**: ``x7J9k2m5p8q1r4t7w0z3c6v9b2n5f8g1``

Variable Substitution

Use secure variable substitution to avoid hardcoding secrets:

.. code-block:: yaml

    aws_defaults:
      iam_keys:
        access_key_id: "${fromEnv:AWS_ACCESS_KEY_ID}"
        secret_access_key: "${fromFile:/run/secrets/aws-secret}"

    services:
      app:
        auth_token: "${fromFile:/run/secrets/app-token}"

Network Security

Loopback Address Requirement

The AWS SDK only accepts requests from loopback addresses for security reasons:

    - ``localhost``, ``127.0.0.1``
    - ECS metadata IPs: ``169.254.170.2``, ``169.254.170.23``, ``fd00:ec2::23``

**Implementation in Docker Compose:**

.. code-block:: yaml

    services:
      your-app:
        network_mode: service:credproxy # Shares network namespace

AWS Security Integration

IAM Role Assumption

CredProxy uses AWS STS to assume roles, following AWS best practices:

.. code-block:: yaml

    services:
      app:
        auth_token: "secure-token"
        source_credentials:
          region: "us-west-2"
        assumed_role:
          RoleArn: "arn:aws:iam::123456789012:role/AppRole"
          RoleSessionName: "app-session"

**Security features:**

    - Temporary credentials with configurable TTL
    - Session naming for audit trails
    - Automatic credential rotation
    - No long-lived credentials in applications

**Credential Flow**:

1. CredProxy uses its configured credentials (IAM profile or keys) **only to assume
   roles**
2. Each service gets credentials from its specific assumed role
3. Applications receive role-based credentials, not CredProxy's base credentials
4. All AWS operations are performed with the least-privilege role permissions

**IAM Policy for CredProxy Base Credentials**:

.. code-block:: json

    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": "sts:AssumeRole",
          "Resource": [
            "arn:aws:iam::123456789012:role/AppRole",
            "arn:aws:iam::123456789012:role/WorkerRole"
          ]
        }
      ]
    }

Note: CredProxy's base credentials should **only** have ``sts:AssumeRole`` permissions
for the specific roles your services need.

Container Security

Docker Security

**Default Non-Root User Implementation**

**CredProxy runs as a non-root user by default** for enhanced security:

    - **User/Group ID**: 1338 (non-privileged, non-standard)
    - **Username**: ``credproxy``
    - **Home Directory**: ``/credproxy``
    - **No Root Access**: Container cannot escalate privileges

See Dockerfile

**Security Benefits of Non-Root Default**

1. **Limited Attack Surface**: Even if compromised, attacker cannot gain root access
2. **File System Restrictions**: Can only modify files within ``/credproxy`` directory
3. **Network Limitations**: Cannot bind to privileged ports (< 1024)
4. **Process Isolation**: Cannot manipulate other containers or host system
5. **Specific UID/GID**: Using 1338 avoids conflicts with system users

Image Security Best Practices

CredProxy follows Docker security best practices by default:

Runtime Security

**Note**: CredProxy already runs as non-root user (1338:1338) by default. Additional
hardening:

.. code-block:: yaml

    services:
      credproxy:
        build: .
        security_opt:
          - no-new-privileges:true # Prevent privilege escalation
        read_only: true # Immutable filesystem
        tmpfs:
          - /tmp # Temporary filesystem for /tmp
        # Note: user: "1338:1338" is set in Dockerfile by default
        cap_drop:
          - ALL # Drop all Linux capabilities
        # No cap_add needed - CredProxy doesn't require additional capabilities

Secrets Management

Docker Secrets

.. code-block:: yaml

    services:
      credproxy:
        secrets:
          - aws_access_key_id
          - aws_secret_access_key
        environment:
          - AWS_ACCESS_KEY_ID_FILE=/run/secrets/aws_access_key_id
          - AWS_SECRET_ACCESS_KEY_FILE=/run/secrets/aws_secret_access_key

    secrets:
      aws_access_key_id:
        external: true
      aws_secret_access_key:
        external: true

Vulnerability Reporting

Security Issues

For security vulnerabilities or sensitive security concerns, please follow our
responsible disclosure policy:

**Private Disclosure Process**:

1. **Do NOT** open public issues for security vulnerabilities
2. Email security concerns to: security@ews-network.net
3. Include detailed description, reproduction steps, and potential impact
4. We will respond within 48 hours and provide a timeline for resolution
5. Security fixes will be coordinated for public disclosure

**What to Report**:

    - Authentication bypasses
    - Credential exposure risks
    - Container escape vulnerabilities
    - Information disclosure
    - Denial of service vulnerabilities
    - Configuration security issues

**Safe Harbor**: We commit to working with researchers who follow responsible
disclosure. Legal action will not be taken against researchers who discover and report
vulnerabilities in good faith.

Supported Versions

Security updates are provided for:

    - Current stable release (0.1.x)
    - Previous minor release for 90 days after new release

Security Updates

Security updates will be:

    - Released as patch versions (e.g., 0.1.1)
    - Announced in security advisories
    - Included in CHANGELOG.md
    - Available as Docker image updates with security tags

Security Best Practices Summary

    - ✅ **Non-root container execution** (UID/GID 1338)
    - ✅ **Minimal base image** (Alpine Linux)
    - ✅ **Token-based authentication** per service
    - ✅ **Memory-only credential storage**
    - ✅ **Network isolation** with loopback requirements
    - ✅ **Role-based access control** with least privilege
    - ✅ **Automatic credential rotation**
    - ✅ **Comprehensive logging** with sensitive data sanitization
