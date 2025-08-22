"""
Centralized configuration management for markdown_lab.

unified configuration system with validation and defaults
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
        creates config instance from dictionary

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
            config_path: output config file path, extension determines format

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
    returns current global config instance
    """
    return DEFAULT_CONFIG


def set_config(config: MarkdownLabConfig) -> None:
    """
    sets global config instance

    Replaces the current global configuration with the provided MarkdownLabConfig instance.
    """
    global DEFAULT_CONFIG
    DEFAULT_CONFIG = config


def load_config_from_env() -> MarkdownLabConfig:
    """
    creates config with environment variable overrides

    Returns:
        A MarkdownLabConfig object reflecting any relevant environment variable settings.
    """
    return MarkdownLabConfig()


# CLI argument configuration helpers
def create_config_from_cli_args(**kwargs) -> MarkdownLabConfig:
    """
    Create configuration from CLI arguments, filtering out None values.

    Args:
        **kwargs: CLI arguments that map to configuration parameters

    Returns:
        MarkdownLabConfig instance with CLI overrides applied
    """
    # Filter out None values to use defaults
    config_dict = {k: v for k, v in kwargs.items() if v is not None}

    # Start with default config and override with provided values
    base_config = get_config()
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


# Backward compatibility constants - to be deprecated
DEFAULT_REQUESTS_PER_SECOND = DEFAULT_CONFIG.requests_per_second
DEFAULT_TIMEOUT = DEFAULT_CONFIG.timeout
DEFAULT_MAX_RETRIES = DEFAULT_CONFIG.max_retries
DEFAULT_CHUNK_SIZE = DEFAULT_CONFIG.chunk_size
DEFAULT_CHUNK_OVERLAP = DEFAULT_CONFIG.chunk_overlap
