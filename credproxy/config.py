#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

from __future__ import annotations

import json
import threading
from typing import Any
from pathlib import Path
from dataclasses import field, dataclass

import yaml
import jsonschema

from credproxy.logger import LOG
from credproxy.metrics import update_active_services
from credproxy.settings import NAMESPACE, get_config_file
from credproxy.sanitizer import (
    register_sensitive_dict,
    register_sensitive_value,
    sanitize_exception_message,
)

# Import substitution parser and centralized logging
from credproxy.substitutions import substitute_variables


def keyisset(key: str, data: dict) -> Any:
    """Check if key exists in dict and return value, raise if missing."""
    if key not in data:
        raise KeyError(f"Required key '{key}' not found in configuration")
    return data[key]


def set_else_none(key: str, data: dict, default: Any) -> Any:
    """Get value from dict or return default if not present."""
    return data.get(key, default)


@dataclass
class IAMProfileAuthConfig:
    """IAM profile authentication configuration."""

    profile_name: str
    config_file: str | None = None  # Path to AWS config file


@dataclass
class IAMKeysAuthConfig:
    """IAM access keys authentication configuration."""

    aws_access_key_id: str
    aws_secret_access_key: str
    session_token: str | None = None  # For temporary credentials


@dataclass
class SourceCredentialsConfig:
    """Source AWS credentials configuration."""

    region: str | None = None
    iam_profile: IAMProfileAuthConfig | None = None
    iam_keys: IAMKeysAuthConfig | None = None


@dataclass
class AssumedRoleConfig:
    """AWS role assumption configuration."""

    RoleArn: str
    RoleSessionName: str = "credproxy"
    DurationSeconds: int = 900
    ExternalId: str | None = None
    PolicyArns: list[dict] | None = None
    Policy: str | None = None
    Tags: list[dict] | None = None
    TransitiveTagKeys: list[str] | None = None
    SerialNumber: str | None = None
    TokenCode: str | None = None
    SourceIdentity: str | None = None


@dataclass
class ServerConfig:
    """Server configuration settings."""

    host: str = "0.0.0.0"
    port: int = 1338
    debug: bool = False
    log_health_checks: bool = False


@dataclass
class CredentialsConfig:
    """Credential management settings."""

    refresh_buffer_seconds: int = 300
    retry_delay: int = 60
    request_timeout: int = 30


@dataclass
class DirectoryConfig:
    """Configuration for a single monitored directory."""

    path: str
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)


@dataclass
class DynamicServicesConfig:
    """Dynamic services configuration settings."""

    enabled: bool = False
    directories: list[DirectoryConfig] = field(
        default_factory=lambda: [DirectoryConfig(path="/credproxy/dynamic")]
    )
    reload_interval: int = 5
    watcher_stop_timeout: int = 5  # Timeout in seconds for stopping the file watcher


