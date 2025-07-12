"""
Tests for Pydantic-based configuration system.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from markdown_lab.core.config_v2 import (
    CONFIG_PROFILES,
    CacheBackend,
    LogLevel,
    MarkdownLabSettings,
    OutputFormat,
    configure_logging,
    create_development_config,
    create_production_config,
    get_config_profile,
    get_settings,
    reset_settings,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestMarkdownLabSettings:
    """Test Pydantic configuration settings."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = MarkdownLabSettings()

        assert settings.requests_per_second == 2.0
        assert settings.timeout == 30
        assert settings.max_retries == 3
        assert settings.cache_enabled is True
        assert settings.log_level == LogLevel.INFO
        assert settings.debug is False
        assert settings.parallel_workers == 4

    def test_validation_positive_numbers(self):
        """Test validation of positive number fields."""
        # Valid positive numbers
        settings = MarkdownLabSettings(
            requests_per_second=5.0, timeout=60, parallel_workers=8
        )
        assert settings.requests_per_second == 5.0
        assert settings.timeout == 60
        assert settings.parallel_workers == 8

        # Invalid negative/zero numbers should raise ValidationError
        with pytest.raises(ValidationError):
            MarkdownLabSettings(requests_per_second=-1.0)

        with pytest.raises(ValidationError):
            MarkdownLabSettings(timeout=0)

        with pytest.raises(ValidationError):
            MarkdownLabSettings(parallel_workers=0)

    def test_validation_ranges(self):
        """Test validation of number ranges."""
        # Valid values within range
        settings = MarkdownLabSettings(
            requests_per_second=10.0,  # 0.1 <= x <= 1000.0
            timeout=120,  # 1 <= x <= 300
            max_retries=5,  # 0 <= x <= 10
        )
        assert settings.requests_per_second == 10.0
        assert settings.timeout == 120
        assert settings.max_retries == 5

        # Values outside valid ranges
        with pytest.raises(ValidationError):
            MarkdownLabSettings(requests_per_second=2000.0)  # > 1000.0

        with pytest.raises(ValidationError):
            MarkdownLabSettings(timeout=500)  # > 300

        with pytest.raises(ValidationError):
            MarkdownLabSettings(max_retries=15)  # > 10

    def test_chunk_validation(self):
        """Test chunk size and overlap validation."""
        # Valid chunk settings
        settings = MarkdownLabSettings(chunk_size=2000, chunk_overlap=400)
        assert settings.chunk_size == 2000
        assert settings.chunk_overlap == 400

        # Invalid: overlap >= chunk_size
        with pytest.raises(
            ValidationError, match="chunk_overlap.*must be less than.*chunk_size"
        ):
            MarkdownLabSettings(
                chunk_size=1000, chunk_overlap=1000  # Equal to chunk_size
            )

        with pytest.raises(
            ValidationError, match="chunk_overlap.*must be less than.*chunk_size"
        ):
            MarkdownLabSettings(
                chunk_size=1000, chunk_overlap=1500  # Greater than chunk_size
            )

    def test_cache_dir_creation(self, temp_dir):
        """Test cache directory creation."""
        cache_path = temp_dir / "test_cache"

        # Directory should be created automatically
        settings = MarkdownLabSettings(cache_dir=cache_path)
        assert settings.cache_dir == cache_path
        assert cache_path.exists()
        assert cache_path.is_dir()

    def test_enum_validation(self):
        """Test enum field validation."""
        # Valid enum values
        settings = MarkdownLabSettings(
            log_level=LogLevel.DEBUG,
            default_output_format=OutputFormat.JSON,
            cache_backend=CacheBackend.MEMORY,
        )
        assert settings.log_level == LogLevel.DEBUG
        assert settings.default_output_format == OutputFormat.JSON
        assert settings.cache_backend == CacheBackend.MEMORY

        # Invalid enum values should raise ValidationError
        with pytest.raises(ValidationError):
            MarkdownLabSettings(log_level="INVALID_LEVEL")

        with pytest.raises(ValidationError):
            MarkdownLabSettings(default_output_format="invalid_format")

    def test_path_validation(self, temp_dir):
        """Test Path field validation and directory creation."""
        output_path = temp_dir / "output"
        log_path = temp_dir / "logs" / "app.log"

        settings = MarkdownLabSettings(output_dir=output_path, log_file=log_path)

        # Directories should be created
        assert output_path.exists()
        assert log_path.parent.exists()

        # Path values should be preserved
        assert settings.output_dir == output_path
        assert settings.log_file == log_path

    @patch.dict(
        os.environ,
        {
            "MARKDOWN_LAB_TIMEOUT": "120",
            "MARKDOWN_LAB_REQUESTS_PER_SECOND": "5.5",
            "MARKDOWN_LAB_DEBUG": "true",
            "MARKDOWN_LAB_LOG_LEVEL": "DEBUG",
        },
    )
    def test_environment_variable_override(self):
        """Test configuration override via environment variables."""
        settings = MarkdownLabSettings()

        assert settings.timeout == 120
        assert settings.requests_per_second == 5.5
        assert settings.debug is True
        assert settings.log_level == LogLevel.DEBUG

    def test_telemetry_validation(self):
        """Test telemetry configuration validation."""
        # Telemetry enabled without endpoint should disable telemetry
        with patch("markdown_lab.core.config_v2.logger") as mock_logger:
            settings = MarkdownLabSettings(
                telemetry_enabled=True, telemetry_endpoint=None
            )

            assert settings.telemetry_enabled is False
            mock_logger.warning.assert_called_once()

        # Telemetry with endpoint should remain enabled
        settings = MarkdownLabSettings(
            telemetry_enabled=True, telemetry_endpoint="http://localhost:4317"
        )
        assert settings.telemetry_enabled is True
        assert settings.telemetry_endpoint == "http://localhost:4317"

    def test_parallel_workers_validation(self):
        """Test parallel workers validation warning."""
        with patch("os.cpu_count", return_value=2):
            with patch("markdown_lab.core.config_v2.logger") as mock_logger:
                # High worker count should trigger warning
                settings = MarkdownLabSettings(parallel_workers=10)  # > 2 * 2 = 4

                assert settings.parallel_workers == 10  # Value preserved
                mock_logger.warning.assert_called_once()

    def test_config_methods(self):
        """Test configuration helper methods."""
        settings = MarkdownLabSettings(
            requests_per_second=5.0,
            cache_enabled=True,
            chunk_size=2000,
            telemetry_enabled=True,
        )

        # Test get_cache_config
        cache_config = settings.get_cache_config()
        assert cache_config["enabled"] is True
        assert cache_config["max_memory_items"] == settings.cache_max_memory_items

        # Test get_network_config
        network_config = settings.get_network_config()
        assert network_config["requests_per_second"] == 5.0
        assert network_config["timeout"] == settings.timeout

        # Test get_processing_config
        processing_config = settings.get_processing_config()
        assert processing_config["chunk_size"] == 2000
        assert processing_config["parallel_workers"] == settings.parallel_workers

        # Test get_monitoring_config
        monitoring_config = settings.get_monitoring_config()
        assert monitoring_config["telemetry_enabled"] is True
        assert monitoring_config["log_level"] == settings.log_level.value

    def test_legacy_config_conversion(self):
        """Test conversion to legacy config format."""
        settings = MarkdownLabSettings(requests_per_second=3.0, timeout=45, debug=True)

        legacy_config = settings.to_legacy_config()

        assert legacy_config.requests_per_second == 3.0
        assert legacy_config.timeout == 45
        assert legacy_config.debug is True

    def test_save_and_load_config(self, temp_dir):
        """Test saving and loading configuration to/from file."""
        config_file = temp_dir / "config.json"

        # Create settings with custom values
        original_settings = MarkdownLabSettings(
            requests_per_second=7.5,
            timeout=90,
            debug=True,
            cache_enabled=False,
            log_level=LogLevel.WARNING,
        )

        # Save to file
        original_settings.save_to_file(config_file)
        assert config_file.exists()

        # Load from file
        loaded_settings = MarkdownLabSettings.load_from_file(config_file)

        # Verify loaded settings match original
        assert loaded_settings.requests_per_second == 7.5
        assert loaded_settings.timeout == 90
        assert loaded_settings.debug is True
        assert loaded_settings.cache_enabled is False
        assert loaded_settings.log_level == LogLevel.WARNING

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading from nonexistent file raises appropriate error."""
        nonexistent_file = temp_dir / "missing.json"

        with pytest.raises(FileNotFoundError):
            MarkdownLabSettings.load_from_file(nonexistent_file)


class TestConfigurationProfiles:
    """Test configuration profiles and global settings."""

    def test_development_config(self):
        """Test development configuration profile."""
        dev_config = create_development_config()

        assert dev_config.debug is True
        assert dev_config.development_mode is True
        assert dev_config.log_level == LogLevel.DEBUG
        assert dev_config.profile_performance is True
        assert dev_config.structured_logging is True

    def test_production_config(self):
        """Test production configuration profile."""
        prod_config = create_production_config()

        assert prod_config.debug is False
        assert prod_config.development_mode is False
        assert prod_config.log_level == LogLevel.INFO
        assert prod_config.profile_performance is False
        assert prod_config.structured_logging is True
        assert prod_config.respect_robots_txt is True
        assert prod_config.allow_insecure_ssl is False

    def test_get_config_profile(self):
        """Test getting configuration profiles by name."""
        # Valid profiles
        dev_config = get_config_profile("development")
        assert dev_config.debug is True

        prod_config = get_config_profile("production")
        assert prod_config.debug is False

        default_config = get_config_profile("default")
        assert isinstance(default_config, MarkdownLabSettings)

        # Invalid profile
        with pytest.raises(ValueError, match="Unknown profile"):
            get_config_profile("invalid_profile")

    def test_available_profiles(self):
        """Test that all defined profiles are available."""
        expected_profiles = {"development", "production", "default"}
        actual_profiles = set(CONFIG_PROFILES.keys())

        assert actual_profiles == expected_profiles

        # Verify all profiles can be created
        for profile_name in CONFIG_PROFILES:
            config = get_config_profile(profile_name)
            assert isinstance(config, MarkdownLabSettings)


class TestGlobalSettings:
    """Test global settings management."""

    def teardown_method(self):
        """Reset global settings after each test."""
        reset_settings()

    def test_global_settings_singleton(self):
        """Test global settings singleton behavior."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reset_settings(self):
        """Test resetting global settings."""
        settings1 = get_settings()
        reset_settings()
        settings2 = get_settings()

        assert settings1 is not settings2

    def test_configure_logging(self, temp_dir):
        """Test logging configuration."""
        log_file = temp_dir / "test.log"

        settings = MarkdownLabSettings(
            log_level=LogLevel.WARNING, log_file=log_file, debug=True
        )

        # Should not raise an error
        configure_logging(settings)

        # Test with default settings
        configure_logging()


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""

    def test_invalid_json_in_config_file(self, temp_dir):
        """Test handling of invalid JSON in config file."""
        config_file = temp_dir / "invalid.json"

        # Write invalid JSON
        with open(config_file, "w") as f:
            f.write("{ invalid json content")

        with pytest.raises(json.JSONDecodeError):
            MarkdownLabSettings.load_from_file(config_file)

    def test_permission_error_cache_dir(self):
        """Test handling of permission errors when creating cache dir."""
        # This test would require mocking filesystem operations
        # to simulate permission errors in a controlled way
        pass

    def test_extreme_values(self):
        """Test configuration with extreme but valid values."""
        settings = MarkdownLabSettings(
            requests_per_second=1000.0,  # Maximum allowed
            timeout=300,  # Maximum allowed
            max_retries=10,  # Maximum allowed
            parallel_workers=32,  # Maximum allowed
            chunk_size=10000,  # Maximum allowed
        )

        assert settings.requests_per_second == 1000.0
        assert settings.timeout == 300
        assert settings.max_retries == 10
        assert settings.parallel_workers == 32
        assert settings.chunk_size == 10000

    def test_custom_headers_and_domains(self):
        """Test custom headers and domain lists."""
        settings = MarkdownLabSettings(
            custom_headers={"X-Custom": "value", "Authorization": "Bearer token"},
            excluded_domains=["blocked.com", "spam.net"],
            priority_domains=["important.org", "priority.edu"],
        )

        assert settings.custom_headers["X-Custom"] == "value"
        assert "blocked.com" in settings.excluded_domains
        assert "important.org" in settings.priority_domains


@pytest.mark.asyncio
async def test_async_compatibility():
    """Test that configuration works well with async code."""
    settings = MarkdownLabSettings(requests_per_second=5.0, cache_enabled=True)

    # Configuration should be usable in async context
    assert settings.requests_per_second == 5.0

    # Helper methods should work
    cache_config = settings.get_cache_config()
    assert cache_config["enabled"] is True


def test_pydantic_features():
    """Test specific Pydantic features work correctly."""
    # Test field aliases and validation
    settings = MarkdownLabSettings()

    # Test that enum values are properly handled
    assert isinstance(settings.log_level, LogLevel)
    assert isinstance(settings.default_output_format, OutputFormat)
    assert isinstance(settings.cache_backend, CacheBackend)

    # Test model_dump functionality
    config_dict = settings.model_dump()
    assert isinstance(config_dict, dict)
    assert "requests_per_second" in config_dict

    # Test field validation on assignment
    settings.requests_per_second = 10.0
    assert settings.requests_per_second == 10.0

    with pytest.raises(ValidationError):
        settings.requests_per_second = -5.0
