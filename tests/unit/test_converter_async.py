"""
Unit tests for Converter async resource management.
"""
import pytest
from markdown_lab.core.converter import Converter
from markdown_lab.core.config import MarkdownLabConfig


class TestConverterAsyncResourceManagement:
    """Test async resource management for Converter class."""

    @pytest.fixture
    def test_config(self):
        """Test configuration for converter."""
        return MarkdownLabConfig(
            timeout=10,
            max_retries=2,
            cache_enabled=True,
        )

    @pytest.fixture
    def converter(self, test_config):
        """Fixture for Converter instance."""
        return Converter(test_config)

    def test_converter_close_method(self, converter):
        """Test Converter close method."""
        converter.close()
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_converter_async_close(self, converter):
        """Test Converter async close method."""
        await converter.aclose()
        # Should not raise any exceptions

    def test_converter_context_manager(self, test_config):
        """Test Converter as context manager."""
        with Converter(test_config) as converter:
            assert converter is not None
            assert hasattr(converter, "client")
        # Should complete without errors

    @pytest.mark.asyncio
    async def test_converter_async_context_manager(self, test_config):
        """Test Converter as async context manager."""
        async with Converter(test_config) as converter:
            assert converter is not None
            assert hasattr(converter, "client")
            assert hasattr(converter, "aclose")
        # Should complete without errors

    def test_converter_close_with_client(self, converter):
        """Test converter close properly handles client cleanup."""
        # Ensure client exists
        assert converter.client is not None
        
        # Close should not raise exceptions
        converter.close()

    @pytest.mark.asyncio
    async def test_converter_async_close_with_client(self, converter):
        """Test converter async close properly handles client cleanup."""
        # Ensure client exists
        assert converter.client is not None
        
        # Async close should not raise exceptions
        await converter.aclose()

    def test_converter_close_without_client(self, test_config):
        """Test converter close handles missing client gracefully."""
        converter = Converter(test_config)
        # Remove client to test edge case
        converter.client = None
        
        # Should not raise exceptions
        converter.close()

    @pytest.mark.asyncio
    async def test_converter_async_close_without_client(self, test_config):
        """Test converter async close handles missing client gracefully."""
        converter = Converter(test_config)
        # Remove client to test edge case
        converter.client = None
        
        # Should not raise exceptions
        await converter.aclose()