"""
Cache module for HTTP requests to avoid repeated network calls.
"""

import hashlib
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from markdown_lab.core.config import MarkdownLabConfig, get_config

logger = logging.getLogger("request_cache")


class RequestCache:
    """Simple cache for HTTP requests to avoid repeated network calls."""

    def __init__(self, config: Optional[MarkdownLabConfig] = None, cache_dir: Optional[str] = None, max_age: Optional[int] = None):
        """
        Initializes a RequestCache instance with centralized configuration.

        Args:
            config: Optional MarkdownLabConfig instance. Uses default if not provided.
            cache_dir: Override cache directory (deprecated, use config)
            max_age: Override max age (deprecated, use config)
        """
        # Use provided config or get default, with optional parameter overrides for backward compatibility
        self.config = config or get_config()
        
        self.cache_dir = Path(cache_dir if cache_dir is not None else self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = max_age if max_age is not None else self.config.cache_ttl
        self.max_memory_size = self.config.cache_max_memory
        self.max_disk_size = self.config.cache_max_disk
        self.memory_cache: Dict[str, Tuple[str, float]] = (
            {}
        )  # url -> (content, timestamp)
        self.current_memory_size = 0

    def _get_cache_key(self, url: str) -> str:
        """
        Generates an MD5 hash of the URL to use as a cache key.
        """
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, url: str) -> Path:
        """Get the path to the cache file for a URL."""
        key = self._get_cache_key(url)
        return self.cache_dir / key

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
            content, timestamp = self.memory_cache[url]
            if time.time() - timestamp <= self.max_age:
                return content
            # Remove expired item from memory cache
            del self.memory_cache[url]

        # Check disk cache
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            # Check if cache is expired
            if time.time() - cache_path.stat().st_mtime <= self.max_age:
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Add to memory cache
                    self.memory_cache[url] = (content, time.time())
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
        Cache a response for a URL with size limits.

        Args:
            url: The URL to cache
            content: The content to cache
        """
        content_size = sys.getsizeof(content)
        
        # Check if adding this would exceed memory limits
        if self.current_memory_size + content_size > self.max_memory_size:
            # Remove oldest items until we have space
            self._evict_memory_items(content_size)
        
        # Update memory cache
        self.memory_cache[url] = (content, time.time())
        self.current_memory_size += content_size

        # Update disk cache with size check
        cache_path = self._get_cache_path(url)
        try:
            # Check disk space before writing
            if self._get_disk_cache_size() + len(content.encode('utf-8')) <= self.max_disk_size:
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                logger.warning(f"Disk cache size limit exceeded, skipping disk cache for {url}")
        except IOError as e:
            logger.warning(f"Failed to save response to cache: {e}")

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
            for k, (_, timestamp) in self.memory_cache.items()
            if current_time - timestamp > max_age
        ]
        for k in expired_keys:
            del self.memory_cache[k]

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

    def _evict_memory_items(self, space_needed: int) -> None:
        """Evict items from memory cache to make space."""
        # Sort by timestamp (oldest first)
        sorted_items = sorted(self.memory_cache.items(), key=lambda x: x[1][1])
        
        space_freed = 0
        for url, (content, timestamp) in sorted_items:
            content_size = sys.getsizeof(content)
            del self.memory_cache[url]
            self.current_memory_size -= content_size
            space_freed += content_size
            
            if space_freed >= space_needed:
                break

    def _get_disk_cache_size(self) -> int:
        """Get current disk cache size in bytes."""
        total_size = 0
        for cache_file in self.cache_dir.glob("*"):
            try:
                total_size += cache_file.stat().st_size
            except OSError:
                continue
        return total_size
