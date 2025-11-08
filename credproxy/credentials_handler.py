#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING
from dataclasses import asdict, dataclass

import boto3
from botocore.exceptions import ClientError

from credproxy.logger import LOG


if TYPE_CHECKING:
    from credproxy.config import Config, ServiceConfig


@dataclass
class ServiceCredentialsManager:
    """Service credentials manager with caching and expiry time."""

    aws_access_key_id: str
    aws_secret_access_key: str
    session_token: str
    expiry: float

    def is_expired(self) -> bool:
        """Check if credentials are expired."""
        return time.time() > self.expiry

    def get_sensitive_values(self) -> list[str]:
        """Get list of sensitive values that should be sanitized.

        Returns:
            List of credential values
        """
        return [
            self.aws_access_key_id,
            self.aws_secret_access_key,
            self.session_token,
        ]

    def to_dict(self) -> dict:
        """Convert to dictionary format for API response."""
        from datetime import datetime, timezone

        expiration_iso = datetime.fromtimestamp(self.expiry, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        return {
            "AccessKeyId": self.aws_access_key_id,
            "SecretAccessKey": self.aws_secret_access_key,
            "Token": self.session_token,
            "Expiration": expiration_iso,
        }


class CredentialsHandler:
    """Simple credentials handler with caching and expiry."""

    def __init__(self, config: Config):
        self.config = config
        self.cache: dict[str, ServiceCredentialsManager] = {}
        self._cache_lock = threading.RLock()
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()
        self._start_cache_cleanup()

    def _start_cache_cleanup(self) -> None:
        """Start background thread for periodic cache cleanup."""

        def cleanup_expired():
            """Periodically clean up expired credentials from cache."""
            while not self._stop_cleanup.is_set():
                try:
                    # Wait for 60 seconds or until stop is signaled
                    if self._stop_cleanup.wait(timeout=60):
                        break

                    # Clean up expired entries
                    with self._cache_lock:
                        expired_services = [
                            service_name
                            for service_name, creds in self.cache.items()
                            if creds.is_expired()
                        ]
                        for service_name in expired_services:
                            # Unregister sensitive values before removing from cache
                            from credproxy.sanitizer import unregister_sensitive_value

                            creds = self.cache[service_name]
                            for value in creds.get_sensitive_values():
                                unregister_sensitive_value(value)

                            del self.cache[service_name]
                            LOG.debug(
                                "Removed expired credentials from cache: %s",
                                service_name,
                            )

                        if expired_services:
                            LOG.info(
                                "Cache cleanup: removed %d expired credential entries",
                                len(expired_services),
                            )
                except Exception as error:
                    LOG.error("Error during cache cleanup")
                    LOG.exception(error)

        self._cleanup_thread = threading.Thread(
            target=cleanup_expired, daemon=True, name="cache-cleanup"
        )
        self._cleanup_thread.start()
        LOG.debug("Started background cache cleanup thread")

    def cleanup(self) -> None:
        """Clean up resources during graceful shutdown."""
        # Stop the cleanup thread
        if self._cleanup_thread:
            LOG.info("Stopping cache cleanup thread")
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5)
            LOG.info("Cache cleanup thread stopped")

        with self._cache_lock:
            cache_size = len(self.cache)
            if cache_size > 0:
                LOG.info(
                    "Cleaning up %d cached credential entries during shutdown",
                    cache_size,
                )
                # Unregister all sensitive values
                from credproxy.sanitizer import unregister_sensitive_value

                for creds in self.cache.values():
                    for value in creds.get_sensitive_values():
                        unregister_sensitive_value(value)

                self.cache.clear()
                LOG.info("Credential cache cleared successfully")
            else:
                LOG.info("No cached credentials to clean up")

    def get_credentials(self, service_name: str) -> dict:
        """Get credentials for a service, using cache if not expired."""
        with self._cache_lock:
            # Check cache first
            if service_name in self.cache:
                cached = self.cache[service_name]
                if not cached.is_expired():
                    LOG.debug("Using cached credentials for %s", service_name)
                    return cached.to_dict()
                else:
                    # Cache expired
                    pass
            else:
                # Not in cache
                pass

        # Generate new credentials
        LOG.info("Generating new credentials for %s", service_name)
        service_config = self.config.services[service_name]
        credentials = self._assume_role(service_config)

        # Register temporary credentials for sanitization
        from credproxy.sanitizer import register_sensitive_value

        register_sensitive_value(credentials["AccessKeyId"])
        register_sensitive_value(credentials["SecretAccessKey"])
        register_sensitive_value(credentials["SessionToken"])

        # Use the exact expiration from STS assume role API call
        expiry_time = credentials["Expiration"].timestamp()
        service_creds = ServiceCredentialsManager(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            session_token=credentials["SessionToken"],
            expiry=expiry_time,
        )

        with self._cache_lock:
            self.cache[service_name] = service_creds
        return service_creds.to_dict()

    def _assume_role(self, service_config: ServiceConfig) -> dict:
        """Assume role for service and return credentials."""
        # Get service name for metrics
        service_name = next(
            (
                name
                for name, config in self.config.services.items()
                if config == service_config
            ),
            "unknown",
        )

        try:
            # Get AWS config for this service
            aws_config = self._get_aws_config(service_config)

            # Create STS client with profile if specified
            profile_name = aws_config.pop("profile_name", None)
            if profile_name:
                session = boto3.Session(profile_name=profile_name)
                sts_client = session.client("sts", **aws_config)
            else:
                sts_client = boto3.client("sts", **aws_config)

            # Convert dataclass to dict and filter out None values for boto3 API call
            assumed_role_dict = asdict(service_config.assumed_role)
            assume_role_params = {
                k: v for k, v in assumed_role_dict.items() if v is not None
            }

            # Assume role
            response = sts_client.assume_role(**assume_role_params)

            # AWS operation successful - no detailed metrics needed

            return response["Credentials"]

        except ClientError as error:
            # AWS operation failed - no detailed metrics needed

            LOG.error("Failed to assume role for %s: %s", service_name, str(error))
            raise

    def _get_aws_config(self, service_config: ServiceConfig) -> dict:
        """Get AWS configuration for a service."""
        service_creds = service_config.source_credentials
        default_creds = self.config.aws_defaults

        # Use or operator for clean fallbacks
        region = (service_creds and service_creds.region) or (
            default_creds and default_creds.region
        )
        profile_config = (service_creds and service_creds.iam_profile) or (
            default_creds and default_creds.iam_profile
        )
        keys = (service_creds and service_creds.iam_keys) or (
            default_creds and default_creds.iam_keys
        )

        aws_config = {"region_name": region}

        # Auto-detect auth method based on presence of config objects
        if profile_config and profile_config.profile_name:
            # IAM profile authentication
            aws_config["profile_name"] = profile_config.profile_name
        elif keys:
            # IAM keys authentication
            aws_config.update(
                {
                    "aws_access_key_id": keys.aws_access_key_id,
                    "aws_secret_access_key": keys.aws_secret_access_key,
                }
            )
            if hasattr(keys, "session_token") and keys.session_token:
                aws_config["aws_session_token"] = keys.session_token
        # If neither profile_config nor keys present, use default SDK behavior

        return aws_config
