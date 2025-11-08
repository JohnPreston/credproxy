#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

from __future__ import annotations

import re
import threading
from typing import Any


class SensitiveValueSanitizer:
    """Thread-safe sanitizer that tracks actual sensitive values for redaction.

    This class maintains a registry of sensitive values (tokens, keys, etc.) and
    sanitizes them wherever they appear in logs or data structures.
    """

    def __init__(self):
        self._sensitive_values: set[str] = set()
        self._lock = threading.RLock()

    def register_sensitive_value(self, value: str) -> None:
        """Register a sensitive value for sanitization.

        Args:
            value: The sensitive value to track and sanitize
        """
        if value and isinstance(value, str) and len(value) >= 4:
            with self._lock:
                self._sensitive_values.add(value)

    def register_sensitive_dict(self, data: dict) -> None:
        """Register all sensitive values from a dictionary.

        Automatically detects and registers values from keys that look sensitive.

        Args:
            data: Dictionary containing potential sensitive data
        """
        if not isinstance(data, dict):
            return

        # Keys that typically contain sensitive data
        sensitive_key_patterns = [
            re.compile(r"password", re.IGNORECASE),
            re.compile(r"secret", re.IGNORECASE),
            re.compile(r"token", re.IGNORECASE),
            re.compile(r"auth", re.IGNORECASE),
            re.compile(r"_key$", re.IGNORECASE),
            re.compile(r"external_?id", re.IGNORECASE),
            re.compile(r"credentials?", re.IGNORECASE),
            re.compile(r"access_?key", re.IGNORECASE),
        ]

        for key, value in data.items():
            # Check if key matches sensitive pattern
            is_sensitive = any(
                pattern.search(key) for pattern in sensitive_key_patterns
            )

            if is_sensitive and isinstance(value, str):
                self.register_sensitive_value(value)
            elif isinstance(value, dict):
                # Recursively process nested dicts
                self.register_sensitive_dict(value)
            elif isinstance(value, list):
                # Process list items
                for item in value:
                    if isinstance(item, dict):
                        self.register_sensitive_dict(item)

    def sanitize_string(self, text: str) -> str:
        """Sanitize a string by replacing all registered sensitive values.

        Args:
            text: The text to sanitize

        Returns:
            Sanitized text with sensitive values redacted
        """
        if not text or not isinstance(text, str):
            return text

        sanitized = text
        with self._lock:
            for sensitive_value in self._sensitive_values:
                if sensitive_value in sanitized:
                    # Show first 4 chars + masking
                    redacted = (
                        sensitive_value[:4] + "****"
                        if len(sensitive_value) > 4
                        else "****"
                    )
                    sanitized = sanitized.replace(sensitive_value, redacted)

        return sanitized

    def unregister_sensitive_value(self, value: str) -> None:
        """Unregister a sensitive value.

        Args:
            value: The sensitive value to remove from tracking
        """
        if value and isinstance(value, str):
            with self._lock:
                self._sensitive_values.discard(value)

    def clear(self) -> None:
        """Clear all registered sensitive values."""
        with self._lock:
            self._sensitive_values.clear()


# Global sanitizer instance - one per process
_SANITIZER = SensitiveValueSanitizer()


def register_sensitive_value(value: str) -> None:
    """Register a sensitive value for sanitization globally.

    Args:
        value: The sensitive value to track and sanitize
    """
    _SANITIZER.register_sensitive_value(value)


def register_sensitive_dict(data: dict) -> None:
    """Register all sensitive values from a dictionary globally.

    Args:
        data: Dictionary containing potential sensitive data
    """
    _SANITIZER.register_sensitive_dict(data)


def unregister_sensitive_value(value: str) -> None:
    """Unregister a sensitive value globally.

    Args:
        value: The sensitive value to remove from tracking
    """
    _SANITIZER.unregister_sensitive_value(value)


def _sanitize_string(value: str) -> str:
    """Sanitize a string value by showing only first 4 chars or **** if shorter.

    Also checks against registered sensitive values.
    """
    if value is None:
        return None

    if not value:
        return value

    # First, check if this exact value is registered as sensitive
    sanitized = _SANITIZER.sanitize_string(value)
    if sanitized != value:
        return sanitized

    # Fallback to length-based masking for short values
    if len(value) <= 4:
        return "****"

    return value[:4] + "****"


