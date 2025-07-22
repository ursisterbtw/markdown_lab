"""
Unit tests for cache size limits and eviction policies.
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from markdown_lab.core.cache import RequestCache


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
        return RequestCache(
            cache_dir=temp_cache_dir,
            max_age=3600,
            max_memory_items=3,  # Small limit for testing
            max_disk_size_mb=1   # 1MB limit for testing
        )

    @pytest.fixture  
    def memory_only_cache(self, temp_cache_dir):
        """Create cache with disabled disk cache for pure memory testing."""
        cache = RequestCache(
            cache_dir=temp_cache_dir,
            max_age=3600,
            max_memory_items=3,
            max_disk_size_mb=1
        )
        # Disable disk writes for testing memory-only behavior
        cache._disk_cache_disabled = True
        return cache

    def test_memory_cache_size_limit(self, memory_only_cache):
        """Test that memory cache enforces size limits."""
        cache = memory_only_cache
        
        # Add items up to the limit
        cache.set("url1", "content1")
        cache.set("url2", "content2") 
        cache.set("url3", "content3")
        
        assert len(cache.memory_cache) == 3
        assert cache.get("url1") == "content1"
        assert cache.get("url2") == "content2"
        assert cache.get("url3") == "content3"
        
        # Adding one more should evict the least recently used
        cache.set("url4", "content4")
        
        assert len(cache.memory_cache) == 3
        assert cache.get("url4") == "content4"
        # url1 should be evicted (least recently used)
        assert cache.get("url1") is None

    def test_lru_eviction_policy(self, memory_only_cache):
        """Test that LRU eviction works correctly."""
        cache = memory_only_cache
        
        # Fill cache
        cache.set("url1", "content1")
        cache.set("url2", "content2")
        cache.set("url3", "content3")
        
        # Access url1 to make it more recently used
        cache.get("url1")
        
        # Add new item - should evict url2 (least recently used)
        cache.set("url4", "content4")
        
        assert cache.get("url1") == "content1"  # Still there (was accessed)
        assert cache.get("url2") is None        # Evicted
        assert cache.get("url3") == "content3"  # Still there
        assert cache.get("url4") == "content4"  # New item

    def test_cache_stats(self, cache):
        """Test cache statistics reporting."""
        # Add some items
        cache.set("url1", "content1")
        cache.set("url2", "content2")
        
        stats = cache.get_stats()
        
        assert stats["memory_items"] == 2
        assert stats["memory_limit"] == 3
        assert stats["memory_usage_pct"] == (2/3) * 100
        assert stats["disk_limit_mb"] == 1
        assert stats["max_age_seconds"] == 3600
        assert "disk_files" in stats
        assert "disk_size_mb" in stats
        assert "disk_usage_pct" in stats

    def test_disk_cache_size_calculation(self, cache):
        """Test disk cache size calculation."""
        # Add some content to create disk files
        large_content = "x" * 1000  # 1KB content
        cache.set("url1", large_content)
        cache.set("url2", large_content)
        
        # Force write to disk by clearing memory cache
        cache.memory_cache.clear()
        
        disk_size = cache._get_disk_cache_size_mb()
        assert disk_size > 0
        assert disk_size < 1  # Should be less than 1MB

    def test_disk_cache_cleanup(self, cache):
        """Test disk cache cleanup when size limit exceeded."""
        # Create content that will exceed 1MB limit
        large_content = "x" * 200000  # 200KB content
        
        # Add enough items to exceed disk limit
        for i in range(7):  # 7 * 200KB = 1.4MB > 1MB limit
            cache.set(f"url{i}", large_content)
        
        # Force disk cache cleanup
        cache._cleanup_disk_cache_if_needed()
        
        # Verify size is under limit
        disk_size = cache._get_disk_cache_size_mb()
        assert disk_size <= cache.max_disk_size_mb

    def test_cache_clear_respects_new_structure(self, cache):
        """Test that cache clear works with new tuple structure."""
        import time

        # Add some items
        cache.set("url1", "content1")
        cache.set("url2", "content2")
        
        # Wait a bit then clear with very short max_age
        time.sleep(0.1)
        cleared_count = cache.clear(max_age=0.05)  # 50ms
        
        assert cleared_count >= 2
        assert len(cache.memory_cache) == 0
        assert len(cache._access_order) == 0

    def test_cache_access_count_tracking(self, cache):
        """Test that cache tracks access counts correctly."""
        cache.set("url1", "content1")
        
        # Access multiple times
        cache.get("url1")
        cache.get("url1")
        cache.get("url1")
        
        # Check that access count increased
        content, timestamp, access_count = cache.memory_cache["url1"]
        assert access_count == 4  # 1 from set + 3 from gets

    def test_expired_item_cleanup(self, cache):
        """Test that expired items are properly cleaned up."""
        import time

        # Create cache with very short max_age
        short_cache = RequestCache(
            cache_dir=cache.cache_dir,
            max_age=0.1,  # 100ms
            max_memory_items=10,
            max_disk_size_mb=1
        )
        
        short_cache.set("url1", "content1")
        assert short_cache.get("url1") == "content1"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should return None and clean up expired item
        assert short_cache.get("url1") is None
        assert "url1" not in short_cache.memory_cache
        assert "url1" not in short_cache._access_order

    def test_cache_handles_empty_access_order(self, cache):
        """Test cache handles edge case of empty access order."""
        # Manually create inconsistent state
        cache.memory_cache["url1"] = ("content1", 1234567890, 1)
        # Don't add to _access_order

        # Should not crash when trying to evict
        cache._evict_lru_if_needed()

    def test_cache_concurrent_access_safety(self, cache):
        """Test cache behavior under concurrent-like access patterns."""
        # Simulate rapid access patterns
        for i in range(10):
            cache.set(f"url{i}", f"content{i}")
            if i % 2 == 0:
                cache.get(f"url{i//2}")  # Access some items
        
        # Should maintain consistency
        assert len(cache.memory_cache) <= cache.max_memory_items
        assert len(cache._access_order) == len(cache.memory_cache)
        
        # All items in memory_cache should be in _access_order
        for url in cache.memory_cache.keys():
            assert url in cache._access_order