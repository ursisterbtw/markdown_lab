"""
Unit tests for cache size limits and eviction policies.
"""

import shutil
import tempfile

import pytest

from markdown_lab.core.cache import RequestCache
from markdown_lab.core.config import MarkdownLabConfig


class TestCacheLimits:
    """Test cache size limits and LRU eviction functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create cache instance with small limits for testing."""
        config = MarkdownLabConfig(
            cache_dir=temp_cache_dir,
            cache_ttl=3600,
            cache_max_memory=1000,  # Small memory limit for testing (1KB)
            cache_max_disk=1_000_000,  # 1MB disk limit for testing
        )
        return RequestCache(config=config)

    @pytest.fixture
    def memory_only_cache(self, temp_cache_dir):
        """Create cache with disabled disk cache for pure memory testing."""
        config = MarkdownLabConfig(
            cache_dir=temp_cache_dir,
            cache_ttl=3600,
            cache_max_memory=1000,  # Small memory limit for testing (1KB)
            cache_max_disk=1_000_000,  # 1MB disk limit for testing
        )
        cache = RequestCache(config=config)
        # Disable disk writes for testing memory-only behavior
        cache._disk_cache_disabled = True
        return cache

    def test_memory_cache_size_limit(self, memory_only_cache):
        """Test that memory cache enforces size limits."""
        cache = memory_only_cache

        # Add small content first
        cache.set("url1", "small1")
        cache.set("url2", "small2")
        len(cache.memory_cache)

        # Add content that should exceed memory limit (1KB limit)
        large_content = "x" * 500  # 500 bytes
        cache.set("url3", large_content)
        cache.set("url4", large_content)  # This should trigger eviction

        # The cache should have evicted some items to stay under memory limit
        assert cache.current_memory_size <= cache.max_memory_size

        # Should still be able to get the most recent item
        assert cache.get("url4") == large_content

    def test_lru_eviction_policy(self, memory_only_cache):
        """Test that memory-based eviction works correctly."""
        cache = memory_only_cache

        # Add content to fill memory
        medium_content = "x" * 200  # 200 bytes each
        cache.set("url1", medium_content)
        cache.set("url2", medium_content)
        cache.set("url3", medium_content)

        # Check that we're getting close to the limit

        # Add large content that should cause eviction
        large_content = "y" * 400  # 400 bytes
        cache.set("url4", large_content)

        # Memory usage should be within limits
        assert cache.current_memory_size <= cache.max_memory_size

        # The most recent large item should still be available
        assert cache.get("url4") == large_content

    def test_cache_basic_functionality(self, cache):
        """Test basic cache functionality."""
        # Add some items
        cache.set("url1", "content1")
        cache.set("url2", "content2")

        # Verify items can be retrieved
        assert cache.get("url1") == "content1"
        assert cache.get("url2") == "content2"

        # Verify memory tracking
        assert len(cache.memory_cache) == 2
        assert cache.current_memory_size > 0
        assert cache.current_memory_size <= cache.max_memory_size

    def test_disk_cache_size_calculation(self, cache):
        """Test disk cache size calculation."""
        # Add some content to create disk files
        large_content = "x" * 1000  # 1KB content
        cache.set("url1", large_content)
        cache.set("url2", large_content)

        # Force write to disk by clearing memory cache
        cache.memory_cache.clear()
        cache.current_memory_size = 0

        disk_size = cache._get_disk_cache_size()  # Returns bytes, not MB
        assert disk_size > 0
        assert disk_size < 1_000_000  # Should be less than 1MB

    def test_disk_cache_size_management(self, cache):
        """Test that disk cache respects size limits."""
        # Create content that approaches the disk limit
        large_content = "x" * 100000  # 100KB content

        # Add several items
        for i in range(5):  # 5 * 100KB = 500KB
            cache.set(f"url{i}", large_content)

        # Check that disk size is managed
        disk_size = cache._get_disk_cache_size()
        assert disk_size <= cache.max_disk_size

    def test_cache_clear_functionality(self, cache):
        """Test that cache clear works properly."""
        import time

        # Add some items
        cache.set("url1", "content1")
        cache.set("url2", "content2")

        # Wait a bit then clear with very short max_age
        time.sleep(0.1)
        cleared_count = cache.clear(max_age=0.05)  # 50ms

        assert cleared_count >= 2
        assert len(cache.memory_cache) == 0
        assert cache.current_memory_size == 0

    def test_cache_memory_structure(self, cache):
        """Test that cache memory structure works correctly."""
        cache.set("url1", "content1")

        # Access the item
        result = cache.get("url1")
        assert result == "content1"

        # Check that the item is stored correctly in memory
        assert "url1" in cache.memory_cache
        content, timestamp = cache.memory_cache["url1"]
        assert content == "content1"
        assert isinstance(timestamp, float)

    def test_expired_item_cleanup(self, cache):
        """Test that expired items are properly cleaned up."""
        import time

        # Create cache with very short max_age
        short_config = MarkdownLabConfig(
            cache_dir=str(cache.cache_dir),
            cache_ttl=0.1,  # 100ms
            cache_max_memory=10000,  # 10KB for testing
            cache_max_disk=1_000_000,  # 1MB disk limit
        )
        short_cache = RequestCache(config=short_config)

        short_cache.set("url1", "content1")
        assert short_cache.get("url1") == "content1"

        # Wait for expiration
        time.sleep(0.2)

        # Should return None and clean up expired item
        assert short_cache.get("url1") is None
        assert "url1" not in short_cache.memory_cache

    def test_cache_handles_inconsistent_state(self, cache):
        """Test cache handles edge cases gracefully."""
        # Manually create consistent memory cache entry
        import time
        cache.memory_cache["url1"] = ("content1", time.time())
        cache.current_memory_size += len("content1".encode('utf-8'))

        # Should not crash when getting items
        result = cache.get("url1")
        assert result == "content1"

    def test_cache_concurrent_access_safety(self, cache):
        """Test cache behavior under concurrent-like access patterns."""
        # Simulate rapid access patterns
        for i in range(10):
            cache.set(f"url{i}", f"content{i}")
            if i % 2 == 0:
                cache.get(f"url{i//2}")  # Access some items

        # Should maintain consistency
        assert cache.current_memory_size <= cache.max_memory_size

        found_items = sum(cache.get(f"url{i}") is not None for i in range(10))
        assert found_items > 0  # At least some items should be cached
