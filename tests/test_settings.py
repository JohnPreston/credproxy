# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for settings functionality."""

from __future__ import annotations

import os

from credproxy.settings import (
    get_log_level,
    _validate_log_level,
    get_credproxy_namespace,
)


class TestLogLevelValidation:
    """Test log level validation function."""

    def test_valid_levels(self):
        """Test valid log level values."""
        assert _validate_log_level("debug") == "debug"
        assert _validate_log_level("info") == "info"
        assert _validate_log_level("warning") == "warning"
        assert _validate_log_level("error") == "error"
        assert _validate_log_level("critical") == "critical"

        # Test case insensitivity
        assert _validate_log_level("DEBUG") == "debug"
        assert _validate_log_level("INFO") == "info"
        assert _validate_log_level("WARNING") == "warning"
        assert _validate_log_level("ERROR") == "error"
        assert _validate_log_level("CRITICAL") == "critical"

        # Test mixed case
        assert _validate_log_level("Debug") == "debug"
        assert _validate_log_level("Info") == "info"
        assert _validate_log_level("Warning") == "warning"
        assert _validate_log_level("Error") == "error"
        assert _validate_log_level("Critical") == "critical"

        # Test with whitespace
        assert _validate_log_level("  debug  ") == "debug"
        assert _validate_log_level("  info  ") == "info"

    def test_invalid_levels_fallback(self):
        """Test invalid log level values fallback to 'warning'."""
        assert _validate_log_level("invalid") == "warning"
        assert _validate_log_level("trace") == "warning"
        assert _validate_log_level("verbose") == "warning"
        assert _validate_log_level("") == "warning"
        assert _validate_log_level("notice") == "warning"


class TestGetLogLevel:
    """Test get_log_level function with environment variables."""

    def setup_method(self):
        """Setup test environment."""
        self.namespace = get_credproxy_namespace()
        self.env_var = f"{self.namespace}LOG_LEVEL"

    def teardown_method(self):
        """Cleanup test environment."""
        if self.env_var in os.environ:
            del os.environ[self.env_var]

    def test_default_level(self):
        """Test default log level when environment variable is not set."""
        if self.env_var in os.environ:
            del os.environ[self.env_var]
        assert get_log_level(self.namespace) == "warning"

    def test_valid_level_from_env(self):
        """Test getting valid level from environment variable."""
        os.environ[self.env_var] = "debug"
        assert get_log_level(self.namespace) == "debug"

        os.environ[self.env_var] = "info"
        assert get_log_level(self.namespace) == "info"

        os.environ[self.env_var] = "warning"
        assert get_log_level(self.namespace) == "warning"

        os.environ[self.env_var] = "error"
        assert get_log_level(self.namespace) == "error"

        os.environ[self.env_var] = "critical"
        assert get_log_level(self.namespace) == "critical"

    def test_case_insensitive_level(self):
        """Test case-insensitive level from environment."""
        os.environ[self.env_var] = "DEBUG"
        assert get_log_level(self.namespace) == "debug"

        os.environ[self.env_var] = "INFO"
        assert get_log_level(self.namespace) == "info"

        os.environ[self.env_var] = "WARNING"
        assert get_log_level(self.namespace) == "warning"

        os.environ[self.env_var] = "ERROR"
        assert get_log_level(self.namespace) == "error"

        os.environ[self.env_var] = "CRITICAL"
        assert get_log_level(self.namespace) == "critical"

    def test_invalid_level_fallback(self):
        """Test invalid level falls back to 'warning'."""
        os.environ[self.env_var] = "invalid"
        assert get_log_level(self.namespace) == "warning"

        os.environ[self.env_var] = "trace"
        assert get_log_level(self.namespace) == "warning"

    def test_whitespace_handling(self):
        """Test whitespace handling in level."""
        os.environ[self.env_var] = "  debug  "
        assert get_log_level(self.namespace) == "debug"


class TestNamespaceHandling:
    """Test namespace handling in settings functions."""

    def test_custom_namespace(self):
        """Test functions with custom namespace."""
        custom_namespace = "CUSTOM_"

        # Test log level with custom namespace
        os.environ[f"{custom_namespace}LOG_LEVEL"] = "debug"
        assert get_log_level(custom_namespace) == "debug"

        # Cleanup
        del os.environ[f"{custom_namespace}LOG_LEVEL"]

    def test_isolation_between_namespaces(self):
        """Test that different namespaces don't interfere."""
        namespace1 = "NS1_"
        namespace2 = "NS2_"

        os.environ[f"{namespace1}LOG_LEVEL"] = "debug"
        os.environ[f"{namespace2}LOG_LEVEL"] = "error"

        assert get_log_level(namespace1) == "debug"
        assert get_log_level(namespace2) == "error"

        # Cleanup
        del os.environ[f"{namespace1}LOG_LEVEL"]
        del os.environ[f"{namespace2}LOG_LEVEL"]
