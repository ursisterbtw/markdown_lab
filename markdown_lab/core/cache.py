"""
Cache module for HTTP requests to avoid repeated network calls.
"""

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles

logger = logging.getLogger("request_cache")


class RequestCache:
    """Simple cache for HTTP requests to avoid repeated network calls."""

    def __init__(self, cache_dir: str = ".request_cache", max_age: int = 3600):
        """
        Initializes a RequestCache instance with a specified cache directory and maximum cache age.

        Creates the cache directory if it does not exist and sets up an in-memory cache for HTTP responses.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = max_age
        self.memory_cache: Dict[str, Tuple[str, float]] = (
            {}
        )  # url -> (content, timestamp)

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
        Cache a response for a URL.

        Args:
            url: The URL to cache
            content: The content to cache
        """
        # Update memory cache
        self.memory_cache[url] = (content, time.time())

        # Update disk cache
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


class AsyncRequestCache:
    """Async cache for HTTP requests with LRU eviction and batch operations."""

    def __init__(
        self,
        cache_dir: str = ".request_cache",
        max_age: int = 3600,
        max_size: int = 1000,
    ):
        """
        Initialize async cache with specified directory, max age, and size limit.

        Args:
            cache_dir: Directory for cache storage
            max_age: Maximum cache age in seconds
            max_size: Maximum number of items in memory cache
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = max_age
        self.max_size = max_size
        self.memory_cache: Dict[str, Tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    def _get_cache_key(self, url: str) -> str:
        """Generate MD5 hash of URL for cache key."""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, url: str) -> Path:
        """Get path to cache file for URL."""
        key = self._get_cache_key(url)
        return self.cache_dir / key

    async def get(self, url: str) -> Optional[str]:
        """
        Get cached response for URL if exists and not expired.

        Args:
            url: URL to get from cache

        Returns:
            Cached content or None if not found/expired
        """
        async with self._lock:
            # Check memory cache
            if url in self.memory_cache:
                content, timestamp = self.memory_cache[url]
                if time.time() - timestamp <= self.max_age:
                    # Move to end for LRU
                    del self.memory_cache[url]
                    self.memory_cache[url] = (content, timestamp)
                    return content
                # Remove expired
                del self.memory_cache[url]

        # Check disk cache
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            if time.time() - cache_path.stat().st_mtime <= self.max_age:
                try:
                    async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
                        content = await f.read()

                    # Add to memory cache
                    async with self._lock:
                        self._add_to_memory_cache(url, content)

                    return content
                except IOError as e:
                    logger.error(f"Failed to read cache file {cache_path}: {e}")

            # Remove expired file
            try:
                cache_path.unlink()
            except OSError as e:
                logger.warning(f"Failed to remove expired cache file {cache_path}: {e}")

        return None

    async def set(self, url: str, content: str) -> None:
        """
        Cache response for URL.

        Args:
            url: URL to cache
            content: Content to cache
        """
        # Update memory cache
        async with self._lock:
            self._add_to_memory_cache(url, content)

        # Update disk cache
        cache_path = self._get_cache_path(url)
        try:
            async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
                await f.write(content)
        except IOError as e:
            logger.warning(f"Failed to save response to cache: {e}")

    def _add_to_memory_cache(self, url: str, content: str) -> None:
        """Add item to memory cache with LRU eviction."""
        # Remove if exists to add at end
        if url in self.memory_cache:
            del self.memory_cache[url]

        # Evict oldest if at capacity
        if len(self.memory_cache) >= self.max_size:
            # Remove first item (oldest)
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]

        # Add to end
        self.memory_cache[url] = (content, time.time())

    async def get_batch(self, urls: List[str]) -> Dict[str, Optional[str]]:
        """
        Get multiple URLs from cache in batch.

        Args:
            urls: List of URLs to retrieve

        Returns:
            Dictionary mapping URLs to cached content (None if not cached)
        """
        tasks = [self.get(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return dict(zip(urls, results, strict=False))

    async def set_batch(self, items: Dict[str, str]) -> None:
        """
        Set multiple URL responses in cache.

        Args:
            items: Dictionary mapping URLs to content
        """
        tasks = [self.set(url, content) for url, content in items.items()]
        await asyncio.gather(*tasks)

    async def clear(self, max_age: Optional[int] = None) -> int:
        """
        Clear expired cache entries.

        Args:
            max_age: Maximum age in seconds (uses default if not provided)

        Returns:
            Number of entries removed
        """
        if max_age is None:
            max_age = self.max_age

        # Clear memory cache
        async with self._lock:
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
