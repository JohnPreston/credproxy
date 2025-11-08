"""Tests for regex filtering functionality in dynamic services."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

from credproxy.config import DirectoryConfig
from credproxy.file_watcher import should_include_file


class TestRegexFiltering:
    """Test regex filtering functionality for dynamic services."""

    def test_should_include_file_no_patterns(self):
        """Test file inclusion when no patterns are specified."""
        file_path = "/test/service.yaml"

        # Empty patterns should include all files
        result = should_include_file(file_path, [], [])
        assert result is True

    def test_should_include_file_include_only(self):
        """Test file inclusion with only include patterns."""
        file_path = "/test/service.yaml"

        # Should match .yaml files
        result = should_include_file(file_path, [r".*\.yaml$"], [])
        assert result is True

    def test_should_include_file_exclude_only(self):
        """Test file exclusion with only exclude patterns."""
        file_path = "/test/service.tmp"

        # Should exclude .tmp files
        result = should_include_file(file_path, [], [r".*\.tmp$"])
        assert result is False

    def test_should_include_file_include_and_exclude_match_include(self):
        """Test file inclusion when file matches include but not exclude."""
        file_path = "/test/service.yaml"

        # Include .yaml files, exclude .tmp files
        result = should_include_file(file_path, [r".*\.yaml$"], [r".*\.tmp$"])
        assert result is True

    def test_should_include_file_include_and_exclude_match_exclude(self):
        """Test file exclusion when file matches exclude pattern."""
        file_path = "/test/service.tmp.yaml"

        # Include .yaml files, exclude .tmp files
        result = should_include_file(file_path, [r".*\.yaml$"], [r".*\.tmp.*"])
        assert result is False

    def test_should_include_file_no_include_match(self):
        """Test file exclusion when file doesn't match include patterns."""
        file_path = "/test/service.json"

        # Only include .yaml files
        result = should_include_file(file_path, [r".*\.yaml$"], [])
        assert result is False

    def test_should_include_file_complex_patterns(self):
        """Test file inclusion with complex regex patterns."""
        # Test various file names
        test_cases = [
            # (filename, include_patterns, exclude_patterns, expected_result)
            ("service.yaml", [r".*\.yaml$"], [], True),
            ("service.yml", [r".*\.ya?ml$"], [], True),
            ("config.yaml", [r".*\.yaml$"], [r".*config.*"], False),
            ("service.json", [r".*\.(yaml|yml|json)$"], [], True),
            ("backup.yaml", [r".*\.yaml$"], [r".*backup.*"], False),
            ("prod-service.yaml", [r".*prod-.*\.yaml$"], [], True),
            ("dev-service.yaml", [r".*prod-.*\.yaml$"], [], False),
            ("service.yaml.bak", [r".*\.yaml$"], [r".*\.bak$"], False),
        ]

        for filename, include_patterns, exclude_patterns, expected in test_cases:
            file_path = f"/test/{filename}"
            result = should_include_file(file_path, include_patterns, exclude_patterns)
            assert result == expected, (
                f"Failed for {filename} with include={include_patterns}, "
                f"exclude={exclude_patterns}"
            )

    def test_should_include_file_case_sensitivity(self):
        """Test that regex patterns are case-sensitive by default."""
        file_path = "/test/SERVICE.YAML"

        # Should not match if pattern expects lowercase
        result = should_include_file(file_path, [r".*\.yaml$"], [])
        assert result is False

    def test_should_include_file_case_insensitive_pattern(self):
        """Test case-insensitive regex patterns."""
        file_path = "/test/SERVICE.YAML"

        # Should match with case-insensitive flag
        result = should_include_file(file_path, [r"(?i).*\.yaml$"], [])
        assert result is True

    def test_should_include_file_directory_patterns(self):
        """Test patterns that include directory paths."""
        file_path = "/test/services/prod/service.yaml"

        # Should match directory-based patterns
        result = should_include_file(file_path, [r".*services/prod/.*\.yaml$"], [])
        assert result is True

    def test_should_include_file_multiple_include_patterns(self):
        """Test file inclusion with multiple include patterns."""
        file_path = "/test/service.yaml"

        # Should match if any include pattern matches
        result = should_include_file(
            file_path, [r".*\.json$", r".*\.yaml$", r".*\.yml$"], []
        )
        assert result is True

    def test_should_include_file_multiple_exclude_patterns(self):
        """Test file exclusion with multiple exclude patterns."""
        file_path = "/test/service.tmp.yaml"

        # Should exclude if any exclude pattern matches
        result = should_include_file(
            file_path, [r".*\.yaml$"], [r".*\.tmp\..*$", r".*\.bak$"]
        )
        assert result is False

    def test_should_include_file_empty_string_patterns(self):
        """Test handling of empty string patterns."""
        file_path = "/test/service.yaml"

        # Empty string patterns match everything in regex, so this should be True
        result = should_include_file(file_path, [""], [])
        assert result is True

    def test_should_include_file_dot_files(self):
        """Test handling of dot files (hidden files)."""
        file_path = "/test/.service.yaml"

        # Should match dot files if pattern allows
        result = should_include_file(file_path, [r".*\.yaml$"], [])
        assert result is True

    def test_should_include_file_exclude_dot_files(self):
        """Test exclusion of dot files."""
        file_path = "/test/.service.yaml"

        # Should exclude dot files
        result = should_include_file(file_path, [r".*\.yaml$"], [r".*/\..*"])
        assert result is False

    def test_should_include_file_invalid_regex_include(self):
        """Test handling of invalid regex in include patterns."""
        file_path = "/test/service.yaml"

        # Invalid regex should be handled gracefully
        result = should_include_file(file_path, ["[invalid*regex"], [])
        assert result is False

    def test_should_include_file_invalid_regex_exclude(self):
        """Test handling of invalid regex in exclude patterns."""
        file_path = "/test/service.yaml"

        # Invalid exclude regex should not affect inclusion
        result = should_include_file(file_path, [r".*\.yaml$"], ["[invalid*regex"])
        assert result is True

    def test_should_include_file_special_characters(self):
        """Test patterns with special regex characters."""
        file_path = "/test/service-v1.2.3.yaml"

        # Should match patterns with special characters
        result = should_include_file(file_path, [r".*-v\d+\.\d+\.\d+\.yaml$"], [])
        assert result is True

    def test_should_include_file_word_boundaries(self):
        """Test patterns with word boundaries."""
        file_path = "/test/prod-service.yaml"

        # Should match with word boundaries
        result = should_include_file(file_path, [r".*\bprod\b.*\.yaml$"], [])
        assert result is True

    def test_should_include_file_start_end_anchors(self):
        """Test patterns with start and end anchors."""
        file_path = "/test/service.yaml"

        # Should match with anchors
        result = should_include_file(file_path, [r"^/test/.*\.yaml$"], [])
        assert result is True

    def test_should_include_file_no_match_with_anchors(self):
        """Test non-matching patterns with anchors."""
        file_path = "/test/service.yaml"

        # Should not match if anchors don't align
        result = should_include_file(file_path, [r"^service\.yaml$"], [])
        assert result is False

    def test_should_include_file_real_world_config_patterns(self):
        """Test real-world configuration file patterns."""
        test_cases = [
            # Common config file patterns
            ("deployment.yaml", [r".*\.(yaml|yml)$"], [], True),
            ("k8s-config.yml", [r".*\.(yaml|yml)$"], [], True),
            ("docker-compose.yaml", [r".*\.(yaml|yml)$"], [], True),
            ("values.yaml", [r".*\.(yaml|yml)$"], [], True),
            ("config.json", [r".*\.(yaml|yml)$"], [], False),
            # Exclude temporary files
            ("service.yaml~", [r".*\.(yaml|yml)$"], [r".*~$"], False),
            ("service.yaml.tmp", [r".*\.(yaml|yml)$"], [r".*\.tmp$"], False),
            ("#service.yaml#", [r".*\.(yaml|yml)$"], [r"^#.*#$"], False),
            # Include only specific directories
            ("/prod/service.yaml", [r".*/prod/.*\.yaml$"], [], True),
            ("/dev/service.yaml", [r".*/prod/.*\.yaml$"], [], False),
        ]

        for filename, include_patterns, exclude_patterns, expected in test_cases:
            file_path = f"/test/{filename}"
            result = should_include_file(file_path, include_patterns, exclude_patterns)
            assert result == expected, (
                f"Failed for {filename} with include={include_patterns}, "
                f"exclude={exclude_patterns}"
            )


