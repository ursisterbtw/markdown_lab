"""
Hierarchical caching system with L1/L2/L3 architecture.

This module provides a sophisticated multi-level cache system:
- L1: Memory cache (fastest access, limited size)
- L2: Disk cache (persistent, larger capacity)
- L3: Network cache (optional, for distributed setups)

The hierarchical design provides optimal performance with automatic
promotion between cache levels and intelligent eviction policies.
"""

import asyncio
import gzip
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import diskcache  # type: ignore
from cachetools import LRUCache  # type: ignore

from ..core.config import MarkdownLabConfig

logger = logging.getLogger(__name__)

# Compression threshold for L2 disk cache
COMPRESSION_THRESHOLD = 1024


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    hits: int = 0
    misses: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    evictions: int = 0
    storage_size_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def l1_hit_rate(self) -> float:
        """Calculate L1 cache hit rate."""
        return self.l1_hits / self.hits if self.hits > 0 else 0.0


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class L1MemoryCache(CacheBackend):
    """L1 memory cache using LRU eviction."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """Initialize L1 memory cache.

        Args:
            max_size: Maximum number of items to store
            ttl: Time to live for cache entries in seconds
        """
        self.cache = LRUCache(maxsize=max_size)
        self.ttl = ttl
        self.timestamps: Dict[str, float] = {}
        self.hits = 0
        self.misses = 0

        logger.debug(f"L1MemoryCache initialized: max_size={max_size}, ttl={ttl}s")

    async def get(self, key: str) -> Optional[bytes]:
        """Get value from L1 cache."""
        try:
            value = self.cache[key]
            timestamp = self.timestamps.get(key, 0)

            # Check TTL
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                self.timestamps.pop(key, None)
                self.misses += 1
                return None

            self.hits += 1
            logger.debug(f"L1 cache hit: {key}")
            return value

        except KeyError:
            self.misses += 1
            return None

    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        """Set value in L1 cache."""
        self.cache[key] = value
        self.timestamps[key] = time.time()
        logger.debug(f"L1 cache set: {key} ({len(value)} bytes)")

    async def delete(self, key: str) -> bool:
        """Delete value from L1 cache."""
        try:
            del self.cache[key]
            self.timestamps.pop(key, None)
            return True
        except KeyError:
            return False

    async def clear(self) -> None:
        """Clear L1 cache."""
        self.cache.clear()
        self.timestamps.clear()
        logger.info("L1 cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get L1 cache statistics."""
        return {
            "type": "L1Memory",
            "size": len(self.cache),
            "max_size": self.cache.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0.0
        }


class L2DiskCache(CacheBackend):
    """L2 disk cache with compression and size limits."""

    def __init__(self, cache_dir: Path, max_size: int = 1024 * 1024 * 1024, ttl: int = 86400):
        """Initialize L2 disk cache.

        Args:
            cache_dir: Directory for cache storage
            max_size: Maximum cache size in bytes (default 1GB)
            ttl: Time to live for cache entries in seconds (default 24h)
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Use diskcache for efficient disk-based storage
        self.cache = diskcache.Cache(
            directory=str(cache_dir),
            size_limit=max_size,
            # Enable automatic cleanup of expired entries
            eviction_policy='least-recently-used',
            # Compress large values
            cull_limit=10
        )

        self.ttl = ttl
        self.hits = 0
        self.misses = 0

        logger.debug(f"L2DiskCache initialized: dir={cache_dir}, max_size={max_size//1024//1024}MB, ttl={ttl}s")

    async def get(self, key: str) -> Optional[bytes]:
        """Get value from L2 cache."""
        try:
            # diskcache operations are CPU-bound, run in thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.cache.get, key, None
            )

            if result is not None:
                value, timestamp = result

                # Check TTL
                if time.time() - timestamp > self.ttl:
                    await self.delete(key)
                    self.misses += 1
                    return None

                self.hits += 1
                logger.debug(f"L2 cache hit: {key}")
                return self._decompress(value)

            self.misses += 1
            return None

        except (OSError, ValueError) as e:
            logger.warning(f"L2 cache get error for {key}: {e}")
            self.misses += 1
            return None

    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        """Set value in L2 cache."""
        try:
            compressed_value = self._compress(value)
            cache_value = (compressed_value, time.time())

            # Run disk operation in thread pool
            await asyncio.get_event_loop().run_in_executor(
                None, self.cache.set, key, cache_value
            )

            logger.debug(f"L2 cache set: {key} ({len(value)} -> {len(compressed_value)} bytes)")

        except (OSError, ValueError) as e:
            logger.warning(f"L2 cache set error for {key}: {e}")

    async def delete(self, key: str) -> bool:
        """Delete value from L2 cache."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self.cache.delete, key
            )
        except (OSError, ValueError) as e:
            logger.warning(f"L2 cache delete error for {key}: {e}")
            return False

    async def clear(self) -> None:
        """Clear L2 cache."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.cache.clear
            )
            logger.info("L2 cache cleared")
        except (OSError, ValueError) as e:
            logger.warning(f"L2 cache clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get L2 cache statistics."""
        volume = self.cache.volume()
        return {
            "type": "L2Disk",
            "size": len(self.cache),
            "volume_bytes": volume,
            "max_size_bytes": self.cache.size_limit,
            "utilization": volume / self.cache.size_limit if self.cache.size_limit > 0 else 0.0,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0.0
        }

    def _compress(self, data: bytes) -> bytes:
        """Compress data for storage efficiency."""
        return gzip.compress(data, compresslevel=6) if len(data) > COMPRESSION_THRESHOLD else data

    def _decompress(self, data: bytes) -> bytes:
        """Decompress stored data."""
        try:
            # Try to decompress - if it fails, data wasn't compressed
            return gzip.decompress(data)
        except gzip.BadGzipFile:
            return data


