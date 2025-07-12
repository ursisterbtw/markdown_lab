#!/usr/bin/env python3
"""
Demonstration of the new Pydantic-based configuration system.

This example shows how to use the modern configuration management
with validation, environment variables, and profiles.
"""

import contextlib
import os
from pathlib import Path

from markdown_lab.core.config_v2 import (
    CacheBackend,
    LogLevel,
    MarkdownLabSettings,
    OutputFormat,
    configure_logging,
    get_config_profile,
    get_settings,
)


def demo_basic_usage():
    """Demonstrate basic configuration usage."""

    # Create default configuration
    MarkdownLabSettings()


def demo_custom_configuration():
    """Demonstrate custom configuration with validation."""

    with contextlib.suppress(Exception):
        # Create custom configuration
        MarkdownLabSettings(
            requests_per_second=5.0,
            timeout=60,
            max_retries=5,
            chunk_size=2000,
            chunk_overlap=300,
            log_level=LogLevel.DEBUG,
            default_output_format=OutputFormat.JSON,
            cache_backend=CacheBackend.BOTH,
            parallel_workers=8,
            debug=True,
        )


def demo_validation_errors():
    """Demonstrate configuration validation."""

    # Test various validation scenarios
    validation_tests = [
        ("Negative requests per second", {"requests_per_second": -1.0}),
        ("Zero timeout", {"timeout": 0}),
        ("Overlap >= chunk size", {"chunk_size": 1000, "chunk_overlap": 1000}),
        ("Requests per second too high", {"requests_per_second": 2000.0}),
        ("Invalid log level", {"log_level": "INVALID"}),
    ]

    for _test_name, kwargs in validation_tests:
        with contextlib.suppress(Exception):
            MarkdownLabSettings(**kwargs)


def demo_environment_variables():
    """Demonstrate environment variable support."""

    # Set some environment variables
    os.environ["MARKDOWN_LAB_TIMEOUT"] = "120"
    os.environ["MARKDOWN_LAB_REQUESTS_PER_SECOND"] = "10.0"
    os.environ["MARKDOWN_LAB_DEBUG"] = "true"
    os.environ["MARKDOWN_LAB_LOG_LEVEL"] = "WARNING"

    # Create configuration (should pick up env vars)
    MarkdownLabSettings()

    # Clean up environment variables
    for key in [
        "MARKDOWN_LAB_TIMEOUT",
        "MARKDOWN_LAB_REQUESTS_PER_SECOND",
        "MARKDOWN_LAB_DEBUG",
        "MARKDOWN_LAB_LOG_LEVEL",
    ]:
        os.environ.pop(key, None)


def demo_configuration_profiles():
    """Demonstrate configuration profiles."""

    # Development profile
    get_config_profile("development")

    # Production profile
    get_config_profile("production")


def demo_helper_methods():
    """Demonstrate configuration helper methods."""

    config = MarkdownLabSettings(
        requests_per_second=8.0,
        cache_enabled=True,
        telemetry_enabled=True,
        parallel_workers=6,
    )

    # Network configuration
    network_config = config.get_network_config()
    for _key, _value in network_config.items():
        pass

    # Cache configuration
    cache_config = config.get_cache_config()
    for _key, _value in cache_config.items():
        pass

    # Processing configuration
    processing_config = config.get_processing_config()
    for _key, _value in processing_config.items():
        pass


def demo_save_and_load():
    """Demonstrate saving and loading configuration."""

    # Create a custom configuration
    config = MarkdownLabSettings(
        requests_per_second=15.0,
        timeout=90,
        debug=True,
        log_level=LogLevel.DEBUG,
        cache_enabled=False,
        parallel_workers=12,
    )

    # Save to file
    config_file = Path("/tmp/markdown_lab_config.json")
    config.save_to_file(config_file)

    # Load from file
    MarkdownLabSettings.load_from_file(config_file)

    # Verify values match

    # Clean up
    config_file.unlink(missing_ok=True)


def demo_global_settings():
    """Demonstrate global settings management."""

    # Get global settings (singleton)
    settings1 = get_settings()
    get_settings()

    # Configure logging based on settings
    configure_logging(settings1)


def demo_advanced_features():
    """Demonstrate advanced configuration features."""

    config = MarkdownLabSettings(
        custom_headers={"X-API-Key": "secret", "User-Agent": "Custom/1.0"},
        excluded_domains=["spam.com", "blocked.net"],
        priority_domains=["important.org", "priority.edu"],
        rate_limit_burst_size=20,
        streaming_threshold_mb=5.0,
    )

    for _key, _value in config.custom_headers.items():
        pass


def main():
    """Run all configuration demonstrations."""

    demo_basic_usage()
    demo_custom_configuration()
    demo_validation_errors()
    demo_environment_variables()
    demo_configuration_profiles()
    demo_helper_methods()
    demo_save_and_load()
    demo_global_settings()
    demo_advanced_features()


if __name__ == "__main__":
    main()
