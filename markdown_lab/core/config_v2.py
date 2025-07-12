"""
Modern Pydantic-based configuration management for markdown_lab.

This module provides type-safe configuration with validation, environment
variable support, and comprehensive settings management. Replaces the
traditional config.py with a more robust, validated approach.
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator, model_validator
from pydantic.types import PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Available log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OutputFormat(str, Enum):
    """Available output formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"


class CacheBackend(str, Enum):
    """Available cache backends."""

    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"
    BOTH = "both"


class MarkdownLabSettings(BaseSettings):
    """
    Configuration settings with validation and environment support.

    All settings can be overridden via environment variables with the
    MARKDOWN_LAB_ prefix (e.g., MARKDOWN_LAB_TIMEOUT=60).
    """

    # === Network Settings ===
    requests_per_second: PositiveFloat = Field(
        default=2.0,
        description="Maximum requests per second for rate limiting",
        ge=0.1,
        le=1000.0,
    )

    timeout: PositiveInt = Field(
        default=30, description="HTTP request timeout in seconds", ge=1, le=300
    )

    max_retries: int = Field(
        default=3, description="Maximum number of request retries", ge=0, le=10
    )

    max_concurrent_requests: PositiveInt = Field(
        default=10, description="Maximum concurrent HTTP requests", ge=1, le=100
    )

    http2_enabled: bool = Field(default=True, description="Enable HTTP/2 support")

    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; MarkdownLab/1.0)",
        description="User agent string for HTTP requests",
    )

    # === Processing Settings ===
    chunk_size: PositiveInt = Field(
        default=1500,
        description="Default chunk size for text processing",
        ge=100,
        le=10000,
    )

    chunk_overlap: int = Field(
        default=200, description="Overlap between chunks in characters", ge=0, le=2000
    )

    parallel_workers: PositiveInt = Field(
        default=4, description="Number of parallel workers for processing", ge=1, le=32
    )

    max_document_size_mb: PositiveFloat = Field(
        default=50.0,
        description="Maximum document size to process (MB)",
        ge=0.1,
        le=500.0,
    )

    streaming_threshold_mb: PositiveFloat = Field(
        default=10.0,
        description="Use streaming parser for documents larger than this (MB)",
        ge=1.0,
        le=100.0,
    )

    # === Cache Settings ===
    cache_enabled: bool = Field(default=True, description="Enable caching system")

    cache_backend: CacheBackend = Field(
        default=CacheBackend.BOTH, description="Cache backend to use"
    )

    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "markdown_lab",
        description="Directory for disk cache",
    )

    cache_max_memory_items: PositiveInt = Field(
        default=1000, description="Maximum items in memory cache", ge=10, le=10000
    )

    cache_max_disk_mb: PositiveFloat = Field(
        default=500.0, description="Maximum disk cache size in MB", ge=10.0, le=10000.0
    )

    cache_ttl_hours: PositiveFloat = Field(
        default=24.0,
        description="Default cache TTL in hours",
        ge=0.1,
        le=720.0,  # 30 days
    )

    # === Rate Limiting Settings ===
    rate_limit_burst_size: PositiveInt = Field(
        default=10,
        description="Token bucket burst size for rate limiting",
        ge=1,
        le=1000,
    )

    rate_limit_per_domain: bool = Field(
        default=True, description="Apply rate limiting per domain"
    )

    # === Output Settings ===
    default_output_format: OutputFormat = Field(
        default=OutputFormat.MARKDOWN, description="Default output format"
    )

    output_dir: Optional[Path] = Field(
        default=None, description="Default output directory"
    )

    preserve_structure: bool = Field(
        default=True, description="Preserve document structure in output"
    )

    include_metadata: bool = Field(
        default=True, description="Include metadata in output"
    )

    # === Logging Settings ===
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")

    log_file: Optional[Path] = Field(
        default=None, description="Log file path (None for console only)"
    )

    structured_logging: bool = Field(
        default=False, description="Enable structured JSON logging"
    )

    # === Monitoring & Telemetry ===
    telemetry_enabled: bool = Field(
        default=False, description="Enable telemetry collection"
    )

    telemetry_endpoint: Optional[str] = Field(
        default=None, description="OpenTelemetry endpoint URL"
    )

    metrics_enabled: bool = Field(
        default=False, description="Enable metrics collection"
    )

    metrics_port: Optional[PositiveInt] = Field(
        default=None, description="Port for metrics server", ge=1024, le=65535
    )

    # === Development Settings ===
    debug: bool = Field(default=False, description="Enable debug mode")

    development_mode: bool = Field(
        default=False, description="Enable development mode features"
    )

    profile_performance: bool = Field(
        default=False, description="Enable performance profiling"
    )

    # === Security Settings ===
    allow_insecure_ssl: bool = Field(
        default=False, description="Allow insecure SSL connections"
    )

    respect_robots_txt: bool = Field(
        default=True, description="Respect robots.txt files"
    )

    max_redirects: PositiveInt = Field(
        default=10,
        description="Maximum number of HTTP redirects to follow",
        ge=0,
        le=50,
    )

    # === Advanced Settings ===
    custom_headers: Dict[str, str] = Field(
        default_factory=dict, description="Custom HTTP headers to include"
    )

    excluded_domains: List[str] = Field(
        default_factory=list, description="Domains to exclude from processing"
    )

    priority_domains: List[str] = Field(
        default_factory=list, description="Domains to prioritize for processing"
    )

    # === Configuration Validation ===

    @field_validator("cache_dir")
    @classmethod
    def ensure_cache_dir_exists(cls, v: Path) -> Path:
        """Ensure cache directory exists."""
        try:
            v.mkdir(parents=True, exist_ok=True)
            return v
        except OSError as e:
            logger.warning(f"Cannot create cache directory {v}: {e}")
            # Fallback to temp directory
            import tempfile

            fallback = Path(tempfile.gettempdir()) / "markdown_lab_cache"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    @field_validator("output_dir")
    @classmethod
    def ensure_output_dir_exists(cls, v: Optional[Path]) -> Optional[Path]:
        """Ensure output directory exists if specified."""
        if v is not None:
            try:
                v.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning(f"Cannot create output directory {v}: {e}")
                return None
        return v

    @field_validator("log_file")
    @classmethod
    def ensure_log_dir_exists(cls, v: Optional[Path]) -> Optional[Path]:
        """Ensure log file directory exists."""
        if v is not None:
            try:
                v.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning(f"Cannot create log directory {v.parent}: {e}")
                return None
        return v

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "MarkdownLabSettings":
        """Validate chunk size and overlap relationship."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunk_size})"
            )

        return self

    @model_validator(mode="after")
    def validate_cache_settings(self) -> "MarkdownLabSettings":
        """Validate cache configuration."""
        return self

    @model_validator(mode="after")
    def validate_telemetry_settings(self) -> "MarkdownLabSettings":
        """Validate telemetry configuration."""
        if self.telemetry_enabled and not self.telemetry_endpoint:
            logger.warning(
                "Telemetry enabled but no endpoint specified. "
                "Telemetry will be disabled."
            )
            self.telemetry_enabled = False

        return self

    @model_validator(mode="after")
    def validate_parallel_settings(self) -> "MarkdownLabSettings":
        """Validate parallel processing settings."""
        # Ensure we don't overwhelm the system

        cpu_count = os.cpu_count() or 4

        if self.parallel_workers > cpu_count * 2:
            logger.warning(
                f"parallel_workers ({self.parallel_workers}) is high for this system "
                f"({cpu_count} CPUs). Consider reducing it."
            )

        return self

    model_config = {
        "env_prefix": "MARKDOWN_LAB_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "populate_by_name": True,
        "use_enum_values": True,
        "validate_assignment": True,
        "extra": "forbid",  # Don't allow extra fields
    }

    def to_legacy_config(self) -> "MarkdownLabConfig":
        """Convert to legacy config format for backward compatibility."""
        from .config import MarkdownLabConfig

        return MarkdownLabConfig(
            requests_per_second=self.requests_per_second,
            timeout=self.timeout,
            max_retries=self.max_retries,
            max_concurrent_requests=self.max_concurrent_requests,
            cache_enabled=self.cache_enabled,
            debug=self.debug,
            user_agent=self.user_agent,
        )

    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache-specific configuration."""
        return {
            "enabled": self.cache_enabled,
            "backend": (
                self.cache_backend
                if isinstance(self.cache_backend, str)
                else self.cache_backend.value
            ),
            "cache_dir": str(self.cache_dir),
            "max_memory_items": self.cache_max_memory_items,
            "max_disk_mb": self.cache_max_disk_mb,
            "ttl_hours": self.cache_ttl_hours,
        }

    def get_network_config(self) -> Dict[str, Any]:
        """Get network-specific configuration."""
        return {
            "requests_per_second": self.requests_per_second,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "max_concurrent_requests": self.max_concurrent_requests,
            "http2_enabled": self.http2_enabled,
            "user_agent": self.user_agent,
            "max_redirects": self.max_redirects,
            "allow_insecure_ssl": self.allow_insecure_ssl,
            "custom_headers": self.custom_headers,
        }

    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing-specific configuration."""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "parallel_workers": self.parallel_workers,
            "max_document_size_mb": self.max_document_size_mb,
            "streaming_threshold_mb": self.streaming_threshold_mb,
            "default_output_format": (
                self.default_output_format
                if isinstance(self.default_output_format, str)
                else self.default_output_format.value
            ),
            "preserve_structure": self.preserve_structure,
            "include_metadata": self.include_metadata,
        }

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring and telemetry configuration."""
        return {
            "telemetry_enabled": self.telemetry_enabled,
            "telemetry_endpoint": self.telemetry_endpoint,
            "metrics_enabled": self.metrics_enabled,
            "metrics_port": self.metrics_port,
            "log_level": (
                self.log_level
                if isinstance(self.log_level, str)
                else self.log_level.value
            ),
            "log_file": str(self.log_file) if self.log_file else None,
            "structured_logging": self.structured_logging,
        }

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to a file."""
        file_path = Path(file_path)

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Export configuration
        config_dict = self.model_dump()

        # Convert Path objects to strings for JSON serialization
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)

        import json

        with open(file_path, "w") as f:
            json.dump(config_dict, f, indent=2, default=str)

        logger.info(f"Configuration saved to {file_path}")

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "MarkdownLabSettings":
        """Load configuration from a file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        import json

        with open(file_path, "r") as f:
            config_dict = json.load(f)

        logger.info(f"Configuration loaded from {file_path}")
        return cls(**config_dict)