class TestRegexFilteringIntegration:
    """Integration tests for regex filtering with file watcher."""

    def test_file_handler_with_regex_patterns(self):
        """Test ServiceFileHandler with regex patterns."""
        from credproxy.file_watcher import ServiceFileHandler

        config = Mock()
        config.dynamic_services = Mock()
        config.dynamic_services.directories = [
            DirectoryConfig(
                path="/tmp/test",
                include_patterns=[r".*\.yaml$"],
                exclude_patterns=[r".*\.tmp$"],
            )
        ]
        config.dynamic_services.include_patterns = [r".*\.yaml$"]
        config.dynamic_services.exclude_patterns = [r".*\.tmp$"]
        config.dynamic_services.reload_interval = 5

        handler = ServiceFileHandler(config, 5)

        # Test that handler is initialized with patterns
        assert handler.config == config
        assert handler.reload_interval == 5

    def test_file_filtering_with_temp_files(self):
        """Test that temporary files are properly filtered."""
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files that should be included
            included_file = Path(temp_dir) / "service.yaml"
            included_file.write_text("test content")

            # Create files that should be excluded
            excluded_file = Path(temp_dir) / "service.tmp"
            excluded_file.write_text("test content")

            # Test filtering
            assert (
                should_include_file(str(included_file), [r".*\.yaml$"], [r".*\.tmp$"])
                is True
            )
            assert (
                should_include_file(str(excluded_file), [r".*\.yaml$"], [r".*\.tmp$"])
                is False
            )

    def test_file_filtering_with_complex_config(self):
        """Test filtering with complex configuration patterns."""
        config_patterns = [
            # Include patterns
            [r".*\.(yaml|yml)$", r".*\.(json)$"],
            # Exclude patterns
            [r".*\.tmp$", r".*\.bak$", r".*~$", r"^#.*#$"],
        ]

        test_files = [
            ("config.yaml", True),
            ("config.yml", True),
            ("config.json", True),
            ("config.tmp", False),
            ("config.bak", False),
            ("config.yaml~", False),
            ("#config.yaml#", False),
            ("config.xml", False),
        ]

        for filename, expected in test_files:
            file_path = f"/test/{filename}"
            result = should_include_file(
                file_path, config_patterns[0], config_patterns[1]
            )
            assert result == expected, f"Failed for {filename}"
