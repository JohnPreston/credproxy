#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""
CredProxy Environment Variables Configuration

This module centralizes all environment variable definitions to ensure consistency
and avoid duplication throughout the codebase.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_credproxy_namespace() -> str:
    return os.environ.get("CREDPROXY_NAMESPACE", "CREDPROXY_")


def get_config_file(namespace: str) -> str:
    default_path = "/credproxy/config.yaml"
    config_file = os.environ.get(f"{namespace}CONFIG_FILE", default_path)
    # Always return absolute path
    return str(Path(config_file).resolve())


def get_from_env_tag(namespace: str) -> str:
    return os.environ.get(f"{namespace}FROM_ENV_TAG", "fromEnv")


def get_from_file_tag(namespace: str) -> str:
    return os.environ.get(f"{namespace}FROM_FILE_TAG", "fromFile")


def get_tag_separator(namespace: str) -> str:
    return os.environ.get(f"{namespace}TAG_SEPARATOR", ":")


def _validate_log_level(log_level: str):
    """Validate log level, accepting case-insensitive values with fallback."""
    valid_levels = {"debug", "info", "warning", "error", "critical"}
    normalized_level = log_level.lower().strip()
    return normalized_level if normalized_level in valid_levels else "warning"


def get_log_level(namespace: str) -> str:
    """Get log level from environment with validation and fallback."""
    raw_level = os.environ.get(f"{namespace}LOG_LEVEL", "warning")
    return _validate_log_level(raw_level)


def get_log_health_checks(namespace: str) -> bool:
    """Get health check logging setting from environment."""
    raw_value = os.environ.get(f"{namespace}LOG_HEALTH_CHECKS", "").lower().strip()
    return raw_value in {"true", "1", "yes", "on"}


NAMESPACE = get_credproxy_namespace()

# Substitution Tags (for config file variable substitution)
FROM_ENV_TAG: str = get_from_env_tag(NAMESPACE)
FROM_FILE_TAG: str = get_from_file_tag(NAMESPACE)
TAG_SEPARATOR: str = get_tag_separator(NAMESPACE)

# Logging
LOG_LEVEL: str = get_log_level(NAMESPACE)
LOG_HEALTH_CHECKS: bool = get_log_health_checks(NAMESPACE)
