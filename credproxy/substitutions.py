#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

from __future__ import annotations

import os
import re
from typing import Any
from pathlib import Path

from credproxy.settings import FROM_ENV_TAG, FROM_FILE_TAG, TAG_SEPARATOR


# Substitution tags are now imported from credproxy.settings

# Build regex pattern dynamically based on configurable tags
VARIABLE_PATTERN = re.compile(
    rf"\$\{{({FROM_ENV_TAG}|{FROM_FILE_TAG}){re.escape(TAG_SEPARATOR)}([^}}]+)\}}"
)


def substitute_variables(value: Any) -> Any:
    """
    Substitute variables in configuration values. Recursively.

    Supports:
    - ${{FROM_ENV_TAG}}{TAG_SEPARATOR}VAR_NAME - environment variable
    - ${{FROM_FILE_TAG}}{TAG_SEPARATOR}/path/to/file - file contents

    Default syntax:
    - ${fromEnv:VAR_NAME} - environment variable
    - ${fromFile:/path/to/file} - file contents

    Environment variables to customize:
    - FROM_ENV_TAG: Change "fromEnv" tag (default: "fromEnv")
    - FROM_FILE_TAG: Change "fromFile" tag (default: "fromFile")
    - TAG_SEPARATOR: Change ":" separator (default: ":")

    Args:
        value: The value to substitute variables in

    Returns:
        The value with variables substituted
    """
    if isinstance(value, str):
        return _substitute_string(value)
    elif isinstance(value, dict):
        return {key: substitute_variables(val) for key, val in value.items()}
    elif isinstance(value, list):
        return [substitute_variables(item) for item in value]
    else:
        return value


def _substitute_string(value: str, depth: int = 0, max_depth: int = 10) -> str:
    """Substitute variables in a string with recursion depth limit.

    Args:
        value: The string value to substitute
        depth: Current recursion depth (default: 0)
        max_depth: Maximum allowed recursion depth (default: 10)

    Returns:
        String with variables substituted

    Raises:
        ValueError: If maximum recursion depth is exceeded
    """
    if depth >= max_depth:
        raise ValueError(
            f"Maximum substitution depth ({max_depth}) exceeded. "
            f"Check for circular references in configuration."
        )

    def replace_match(match):
        var_type, var_value = match.groups()

        if var_type == FROM_ENV_TAG:
            substituted = _substitute_env(var_value)
        elif var_type == FROM_FILE_TAG:
            substituted = _substitute_file(var_value)
        else:
            raise ValueError(f"Unknown variable type: {var_type}")

        # Recursively substitute variables in the result with incremented depth
        return _substitute_string(substituted, depth + 1, max_depth)

    return VARIABLE_PATTERN.sub(replace_match, value)


def _substitute_env(var_name: str) -> str:
    """Substitute environment variable."""
    env_value = os.getenv(var_name)
    if env_value is None:
        raise ValueError(f"Environment variable '{var_name}' not found")
    return env_value


def _substitute_file(file_path: str) -> str:
    """Substitute file contents."""
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File '{file_path}' not found")

    try:
        content = path.read_text()

        # Check if content is effectively a single line with just trailing newline
        if content.endswith("\n"):
            # Remove trailing newline and check if there are any other newlines
            content_without_trailing_newline = content[:-1]
            if "\n" not in content_without_trailing_newline:
                # Single line with trailing newline - remove the trailing newline
                return content_without_trailing_newline
            else:
                # Multiple lines - preserve all newlines including the trailing one
                return content
        else:
            # No trailing newline - return as-is
            return content
    except Exception as error:
        raise ValueError(f"Error reading file '{file_path}': {error}")
