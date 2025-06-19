"""
Cache module for HTTP requests to avoid repeated network calls.
"""

import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger("request_cache")


class RequestCache:
    """Cache for HTTP requests to avoid repeated network calls with size limits and LRU eviction."""

    def __init__(
        self, 
        cache_dir: str = ".request_cache", 
        max_age: int = 3600,
        max_memory_items: int = 1000,
        max_disk_size_mb: int = 100
    ):
        """
        Initializes a RequestCache instance with a specified cache directory and limits.

        Creates the cache directory if it does not exist and sets up an in-memory cache 
        with size limits and LRU eviction policy.
        
        Args:
            cache_dir: Directory for disk cache
            max_age: Maximum age of cached items in seconds
            max_memory_items: Maximum number of items in memory cache
            max_disk_size_mb: Maximum disk cache size in MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = max_age
        self.max_memory_items = max_memory_items
        self.max_disk_size_mb = max_disk_size_mb
        
        # Memory cache: url -> (content, timestamp, access_count)
        self.memory_cache: Dict[str, Tuple[str, float, int]] = {}
        self._access_order: Dict[str, float] = {}  # url -> last_access_time

    def _get_cache_key(self, url: str) -> str:
        """
        Generates an MD5 hash of the URL to use as a cache key.
        """
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, url: str) -> Path:
        """Get the path to the cache file for a URL."""
        key = self._get_cache_key(url)
        return self.cache_dir / key

    def _evict_lru_if_needed(self) -> None:
        """Evict least recently used items if cache is full."""
        while len(self.memory_cache) >= self.max_memory_items:
            if not self._access_order:
                # Fallback: remove oldest item by timestamp if access_order is empty
                if self.memory_cache:
                    oldest_url = min(self.memory_cache.keys(), 
                                   key=lambda k: self.memory_cache[k][1])  # timestamp
                    self.memory_cache.pop(oldest_url, None)
                    logger.debug(f"Evicted {oldest_url} from memory cache (fallback)")
                break
            
            # Find the least recently used item
            lru_url = min(self._access_order.keys(), key=lambda k: self._access_order[k])
            
            # Remove from both caches
            self.memory_cache.pop(lru_url, None)
            self._access_order.pop(lru_url, None)
            
            logger.debug(f"Evicted {lru_url} from memory cache (LRU)")

    def _get_disk_cache_size_mb(self) -> float:
        """Calculate current disk cache size in MB."""
        total_size = 0
        for cache_file in self.cache_dir.glob("*"):
            if cache_file.is_file():
                total_size += cache_file.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB

    def _cleanup_disk_cache_if_needed(self) -> None:
        """Remove oldest disk cache files if size limit exceeded."""
        current_size = self._get_disk_cache_size_mb()
        
        if current_size > self.max_disk_size_mb:
            # Get all cache files sorted by modification time (oldest first)
            cache_files = [(f, f.stat().st_mtime) for f in self.cache_dir.glob("*") if f.is_file()]
            cache_files.sort(key=lambda x: x[1])
            
            # Remove files until under limit
            for cache_file, _ in cache_files:
                if current_size <= self.max_disk_size_mb * 0.8:  # Clean to 80% of limit
                    break
                
                file_size_mb = cache_file.stat().st_size / (1024 * 1024)
                cache_file.unlink()
                current_size -= file_size_mb
                logger.debug(f"Removed {cache_file} from disk cache (size limit)")

    def get(self, url: str) -> Optional[str]:
        """
        Get a cached response for a URL if it exists and is not expired.

        Args:
            url: The URL to get from cache

        Returns:
            The cached content or None if not in cache or expired
        """
        # First check memory cache
        if url in self.memory_cache:
            content, timestamp, access_count = self.memory_cache[url]
            if time.time() - timestamp <= self.max_age:
                # Update access time and count
                self._access_order[url] = time.time()
                self.memory_cache[url] = (content, timestamp, access_count + 1)
                return content
            # Remove expired item from memory cache
            del self.memory_cache[url]
            self._access_order.pop(url, None)

        # Check disk cache (if not disabled for testing)
        if not getattr(self, '_disk_cache_disabled', False):
            cache_path = self._get_cache_path(url)
            if cache_path.exists():
                # Check if cache is expired
                if time.time() - cache_path.stat().st_mtime <= self.max_age:
                    try:
                        with open(cache_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        # Add to memory cache with eviction check
                        self._evict_lru_if_needed()
                        current_time = time.time()
                        self.memory_cache[url] = (content, current_time, 1)
                        self._access_order[url] = current_time
                        return content
                    except IOError as e:
                        logger.error(f"Failed to read cache file {cache_path}: {e}")
                        # Log stack trace for debugging
                        import traceback

                        logger.debug(f"Cache read error details: {traceback.format_exc()}")

                # Remove expired cache file
                try:
                    cache_path.unlink()
                except OSError as e:
                    logger.warning(f"Failed to remove expired cache file {cache_path}: {e}")

        return None

    def set(self, url: str, content: str) -> None:
        """
        Cache a response for a URL with size limit enforcement.

        Args:
            url: The URL to cache
            content: The content to cache
        """
        # Evict items if memory cache is full
        self._evict_lru_if_needed()
        
        # Update memory cache with new structure
        current_time = time.time()
        self.memory_cache[url] = (content, current_time, 1)
        self._access_order[url] = current_time

        # Update disk cache with size limit check (if not disabled for testing)
        if not getattr(self, '_disk_cache_disabled', False):
            self._cleanup_disk_cache_if_needed()
            cache_path = self._get_cache_path(url)
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except IOError as e:
                logging.warning(f"Failed to save response to cache: {e}")

    def clear(self, max_age: Optional[int] = None) -> int:
        """
        Removes expired cache entries from both memory and disk.

        Args:
            max_age: Maximum age in seconds for cache validity. If not provided, uses the instance's default.

        Returns:
            The total number of cache entries removed from memory and disk.
        """
        if max_age is None:
            max_age = self.max_age

        # Clear memory cache
        current_time = time.time()
        expired_keys = [
            k
            for k, (_, timestamp, _) in self.memory_cache.items()
            if current_time - timestamp > max_age
        ]
        for k in expired_keys:
            del self.memory_cache[k]
            self._access_order.pop(k, None)

        # Clear disk cache
        count = 0
        for cache_file in self.cache_dir.glob("*"):
            if current_time - cache_file.stat().st_mtime > max_age:
                try:
                    cache_file.unlink()
                    count += 1
                except OSError as e:
                    logger.warning(f"Failed to clear cache file {cache_file}: {e}")

        return count + len(expired_keys)

    def get_stats(self) -> Dict[str, any]:
        """
        Get cache statistics for monitoring and debugging.
        
        Returns:
            Dictionary with cache statistics including size, limits, and usage
        """
        disk_files = len(list(self.cache_dir.glob("*")))
        disk_size_mb = self._get_disk_cache_size_mb()
        
        return {
            "memory_items": len(self.memory_cache),
            "memory_limit": self.max_memory_items,
            "memory_usage_pct": (len(self.memory_cache) / self.max_memory_items) * 100,
            "disk_files": disk_files,
            "disk_size_mb": round(disk_size_mb, 2),
            "disk_limit_mb": self.max_disk_size_mb,
            "disk_usage_pct": (disk_size_mb / self.max_disk_size_mb) * 100,
            "max_age_seconds": self.max_age,
        }
