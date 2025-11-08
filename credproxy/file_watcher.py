#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""File watcher service for dynamic configuration loading."""

from __future__ import annotations

import re
import json
import time
import threading
from typing import TYPE_CHECKING
from pathlib import Path


if TYPE_CHECKING:
    from credproxy.config import Config


import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from credproxy.config import ServiceConfig
from credproxy.logger import LOG


def should_include_file(
    file_path: str, include_patterns: list[str], exclude_patterns: list[str]
) -> bool:
    """
        Apply filtering logic: exclude first, then include.
        Returns True if file should be processed.

    Args:
            file_path: Path to file to check
            include_patterns: List of regex patterns to include (if empty,
                              include all non-excluded)
            exclude_patterns: List of regex patterns to exclude

        Returns:
            True if file should be processed, False otherwise
    """
    # Use full path for matching to support directory-based patterns
    # Normalize path separators for cross-platform compatibility
    normalized_path = file_path.replace("\\", "/")

    # Step 1: Check exclude patterns
    for pattern in exclude_patterns:
        try:
            if re.match(pattern, normalized_path):
                LOG.debug("File %s excluded by pattern: %s", normalized_path, pattern)
                return False
        except re.error as error:
            LOG.warning("Invalid exclude pattern '%s': %s", pattern, error)

    # Step 2: Check include patterns
    if not include_patterns:
        LOG.debug("File %s included (no include patterns)", normalized_path)
        return True

    for pattern in include_patterns:
        try:
            if re.match(pattern, normalized_path):
                LOG.debug("File %s included by pattern: %s", normalized_path, pattern)
                return True
        except re.error as error:
            LOG.warning("Invalid include pattern '%s': %s", pattern, error)

    LOG.debug("File %s excluded (no include pattern match)", normalized_path)
    return False


def get_directory_patterns(
    file_path: str, directories: list
) -> tuple[list[str], list[str]]:
    """
    Get the include and exclude patterns for the directory that contains the given file.

    Args:
        file_path: Path to the file to check
        directories: List of DirectoryConfig objects

    Returns:
        Tuple of (include_patterns, exclude_patterns) for the matching directory
    """
    from credproxy.config import DirectoryConfig

    normalized_file_path = str(Path(file_path).resolve()).replace("\\", "/")

    for directory_config in directories:
        if isinstance(directory_config, DirectoryConfig):
            directory_path = str(Path(directory_config.path).resolve()).replace(
                "\\", "/"
            )
            if normalized_file_path.startswith(directory_path):
                return (
                    directory_config.include_patterns,
                    directory_config.exclude_patterns,
                )

    # If no matching directory found, return empty patterns (include all)
    return [], []


