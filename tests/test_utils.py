# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for utility functions."""

from __future__ import annotations

import pytest

from credproxy.config import keyisset, set_else_none


class TestKeyIsSet:
    """Test the keyisset utility function."""

    def test_keyisset_existing_key(self):
        """Test keyisset returns value when key exists."""
        data = {"existing_key": "test_value", "other_key": 123}
        result = keyisset("existing_key", data)
        assert result == "test_value"

    def test_keyisset_missing_key(self):
        """Test keyisset raises KeyError when key is missing."""
        data = {"existing_key": "test_value"}
        with pytest.raises(
            KeyError, match="Required key 'missing_key' not found in configuration"
        ):
            keyisset("missing_key", data)

    def test_keyisset_none_value(self):
        """Test keyisset returns None when key exists but value is None."""
        data = {"key_with_none": None}
        result = keyisset("key_with_none", data)
        assert result is None

    def test_keyisset_empty_string(self):
        """Test keyisset returns empty string when key exists."""
        data = {"empty_string": ""}
        result = keyisset("empty_string", data)
        assert result == ""

    def test_keyisset_complex_value(self):
        """Test keyisset returns complex objects."""
        nested_dict = {"nested": "value"}
        data = {"complex": nested_dict}
        result = keyisset("complex", data)
        assert result == nested_dict


class TestSetElseNone:
    """Test the set_else_none utility function."""

    def test_set_else_none_existing_key(self):
        """Test set_else_none returns value when key exists."""
        data = {"existing_key": "test_value"}
        result = set_else_none("existing_key", data, "default")
        assert result == "test_value"

    def test_set_else_none_missing_key(self):
        """Test set_else_none returns default when key is missing."""
        data = {"other_key": "value"}
        result = set_else_none("missing_key", data, "default_value")
        assert result == "default_value"

    def test_set_else_none_none_default(self):
        """Test set_else_none returns None when key missing and default is None."""
        data = {"other_key": "value"}
        result = set_else_none("missing_key", data, None)
        assert result is None

    def test_set_else_none_existing_key_none_value(self):
        """Test set_else_none returns None when key exists but value is None."""
        data = {"key_with_none": None}
        result = set_else_none("key_with_none", data, "default")
        assert result is None

    def test_set_else_none_complex_default(self):
        """Test set_else_none returns complex default object."""
        default_dict = {"default": "dict"}
        data = {"other_key": "value"}
        result = set_else_none("missing_key", data, default_dict)
        assert result == default_dict

    def test_set_else_none_empty_dict(self):
        """Test set_else_none with empty dictionary."""
        data = {}
        result = set_else_none("any_key", data, "default")
        assert result == "default"
