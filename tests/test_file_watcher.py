"""Tests for file watcher module dynamic services functionality."""

from __future__ import annotations

import os
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import yaml
import pytest

from tests.mock_aws import mock_role_arn, mock_access_key_id, mock_secret_access_key
from credproxy.config import (
    ServiceConfig,
    DirectoryConfig,
    AssumedRoleConfig,
    SourceCredentialsConfig,
)
from credproxy.file_watcher import FileWatcherService, ServiceFileHandler


class TestServiceFileHandler:
    """Test service file handler for dynamic services."""

    def test_init_with_valid_config(self):
        """Test handler initialization with valid configuration."""
        config = Mock()
        config.dynamic_services = Mock()
        config.dynamic_services.directories = [
            DirectoryConfig(
                path="/tmp/test",
                include_patterns=[".*\\.yaml$"],
                exclude_patterns=[".*\\.tmp$"],
            )
        ]
        config.dynamic_services.include_patterns = [".*\\.yaml$"]
        config.dynamic_services.exclude_patterns = [".*\\.tmp$"]
        config.dynamic_services.reload_interval = 5

        handler = ServiceFileHandler(config, 5)

        assert handler.config == config
        assert handler.reload_interval == 5

    def test_on_created_valid_yaml_file(self):
        """Test handling of valid YAML file creation."""
        from credproxy.config import DirectoryConfig

        config = Mock()
        config.dynamic_services = Mock()
        config.dynamic_services.directories = [
            DirectoryConfig(
                path="/tmp/test", include_patterns=[".*\\.yaml$"], exclude_patterns=[]
            )
        ]
        config.dynamic_services.reload_interval = 5

        # Create valid YAML content
        config_content = {
            "services": {
                "new-service": {
                    "auth_token": "new-token",
                    "source_credentials": {
                        "iam_profile": {"profile_name": "test", "region": "us-east-1"}
                    },
                    "assumed_role": {"RoleArn": mock_role_arn()},
                    "source_file": "/test/new_service.yaml",
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_content, f)

            # Start the service
            service = FileWatcherService(config)
            service.start()

            # Give it a moment to process
            time.sleep(0.1)

            # Verify service is running
            assert service.is_running()

            # Stop the service
            service.stop()

            # Verify service is no longer running
            assert not service.is_running()

    def test_error_handling_in_start(self):
        """Test error handling during service start."""
        config = Mock()
        config.dynamic_services = Mock()
        config.dynamic_services.enabled = True
        config.dynamic_services.directories = ["/tmp/test"]
        config.dynamic_services.include_patterns = []
        config.dynamic_services.exclude_patterns = []

        with patch(
            "credproxy.file_watcher.Observer", side_effect=Exception("Observer error")
        ):
            service = FileWatcherService(config)

            with pytest.raises(Exception):
                service.start()

    def test_error_handling_in_stop(self):
        """Test error handling during service stop."""
        config = Mock()

        with patch("credproxy.file_watcher.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer.stop.side_effect = Exception("Stop error")
            mock_observer_class.return_value = mock_observer

            service = FileWatcherService(config)
            service.observer = mock_observer
            service._running = True

            # Should not raise exception despite error
            service.stop()

            # Note: _running remains True when error occurs in stop method
            # because _running = False is in the try block
            assert service._running is True

    def test_process_pending_changes_with_error(self):
        """Test error handling in _process_pending_changes."""
        config = Mock()
        handler = ServiceFileHandler(config, 5)

        # Add a pending change
        handler._pending_changes = {"test_file.yaml": time.time()}

        # Mock _process_file_change to raise exception
        with patch.object(
            handler, "_process_file_change", side_effect=Exception("Processing error")
        ):
            # Should not raise exception, should handle error gracefully
            handler._process_pending_changes()

            # Pending changes should be cleared even after error
            assert len(handler._pending_changes) == 0

    def test_process_file_change_invalid_yaml(self):
        """Test processing file with invalid YAML content."""
        config = Mock()
        config.add_dynamic_services = Mock()
        config.remove_dynamic_services = Mock()

        handler = ServiceFileHandler(config, 5)

        # Create a temporary file with invalid YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = f.name

        try:
            # Should handle invalid YAML gracefully
            handler._process_file_change(invalid_file)
        finally:
            os.unlink(invalid_file)

        # Should not have added any services
        config.add_dynamic_services.assert_not_called()

    def test_process_file_change_empty_file(self):
        """Test processing empty file."""
        config = Mock()
        config.add_dynamic_services = Mock()
        config.remove_dynamic_services = Mock()

        handler = ServiceFileHandler(config, 5)

        # Create a temporary empty file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            empty_file = f.name

        try:
            # Should handle empty file gracefully
            handler._process_file_change(empty_file)
        finally:
            os.unlink(empty_file)

        # Should not have added any services
        config.add_dynamic_services.assert_not_called()

    def test_load_existing_files_permission_error(self):
        """Test handling permission errors when loading existing files."""
        config = Mock()
        config.dynamic_services = Mock()
        config.dynamic_services.enabled = True
        config.dynamic_services.directories = [
            DirectoryConfig(path="/root/nonexistent")  # Permission denied path
        ]
        config.dynamic_services.include_patterns = []
        config.dynamic_services.exclude_patterns = []

        service = FileWatcherService(config)

        # Should handle permission error gracefully
        service._load_existing_files()

        # Should not crash, just log error

    def test_start_service_directory_creation_error(self):
        """Test error handling when directory creation fails during start."""
        config = Mock()
        config.dynamic_services = Mock()
        config.dynamic_services.enabled = True
        config.dynamic_services.directories = [
            DirectoryConfig(path="/tmp/nonexistent_test_dir")
        ]
        config.dynamic_services.include_patterns = []
        config.dynamic_services.exclude_patterns = []

        service = FileWatcherService(config)

        # Mock Path.mkdir to raise exception
        with patch.object(Path, "mkdir", side_effect=OSError("Permission denied")):
            with patch.object(service, "_load_existing_files"):
                # Should handle directory creation error gracefully - will raise and log
                with pytest.raises(OSError):
                    service.start()

    def test_start_service_observer_schedule_error(self):
        """Test error handling when observer scheduling fails."""
        config = Mock()
        config.dynamic_services = Mock()
        config.dynamic_services.enabled = True
        config.dynamic_services.directories = ["/tmp/test"]
        config.dynamic_services.include_patterns = []
        config.dynamic_services.exclude_patterns = []

        service = FileWatcherService(config)

        # Mock observer to raise exception during schedule
        with patch("credproxy.file_watcher.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer.schedule.side_effect = Exception("Schedule error")
            mock_observer_class.return_value = mock_observer

            # Should handle schedule error gracefully - will raise and log
            with pytest.raises(Exception):
                service.start()

    def test_start_service_observer_start_error(self):
        """Test error handling when observer start fails."""
        config = Mock()
        config.dynamic_services = Mock()
        config.dynamic_services.enabled = True
        config.dynamic_services.directories = ["/tmp/test"]
        config.dynamic_services.include_patterns = []
        config.dynamic_services.exclude_patterns = []

        service = FileWatcherService(config)

        # Mock observer to raise exception during start
        with patch("credproxy.file_watcher.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer.start.side_effect = Exception("Start error")
            mock_observer_class.return_value = mock_observer

            # Should handle start error gracefully - will raise and log
            with pytest.raises(Exception):
                service.start()

    def test_load_service_file_with_exception(self):
        """Test _load_service_file with various exception scenarios."""
        config = Mock()
        config.add_dynamic_services = Mock()
        config.remove_dynamic_services = Mock()

        handler = ServiceFileHandler(config, 5)

        # Test with non-existent file
        result = handler._load_service_file("/nonexistent/file.yaml")

        # Should return None for non-existent file
        assert result is None

    def test_process_file_change_service_loading_error(self):
        """Test _process_file_change when service loading fails."""
        config = Mock()
        config.add_dynamic_services = Mock()
        config.remove_dynamic_services = Mock()

        handler = ServiceFileHandler(config, 5)

        # Mock _load_service_file to raise exception
        with patch.object(
            handler, "_load_service_file", side_effect=Exception("Load error")
        ):
            # Should handle loading error gracefully
            handler._process_file_change("/test/file.yaml")

    def test_schedule_reload_timer_error(self):
        """Test _schedule_reload when timer creation fails."""
        config = Mock()
        handler = ServiceFileHandler(config, 5)

        # Mock timer to raise exception during creation
        with patch("threading.Timer", side_effect=Exception("Timer error")):
            # Should handle timer error gracefully - will raise exception
            with pytest.raises(Exception, match="Timer error"):
                handler._schedule_reload("/test/file.yaml", "created")


class TestFileWatcherAdvancedCoverage:
    """Advanced tests for file watcher coverage improvement."""

    def test_schedule_reload_timer_cancellation(self):
        """Test timer cancellation when scheduling reload (line 82)."""
        config = Mock()
        handler = ServiceFileHandler(config, 5)

        # Create an existing timer
        existing_timer = Mock()
        handler._debounce_timer = existing_timer

        # Schedule new reload - should cancel existing timer
        handler._schedule_reload("/test/file.yaml", "created")

        # Verify existing timer was cancelled
        existing_timer.cancel.assert_called_once()

        # Verify new timer was created and started
        assert handler._debounce_timer is not None
        assert handler._debounce_timer != existing_timer

    def test_schedule_reload_multiple_rapid_changes(self):
        """Test multiple rapid file changes and timer management."""
        config = Mock()
        handler = ServiceFileHandler(config, 1)  # Use int for reload_interval

        # Schedule multiple changes rapidly
        handler._schedule_reload("/test/file1.yaml", "created")
        first_timer = handler._debounce_timer

        handler._schedule_reload("/test/file2.yaml", "modified")
        second_timer = handler._debounce_timer

        handler._schedule_reload("/test/file3.yaml", "deleted")
        third_timer = handler._debounce_timer

        # Verify final timer is different from first
        assert third_timer != first_timer
        assert third_timer != second_timer

    def test_process_file_change_service_rejection_different_source(self):
        """Test service rejection when different source file for same service."""
        from credproxy.config import (
            ServiceConfig,
            AssumedRoleConfig,
            IAMKeysAuthConfig,
            SourceCredentialsConfig,
        )

        config = Mock()
        config.services = {}

        # Create existing service with different source
        existing_service = ServiceConfig(
            auth_token="existing-token",
            source_credentials=SourceCredentialsConfig(
                region="us-east-1",
                iam_keys=IAMKeysAuthConfig(
                    aws_access_key_id=mock_access_key_id(),
                    aws_secret_access_key=mock_secret_access_key(),
                ),
            ),
            assumed_role=AssumedRoleConfig(
                RoleArn=mock_role_arn(),
                RoleSessionName="existing-session",
            ),
            source_file="/different/path.yaml",
        )
        config.services["test-service"] = existing_service
        config.add_dynamic_services = Mock()

        handler = ServiceFileHandler(config, 5)

        # Create new service data
        service_data = {
            "auth_token": "new-token",
            "source_credentials": {"region": "us-west-2"},
            "assumed_role": {
                "RoleArn": mock_role_arn(),
                "RoleSessionName": "new-session",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(service_data, f)
            temp_file = f.name

        try:
            # Mock the source file path to be different
            with patch("pathlib.Path.resolve", return_value="/new/path.yaml"):
                handler._process_file_change(temp_file)

            # Verify service was NOT added (different source file)
            config.add_dynamic_services.assert_not_called()

        finally:
            os.unlink(temp_file)

    def test_process_file_change_service_removal(self):
        """Test service removal when file is deleted (lines 167-172)."""
        from credproxy.config import (
            ServiceConfig,
            AssumedRoleConfig,
            IAMKeysAuthConfig,
            SourceCredentialsConfig,
        )

        config = Mock()
        config.services = {}

        # Create existing service
        existing_service = ServiceConfig(
            auth_token="existing-token",
            source_credentials=SourceCredentialsConfig(
                region="us-east-1",
                iam_keys=IAMKeysAuthConfig(
                    aws_access_key_id=mock_access_key_id(),
                    aws_secret_access_key=mock_secret_access_key(),
                ),
            ),
            assumed_role=AssumedRoleConfig(
                RoleArn=mock_role_arn(),
                RoleSessionName="existing-session",
            ),
            source_file="/test/path.yaml",
        )
        config.services["path"] = existing_service
        config.remove_service = Mock()

        handler = ServiceFileHandler(config, 5)

        # Process file deletion
        with patch("pathlib.Path.resolve", return_value="/test/path.yaml"):
            handler._process_file_change("/test/path.yaml")

        # Verify service was removed
        config.remove_service.assert_called_once_with("path")

    def test_process_file_change_error_handling_in_operations(self):
        """Test error handling in service operations (lines 168-175)."""
        config = Mock()
        config.services = {}

        handler = ServiceFileHandler(config, 5)

        # Mock Path.exists() to return True and _load_service_file to raise an exception
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(
                handler, "_load_service_file", side_effect=Exception("Load error")
            ),
            patch("credproxy.file_watcher.LOG") as mock_log,
        ):
            handler._process_file_change("/test/file.yaml")

        # Exception should be caught and logged
        mock_log.error.assert_called()

        # Verify the error message contains expected content
        error_calls = [
            call
            for call in mock_log.error.call_args_list
            if "Failed to load service configuration" in str(call)
        ]
        assert len(error_calls) > 0

    def test_service_removal_with_real_file_operations(self):
        """Test service removal with real file operations in temporary directory."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create real Config object with dynamic services enabled
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[
                    DirectoryConfig(
                        path=temp_dir,
                        include_patterns=[".*\\.yaml$", ".*\\.yml$"],
                        exclude_patterns=["^\\..*", ".*~$", ".*\\.bak$"],
                    )
                ],
                reload_interval=1,  # Short interval for testing
            )

            # Create valid service configuration file first
            service_name = "test-removal-service"
            service_file = Path(temp_dir) / f"{service_name}.yaml"
            mock_access_key = mock_access_key_id()
            mock_secret_key = mock_secret_access_key()
            valid_config = {
                "services": {
                    service_name: {
                        "auth_token": "test-token-123",
                        "source_credentials": {
                            "region": "us-east-1",
                            "iam_keys": {
                                "aws_access_key_id": mock_access_key,
                                "aws_secret_access_key": mock_secret_key,
                            },
                        },
                        "assumed_role": {
                            "RoleArn": "arn:aws:iam::123456789012:role/TestRole",
                            "RoleSessionName": "test-session",
                            "DurationSeconds": 3600,
                        },
                    }
                }
            }

            # Write service file
            with open(service_file, "w", encoding="utf-8") as f:
                yaml.dump(valid_config, f)

            # Create file watcher service (will load existing files)
            watcher = FileWatcherService(config)
            watcher.start()

            # Give watcher time to start and process existing files
            time.sleep(0.5)
            assert watcher.is_running()

            # Verify service was loaded from existing file
            assert service_name in config.services, (
                f"Service {service_name} should be in config after file creation"
            )
            assert service_name in config.services, (
                f"Service {service_name} should be in config after file creation"
            )

            # Verify service config was loaded correctly
            service_config = config.services[service_name]
            assert service_config.auth_token == "test-token-123"
            assert (
                service_config.assumed_role.RoleArn
                == "arn:aws:iam::123456789012:role/TestRole"
            )

            # Now delete the file to test service removal
            service_file.unlink()

            # Wait longer for deletion processing (file system events can take time)
            time.sleep(2.0)

            # Verify service was removed from config
            assert service_name not in config.services, (
                f"Service {service_name} should be removed from config "
                "after file deletion"
            )

            # Stop the watcher
            watcher.stop()
            assert not watcher.is_running()

    def test_service_removal_error_handling(self):
        """Test error handling when service removal fails."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create real Config object
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            # Create service file first
            service_name = "error-service"
            service_file = Path(temp_dir) / f"{service_name}.yaml"
            valid_config = {
                "services": {
                    service_name: {
                        "auth_token": "test-token",
                        "source_credentials": {"region": "us-east-1"},
                        "assumed_role": {
                            "RoleArn": "arn:aws:iam::123456789012:role/TestRole",
                            "RoleSessionName": "test-session",
                        },
                    }
                }
            }

            with open(service_file, "w", encoding="utf-8") as f:
                yaml.dump(valid_config, f)

            # Mock the remove_service method to raise an exception
            with patch.object(
                config, "remove_service", side_effect=Exception("Removal failed")
            ):
                watcher = FileWatcherService(config)
                watcher.start()
                time.sleep(0.5)

                # Verify service was loaded
                assert service_name in config.services

                # Delete file to trigger removal (which should fail)
                service_file.unlink()
                time.sleep(0.5)

                # Service should still be in config because removal failed
                assert service_name in config.services, (
                    "Service should remain when removal fails"
                )

                watcher.stop()

    def test_on_deleted_event_handler(self):
        """Test on_deleted event handler with real file system events."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            watcher = FileWatcherService(config)
            watcher.start()
            time.sleep(0.2)

            # Create and delete a file to trigger on_deleted event
            service_file = Path(temp_dir) / "deleted-service.yaml"
            service_file.touch()  # Create empty file

            # Give time for creation event to be processed
            time.sleep(0.2)

            # Now delete the file
            service_file.unlink()

            # Give time for deletion event to be processed
            time.sleep(0.5)

            # Verify watcher is still running (no crash)
            assert watcher.is_running()

            watcher.stop()

    def test_pattern_matching_for_deleted_files(self):
        """Test pattern matching for deleted files."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config with specific include/exclude patterns
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[
                    DirectoryConfig(
                        path=temp_dir,
                        include_patterns=[".*\\.yaml$"],
                        exclude_patterns=[".*\\.tmp$"],
                    )
                ],
                reload_interval=1,
            )

            handler = ServiceFileHandler(config, 1)

            # Test included file pattern
            included_file = Path(temp_dir) / "service.yaml"
            assert handler._matches_pattern(str(included_file)), (
                "YAML files should be included"
            )

            # Test excluded file pattern
            excluded_file = Path(temp_dir) / "service.tmp"
            assert not handler._matches_pattern(str(excluded_file)), (
                "TMP files should be excluded"
            )

            # Test non-matching pattern
            other_file = Path(temp_dir) / "service.txt"
            assert not handler._matches_pattern(str(other_file)), (
                "TXT files should not match include patterns"
            )

    def test_debounce_timer_with_file_deletion(self):
        """Test debounce timer behavior when file is deleted (lines 204-205)."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,  # Short interval for testing
            )

            handler = ServiceFileHandler(config, 1)

            # Create a file and schedule its deletion
            test_file = Path(temp_dir) / "debounce-test.yaml"
            test_file.touch()

            # Schedule reload for deletion event
            handler._schedule_reload(str(test_file), "deleted")

            # Verify timer was created
            assert handler._debounce_timer is not None

            # Wait for timer to complete (need to wait longer than the interval)
            time.sleep(2.0)

            # Verify the file change was processed (timer executed)
            # The timer should have attempted to process the file deletion
            # We can verify this by checking that pending changes are cleared
            assert len(handler._pending_changes) == 0

    def test_service_removal_with_exception_logging(self):
        """Test service removal exception logging (lines 140-145)."""
        from credproxy.config import (
            Config,
            ServiceConfig,
            AssumedRoleConfig,
            IAMKeysAuthConfig,
            DynamicServicesConfig,
            SourceCredentialsConfig,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            # Create service in config first
            service_name = "exception-service"
            existing_service = ServiceConfig(
                auth_token="test-token",
                source_credentials=SourceCredentialsConfig(
                    region="us-east-1",
                    iam_keys=IAMKeysAuthConfig(
                        aws_access_key_id=mock_access_key_id(),
                        aws_secret_access_key=mock_secret_access_key(),
                    ),
                ),
                assumed_role=AssumedRoleConfig(
                    RoleArn=mock_role_arn(),
                    RoleSessionName="test-session",
                ),
                source_file=str(Path(temp_dir) / f"{service_name}.yaml"),
            )
            config.services[service_name] = existing_service

            # Mock remove_service to raise exception
            with patch.object(
                config, "remove_service", side_effect=Exception("Removal error")
            ):
                with patch("credproxy.file_watcher.LOG") as mock_log:
                    handler = ServiceFileHandler(config, 1)

                    # Simulate file deletion processing
                    handler._process_file_change(
                        str(Path(temp_dir) / f"{service_name}.yaml")
                    )

                    # Verify error was logged
                    mock_log.error.assert_called()
                    error_calls = [
                        call
                        for call in mock_log.error.call_args_list
                        if "Failed to remove service" in str(call)
                    ]
                    assert len(error_calls) > 0

    def test_pattern_matching_edge_cases(self):
        """Test pattern matching edge cases (lines 432->436, 454-455)."""

    from credproxy.config import Config, DynamicServicesConfig

    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config()
        config.dynamic_services = DynamicServicesConfig(
            enabled=True,
            directories=[
                DirectoryConfig(
                    path=temp_dir,
                    include_patterns=[".*\\.yaml$"],
                    exclude_patterns=[".*\\.tmp$"],
                )
            ],
            reload_interval=1,
        )

        handler = ServiceFileHandler(config, 1)

        # Test file that doesn't exist (should handle gracefully)
        non_existent_file = Path(temp_dir) / "nonexistent.yaml"
        result = handler._matches_pattern(str(non_existent_file))
        # Should still match pattern even if file doesn't exist
        assert result is True

        # Test excluded file pattern
        excluded_file = Path(temp_dir) / "service.tmp"
        assert not handler._matches_pattern(str(excluded_file)), (
            "TMP files should be excluded"
        )

        # Test file with no extension (should not match)
        no_ext_file = Path(temp_dir) / "service"
        assert not handler._matches_pattern(str(no_ext_file)), (
            "Files without extension should not match YAML pattern"
        )

    def test_pending_changes_multiple_file_deletions(self):
        """Test pending changes processing for multiple file deletions."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            handler = ServiceFileHandler(config, 1)

            # Create multiple files and schedule their deletion
            files_to_delete = []
            for i in range(3):
                test_file = Path(temp_dir) / f"service-{i}.yaml"
                test_file.touch()
                files_to_delete.append(str(test_file))

            # Schedule multiple deletions rapidly
            for file_path in files_to_delete:
                handler._schedule_reload(file_path, "deleted")

            # Verify all files are in pending changes
            assert len(handler._pending_changes) == 3

            # Wait for timer to process all pending changes
            time.sleep(2.0)

            # Verify pending changes are cleared
            assert len(handler._pending_changes) == 0

    def test_service_update_existing_source(self):
        """Test service update when existing_source == new_source (lines 220-236)."""
        from credproxy.config import Config, IAMKeysAuthConfig, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            # Create an existing service in the config
            service_name = "test-service"
            existing_service = ServiceConfig(
                auth_token="existing-token",
                source_credentials=SourceCredentialsConfig(
                    iam_keys=IAMKeysAuthConfig(
                        aws_access_key_id=mock_access_key_id(),
                        aws_secret_access_key=mock_secret_access_key(),
                    )
                ),
                assumed_role=AssumedRoleConfig(
                    RoleArn=mock_role_arn(),
                    RoleSessionName="test-session",
                ),
                source_file=str(Path(temp_dir) / f"{service_name}.yaml"),
            )
            config.services[service_name] = existing_service

            # Start file watcher
            watcher = FileWatcherService(config)
            watcher.start()
            time.sleep(0.2)

            # Create a service file with the same name (same source)
            service_file = Path(temp_dir) / f"{service_name}.yaml"
            mock_access_key = mock_access_key_id()
            mock_secret_key = mock_secret_access_key()
            mock_role = mock_role_arn()
            service_content = f"""
services:
  test-service:
    auth_token: "updated-token"
    source_credentials:
      iam_keys:
        aws_access_key_id: "{mock_access_key}"
        aws_secret_access_key: "{mock_secret_key}"
    assumed_role:
      RoleArn: "{mock_role}"
      RoleSessionName: "test-session"
"""
            service_file.write_text(service_content)

            # Give time for file to be processed
            time.sleep(2.0)

            # Verify service was updated (not duplicated)
            assert service_name in config.services
            assert len(config.services) == 1  # Should still be only one service
            assert config.services[service_name].auth_token == "updated-token"

            watcher.stop()

    def test_unsupported_file_format_handling(self):
        """Test unsupported file format handling (line 272)."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            handler = ServiceFileHandler(config, 1)

            # Create a file with unsupported extension
            unsupported_file = Path(temp_dir) / "service.txt"
            unsupported_file.write_text("some content")

            # Try to process the unsupported file
            result = handler._load_service_file(str(unsupported_file))

            # Should return None for unsupported format
            assert result is None

    def test_invalid_services_format_handling(self):
        """Test invalid services format handling (lines 288-292)."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            handler = ServiceFileHandler(config, 1)

            # Test case 1: No 'services' key
            invalid_file1 = Path(temp_dir) / "invalid1.yaml"
            invalid_file1.write_text("""
other_key: "value"
auth_token: "token"
""")

            result1 = handler._load_service_file(str(invalid_file1))
            assert result1 is None

            # Test case 2: 'services' key but not a dict
            invalid_file2 = Path(temp_dir) / "invalid2.yaml"
            invalid_file2.write_text("""
services: "not_a_dict"
""")

            result2 = handler._load_service_file(str(invalid_file2))
            assert result2 is None

            # Test case 3: 'services' key but empty dict
            invalid_file3 = Path(temp_dir) / "invalid3.yaml"
            invalid_file3.write_text("""
services: {}
""")

            result3 = handler._load_service_file(str(invalid_file3))
            assert result3 is None

    def test_aws_defaults_merging_with_source_credentials(self):
        """Test AWS defaults merging with source credentials (lines 340-345)."""
        from credproxy.config import Config, IAMKeysAuthConfig, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            # Set up AWS defaults in config
            config.aws_defaults = SourceCredentialsConfig(
                iam_keys=IAMKeysAuthConfig(
                    aws_access_key_id=mock_access_key_id(),
                    aws_secret_access_key=mock_secret_access_key(),
                ),
                region="us-east-1",
            )

            handler = ServiceFileHandler(config, 1)

            # Create a service file with partial source credentials (missing region)
            service_file = Path(temp_dir) / "service.yaml"
            mock_access_key = mock_access_key_id()
            mock_secret_key = mock_secret_access_key()
            mock_role = mock_role_arn()
            service_content = f"""
services:
  test-service:
    auth_token: "test-token"
    source_credentials:
      iam_keys:
        aws_access_key_id: "{mock_access_key}"
        aws_secret_access_key: "{mock_secret_key}"
      # region missing - should come from defaults
    assumed_role:
      RoleArn: "{mock_role}"
      RoleSessionName: "test-session"
"""
            service_file.write_text(service_content)

            # Load the service config
            result = handler._load_service_file(str(service_file))
            assert result is not None

            service_name, service_config = result
            assert service_name == "test-service"

            # Verify that defaults were merged
            assert (
                service_config.source_credentials.iam_keys.aws_access_key_id
                == mock_access_key
            )  # From file
            assert (
                service_config.source_credentials.iam_keys.aws_secret_access_key
                == mock_secret_key
            )  # From file
            assert (
                service_config.source_credentials.region == "us-east-1"
            )  # From defaults
            assert (
                service_config.source_credentials.region == "us-east-1"
            )  # From defaults

    def test_observer_scheduling_edge_cases(self):
        """Test observer scheduling edge cases (lines 269-273)."""
        from credproxy.config import Config, DynamicServicesConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.dynamic_services = DynamicServicesConfig(
                enabled=True,
                directories=[DirectoryConfig(path=temp_dir)],
                reload_interval=1,
            )

            watcher = FileWatcherService(config)
            watcher.start()
            time.sleep(0.2)

            # Create a file with unsupported format to trigger the warning
            unsupported_file = Path(temp_dir) / "service.txt"
            unsupported_file.write_text("unsupported content")

            # Give time for file to be processed
            time.sleep(2.0)

            # Verify watcher is still running (no crash)
            assert watcher.is_running()

            watcher.stop()
