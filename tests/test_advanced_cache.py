"""
Tests for advanced caching system.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.network.advanced_cache import (
    AdvancedCache,
    CacheEntry,
    CacheStats,
    DiskCache,
    LRUMemoryCache,
    cached_function,
    get_advanced_cache,
)


@pytest.fixture
def temp_cache_dir():
    """Create temporary directory for cache tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def config(temp_cache_dir):
    """Create test configuration."""
    config = MarkdownLabConfig()
    config.cache_dir = str(temp_cache_dir)
    return config


class TestCacheStats:
    """Test cache statistics tracking."""

    def test_empty_stats(self):
        """Test empty statistics."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0
        assert stats.memory_hit_rate == 0.0
        assert stats.total_requests == 0

    def test_hit_rate_calculation(self):
        """Test hit rate calculations."""
        stats = CacheStats(memory_hits=60, disk_hits=30, misses=10, total_requests=100)

        assert stats.hit_rate == 0.9  # 90% hit rate
        assert stats.memory_hit_rate == 0.6  # 60% memory hit rate

    def test_stats_to_dict(self):
        """Test statistics dictionary conversion."""
        stats = CacheStats(memory_hits=10, disk_hits=5, misses=2, total_requests=17)
        result = stats.to_dict()

        assert result["memory_hits"] == 10
        assert result["disk_hits"] == 5
        assert result["total_requests"] == 17
        assert "hit_rate" in result
        assert "memory_hit_rate" in result


class TestCacheEntry:
    """Test cache entry functionality."""

    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry("test_data")
        assert entry.data == "test_data"
        assert entry.access_count == 0
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry TTL expiration."""
        # Entry that expires immediately
        entry = CacheEntry("test_data", ttl=0.01)
        time.sleep(0.02)
        assert entry.is_expired()

        # Entry that doesn't expire
        entry_no_ttl = CacheEntry("test_data")
        assert not entry_no_ttl.is_expired()

    def test_cache_entry_touch(self):
        """Test cache entry access tracking."""
        entry = CacheEntry("test_data")
        initial_time = entry.timestamp
        initial_count = entry.access_count

        time.sleep(0.01)
        entry.touch()

        assert entry.access_count == initial_count + 1
        assert entry.timestamp > initial_time


