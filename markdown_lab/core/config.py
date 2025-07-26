"""
Centralized configuration management for markdown_lab.

This module provides a unified configuration system that eliminates scattered
configuration parameters across the codebase and provides validation and defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class MarkdownLabConfig:
    """Centralized configuration for all markdown_lab operations.

    This configuration class consolidates all settings that were previously
    scattered across multiple modules and classes.
    """

    # Network configuration
    requests_per_second: float = 1.0
    timeout: int = 30
    max_retries: int = 3
    user_agent: str = (
        "MarkdownLab/1.0 (Python; +https://github.com/ursisterbtw/markdown_lab)"
    )

    # Processing configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_file_size: int = 10_000_000  # 10MB
    max_concurrent_requests: int = 10

    # Cache configuration
    cache_enabled: bool = True
    cache_dir: str = ".request_cache"
    cache_max_memory: int = 100_000_000  # 100MB
    cache_max_disk: int = 1_000_000_000  # 1GB
    cache_ttl: int = 3600  # 1 hour

    # Performance configuration
    parallel_workers: int = 4
    memory_limit: int = 500_000_000  # 500MB
    enable_performance_monitoring: bool = True

    # Output configuration
    default_output_format: str = "markdown"
    preserve_whitespace: bool = False
    include_metadata: bool = True

    # Advanced configuration
    js_rendering_enabled: bool = False
    rust_backend_enabled: bool = True
    fallback_to_python: bool = True

    def __post_init__(self):
        """
        Validates configuration values and applies environment variable overrides after initialization.
        """
        self._validate_config()
        self._apply_environment_overrides()

    def _validate_config(self) -> None:
        """
        Validates configuration parameters and raises ValueError if any constraints are violated.

        Checks that numeric parameters are within valid ranges and that the default output format is supported.
        """
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")

        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        if self.parallel_workers <= 0:
            raise ValueError("parallel_workers must be positive")

        if self.cache_max_memory <= 0:
            raise ValueError("cache_max_memory must be positive")

        if self.cache_max_disk <= 0:
            raise ValueError("cache_max_disk must be positive")

        if self.default_output_format not in ["markdown", "json", "xml"]:
            raise ValueError(
                "default_output_format must be 'markdown', 'json', or 'xml'"
            )

    def _apply_environment_overrides(self) -> None:
        """
        Overrides configuration attributes with values from corresponding environment variables.

        Reads predefined environment variables, converts their values to the appropriate types, and updates the configuration instance. Raises ValueError if an environment variable cannot be converted to the expected type.
        """
        env_mappings = {
            "MARKDOWN_LAB_REQUESTS_PER_SECOND": ("requests_per_second", float),
            "MARKDOWN_LAB_TIMEOUT": ("timeout", int),
            "MARKDOWN_LAB_MAX_RETRIES": ("max_retries", int),
            "MARKDOWN_LAB_CHUNK_SIZE": ("chunk_size", int),
            "MARKDOWN_LAB_CHUNK_OVERLAP": ("chunk_overlap", int),
            "MARKDOWN_LAB_CACHE_ENABLED": (
                "cache_enabled",
                lambda x: x.lower() == "true",
            ),
            "MARKDOWN_LAB_CACHE_DIR": ("cache_dir", str),
            "MARKDOWN_LAB_PARALLEL_WORKERS": ("parallel_workers", int),
            "MARKDOWN_LAB_RUST_BACKEND": (
                "rust_backend_enabled",
                lambda x: x.lower() == "true",
            ),
        }

        for env_var, (attr_name, type_converter) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    setattr(self, attr_name, type_converter(env_value))
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Invalid environment variable {env_var}={env_value}: {e}"
                    ) from e

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "MarkdownLabConfig":
        """
        Creates a MarkdownLabConfig instance from a dictionary of configuration values.

        Args:
            config_dict: A dictionary containing configuration parameters keyed by attribute name.

        Returns:
            A MarkdownLabConfig instance initialized with the provided values.
        """
        return cls(**config_dict)

    @classmethod
    def from_file(cls, config_path: str) -> "MarkdownLabConfig":
        """
        Loads a MarkdownLabConfig instance from a JSON or YAML configuration file.

        Args:
            config_path: Path to the configuration file.

        Returns:
            A MarkdownLabConfig instance populated with values from the file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ImportError: If loading a YAML file without PyYAML installed.
            ValueError: If the file format is not supported.
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        if config_path.suffix.lower() == ".json":
            import json

            with open(config_path, "r") as f:
                config_dict = json.load(f)
        elif config_path.suffix.lower() in {".yml", ".yaml"}:
            try:
                import yaml

                with open(config_path, "r") as f:
                    config_dict = yaml.safe_load(f)
            except ImportError as e:
                raise ImportError(
                    "PyYAML is required to load YAML configuration files"
                ) from e
        else:
            raise ValueError(
                f"Unsupported configuration file format: {config_path.suffix}"
            )

        return cls.from_dict(config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the configuration instance to a dictionary.

        Returns:
            A dictionary representation of the configuration parameters.
        """
        from dataclasses import asdict

        return asdict(self)

    def save_to_file(self, config_path: str) -> None:
        """
        Saves the configuration to a JSON or YAML file.

        Args:
            config_path: Path to the output configuration file. The file extension determines the format (.json, .yml, or .yaml).

        Raises:
            ImportError: If saving as YAML and PyYAML is not installed.
            ValueError: If the file extension is not supported.
        """
        config_path = Path(config_path)
        config_dict = self.to_dict()

        if config_path.suffix.lower() == ".json":
            import json

            with open(config_path, "w") as f:
                json.dump(config_dict, f, indent=2)
        elif config_path.suffix.lower() in {".yml", ".yaml"}:
            try:
                import yaml

                with open(config_path, "w") as f:
                    yaml.dump(config_dict, f, default_flow_style=False)
            except ImportError as e:
                raise ImportError(
                    "PyYAML is required to save YAML configuration files"
                ) from e
        else:
            raise ValueError(
                f"Unsupported configuration file format: {config_path.suffix}"
            )

    def update(self, **kwargs) -> "MarkdownLabConfig":
        """
        Returns a new configuration instance with updated values for specified parameters.

        Args:
            **kwargs: Configuration fields to update.

        Returns:
            A new MarkdownLabConfig instance with the specified fields updated.
        """
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return self.from_dict(config_dict)


# Global default configuration instance
DEFAULT_CONFIG = MarkdownLabConfig()


def get_config() -> MarkdownLabConfig:
    """
    Returns the current global MarkdownLab configuration instance.
    """
    return DEFAULT_CONFIG


def set_config(config: MarkdownLabConfig) -> None:
    """
    Sets the global configuration instance for the markdown_lab project.

    Replaces the current global configuration with the provided MarkdownLabConfig instance.
    """
    global DEFAULT_CONFIG
    DEFAULT_CONFIG = config


def load_config_from_env() -> MarkdownLabConfig:
    """
    Creates a new MarkdownLabConfig instance with environment variable overrides applied.

    Returns:
        A MarkdownLabConfig object reflecting any relevant environment variable settings.
    """
    return MarkdownLabConfig()


# CLI argument configuration helpers
def create_config_from_cli_args(profile: str = None, **kwargs) -> MarkdownLabConfig:
    """
    Create configuration from CLI arguments, with optional profile support.

    Args:
        profile: Optional profile name to use as base configuration
        **kwargs: CLI arguments that map to configuration parameters

    Returns:
        MarkdownLabConfig instance with profile and CLI overrides applied
    """
    # Start with profile or default config
    base_config = get_profile(profile) if profile else get_config()
    # Filter out None values to use profile/defaults
    config_dict = {k: v for k, v in kwargs.items() if v is not None}

    # Override with provided CLI values
    return base_config.update(**config_dict)


def get_cli_defaults() -> dict:
    """
    Get default values for CLI arguments from configuration.

    Returns:
        Dictionary of default values for common CLI parameters
    """
    config = get_config()
    return {
        "requests_per_second": config.requests_per_second,
        "timeout": config.timeout,
        "max_retries": config.max_retries,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
        "cache_enabled": config.cache_enabled,
        "cache_ttl": config.cache_ttl,
        "parallel_workers": config.parallel_workers,
    }


# Configuration Profiles for simplified CLI usage
CONFIGURATION_PROFILES = {
    "dev": {
        "requests_per_second": 0.5,  # Slower for development to avoid rate limits
        "timeout": 60,  # Longer timeout for debugging
        "max_retries": 1,  # Fewer retries for faster feedback
        "cache_enabled": True,
        "cache_ttl": 300,  # 5 minutes cache for development
        "parallel_workers": 2,  # Fewer workers to reduce resource usage
        "chunk_size": 500,  # Smaller chunks for testing
        "chunk_overlap": 50,
        "enable_performance_monitoring": True,
        "rust_backend_enabled": True,
        "fallback_to_python": True,
    },
    "prod": {
        "requests_per_second": 2.0,  # Faster for production
        "timeout": 30,  # Standard timeout
        "max_retries": 3,  # Standard retries
        "cache_enabled": True,
        "cache_ttl": 3600,  # 1 hour cache
        "parallel_workers": 8,  # More workers for production
        "chunk_size": 1500,  # Larger chunks for efficiency
        "chunk_overlap": 200,
        "enable_performance_monitoring": False,  # Reduce overhead
        "rust_backend_enabled": True,
        "fallback_to_python": False,  # Fail fast in production
    },
    "fast": {
        "requests_per_second": 5.0,  # Maximum speed
        "timeout": 15,  # Short timeout
        "max_retries": 1,  # Minimal retries
        "cache_enabled": True,
        "cache_ttl": 7200,  # 2 hours cache
        "parallel_workers": 16,  # Maximum workers
        "chunk_size": 2000,  # Large chunks
        "chunk_overlap": 100,  # Minimal overlap
        "enable_performance_monitoring": False,
        "rust_backend_enabled": True,
        "fallback_to_python": False,
    },
    "conservative": {
        "requests_per_second": 0.2,  # Very slow to be respectful
        "timeout": 120,  # Long timeout for slow sites
        "max_retries": 5,  # Many retries for reliability
        "cache_enabled": True,
        "cache_ttl": 86400,  # 24 hours cache
        "parallel_workers": 1,  # Sequential processing
        "chunk_size": 800,  # Medium chunks
        "chunk_overlap": 300,  # High overlap
        "enable_performance_monitoring": True,
        "rust_backend_enabled": True,
        "fallback_to_python": True,
    },
}


def get_profile(profile_name: str) -> MarkdownLabConfig:
    """
    Get a configuration profile by name.

    Args:
        profile_name: Name of the profile ('dev', 'prod', 'fast', 'conservative')

    Returns:
        MarkdownLabConfig instance configured for the specified profile

    Raises:
        ValueError: If the profile name is not recognized
    """
    if profile_name not in CONFIGURATION_PROFILES:
        available = ", ".join(CONFIGURATION_PROFILES.keys())
        raise ValueError(f"Unknown profile '{profile_name}'. Available: {available}")

    profile_config = CONFIGURATION_PROFILES[profile_name]
    return MarkdownLabConfig.from_dict(profile_config)


def list_profiles() -> list[str]:
    """
    List all available configuration profiles.

    Returns:
        List of profile names
    """
    return list(CONFIGURATION_PROFILES.keys())


def get_profile_description(profile_name: str) -> str:
    """
    Get a human-readable description of a configuration profile.

    Args:
        profile_name: Name of the profile

    Returns:
        Description string for the profile
    """
    descriptions = {
        "dev": "🔧 Development profile - slower, more debugging, shorter cache",
        "prod": "🚀 Production profile - balanced performance and reliability",
        "fast": "⚡ Fast profile - maximum speed, minimal safety margins",
        "conservative": "🛡️ Conservative profile - respectful, reliable, patient",
    }
    return descriptions.get(profile_name, f"Profile: {profile_name}")


# Backward compatibility constants - to be deprecated
DEFAULT_REQUESTS_PER_SECOND = DEFAULT_CONFIG.requests_per_second
DEFAULT_TIMEOUT = DEFAULT_CONFIG.timeout
DEFAULT_MAX_RETRIES = DEFAULT_CONFIG.max_retries
DEFAULT_CHUNK_SIZE = DEFAULT_CONFIG.chunk_size
DEFAULT_CHUNK_OVERLAP = DEFAULT_CONFIG.chunk_overlap
