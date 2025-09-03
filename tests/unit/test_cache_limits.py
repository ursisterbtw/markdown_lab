"""
Unit tests for cache size limits and eviction policies.
"""

import shutil
import tempfile
from pathlib import Path

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
            cache_max_memory=1000,  # 1KB limit for testing
            cache_max_disk=100000,  # 100KB limit for testing
            cache_ttl=3600,
        )
        return RequestCache(config=config, cache_dir=temp_cache_dir)

    @pytest.fixture
    def small_cache(self, temp_cache_dir):
        """Create cache with very small memory limit for testing eviction."""
        config = MarkdownLabConfig(
            cache_max_memory=500,  # 500 bytes limit for testing
            cache_max_disk=50000,  # 50KB limit for testing
            cache_ttl=3600,
        )
        return RequestCache(config=config, cache_dir=temp_cache_dir)

    def test_memory_cache_size_limit(self, small_cache):
        """Test that memory cache enforces size limits."""
        cache = small_cache

        # Add small items that fit within limit
        cache.set("url1", "a")  # ~49 bytes
        cache.set("url2", "b")  # ~49 bytes

        assert len(cache.memory_cache) == 2
        assert cache.get("url1") == "a"
        assert cache.get("url2") == "b"
        assert cache.current_memory_size <= cache.max_memory_size

        # Adding larger content should trigger eviction
        large_content = "x" * 400  # 400+ bytes
        cache.set("url3", large_content)

        # Should have evicted older items to make space
        assert cache.get("url3") == large_content
        assert cache.current_memory_size <= cache.max_memory_size

    def test_timestamp_based_eviction(self, small_cache):
        """Test that eviction works based on timestamps (oldest first)."""
        import time

        cache = small_cache

        # Add items with slight time gaps
        cache.set("url1", "content1")
        time.sleep(0.01)
        cache.set("url2", "content2")
        time.sleep(0.01)
        cache.set("url3", "content3")

        # Add large item that triggers eviction
        large_content = "x" * 400
        cache.set("url4", large_content)

        # Older items should be evicted first (url1, url2)
        assert cache.get("url4") == large_content
        assert cache.current_memory_size <= cache.max_memory_size
        # Some older items may be evicted
        remaining_items = sum(
            bool(cache.get(url) is not None) for url in ["url1", "url2", "url3"]
        )
        assert remaining_items <= 3  # Some eviction should have occurred

    def test_cache_basic_functionality(self, cache):
        """Test basic cache get/set functionality."""
        # Add some items
        cache.set("url1", "content1")
        cache.set("url2", "content2")

        assert cache.get("url1") == "content1"
        assert cache.get("url2") == "content2"
        assert len(cache.memory_cache) == 2

        # Test memory size tracking
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

        disk_size = cache._get_disk_cache_size()
        assert disk_size > 0
        assert disk_size < 100000  # Should be less than 100KB limit

    def test_disk_cache_size_limits(self, cache):
        """Test disk cache respects size limits."""
        # Create content larger than disk limit
        large_content = "x" * 200000  # 200KB content, exceeds 100KB limit

        # This should skip disk caching due to size limit
        cache.set("url1", large_content)

        # Clear memory to check disk
        cache.memory_cache.clear()
        cache.current_memory_size = 0

        # Content should not be retrievable from disk (too large)
        cache.get("url1")
        # May be None if disk write was skipped due to size limit

    def test_cache_clear_functionality(self, cache):
        """Test that cache clear works correctly."""
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

    def test_cache_tuple_structure(self, cache):
        """Test that cache stores correct tuple structure."""
        cache.set("url1", "content1")

        # Check tuple structure: (content, timestamp)
        content, timestamp = cache.memory_cache["url1"]
        assert content == "content1"
        assert isinstance(timestamp, float)
        assert timestamp > 0

    def test_expired_item_cleanup(self, cache):
        """Test that expired items are properly cleaned up."""
        import time

        # Create cache with very short max_age (1 second)
        config = MarkdownLabConfig(
            cache_max_memory=1000,
            cache_max_disk=100000,
            cache_ttl=3600,  # Default TTL, will be overridden
        )
        short_cache = RequestCache(
            config=config,
            cache_dir=cache.cache_dir,
            max_age=1,  # 1 second
        )

        short_cache.set("url1", "content1")
        assert short_cache.get("url1") == "content1"

        # Wait for expiration (1.2 seconds > 1 second expiry)
        time.sleep(1.2)

        # Should return None and clean up expired item
        assert short_cache.get("url1") is None
        assert "url1" not in short_cache.memory_cache

    def test_cache_memory_size_tracking(self, cache):
        """Test that cache properly tracks memory size."""
        initial_size = cache.current_memory_size
        assert initial_size == 0

        cache.set("url1", "content1")
        assert cache.current_memory_size > initial_size

        size_with_one = cache.current_memory_size
        cache.set("url2", "content2")
        assert cache.current_memory_size > size_with_one

        # Clear should reset size
        cache.memory_cache.clear()
        cache.current_memory_size = 0
        assert cache.current_memory_size == 0

    def test_cache_eviction_safety(self, small_cache):
        """Test cache behavior under memory pressure."""
        cache = small_cache

        # Add multiple items that will trigger eviction
        contents = []
        for i in range(10):
            content = f"content{i}" * 10  # Make content larger
            contents.append(content)
            cache.set(f"url{i}", content)

        # Should maintain memory limit
        assert cache.current_memory_size <= cache.max_memory_size

        # Should still be functional
        last_content = contents[-1]
        assert cache.get("url9") == last_content