# Global settings instance
_settings: Optional[MarkdownLabSettings] = None


def get_settings() -> MarkdownLabSettings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = MarkdownLabSettings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance."""
    global _settings
    _settings = None


def configure_logging(settings: Optional[MarkdownLabSettings] = None) -> None:
    """Configure logging based on settings."""
    if settings is None:
        settings = get_settings()

    log_level_str = (
        settings.log_level
        if isinstance(settings.log_level, str)
        else settings.log_level.value
    )
    log_config = {
        "level": getattr(logging, log_level_str),
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }

    if settings.log_file:
        log_config["filename"] = str(settings.log_file)
        log_config["filemode"] = "a"

    logging.basicConfig(**log_config)

    if settings.debug:
        logging.getLogger("markdown_lab").setLevel(logging.DEBUG)


def create_development_config() -> MarkdownLabSettings:
    """Create a development configuration with appropriate defaults."""
    return MarkdownLabSettings(
        debug=True,
        development_mode=True,
        log_level=LogLevel.DEBUG,
        profile_performance=True,
        requests_per_second=10.0,
        parallel_workers=2,
        cache_enabled=True,
        telemetry_enabled=False,
        structured_logging=True,
    )


def create_production_config() -> MarkdownLabSettings:
    """Create a production configuration with appropriate defaults."""
    return MarkdownLabSettings(
        debug=False,
        development_mode=False,
        log_level=LogLevel.INFO,
        profile_performance=False,
        requests_per_second=5.0,
        parallel_workers=8,
        cache_enabled=True,
        telemetry_enabled=True,
        structured_logging=True,
        respect_robots_txt=True,
        allow_insecure_ssl=False,
    )


# Configuration profiles
CONFIG_PROFILES = {
    "development": create_development_config,
    "production": create_production_config,
    "default": lambda: MarkdownLabSettings(),
}


def get_config_profile(profile_name: str) -> MarkdownLabSettings:
    """Get a predefined configuration profile."""
    if profile_name not in CONFIG_PROFILES:
        available = ", ".join(CONFIG_PROFILES.keys())
        raise ValueError(f"Unknown profile '{profile_name}'. Available: {available}")

    return CONFIG_PROFILES[profile_name]()


if __name__ == "__main__":
    # Demo configuration usage

    # Create default settings
    settings = MarkdownLabSettings()
