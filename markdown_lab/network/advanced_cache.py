"""
Advanced caching system with LRU eviction and batch operations.

This module provides a two-tier caching system with in-memory LRU cache
for hot data and persistent disk cache for larger datasets. Supports
batch operations, TTL expiration, and intelligent cache promotion.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import aiofiles
import aiofiles.os

from ..core.config import MarkdownLabConfig
from ..core.errors import CacheError

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    memory_hits: int = 0
    disk_hits: int = 0
    misses: int = 0
    evictions: int = 0
    disk_writes: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate overall cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.memory_hits + self.disk_hits) / self.total_requests
    
    @property
    def memory_hit_rate(self) -> float:
        """Calculate memory cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.memory_hits / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'memory_hits': self.memory_hits,
            'disk_hits': self.disk_hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'disk_writes': self.disk_writes,
            'total_requests': self.total_requests,
            'hit_rate': self.hit_rate,
            'memory_hit_rate': self.memory_hit_rate,
        }


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return False if self.ttl is None else time.time() - self.timestamp > self.ttl
    
    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.timestamp = time.time()


class LRUMemoryCache:
    """Thread-safe LRU memory cache with TTL support."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        async with self._lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.touch()
            
            return entry.data
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set item in cache."""
        async with self._lock:
            # Update existing entry
            if key in self.cache:
                self.cache[key] = CacheEntry(value, ttl=ttl)
                self.cache.move_to_end(key)
                return
            
            # Add new entry
            entry = CacheEntry(value, ttl=ttl)
            self.cache[key] = entry
            
            # Evict if necessary
            if len(self.cache) > self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple items from cache."""
        results = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                results[key] = value
        return results
    
    async def set_many(self, items: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """Set multiple items in cache using concurrent operations."""
        await asyncio.gather(*(self.set(key, value, ttl) for key, value in items.items()))
    
    async def delete(self, key: str) -> bool:
        """Delete item from cache."""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self.cache.clear()
    
    async def size(self) -> int:
        """Get current cache size."""
        async with self._lock:
            return len(self.cache)
    
    async def keys(self) -> List[str]:
        """Get all cache keys."""
        async with self._lock:
            return list(self.cache.keys())


class DiskCache:
    """Persistent disk cache with size management."""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 1000):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Use hash to avoid filesystem issues
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from disk cache."""
        cache_path = self._get_cache_path(key)
        
        try:
            if not cache_path.exists():
                return None
            
            async with aiofiles.open(cache_path, 'r') as f:
                data = json.loads(await f.read())
            
            # Check TTL
            if 'ttl' in data and data['ttl'] and time.time() - data['timestamp'] > data['ttl']:
                await aiofiles.os.remove(cache_path)
                return None
            
            # Update access time
            data['access_time'] = time.time()
            async with aiofiles.open(cache_path, 'w') as f:
                await f.write(json.dumps(data))
            
            return data['value']
            
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Error reading cache file {cache_path}: {e}")
            # Clean up corrupted file
            try:
                await aiofiles.os.remove(cache_path)
            except OSError:
                pass
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set item in disk cache."""
        cache_path = self._get_cache_path(key)
        
        try:
            data = {
                'value': value,
                'timestamp': time.time(),
                'access_time': time.time(),
                'ttl': ttl
            }
            
            async with aiofiles.open(cache_path, 'w') as f:
                await f.write(json.dumps(data, default=str))
            
            # Check size limits
            await self._enforce_size_limit()
            
        except (OSError, TypeError) as e:
            logger.warning(f"Error writing cache file {cache_path}: {e}")
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple items from disk cache."""
        tasks = [self.get(key) for key in keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            key: result 
            for key, result in zip(keys, results)
            if result is not None and not isinstance(result, Exception)
        }
    
    async def set_many(self, items: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """Set multiple items in disk cache."""
        tasks = [self.set(key, value, ttl) for key, value in items.items()]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def delete(self, key: str) -> bool:
        """Delete item from disk cache."""
        cache_path = self._get_cache_path(key)
        try:
            await aiofiles.os.remove(cache_path)
            return True
        except OSError:
            return False
    
    async def clear(self) -> None:
        """Clear all disk cache."""
        async with self._lock:
            try:
                for cache_file in self.cache_dir.glob("*.json"):
                    await aiofiles.os.remove(cache_file)
            except OSError as e:
                logger.warning(f"Error clearing disk cache: {e}")
    
    async def _enforce_size_limit(self) -> None:
        """Enforce disk cache size limit by removing oldest files."""
        async with self._lock:
            try:
                # Get all cache files with stats
                files = []
                total_size = 0
                
                for cache_file in self.cache_dir.glob("*.json"):
                    stat = await aiofiles.os.stat(cache_file)
                    files.append((cache_file, stat.st_mtime, stat.st_size))
                    total_size += stat.st_size
                
                # Remove oldest files if over limit
                if total_size > self.max_size_bytes:
                    # Sort by modification time (oldest first)
                    files.sort(key=lambda x: x[1])
                    
                    for cache_file, _, size in files:
                        await aiofiles.os.remove(cache_file)
                        total_size -= size
                        
                        if total_size <= self.max_size_bytes * 0.8:  # 80% threshold
                            break
                            
            except OSError as e:
                logger.warning(f"Error enforcing cache size limit: {e}")
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get disk cache information."""
        try:
            files = list(self.cache_dir.glob("*.json"))
            total_size = 0
            
            for cache_file in files:
                stat = await aiofiles.os.stat(cache_file)
                total_size += stat.st_size
            
            return {
                'files': len(files),
                'total_size_mb': total_size / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'utilization': total_size / self.max_size_bytes if self.max_size_bytes > 0 else 0
            }
        except OSError:
            return {'files': 0, 'total_size_mb': 0, 'max_size_mb': 0, 'utilization': 0}


class AdvancedCache:
    """
    Two-tier cache system with memory and disk layers.
    
    Provides high-performance caching with LRU eviction, TTL support,
    batch operations, and intelligent cache promotion strategies.
    """
    
    def __init__(self, config: MarkdownLabConfig):
        """Initialize advanced cache system."""
        self.config = config
        
        # Initialize cache layers
        self.memory_cache = LRUMemoryCache(max_size=1000)
        
        cache_dir = Path(config.cache_dir if hasattr(config, 'cache_dir') else '.cache')
        self.disk_cache = DiskCache(cache_dir, max_size_mb=500)
        
        # Statistics
        self.stats = CacheStats()
        self._lock = asyncio.Lock()
        
        logger.info(f"Initialized advanced cache: memory_size=1000, disk_dir={cache_dir}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache with two-tier lookup.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        async with self._lock:
            self.stats.total_requests += 1
        
        # Try memory cache first (fastest)
        value = await self.memory_cache.get(key)
        if value is not None:
            async with self._lock:
                self.stats.memory_hits += 1
            return value
        
        # Try disk cache
        value = await self.disk_cache.get(key)
        if value is not None:
            async with self._lock:
                self.stats.disk_hits += 1
            
            # Promote to memory cache
            await self.memory_cache.set(key, value)
            return value
        
        # Cache miss
        async with self._lock:
            self.stats.misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set item in cache with write-through to both layers.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        # Store in memory cache
        await self.memory_cache.set(key, value, ttl)
        
        # Write through to disk cache
        await self.disk_cache.set(key, value, ttl)
        
        async with self._lock:
            self.stats.disk_writes += 1
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Batch retrieval with intelligent cache promotion.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of found key-value pairs
        """
        async with self._lock:
            self.stats.total_requests += len(keys)

        results = {}

        # Check memory cache first (batch operation)
        memory_results = await self.memory_cache.get_many(keys)
        results |= memory_results

        async with self._lock:
            self.stats.memory_hits += len(memory_results)

        if missing_keys := [key for key in keys if key not in memory_results]:
            # Check disk cache for missing keys
            disk_results = await self.disk_cache.get_many(missing_keys)
            results.update(disk_results)

            async with self._lock:
                self.stats.disk_hits += len(disk_results)

            # Promote disk hits to memory cache
            if disk_results:
                await self.memory_cache.set_many(disk_results)

            # Count final misses
            final_missing = len(missing_keys) - len(disk_results)
            async with self._lock:
                self.stats.misses += final_missing

        return results
    
    async def set_many(self, items: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """
        Batch storage with write-through to both layers.
        
        Args:
            items: Dictionary of key-value pairs to cache
            ttl: Time to live in seconds
        """
        # Store in memory cache
        await self.memory_cache.set_many(items, ttl)
        
        # Write through to disk cache
        await self.disk_cache.set_many(items, ttl)
        
        async with self._lock:
            self.stats.disk_writes += len(items)
    
    async def delete(self, key: str) -> bool:
        """Delete item from both cache layers."""
        memory_deleted = await self.memory_cache.delete(key)
        disk_deleted = await self.disk_cache.delete(key)
        return memory_deleted or disk_deleted
    
    async def clear(self) -> None:
        """Clear both cache layers."""
        await self.memory_cache.clear()
        await self.disk_cache.clear()
        
        # Reset stats
        async with self._lock:
            self.stats = CacheStats()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        async with self._lock:
            stats_dict = self.stats.to_dict()
        
        # Add cache layer info
        memory_size = await self.memory_cache.size()
        disk_info = await self.disk_cache.get_cache_info()
        
        stats_dict.update({
            'memory_cache': {
                'size': memory_size,
                'max_size': self.memory_cache.max_size,
                'utilization': memory_size / self.memory_cache.max_size
            },
            'disk_cache': disk_info
        })
        
        return stats_dict
    
    @asynccontextmanager
    async def cached_operation(self, key: str, ttl: Optional[float] = None):
        """
        Context manager for cached operations.
        
        Example:
            async with cache.cached_operation('expensive_key', ttl=3600) as cached:
                if cached.value is None:
                    result = await expensive_operation()
                    await cached.set(result)
                return cached.value
        """
        class CachedValue:
            def __init__(self, cache_instance, key, initial_value):
                self.cache = cache_instance
                self.key = key
                self.value = initial_value
                self._set_called = False
            
            async def set(self, value):
                await self.cache.set(self.key, value, ttl)
                self.value = value
                self._set_called = True
        
        # Get initial value
        initial_value = await self.get(key)
        cached_value = CachedValue(self, key, initial_value)
        
        try:
            yield cached_value
        finally:
            # Optional: Log cache usage
            if not cached_value._set_called and initial_value is None:
                logger.debug(f"Cache miss for key: {key}")


# Global cache instance
_advanced_cache: Optional[AdvancedCache] = None


def get_advanced_cache(config: Optional[MarkdownLabConfig] = None) -> AdvancedCache:
    """Get or create the global advanced cache instance."""
    global _advanced_cache
    if _advanced_cache is None:
        if config is None:
            from ..core.config import MarkdownLabConfig
            config = MarkdownLabConfig()
        _advanced_cache = AdvancedCache(config)
    return _advanced_cache


async def cached_function(key_template: str, ttl: Optional[float] = None):
    """
    Decorator for caching function results.
    
    Args:
        key_template: Template for cache key (can use function args)
        ttl: Time to live in seconds
    
    Example:
        @cached_function("user_{user_id}_data", ttl=3600)
        async def get_user_data(user_id: str):
            return await expensive_api_call(user_id)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = get_advanced_cache()
            
            # Generate cache key
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            key = key_template.format(**bound.arguments)
            
            # Try cache first
            result = await cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator