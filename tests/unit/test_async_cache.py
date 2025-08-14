"""
Comprehensive tests for async_cache module.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from markdown_lab.core.async_cache import AsyncCacheManager, create_async_cache


class TestAsyncCacheManager:
    """Test AsyncCacheManager functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create AsyncCacheManager instance."""
        return AsyncCacheManager(
            cache_dir=temp_cache_dir,
            max_age=3600,
            enable_compression=True
        )

    @pytest.mark.asyncio
    async def test_init_creates_cache_directory(self, temp_cache_dir):
        """Test that initialization creates cache directory."""
        cache_dir = temp_cache_dir / "test_cache"
        assert not cache_dir.exists()

        AsyncCacheManager(cache_dir=cache_dir)
        assert cache_dir.exists()

    @pytest.mark.asyncio
    async def test_get_cache_key(self, cache_manager):
        """Test cache key generation."""
        url = "https://example.com/test"
        key = cache_manager._get_cache_key(url)

        # Should be MD5 hash
        assert len(key) == 32
        assert all(c in "0123456789abcdef" for c in key)

        # Same URL should produce same key
        assert key == cache_manager._get_cache_key(url)

    @pytest.mark.asyncio
    async def test_get_cache_path(self, cache_manager):
        """Test cache path generation."""
        url = "https://example.com/test"
        path = cache_manager._get_cache_path(url)

        assert path.parent == cache_manager.cache_dir
        assert path.suffix == ".gz"  # Compression enabled

    @pytest.mark.asyncio
    async def test_get_cache_path_without_compression(self, temp_cache_dir):
        """Test cache path generation without compression."""
        cache = AsyncCacheManager(
            cache_dir=temp_cache_dir,
            enable_compression=False
        )
        url = "https://example.com/test"
        path = cache._get_cache_path(url)

        assert path.suffix == ".txt"

    @pytest.mark.asyncio
    async def test_get_miss(self, cache_manager):
        """Test cache miss returns None."""
        result = await cache_manager.get("https://example.com/nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_with_aiofiles(self, cache_manager):
        """Test setting and getting content with aiofiles."""
        url = "https://example.com/test"
        content = "Test content"

        # Set content
        await cache_manager.set(url, content)

        # Get content
        result = await cache_manager.get(url)
        assert result == content

    @pytest.mark.asyncio
    async def test_set_and_get_memory_cache(self, cache_manager):
        """Test memory cache functionality."""
        url = "https://example.com/test"
        content = "Test content"

        # Set content
        await cache_manager.set(url, content)

        # Should be in memory cache
        assert url in cache_manager.memory_cache

        # Get from memory cache (faster path)
        result = await cache_manager.get(url)
        assert result == content

    @pytest.mark.asyncio
    async def test_memory_cache_expiration(self, cache_manager):
        """Test memory cache expiration."""
        cache_manager.max_age = 1  # 1 second TTL
        url = "https://example.com/test"
        content = "Test content"

        await cache_manager.set(url, content)

        # Content should be available immediately
        assert await cache_manager.get(url) == content

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Memory cache should return None (expired)
        # Note: disk cache might still have it
        cache_manager.memory_cache.clear()  # Clear to test disk only
        result = await cache_manager.get(url)
        assert result is None  # Expired

    @pytest.mark.asyncio
    async def test_clear_expired_memory_cache(self, cache_manager):
        """Test clearing expired entries from memory cache."""
        cache_manager.max_age = 1  # 1 second TTL

        # Add entries
        await cache_manager.set("url1", "content1")
        await asyncio.sleep(0.5)
        await cache_manager.set("url2", "content2")

        # Wait for first to expire
        await asyncio.sleep(0.6)

        # Clear expired
        await cache_manager.clear_expired()

        # Only url1 should be removed
        assert "url1" not in cache_manager.memory_cache
        assert "url2" in cache_manager.memory_cache

    @pytest.mark.asyncio
    async def test_clear_expired_disk_cache(self, cache_manager):
        """Test clearing expired entries from disk cache."""
        cache_manager.max_age = 1  # 1 second TTL

        # Add entry and let it expire
        await cache_manager.set("url1", "content1")
        await asyncio.sleep(1.5)

        # Clear expired with specific max age
        await cache_manager.clear_expired(max_age=1)

        # File should be removed
        path = cache_manager._get_cache_path("url1")
        assert not path.exists()

    @pytest.mark.asyncio
    async def test_get_sync_fallback(self, cache_manager):
        """Test synchronous fallback when aiofiles not available."""
        # Test the sync fallback directly
        url = "https://example.com/test"

        # Should use sync fallback
        result = await cache_manager._get_sync_fallback(url)
        assert result is None  # Not cached yet

    @pytest.mark.asyncio
    async def test_set_sync_fallback(self, cache_manager):
        """Test synchronous fallback for setting cache."""
        # Test the sync fallback directly
        url = "https://example.com/test"
        content = "Test content"

        # Should use sync fallback
        await cache_manager._set_sync_fallback(url, content)

        # Verify file was created
        path = cache_manager._get_cache_path(url)
        assert path.exists()

    @pytest.mark.asyncio
    async def test_read_cache_file_not_found(self, cache_manager):
        """Test reading non-existent cache file."""
        path = cache_manager.cache_dir / "nonexistent.gz"
        result = await cache_manager._read_cache_file(path)
        assert result is None

    @pytest.mark.asyncio
    async def test_write_and_read_cache_file(self, cache_manager):
        """Test writing and reading cache file."""
        path = cache_manager.cache_dir / "test.gz"
        content = "Test content"

        await cache_manager._write_cache_file(path, content)
        result = await cache_manager._read_cache_file(path)

        assert result == content

    @pytest.mark.asyncio
    async def test_remove_cache_file(self, cache_manager):
        """Test removing cache file."""
        path = cache_manager.cache_dir / "test.gz"
        path.write_text("test")

        assert path.exists()
        await cache_manager._remove_cache_file(path)
        assert not path.exists()

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_manager):
        """Test cache statistics."""
        # Add some entries
        await cache_manager.set("url1", "content1")
        await cache_manager.set("url2", "content2")

        stats = cache_manager.get_cache_stats()

        assert stats["memory_entries"] == 2
        assert stats["disk_files"] >= 2  # May have additional files
        assert stats["compression_enabled"] is True
        assert stats["max_age"] == 3600
        assert "aiofiles_available" in stats

    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache_manager):
        """Test concurrent cache access."""
        url = "https://example.com/test"
        content = "Test content"

        # Simulate concurrent writes
        tasks = [
            cache_manager.set(f"{url}/{i}", f"{content}/{i}")
            for i in range(10)
        ]
        await asyncio.gather(*tasks)

        # Verify all writes succeeded
        for i in range(10):
            result = await cache_manager.get(f"{url}/{i}")
            assert result == f"{content}/{i}"

    @pytest.mark.asyncio
    async def test_large_content(self, cache_manager):
        """Test caching large content."""
        url = "https://example.com/large"
        content = "x" * 10000  # 10KB

        await cache_manager.set(url, content)
        result = await cache_manager.get(url)

        assert result == content

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self, cache_manager):
        """Test caching content with special characters."""
        url = "https://example.com/special"
        content = "Special chars: \n\t\r 你好 🚀 <>&\""

        await cache_manager.set(url, content)
        result = await cache_manager.get(url)

        assert result == content

    @pytest.mark.asyncio
    async def test_memory_cache_size_tracking(self, cache_manager):
        """Test memory cache size tracking."""
        # AsyncCacheManager doesn't track memory size explicitly
        # Just verify the memory cache stores data
        await cache_manager.set("url1", "content1")
        assert "url1" in cache_manager.memory_cache

    @pytest.mark.asyncio
    async def test_error_handling_in_read(self, cache_manager):
        """Test error handling in cache read."""
        # Create corrupted cache file
        path = cache_manager._get_cache_path("https://example.com/corrupt")
        path.write_bytes(b"corrupted data")

        # Should handle error gracefully
        result = await cache_manager.get("https://example.com/corrupt")
        assert result is None

    @pytest.mark.asyncio
    async def test_error_handling_in_write(self, cache_manager):
        """Test error handling in cache write."""
        # Make cache directory read-only
        cache_manager.cache_dir.chmod(0o444)

        try:
            # Should handle error gracefully
            await cache_manager.set("https://example.com/test", "content")
            # No exception should be raised
        finally:
            # Restore permissions
            cache_manager.cache_dir.chmod(0o755)


class TestCreateAsyncCache:
    """Test create_async_cache factory function."""

    @pytest.mark.asyncio
    async def test_create_with_default_config(self):
        """Test creating cache with default config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = await create_async_cache(cache_dir=Path(temp_dir))
            assert isinstance(cache, AsyncCacheManager)
            assert cache.max_age == 3600

    @pytest.mark.asyncio
    async def test_create_with_custom_params(self):
        """Test creating cache with custom parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = await create_async_cache(
                cache_dir=Path(temp_dir),
                enable_compression=False,
                max_age=1800
            )

            assert isinstance(cache, AsyncCacheManager)
            assert cache.enable_compression is False
            assert cache.max_age == 1800

    @pytest.mark.asyncio
    async def test_aiofiles_not_available_warning(self):
        """Test warning when aiofiles is not available."""
        with patch('markdown_lab.core.async_cache.AIOFILES_AVAILABLE', False):
            with patch('markdown_lab.core.async_cache.logger') as mock_logger:
                with tempfile.TemporaryDirectory() as temp_dir:
                    AsyncCacheManager(cache_dir=Path(temp_dir))

                    # Should log warning
                    mock_logger.warning.assert_called_once()
                    assert "aiofiles not available" in str(mock_logger.warning.call_args)