def _is_sensitive_key(key: str) -> bool:
    """Check if a key represents sensitive information using regex patterns."""
    # Compile regex patterns for better performance and flexibility
    sensitive_patterns = [
        re.compile(r"password", re.IGNORECASE),
        re.compile(r"secret", re.IGNORECASE),
        re.compile(r"token", re.IGNORECASE),
        re.compile(r"auth", re.IGNORECASE),
        re.compile(r"key$", re.IGNORECASE),  # Ends with "key"
        re.compile(r"_key$", re.IGNORECASE),  # Ends with "_key"
        re.compile(r"^key$", re.IGNORECASE),  # Exactly "key"
        re.compile(r"external_?id", re.IGNORECASE),  # external_id or externalid
        re.compile(r"private_?key", re.IGNORECASE),
        re.compile(r"api_?key", re.IGNORECASE),
        re.compile(r"access_?key", re.IGNORECASE),
        re.compile(r"secret_?key", re.IGNORECASE),
        re.compile(r"session_?token", re.IGNORECASE),
        re.compile(r"credentials?", re.IGNORECASE),
        re.compile(r"aws_access_key_id", re.IGNORECASE),
        re.compile(r"aws_secret_access_key", re.IGNORECASE),
    ]

    # Check if key matches any sensitive pattern
    for pattern in sensitive_patterns:
        if pattern.search(key):
            return True

    return False


def sanitize_string(text: str) -> str:
    """Sanitize a string by replacing registered sensitive values.

    This is the main public API for sanitizing strings in logs.

    Args:
        text: The text to sanitize

    Returns:
        Sanitized text with sensitive values redacted
    """
    if not text or not isinstance(text, str):
        return text

    return _SANITIZER.sanitize_string(text)


def sanitize_for_logging(data: Any) -> Any:
    """
    Recursively sanitize sensitive data in dictionaries, lists, and other structures.

    This is primarily for legacy compatibility. The recommended approach is to
    register sensitive values and let the logging formatter handle sanitization.

    Args:
        data: Any data structure (dict, list, string, etc.)

    Returns:
        Sanitized version of the data with sensitive values masked
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if _is_sensitive_key(key):
                if value is None:
                    sanitized[key] = None
                elif isinstance(value, str):
                    sanitized[key] = _sanitize_string(value)
                elif isinstance(value, (dict, list, tuple)):
                    # For nested structures, recursively sanitize
                    sanitized[key] = sanitize_for_logging(value)
                else:
                    # For other types, sanitize the string representation
                    sanitized[key] = _sanitize_string(str(value))
            else:
                sanitized[key] = sanitize_for_logging(value)
        return sanitized

    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]

    elif isinstance(data, tuple):
        return tuple(sanitize_for_logging(item) for item in data)

    elif isinstance(data, str):
        # First check against registered sensitive values
        sanitized = _SANITIZER.sanitize_string(data)
        if sanitized != data:
            return sanitized

        # Check if the string itself looks like sensitive data
        sensitive_patterns = [
            r"^AKIA[0-9A-Z]{16}$",  # AWS Access Key ID pattern
            r"^[a-zA-Z0-9+/]{40,}$",  # Base64 encoded secrets
            r"^[a-zA-Z0-9_-]{20,}$",  # Generic long tokens
        ]

        for pattern in sensitive_patterns:
            if re.match(pattern, data):
                return _sanitize_string(data)

        return data

    else:
        return data


def _sanitize_key_value(match, key_name: str) -> str:
    """Helper function to sanitize key-value pairs in exception messages."""
    key = match.group(1)
    value = match.group(2)
    sanitized_value = _sanitize_string(value)
    return f"'{key}': '{sanitized_value}'"


def sanitize_exception_message(message: str) -> str:
    """
    Sanitize exception messages that might contain sensitive data.

    First checks against registered sensitive values, then falls back to
    pattern-based detection.

    Args:
        message: Exception message string

    Returns:
        Sanitized message with sensitive values masked
    """
    # First, sanitize using registered values
    sanitized_message = _SANITIZER.sanitize_string(message)

    # Then apply pattern-based sanitization for key-value pairs
    patterns = [
        (r"'(aws_access_key_id)':\s*'([^']+)'", "aws_access_key_id"),
        (r"'(aws_secret_access_key)':\s*'([^']+)'", "aws_secret_access_key"),
        (r"'(session_token)':\s*'([^']+)'", "session_token"),
        (r"'(auth_token)':\s*'([^']+)'", "auth_token"),
        (r"'(external_id)':\s*'([^']+)'", "external_id"),
        (r"'(password)':\s*'([^']+)'", "password"),
        (r"'(secret)':\s*'([^']+)'", "secret"),
        (r"'(token)':\s*'([^']+)'", "token"),
        (r"'(access_key_id)':\s*'([^']+)'", "access_key_id"),
    ]

    for pattern, key_name in patterns:

        def replacer(match):
            return _sanitize_key_value(match, key_name)

        sanitized_message = re.sub(
            pattern, replacer, sanitized_message, flags=re.IGNORECASE
        )

    return sanitized_message