@dataclass
class PrometheusConfig:
    """Prometheus metrics configuration."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 9090


@dataclass
class MetricsConfig:
    """Metrics and telemetry configuration."""

    prometheus: PrometheusConfig = field(default_factory=PrometheusConfig)


@dataclass
class ServiceConfig:
    """Configuration for a single service."""

    auth_token: str
    source_credentials: SourceCredentialsConfig
    assumed_role: AssumedRoleConfig
    source_file: str | None = None  # Track which file loaded this service


def _parse_directory_configs(
    directories_data: list | str, dynamic_services_data: dict
) -> list[DirectoryConfig]:
    """Parse directory configurations from various formats.

    Args:
        directories_data: List of directory paths or directory config objects
        dynamic_services_data: Parent dynamic services configuration

    Returns:
        List of DirectoryConfig objects
    """
    if isinstance(directories_data, list) and directories_data:
        if isinstance(directories_data[0], str):
            # Old format: list of strings
            return [
                DirectoryConfig(
                    path=path,
                    include_patterns=set_else_none(
                        "include_patterns", dynamic_services_data, []
                    ),
                    exclude_patterns=set_else_none(
                        "exclude_patterns", dynamic_services_data, []
                    ),
                )
                for path in directories_data
            ]
        else:
            # New format: list of objects
            return [
                DirectoryConfig(
                    path=dir_config["path"],
                    include_patterns=set_else_none("include_patterns", dir_config, []),
                    exclude_patterns=set_else_none("exclude_patterns", dir_config, []),
                )
                for dir_config in directories_data
            ]
    return [DirectoryConfig(path="/credproxy/dynamic")]


def merge_aws_config(defaults: dict, overrides: dict) -> dict:
    """Merge AWS configuration with defaults and service-specific overrides."""
    merged = defaults.copy() if defaults else {}

    # Apply service-specific overrides
    for key, value in overrides.items():
        merged[key] = value  # Override even if None is explicitly set

    return merged


@dataclass
class Config:
    """Main configuration class."""

    server: ServerConfig = field(default_factory=ServerConfig)
    credentials: CredentialsConfig = field(default_factory=CredentialsConfig)
    aws_defaults: SourceCredentialsConfig | None = None
    services: dict[str, ServiceConfig] = field(default_factory=dict)
    dynamic_services: DynamicServicesConfig | None = None
    metrics: MetricsConfig = field(default_factory=MetricsConfig)

    # Token-to-service mapping for instant lookup
    _token_to_service: dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )

    # Thread lock for service management operations
    _services_lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False
    )

    # Class-level sanitizer for message sanitization

    def __post_init__(self):
        """Build token-to-service mapping after initialization."""
        self._build_token_mapping()

    def _build_token_mapping(self):
        """Build instant lookup mapping from tokens to service names."""
        self._token_to_service.clear()
        LOG.info("Building token mapping for %d services", len(self.services))
        for service_name, service_config in self.services.items():
            self._token_to_service[service_config.auth_token] = service_name
            LOG.debug(
                "Mapped token for service %s: %s...",
                service_name,
                service_config.auth_token[:8] + "...",
            )
        LOG.info(
            "Token mapping built successfully with %d services",
            len(self._token_to_service),
        )

    def get_service_name_by_token(self, token: str) -> str | None:
        """Get service name by authorization token."""
        service_name = self._token_to_service.get(token)
        LOG.info("Token lookup for %s...: %s", token[:8] + "...", service_name)
        LOG.debug("Token registry contains %d tokens", len(self._token_to_service))
        LOG.debug("Available services: %s", list(self.services.keys()))

        if not service_name:
            LOG.warning("Token not found in registry: %s...", token[:8] + "...")
            LOG.info("Available services in registry: %s", list(self.services.keys()))
            token_list = [f"{token[:8]}..." for token in self._token_to_service.keys()]
            LOG.info("Available tokens in registry: %s", token_list)
        return service_name

    def add_service(self, service_name: str, service_config: ServiceConfig) -> bool:
        """Add a new service dynamically."""
        with self._services_lock:
            # Check if service already exists (static services take precedence)
            if service_name in self.services:
                LOG.warning(
                    "Service '%s' already defined. Ignoring service from %s",
                    service_name,
                    service_config.source_file or "unknown",
                )
                return False

            # Add service and rebuild token mapping
            self.services[service_name] = service_config
            self._build_token_mapping()
            LOG.info(
                "Added dynamic service '%s' from %s with token %s...",
                service_name,
                service_config.source_file or "unknown",
                service_config.auth_token[:8] + "...",
            )

            # Update active services count
            update_active_services(len(self.services))

            return True

    def remove_service(self, service_name: str) -> bool:
        """Remove a service dynamically."""
        with self._services_lock:
            if service_name not in self.services:
                LOG.warning("Service '%s' not found for removal", service_name)
                return False

            # Remove service and rebuild token mapping
            del self.services[service_name]
            self._build_token_mapping()
            LOG.info("Removed dynamic service '%s'", service_name)

            # Update active services count
            update_active_services(len(self.services))

            return True

    def update_service(self, service_name: str, service_config: ServiceConfig) -> bool:
        """Update an existing service dynamically."""
        with self._services_lock:
            if service_name not in self.services:
                LOG.warning("Service '%s' not found for update", service_name)
                return False

            # Update service and rebuild token mapping
            self.services[service_name] = service_config
            self._build_token_mapping()
            LOG.info(
                "Updated dynamic service '%s' from %s",
                service_name,
                service_config.source_file or "unknown",
            )

            # Service updated - no specific metric needed

            return True

    @classmethod
    def from_file(cls, config_path: str | None = None) -> Config:
        """Load configuration from YAML or JSON file."""
        if config_path is None:
            config_path = get_config_file(NAMESPACE)
        else:
            # Check if CREDPROXY_CONFIG_FILE environment variable is set
            # and override the provided config_path if it is
            env_config_path = get_config_file(NAMESPACE)
            default_path = "/credproxy/config.yaml"
            if env_config_path != default_path:
                config_path = env_config_path

        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Load raw YAML/JSON first
        try:
            with open(config_file, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            LOG.info("Loaded configuration from %s as YAML", config_path)
        except yaml.YAMLError as error:
            LOG.debug("YAML parsing failed, trying JSON")
            try:
                with open(config_file, encoding="utf-8") as f:
                    config_data = json.load(f)
                LOG.info("Loaded configuration from %s as JSON", config_path)
            except json.JSONDecodeError as json_error:
                raise ValueError(
                    f"File is not valid YAML or JSON. YAML error: {error}, "
                    f"JSON error: {json_error}"
                ) from error

        return cls.from_dict(config_data, config_path)

    @classmethod
    def from_dict(cls, config_data: dict, config_path: str | None = None) -> Config:
        """Create configuration from dictionary."""
        # Apply variable substitution to the original config data
        config_data = substitute_variables(config_data)

        # Validate the substituted config against schema
        cls.validate_schema(config_data)

        server_data = config_data.get("server", {})
        creds_data = config_data.get("credentials", {})
        aws_defaults_data = config_data.get("aws_defaults", {})
        services_data = config_data.get("services", {})
        dynamic_services_data = config_data.get("dynamic_services", {})
        metrics_data = config_data.get("metrics", {})

        # Create AWS defaults if provided
        aws_defaults = None
        if aws_defaults_data:
            aws_defaults = cls._create_source_credentials_config(aws_defaults_data)

        # Create dynamic services config if provided (needed for validation)
        dynamic_services = None
        if dynamic_services_data:
            # Handle directories - convert from new format to DirectoryConfig objects
            directories_data = set_else_none(
                "directories", dynamic_services_data, ["/credproxy/dynamic"]
            )

            # Parse directories using helper function
            directories = _parse_directory_configs(
                directories_data, dynamic_services_data
            )

            dynamic_services = DynamicServicesConfig(
                enabled=set_else_none("enabled", dynamic_services_data, False),
                directories=directories,
                reload_interval=set_else_none(
                    "reload_interval", dynamic_services_data, 5
                ),
                watcher_stop_timeout=set_else_none(
                    "watcher_stop_timeout", dynamic_services_data, 5
                ),
            )

        services = {}
        for service_name, service_config in services_data.items():
            source_creds_data = service_config.get("source_credentials", {})
            assumed_role_data = service_config.get("assumed_role", {})

            # Merge defaults with service-specific overrides for source credentials
            merged_source_creds_data = merge_aws_config(
                cls._source_credentials_config_to_dict(aws_defaults)
                if aws_defaults
                else {},
                source_creds_data,
            )

            # Register sensitive values for sanitization

            # Register auth token
            auth_token = keyisset("auth_token", service_config)
            register_sensitive_value(auth_token)

            # Register credentials from source_credentials
            register_sensitive_dict(merged_source_creds_data)

            # Register ExternalId if present
            if "ExternalId" in assumed_role_data:
                register_sensitive_value(assumed_role_data["ExternalId"])

            services[service_name] = ServiceConfig(
                auth_token=auth_token,
                source_credentials=cls._create_source_credentials_config(
                    merged_source_creds_data
                ),
                assumed_role=cls._create_assumed_role_config(assumed_role_data),
                source_file=str(Path(config_path).resolve())
                if config_path
                else "static_config",
            )

        # Validate service configurations after inheritance
        cls._validate_services(services, dynamic_services)

        # Create metrics config
        prometheus_data = metrics_data.get("prometheus", {})
        metrics = MetricsConfig(
            prometheus=PrometheusConfig(
                enabled=set_else_none("enabled", prometheus_data, True),
                host=set_else_none("host", prometheus_data, "0.0.0.0"),
                port=set_else_none("port", prometheus_data, 9090),
            )
        )

        # Import LOG_HEALTH_CHECKS from settings for env var support
        from credproxy.settings import LOG_HEALTH_CHECKS

        # Config file setting OR environment variable (either can enable it)
        log_health_checks_config = set_else_none(
            "log_health_checks", server_data, False
        )
        log_health_checks = log_health_checks_config or LOG_HEALTH_CHECKS

        return cls(
            server=ServerConfig(
                host=set_else_none("host", server_data, "localhost"),
                port=set_else_none("port", server_data, 1338),
                debug=set_else_none("debug", server_data, False),
                log_health_checks=log_health_checks,
            ),
            credentials=CredentialsConfig(
                refresh_buffer_seconds=set_else_none(
                    "refresh_buffer_seconds", creds_data, 300
                ),
                retry_delay=set_else_none("retry_delay", creds_data, 60),
                request_timeout=set_else_none("request_timeout", creds_data, 30),
            ),
            aws_defaults=aws_defaults,
            services=services,
            dynamic_services=dynamic_services,
            metrics=metrics,
        )

    @classmethod
    def _create_source_credentials_config(cls, data: dict) -> SourceCredentialsConfig:
        """Create SourceCredentialsConfig from dictionary data."""
        iam_profile_config = None
        iam_keys_config = None

        # Auto-detect auth method based on presence of config objects
        if "iam_profile" in data:
            profile_data = data["iam_profile"]
            iam_profile_config = IAMProfileAuthConfig(
                profile_name=set_else_none("profile_name", profile_data, None),
                config_file=set_else_none("config_file", profile_data, None),
            )
        elif "iam_keys" in data:
            keys_data = data["iam_keys"]
            iam_keys_config = IAMKeysAuthConfig(
                aws_access_key_id=set_else_none("aws_access_key_id", keys_data, None),
                aws_secret_access_key=set_else_none(
                    "aws_secret_access_key", keys_data, None
                ),
                session_token=set_else_none("session_token", keys_data, None),
            )
        # If neither iam_profile nor iam_keys present, use default SDK behavior

        return SourceCredentialsConfig(
            region=set_else_none("region", data, None),
            iam_profile=iam_profile_config,
            iam_keys=iam_keys_config,
        )

    @classmethod
    def _create_assumed_role_config(cls, data: dict) -> AssumedRoleConfig:
        """Create AssumedRoleConfig from dictionary data."""
        return AssumedRoleConfig(
            RoleArn=keyisset("RoleArn", data),
            RoleSessionName=set_else_none("RoleSessionName", data, "credproxy"),
            DurationSeconds=set_else_none("DurationSeconds", data, 900),
            ExternalId=set_else_none("ExternalId", data, None),
            PolicyArns=set_else_none("PolicyArns", data, None),
            Policy=set_else_none("Policy", data, None),
            Tags=set_else_none("Tags", data, None),
            TransitiveTagKeys=set_else_none("TransitiveTagKeys", data, None),
            SerialNumber=set_else_none("SerialNumber", data, None),
            TokenCode=set_else_none("TokenCode", data, None),
            SourceIdentity=set_else_none("SourceIdentity", data, None),
        )

    @classmethod
    def _source_credentials_config_to_dict(
        cls, source_config: SourceCredentialsConfig | None
    ) -> dict:
        """Convert SourceCredentialsConfig to dictionary for merging."""
        if not source_config:
            return {}

        result: dict = {
            "region": source_config.region,
        }

        if source_config.iam_profile:
            result["iam_profile"] = {
                "profile_name": source_config.iam_profile.profile_name,
                "config_file": source_config.iam_profile.config_file,
            }
        elif source_config.iam_keys:
            result["iam_keys"] = {
                "aws_access_key_id": source_config.iam_keys.aws_access_key_id,
                "aws_secret_access_key": source_config.iam_keys.aws_secret_access_key,
                "session_token": source_config.iam_keys.session_token,
            }

        return result

    @classmethod
    def validate_schema(cls, config_data: dict) -> None:
        """Validate configuration data against JSON schema."""
        schema_path = Path(__file__).parent / "config-schema.json"

        if not schema_path.exists():
            LOG.warning("JSON schema file not found at %s", schema_path)
            return

        try:
            with open(schema_path, encoding="utf-8") as f:
                schema = json.load(f)

            # Validate the config data
            jsonschema.validate(config_data, schema)
            LOG.debug("Configuration validation against JSON schema passed")

        except jsonschema.ValidationError as error:
            error_path = (
                " -> ".join(str(p) for p in error.absolute_path)
                if error.absolute_path
                else "root"
            )

            # Use the existing sanitizer to handle exception messages
            full_error_message = str(error)
            sanitized_message = sanitize_exception_message(full_error_message)

            # Log the error - sanitization will be handled by logger
            LOG.error(
                "Configuration validation failed at %s: %s",
                error_path,
                sanitized_message,
            )

            raise ValueError(
                f"Configuration validation failed at {error_path}: {sanitized_message}"
            ) from error
        except jsonschema.SchemaError as error:
            LOG.error("JSON schema error: %s", error.message)
            raise ValueError(f"Invalid JSON schema: {error.message}") from error
        except Exception as error:
            LOG.error("Error validating configuration against schema: %s", str(error))
            raise ValueError(f"Schema validation error: {str(error)}") from error

    @classmethod
    def _validate_services(
        cls,
        services: dict[str, ServiceConfig],
        dynamic_services: DynamicServicesConfig | None = None,
    ) -> None:
        """Validate service configurations after inheritance."""
        # Check if we have either static services or enabled dynamic services
        has_static_services = bool(services)
        has_dynamic_services = dynamic_services and dynamic_services.enabled

        if not has_static_services and not has_dynamic_services:
            raise ValueError(
                "At least one service must be configured. "
                "Either define static services or enable dynamic_services."
            )

        for service_name, service_config in services.items():
            source_creds = service_config.source_credentials
            assumed_role = service_config.assumed_role

            if not source_creds.region:
                raise ValueError(f"AWS region is required for service '{service_name}'")
            if not assumed_role.RoleArn:
                raise ValueError(
                    f"AWS role ARN is required for service '{service_name}'"
                )

            # No additional validation needed:
            # - JSON schema validates required fields within auth sections
            # - _create_source_credentials_config validates presence of auth sections
            # Authentication method auto-detected from iam_keys or iam_profile presence

        LOG.info("Configuration validation passed for %d services", len(services))