class ServiceFileHandler(FileSystemEventHandler):
    """Handle file system events for service configuration files."""

    def __init__(self, config: Config, reload_interval: int):
        self.config = config
        self.reload_interval = reload_interval
        self._pending_changes: dict[str, float] = {}
        self._debounce_timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory and self._matches_pattern(event.src_path):
            absolute_path = Path(event.src_path).resolve()
            LOG.info(
                "File watcher detected new file: %s (event: created, absolute: %s)",
                event.src_path,
                absolute_path,
            )
            self._schedule_reload(str(absolute_path), "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory and self._matches_pattern(event.src_path):
            absolute_path = Path(event.src_path).resolve()
            LOG.info(
                "File watcher detected file change: %s (event: modified, absolute: %s)",
                event.src_path,
                absolute_path,
            )
            self._schedule_reload(str(absolute_path), "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if not event.is_directory and self._matches_pattern(event.src_path):
            LOG.info(
                "File watcher detected file deletion: %s (event: deleted)",
                event.src_path,
            )
            self._schedule_reload(event.src_path, "deleted")

    def _matches_pattern(self, file_path: str) -> bool:
        """Check if file matches the configured include/exclude patterns."""
        if not self.config.dynamic_services:
            return False

        include_patterns, exclude_patterns = get_directory_patterns(
            file_path, self.config.dynamic_services.directories
        )

        return should_include_file(file_path, include_patterns, exclude_patterns)

    def _schedule_reload(self, file_path: str, event_type: str) -> None:
        """Schedule a reload with debouncing.

        Uses a separate lock strategy to prevent potential deadlock between
        timer cancellation and callback execution.
        """
        # Cancel timer outside of lock to prevent deadlock
        timer_to_cancel = None
        with self._lock:
            self._pending_changes[file_path] = time.time()
            timer_to_cancel = self._debounce_timer
            self._debounce_timer = None

        # Cancel old timer outside of lock
        if timer_to_cancel:
            timer_to_cancel.cancel()

        # Create and start new timer
        with self._lock:
            self._debounce_timer = threading.Timer(
                self.reload_interval, self._process_pending_changes
            )
            self._debounce_timer.start()

            LOG.debug("Scheduled reload for %s (event: %s)", file_path, event_type)

    def _process_pending_changes(self) -> None:
        """Process all pending file changes."""
        with self._lock:
            if not self._pending_changes:
                return

            pending = self._pending_changes.copy()
            self._pending_changes.clear()

        for file_path, timestamp in pending.items():
            try:
                self._process_file_change(file_path)
            except Exception as error:
                LOG.error("Failed to process file change for %s: %s", file_path, error)

    def _process_file_change(self, file_path: str) -> None:
        """Process a single file change."""
        path = Path(file_path)

        # Check if file still exists
        if not path.exists():
            # If file deleted, remove service by filename (can't read service name)
            service_name = path.stem
            LOG.info(
                "Service file %s deleted, removing service %s", file_path, service_name
            )
            try:
                self.config.remove_service(service_name)
                LOG.info("Successfully removed service %s from registry", service_name)
            except Exception as error:
                LOG.error("Failed to remove service %s: %s", service_name, error)
            return

        # Load and parse the file
        try:
            LOG.info("Attempting to load service configuration from %s", file_path)
            result = self._load_service_file(file_path)
            if result is None:
                LOG.warning("No valid service configuration found in %s", file_path)
                return

            service_name, service_config = result
            if service_config:
                # Check if service already exists
                if service_name in self.config.services:
                    existing_service = self.config.services[service_name]
                    existing_source = existing_service.source_file
                    new_source = str(Path(file_path).resolve())

                    # Only allow update if it's the same file being modified
                    if existing_source == new_source:
                        LOG.info(
                            "Updating existing service %s from %s",
                            service_name,
                            file_path,
                        )
                        self.config.update_service(service_name, service_config)
                        LOG.info(
                            "Successfully updated service %s in registry", service_name
                        )
                    else:
                        LOG.warning(
                            (
                                "Service '%s' already exists from %s. "
                                "Ignoring duplicate from %s"
                            ),
                            service_name,
                            existing_source,
                            new_source,
                        )
                else:
                    LOG.info("Adding new service %s from %s", service_name, file_path)
                    self.config.add_service(service_name, service_config)
                    LOG.info("Successfully added service %s to registry", service_name)
            else:
                LOG.warning("No valid service configuration found in %s", file_path)
        except Exception as error:
            LOG.error(
                "Failed to load service configuration from %s: %s", file_path, error
            )
            LOG.info(
                "Ignoring problematic file %s and continuing with other services",
                file_path,
            )

    def _load_service_file(self, file_path: str) -> tuple[str, ServiceConfig] | None:
        """Load and validate a service configuration file with substitutions."""
        path = Path(file_path)

        try:
            LOG.info("Loading service configuration file: %s", file_path)
            with open(path, encoding="utf-8") as f:
                if path.suffix.lower() in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif path.suffix.lower() == ".json":
                    data = json.load(f)
                else:
                    LOG.warning("Unsupported file format for %s, skipping", file_path)
                    return None

            if not isinstance(data, dict):
                LOG.error(
                    "Invalid configuration format in %s: expected object", file_path
                )
                return None

            # Only process the 'services' key, ignore all other top-level keys
            if "services" not in data:
                LOG.error("No 'services' key found in %s, ignoring file", file_path)
                return None

            services_data = data["services"]
            if not isinstance(services_data, dict) or not services_data:
                LOG.error(
                    "Invalid 'services' format in %s: expected non-empty object",
                    file_path,
                )
                return None

            # Extract the service configuration (use first service found)
            service_name = ""
            service_data = None
            for name, config in services_data.items():
                service_name = str(name)
                service_data = config
                break

            if not service_data or not service_name:
                LOG.error(
                    "No service configuration found in 'services' of %s", file_path
                )
                return None

            LOG.info(
                "Found service configuration for %s in %s", service_name, file_path
            )

            # Apply variable substitutions using existing substitution logic
            from credproxy.substitutions import substitute_variables

            service_data = substitute_variables(service_data)

            # Validate against service schema
            from credproxy.config import Config

            # Create a temporary config with just this service to validate
            temp_config_data = {"services": {service_name: service_data}}
            try:
                Config.validate_schema(temp_config_data)
                LOG.info(
                    "Schema validation successful for service %s in %s",
                    service_name,
                    file_path,
                )
            except Exception as error:
                LOG.error("Schema validation failed for %s: %s", file_path, error)
                return None

            # Create ServiceConfig object using existing config parsing logic
            source_creds_data = service_data.get("source_credentials", {})
            assumed_role_data = service_data.get("assumed_role", {})

            # Merge with defaults if available
            merged_source_creds_data = source_creds_data
            if self.config.aws_defaults:
                from credproxy.config import merge_aws_config

                defaults_dict = self.config._source_credentials_config_to_dict(
                    self.config.aws_defaults
                )
                merged_source_creds_data = merge_aws_config(
                    defaults_dict, source_creds_data
                )

            service_config = ServiceConfig(
                auth_token=service_data["auth_token"],
                source_credentials=self.config._create_source_credentials_config(
                    merged_source_creds_data
                ),
                assumed_role=self.config._create_assumed_role_config(assumed_role_data),
                source_file=str(
                    Path(file_path).resolve()
                ),  # Track which file loaded this service
            )
            LOG.info("Successfully created service configuration for %s", service_name)
            return service_name, service_config

        except Exception as error:
            LOG.error("Error reading service file %s: %s", file_path, error)
            LOG.info("Ignoring problematic file %s and continuing", file_path)
            return None


class FileWatcherService:
    """Service for monitoring configuration directory for changes."""

    def __init__(self, config: Config):
        self.config = config
        self.observer: Observer | None = None
        self.handler: ServiceFileHandler | None = None
        self._running = False

    def start(self) -> None:
        """Start the file watcher service."""
        if not self.config.dynamic_services or not self.config.dynamic_services.enabled:
            LOG.info("Dynamic services disabled, not starting file watcher")
            return

        if self._running:
            LOG.warning("File watcher service already running")
            return

        try:
            # File watcher starting
            self.handler = ServiceFileHandler(
                config=self.config,
                reload_interval=self.config.dynamic_services.reload_interval,
            )

            self.observer = Observer()
            if self.observer and self.handler:
                # Create observers for each directory
                for directory_config in self.config.dynamic_services.directories:
                    directory = Path(directory_config.path)
                    if not directory.exists():
                        LOG.info("Creating dynamic services directory: %s", directory)
                        directory.mkdir(parents=True, exist_ok=True)

                    self.observer.schedule(
                        self.handler, str(directory), recursive=False
                    )
                    LOG.info("Added directory to watcher: %s", directory.resolve())

                self.observer.start()
            self._running = True

            LOG.info(
                "Started file watcher for %d directories",
                len(self.config.dynamic_services.directories),
            )

            # Load existing files
            self._load_existing_files()

        except Exception as error:
            LOG.error("Failed to start file watcher service: %s", error)
            raise

    def stop(self) -> None:
        """Stop the file watcher service."""
        if not self._running:
            return

        try:
            if self.handler and self.handler._debounce_timer:
                self.handler._debounce_timer.cancel()

            if self.observer:
                # Use configurable timeout with safe fallback
                timeout = 5  # Default timeout
                if (
                    self.config.dynamic_services
                    and hasattr(self.config.dynamic_services, "watcher_stop_timeout")
                    and isinstance(
                        self.config.dynamic_services.watcher_stop_timeout, int
                    )
                ):
                    timeout = self.config.dynamic_services.watcher_stop_timeout
                self.observer.stop()
                self.observer.join(timeout=timeout)

            self._running = False
            LOG.info("Stopped file watcher service")

        except Exception as error:
            LOG.error("Error stopping file watcher service: %s", error)

    def _load_existing_files(self) -> None:
        """Load existing service files from all configured directories."""
        if not self.config.dynamic_services:
            return

        try:
            total_file_count = 0
            for directory_config in self.config.dynamic_services.directories:
                directory = Path(directory_config.path)
                LOG.info("Loading existing service files from %s", directory)

                if not directory.exists():
                    LOG.warning("Directory does not exist: %s", directory)
                    continue

                directory_file_count = 0
                # Scan all files in directory and apply filtering
                for file_path in directory.iterdir():
                    if file_path.is_file():
                        # Apply filtering logic using per-directory patterns
                        if should_include_file(
                            str(file_path),
                            directory_config.include_patterns,
                            directory_config.exclude_patterns,
                        ):
                            directory_file_count += 1
                            total_file_count += 1
                            LOG.info("Loading existing service file: %s", file_path)
                            if self.handler:
                                self.handler._process_file_change(str(file_path))
                        else:
                            LOG.debug("Skipping file %s (filtered out)", file_path)

                LOG.info(
                    "Loaded %d service files from %s", directory_file_count, directory
                )

            LOG.info(
                "Loaded %d total service files from %d directories",
                total_file_count,
                len(self.config.dynamic_services.directories),
            )

        except Exception as error:
            LOG.error("Error loading existing service files: %s", error)

    def is_running(self) -> bool:
        """Check if the file watcher service is running."""
        return self._running