class L3NetworkCache(CacheBackend):
    """L3 network cache for distributed caching (Redis, Memcached, etc.)."""

    def __init__(self, client=None):
        """Initialize L3 network cache.

        Args:
            client: External cache client (Redis, Memcached, etc.)
        """
        self.client = client
        self.hits = 0
        self.misses = 0

        if client:
            logger.debug("L3NetworkCache initialized with external client")
        else:
            logger.debug("L3NetworkCache initialized without client (disabled)")

    async def get(self, key: str) -> Optional[bytes]:
        """Get value from L3 cache."""
        if not self.client:
            return None

        try:
            # This would be implemented based on the specific client
            # For now, return None (L3 cache not implemented)
            self.misses += 1
            return None
        except Exception as e:
            logger.warning(f"L3 cache get error for {key}: {e}")
            self.misses += 1
            return None

    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        """Set value in L3 cache."""
        if not self.client:
            return

        try:
            # This would be implemented based on the specific client
            pass
        except Exception as e:
            logger.warning(f"L3 cache set error for {key}: {e}")

    async def delete(self, key: str) -> bool:
        """Delete value from L3 cache."""
        if not self.client:
            return False

        try:
            # This would be implemented based on the specific client
            return False
        except Exception as e:
            logger.warning(f"L3 cache delete error for {key}: {e}")
            return False

    async def clear(self) -> None:
        """Clear L3 cache."""
        if not self.client:
            return

        try:
            # This would be implemented based on the specific client
            pass
        except Exception as e:
            logger.warning(f"L3 cache clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get L3 cache statistics."""
        return {
            "type": "L3Network",
            "enabled": self.client is not None,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0.0
        }


class HierarchicalCache:
    """Multi-level cache: L1 (Memory) → L2 (Disk) → L3 (Network).

    This cache provides optimal performance through:
    - L1: Fast memory access for hot data
    - L2: Persistent disk storage for warm data
    - L3: Optional network cache for distributed scenarios

    Features:
    - Automatic promotion between levels
    - Intelligent eviction policies
    - Compression for disk storage
    - Comprehensive statistics
    - Async/await support
    """

    def __init__(self, config: MarkdownLabConfig):
        """Initialize hierarchical cache.

        Args:
            config: Configuration object with cache settings
        """
        self.config = config

        # Initialize cache levels
        self.l1 = L1MemoryCache(
            max_size=getattr(config, 'cache_l1_size', 1000),
            ttl=getattr(config, 'cache_ttl', 3600)
        )

        cache_dir = Path(getattr(config, 'cache_dir', '.cache'))
        self.l2 = L2DiskCache(
            cache_dir=cache_dir / 'l2',
            max_size=getattr(config, 'cache_l2_size', 1024 * 1024 * 1024),  # 1GB
            ttl=getattr(config, 'cache_ttl', 86400)  # 24h
        )

        # L3 cache is optional and disabled by default
        self.l3 = L3NetworkCache() if getattr(config, 'cache_l3_enabled', False) else None

        self.stats = CacheStats()

        logger.info("HierarchicalCache initialized with L1+L2+L3 architecture")

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache hierarchy.

        Checks L1 → L2 → L3 in order, promoting values up the hierarchy.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        cache_key = self._hash_key(key)

        # L1: Check memory cache first (fastest)
        if value := await self.l1.get(cache_key):
            self.stats.hits += 1
            self.stats.l1_hits += 1
            return self._decode_value(value)

        # L2: Check disk cache
        if value := await self.l2.get(cache_key):
            self.stats.hits += 1
            self.stats.l2_hits += 1

            # Promote to L1
            await self.l1.set(cache_key, value)

            return self._decode_value(value)

        # L3: Check network cache (if enabled)
        if self.l3 and (value := await self.l3.get(cache_key)):
            self.stats.hits += 1
            self.stats.l3_hits += 1

            # Promote to L1 and L2
            await self.l1.set(cache_key, value)
            await self.l2.set(cache_key, value)

            return self._decode_value(value)

        self.stats.misses += 1
        return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value in cache hierarchy.

        Stores in all available cache levels for optimal access patterns.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        cache_key = self._hash_key(key)
        encoded_value = self._encode_value(value)

        # Store in all cache levels
        await self.l1.set(cache_key, encoded_value, ttl)
        await self.l2.set(cache_key, encoded_value, ttl)

        if self.l3:
            await self.l3.set(cache_key, encoded_value, ttl)

        logger.debug(f"Cached value for key: {key} ({len(value)} chars)")

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Batch retrieval for better performance.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary mapping keys to values (or None if not cached)
        """
        # Process all keys concurrently
        tasks = [self.get(key) for key in keys]
        values = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            key: value if isinstance(value, str) else None
            for key, value in zip(keys, values)
        }

    async def set_many(self, items: Dict[str, str], ttl: Optional[int] = None) -> None:
        """Batch storage for better performance.

        Args:
            items: Dictionary of key-value pairs to cache
            ttl: Time to live in seconds
        """
        tasks = [
            self.set(key, value, ttl)
            for key, value in items.items()
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def delete(self, key: str) -> bool:
        """Delete value from all cache levels.

        Args:
            key: Cache key to delete

        Returns:
            True if any cache level had the key
        """
        cache_key = self._hash_key(key)

        delete_tasks = [
            self.l1.delete(cache_key),
            self.l2.delete(cache_key),
        ]

        if self.l3:
            delete_tasks.append(self.l3.delete(cache_key))

        results = await asyncio.gather(*delete_tasks, return_exceptions=True)

        return any(r for r in results if not isinstance(r, Exception))

    async def clear(self) -> None:
        """Clear all cache levels."""
        clear_tasks = [
            self.l1.clear(),
            self.l2.clear(),
        ]

        if self.l3:
            clear_tasks.append(self.l3.clear())

        await asyncio.gather(*clear_tasks, return_exceptions=True)

        # Reset stats
        self.stats = CacheStats()

        logger.info("All cache levels cleared")

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all cache levels.

        Returns:
            Dictionary with detailed cache statistics
        """
        l1_stats = self.l1.get_stats()
        l2_stats = self.l2.get_stats()
        l3_stats = self.l3.get_stats() if self.l3 else {"type": "L3Network", "enabled": False}

        return {
            "overall": {
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "hit_rate": self.stats.hit_rate,
                "l1_hit_rate": self.stats.l1_hit_rate,
            },
            "l1": l1_stats,
            "l2": l2_stats,
            "l3": l3_stats,
        }

    def _hash_key(self, key: str) -> str:
        """Create consistent hash for cache key."""
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _encode_value(self, value: str) -> bytes:
        """Encode value for storage."""
        return value.encode('utf-8')

    def _decode_value(self, value: bytes) -> str:
        """Decode stored value."""
        return value.decode('utf-8')


# Convenience functions
async def create_cache(config: Optional[MarkdownLabConfig] = None) -> HierarchicalCache:
    """Create hierarchical cache with configuration.

    Args:
        config: Optional configuration (uses default if not provided)

    Returns:
        Configured HierarchicalCache instance
    """
    from ..core.config import get_config

    if config is None:
        config = get_config()

    return HierarchicalCache(config)


# Backward compatibility with existing RequestCache
class RequestCache:
    """Backward compatible wrapper around HierarchicalCache."""

    def __init__(self, cache_dir: str = ".request_cache", max_age: int = 3600):
        """Initialize with simple configuration.

        Args:
            cache_dir: Cache directory
            max_age: Maximum age for cache entries
        """
        # Create a simple config for the hierarchical cache
        from ..core.config import MarkdownLabConfig

        config = MarkdownLabConfig()
        config.cache_dir = cache_dir
        config.cache_ttl = max_age

        self._cache = HierarchicalCache(config)

    def get(self, url: str) -> Optional[str]:
        """Get cached content synchronously."""
        return asyncio.run(self._cache.get(url))

    def set(self, url: str, content: str) -> None:
        """Set cached content synchronously."""
        asyncio.run(self._cache.set(url, content))

    def clear(self) -> int:
        """Clear cache and return number of items cleared."""
        asyncio.run(self._cache.clear())
        return 0  # Can't easily return count in hierarchical cache