class TestLRUMemoryCache:
    """Test LRU memory cache functionality."""

    @pytest.mark.asyncio
    async def test_basic_operations(self):
        """Test basic get/set operations."""
        cache = LRUMemoryCache(max_size=3)

        # Test set and get
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

        # Test missing key
        result = await cache.get("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction policy."""
        cache = LRUMemoryCache(max_size=3)

        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Access key1 to make it recently used
        await cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        await cache.set("key4", "value4")

        assert await cache.get("key1") == "value1"  # Still there
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") == "value3"  # Still there
        assert await cache.get("key4") == "value4"  # New item

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration in memory cache."""
        cache = LRUMemoryCache(max_size=10)

        # Set with short TTL
        await cache.set("ttl_key", "ttl_value", ttl=0.05)

        # Should be available immediately
        result = await cache.get("ttl_key")
        assert result == "ttl_value"

        # Wait for expiration
        await asyncio.sleep(0.1)

        # Should be expired
        result = await cache.get("ttl_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """Test batch get/set operations."""
        cache = LRUMemoryCache(max_size=10)

        # Batch set
        items = {"key1": "value1", "key2": "value2", "key3": "value3"}
        await cache.set_many(items)

        # Batch get
        results = await cache.get_many(["key1", "key2", "key4"])

        assert results["key1"] == "value1"
        assert results["key2"] == "value2"
        assert "key4" not in results  # Missing key

    @pytest.mark.asyncio
    async def test_cache_management(self):
        """Test cache management operations."""
        cache = LRUMemoryCache(max_size=10)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Test size
        assert await cache.size() == 2

        # Test keys
        keys = await cache.keys()
        assert "key1" in keys
        assert "key2" in keys

        # Test delete
        deleted = await cache.delete("key1")
        assert deleted is True
        assert await cache.get("key1") is None
        assert await cache.size() == 1

        # Test clear
        await cache.clear()
        assert await cache.size() == 0


class TestDiskCache:
    """Test disk cache functionality."""

    @pytest.mark.asyncio
    async def test_basic_disk_operations(self, temp_cache_dir):
        """Test basic disk cache operations."""
        cache = DiskCache(temp_cache_dir, max_size_mb=10)

        # Test set and get
        await cache.set("disk_key", {"data": "test_value"})
        result = await cache.get("disk_key")
        assert result == {"data": "test_value"}

        # Test missing key
        result = await cache.get("missing_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_disk_ttl_expiration(self, temp_cache_dir):
        """Test TTL expiration in disk cache."""
        cache = DiskCache(temp_cache_dir, max_size_mb=10)

        # Set with short TTL
        await cache.set("ttl_disk_key", "ttl_value", ttl=0.05)

        # Should be available immediately
        result = await cache.get("ttl_disk_key")
        assert result == "ttl_value"

        # Wait for expiration
        await asyncio.sleep(0.1)

        # Should be expired and removed
        result = await cache.get("ttl_disk_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_disk_batch_operations(self, temp_cache_dir):
        """Test batch operations on disk cache."""
        cache = DiskCache(temp_cache_dir, max_size_mb=10)

        # Batch set
        items = {
            "batch_key1": {"value": 1},
            "batch_key2": {"value": 2},
            "batch_key3": {"value": 3},
        }
        await cache.set_many(items)

        # Batch get
        results = await cache.get_many(["batch_key1", "batch_key2", "missing"])

        assert results["batch_key1"] == {"value": 1}
        assert results["batch_key2"] == {"value": 2}
        assert "missing" not in results

    @pytest.mark.asyncio
    async def test_disk_cache_info(self, temp_cache_dir):
        """Test disk cache information."""
        cache = DiskCache(temp_cache_dir, max_size_mb=10)

        # Add some data
        await cache.set("info_key1", "data1")
        await cache.set("info_key2", "data2")

        info = await cache.get_cache_info()

        assert info["files"] == 2
        assert info["total_size_mb"] > 0
        assert info["max_size_mb"] == 10
        assert 0 <= info["utilization"] <= 1

    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self, temp_cache_dir):
        """Test handling of corrupted cache files."""
        cache = DiskCache(temp_cache_dir, max_size_mb=10)

        # Create a corrupted cache file
        corrupted_path = cache._get_cache_path("corrupted_key")
        with open(corrupted_path, "w") as f:
            f.write("invalid json content {")

        # Should handle gracefully
        result = await cache.get("corrupted_key")
        assert result is None

        # File should be cleaned up
        assert not corrupted_path.exists()


class TestAdvancedCache:
    """Test advanced two-tier cache system."""

    @pytest.mark.asyncio
    async def test_two_tier_lookup(self, config):
        """Test two-tier cache lookup."""
        cache = AdvancedCache(config)

        # Set data (goes to both layers)
        await cache.set("tier_key", "tier_value")

        # Clear memory cache to test disk promotion
        await cache.memory_cache.clear()

        # Get should promote from disk to memory
        result = await cache.get("tier_key")
        assert result == "tier_value"

        # Should now be in memory cache
        memory_result = await cache.memory_cache.get("tier_key")
        assert memory_result == "tier_value"

    @pytest.mark.asyncio
    async def test_batch_operations_with_promotion(self, config):
        """Test batch operations with cache promotion."""
        cache = AdvancedCache(config)

        # Set some data
        items = {"batch1": "value1", "batch2": "value2", "batch3": "value3"}
        await cache.set_many(items)

        # Clear memory to test promotion
        await cache.memory_cache.clear()

        # Batch get should promote from disk
        results = await cache.get_many(["batch1", "batch2", "missing"])

        assert results["batch1"] == "value1"
        assert results["batch2"] == "value2"
        assert "missing" not in results

        # Should be promoted to memory
        memory_result = await cache.memory_cache.get("batch1")
        assert memory_result == "value1"

    @pytest.mark.asyncio
    async def test_cache_statistics(self, config):
        """Test cache statistics tracking."""
        cache = AdvancedCache(config)

        # Generate some cache activity
        await cache.set("stats_key1", "value1")
        await cache.set("stats_key2", "value2")

        # Memory hits
        await cache.get("stats_key1")
        await cache.get("stats_key2")

        # Clear memory and cause disk hits
        await cache.memory_cache.clear()
        await cache.get("stats_key1")  # Disk hit + promotion

        # Cache miss
        await cache.get("missing_key")

        stats = await cache.get_stats()

        assert stats["memory_hits"] >= 2
        assert stats["disk_hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["total_requests"] >= 4
        assert stats["hit_rate"] > 0
        assert "memory_cache" in stats
        assert "disk_cache" in stats

    @pytest.mark.asyncio
    async def test_cached_operation_context_manager(self, config):
        """Test cached operation context manager."""
        cache = AdvancedCache(config)

        # First call - cache miss
        async with cache.cached_operation("expensive_op", ttl=3600) as cached:
            assert cached.value is None

            # Simulate expensive operation
            result = "expensive_result"
            await cached.set(result)

            assert cached.value == "expensive_result"

        # Second call - cache hit
        async with cache.cached_operation("expensive_op") as cached:
            assert cached.value == "expensive_result"

    @pytest.mark.asyncio
    async def test_cache_deletion(self, config):
        """Test cache deletion from both layers."""
        cache = AdvancedCache(config)

        await cache.set("delete_key", "delete_value")

        # Verify it's in both layers
        assert await cache.memory_cache.get("delete_key") is not None
        assert await cache.disk_cache.get("delete_key") is not None

        # Delete from cache
        deleted = await cache.delete("delete_key")
        assert deleted is True

        # Should be gone from both layers
        assert await cache.memory_cache.get("delete_key") is None
        assert await cache.disk_cache.get("delete_key") is None

    @pytest.mark.asyncio
    async def test_cache_clear(self, config):
        """Test clearing both cache layers."""
        cache = AdvancedCache(config)

        # Add data to both layers
        await cache.set("clear_key1", "value1")
        await cache.set("clear_key2", "value2")

        # Clear cache
        await cache.clear()

        # Should be empty
        assert await cache.get("clear_key1") is None
        assert await cache.get("clear_key2") is None

        # Stats should be reset
        stats = await cache.get_stats()
        assert stats["total_requests"] == 2  # From the get calls above


class TestGlobalCacheInstance:
    """Test global cache instance management."""

    def test_get_advanced_cache_singleton(self, config):
        """Test global cache instance is singleton."""
        cache1 = get_advanced_cache(config)
        cache2 = get_advanced_cache()

        assert cache1 is cache2

    @pytest.mark.asyncio
    async def test_cached_function_decorator(self, config):
        """Test cached function decorator."""
        # Reset global cache
        import markdown_lab.network.advanced_cache

        markdown_lab.network.advanced_cache._advanced_cache = None

        call_count = 0

        @cached_function("test_func_{arg1}_{arg2}", ttl=3600)
        async def expensive_function(arg1: str, arg2: int):
            nonlocal call_count
            call_count += 1
            return f"result_{arg1}_{arg2}_{call_count}"

        # First call
        result1 = await expensive_function("test", 123)
        assert result1 == "result_test_123_1"
        assert call_count == 1

        # Second call with same args - should be cached
        result2 = await expensive_function("test", 123)
        assert result2 == "result_test_123_1"  # Same result
        assert call_count == 1  # Not called again

        # Different args - should call function
        result3 = await expensive_function("other", 456)
        assert result3 == "result_other_456_2"
        assert call_count == 2


@pytest.mark.asyncio
async def test_performance_characteristics(config):
    """Test cache performance characteristics."""
    cache = AdvancedCache(config)

    # Warm up the cache
    warm_up_items = {f"perf_key_{i}": f"value_{i}" for i in range(100)}
    await cache.set_many(warm_up_items)

    # Test batch retrieval performance
    start_time = time.time()
    keys = [f"perf_key_{i}" for i in range(100)]
    results = await cache.get_many(keys)
    elapsed = time.time() - start_time

    # Should retrieve all items
    assert len(results) == 100

    # Should be reasonably fast (less than 100ms for 100 items)
    assert elapsed < 0.1

    # Test cache hit rate
    stats = await cache.get_stats()
    assert stats["hit_rate"] > 0.9  # Should have high hit rate


@pytest.mark.asyncio
async def test_concurrent_access(config):
    """Test concurrent cache access."""
    cache = AdvancedCache(config)

    async def worker(worker_id: int):
        for i in range(10):
            key = f"concurrent_{worker_id}_{i}"
            value = f"value_{worker_id}_{i}"

            await cache.set(key, value)
            result = await cache.get(key)
            assert result == value

    # Run multiple workers concurrently
    tasks = [worker(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # Verify all data is accessible
    for worker_id in range(5):
        for i in range(10):
            key = f"concurrent_{worker_id}_{i}"
            result = await cache.get(key)
            assert result == f"value_{worker_id}_{i}"
