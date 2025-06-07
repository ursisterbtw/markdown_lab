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
    """Simple cache for HTTP requests to avoid repeated network calls."""

    def __init__(self, cache_dir: str = ".request_cache", max_age: int = 3600):
        """
        Initialize the request cache.

        Args:
            cache_dir: Directory to store cached responses
            max_age: Maximum age of cached responses in seconds (default: 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = max_age
        self.memory_cache: Dict[str, Tuple[str, float]] = (
            {}
        )  # url -> (content, timestamp)

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from a URL."""
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
        Clear expired cache entries.

        Args:
            max_age: Maximum age in seconds (defaults to instance max_age)

        Returns:
            Number of cache entries removed
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
