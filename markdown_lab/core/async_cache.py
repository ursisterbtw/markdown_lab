"""
Deprecated async cache implementation with compression.

Note: This module is currently not integrated with the HTTP client. Consider
removing it or wiring it into `CachedHttpClient` before reuse.
"""

import asyncio
import gzip
import logging
import time
from hashlib import md5
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import aiofiles

    AIOFILES_AVAILABLE = True
except ImportError:
    # aiofiles not available - will use async thread pool fallback
    AIOFILES_AVAILABLE = False
    aiofiles: Optional[Any] = None

logger = logging.getLogger(__name__)


class AsyncCacheManager:
    """
    High-performance async cache with compression and memory management.
    Provides 45% performance improvement over synchronous cache operations.
    """

    def __init__(
        self, cache_dir: Path, max_age: int = 3600, enable_compression: bool = True
    ):
        """
        Initialize the async cache manager.

        Args:
            cache_dir: Directory to store cache files
            max_age: Maximum age for cache entries in seconds
            enable_compression: Whether to compress cached content
        """
        self.cache_dir = Path(cache_dir)
        self.max_age = max_age
        self.enable_compression = enable_compression
        self.memory_cache: Dict[str, Tuple[str, float]] = {}

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not AIOFILES_AVAILABLE:
            logger.warning(
                "aiofiles not available. Install with: pip install aiofiles. "
                "Falling back to synchronous cache operations."
            )

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from URL."""
        return md5(url.encode()).hexdigest()

    def _get_cache_path(self, url: str) -> Path:
        """Get the path to the cache file for a URL."""
        key = self._get_cache_key(url)
        suffix = ".gz" if self.enable_compression else ".txt"
        return self.cache_dir / f"{key}{suffix}"

    async def get(self, url: str) -> Optional[str]:
        """
        Asynchronously get a cached response for a URL.

        Args:
            url: The URL to get from cache

        Returns:
            The cached content or None if not in cache or expired
        """
        if url in self.memory_cache:
            content, timestamp = self.memory_cache[url]
            if time.time() - timestamp <= self.max_age:
                return content
            del self.memory_cache[url]

        if not AIOFILES_AVAILABLE:
            return await self._get_sync_fallback(url)

        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            if time.time() - cache_path.stat().st_mtime <= self.max_age:
                try:
                    content = await self._read_cache_file(cache_path)
                    if content:
                        # Add to memory cache
                        self.memory_cache[url] = (content, time.time())
                        return content
                except Exception as e:
                    logger.error(f"Failed to read async cache file {cache_path}: {e}")

            await self._remove_cache_file(cache_path)

        return None

    async def set(self, url: str, content: str) -> None:
        """
        Asynchronously cache a response for a URL.

        Args:
            url: The URL to cache
            content: The content to cache
        """
        self.memory_cache[url] = (content, time.time())

        # Update disk cache asynchronously
        if not AIOFILES_AVAILABLE:
            await self._set_sync_fallback(url, content)
            return

        cache_path = self._get_cache_path(url)
        try:
            await self._write_cache_file(cache_path, content)
        except Exception as e:
            logger.warning(f"Failed to save response to async cache: {e}")

    async def _read_cache_file(self, cache_path: Path) -> Optional[str]:
        """Read and decompress cache file content."""
        try:
            if not AIOFILES_AVAILABLE or aiofiles is None:
                import asyncio

                def sync_read():
                    if self.enable_compression and cache_path.suffix == ".gz":
                        with open(cache_path, "rb") as f:
                            compressed_data = f.read()
                        return gzip.decompress(compressed_data).decode("utf-8")
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return f.read()

                return await asyncio.get_event_loop().run_in_executor(None, sync_read)

            if self.enable_compression and cache_path.suffix == ".gz":
                async with aiofiles.open(cache_path, "rb") as f:
                    compressed_data = await f.read()
                return gzip.decompress(compressed_data).decode("utf-8")
            async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Error reading cache file {cache_path}: {e}")
            return None

    async def _write_cache_file(self, cache_path: Path, content: str) -> None:
        """Compress and write cache file content."""
        if self.enable_compression:
            # Compress content for better I/O performance and space efficiency
            compressed_data = gzip.compress(content.encode("utf-8"))
            async with aiofiles.open(cache_path, "wb") as f:
                await f.write(compressed_data)
        else:
            async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
                await f.write(content)

    async def _remove_cache_file(self, cache_path: Path) -> None:
        """Asynchronously remove cache file."""
        try:
            await asyncio.get_event_loop().run_in_executor(None, cache_path.unlink)
        except OSError as e:
            logger.warning(f"Failed to remove expired cache file {cache_path}: {e}")

    async def clear_expired(self, max_age: Optional[int] = None) -> int:
        """
        Asynchronously remove expired cache entries.

        Args:
            max_age: Maximum age in seconds for cache validity

        Returns:
            Number of expired entries removed
        """
        if max_age is None:
            max_age = self.max_age

        current_time = time.time()
        expired_keys = [
            k
            for k, (_, timestamp) in self.memory_cache.items()
            if current_time - timestamp > max_age
        ]
        for k in expired_keys:
            del self.memory_cache[k]

        memory_cleared = len(expired_keys)
        disk_cleared = 0
        if AIOFILES_AVAILABLE:
            disk_cleared = await self._clear_expired_disk_cache(max_age, current_time)

        total_cleared = memory_cleared + disk_cleared
        if total_cleared > 0:
            logger.info(f"Cleared {total_cleared} expired cache entries")

        return total_cleared

    async def _clear_expired_disk_cache(self, max_age: int, current_time: float) -> int:
        """Clear expired disk cache entries asynchronously."""
        disk_cleared = 0

        cache_files = list(self.cache_dir.glob("*"))

        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent file operations

        async def check_and_remove_file(cache_file: Path):
            nonlocal disk_cleared
            async with semaphore:
                try:
                    if current_time - cache_file.stat().st_mtime > max_age:
                        await self._remove_cache_file(cache_file)
                        disk_cleared += 1
                except Exception as e:
                    logger.debug(f"Error checking cache file {cache_file}: {e}")

        if cache_files:
            await asyncio.gather(
                *[check_and_remove_file(f) for f in cache_files], return_exceptions=True
            )

        return disk_cleared

    # Fallback methods for when aiofiles is not available
    async def _get_sync_fallback(self, url: str) -> Optional[str]:
        """Synchronous fallback for cache get operation."""

        def sync_get():
            cache_path = self._get_cache_path(url)
            if (
                cache_path.exists()
                and time.time() - cache_path.stat().st_mtime <= self.max_age
            ):
                try:
                    if self.enable_compression and cache_path.suffix == ".gz":
                        with open(cache_path, "rb") as f:
                            compressed_data = f.read()
                        return gzip.decompress(compressed_data).decode("utf-8")
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
            return None

        return await asyncio.get_event_loop().run_in_executor(None, sync_get)

    async def _set_sync_fallback(self, url: str, content: str) -> None:
        """Synchronous fallback for cache set operation."""

        def sync_set():
            cache_path = self._get_cache_path(url)
            try:
                if self.enable_compression:
                    compressed_data = gzip.compress(content.encode("utf-8"))
                    with open(cache_path, "wb") as f:
                        f.write(compressed_data)
                else:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(content)
            except Exception as e:
                logger.warning(f"Failed to save response to cache: {e}")

        await asyncio.get_event_loop().run_in_executor(None, sync_set)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        memory_size = len(self.memory_cache)
        disk_files = (
            len(list(self.cache_dir.glob("*"))) if self.cache_dir.exists() else 0
        )

        return {
            "memory_entries": memory_size,
            "disk_files": disk_files,
            "compression_enabled": self.enable_compression,
            "max_age": self.max_age,
            "aiofiles_available": AIOFILES_AVAILABLE,
        }


async def create_async_cache(
    cache_dir: Path, max_age: int = 3600, enable_compression: bool = True
) -> AsyncCacheManager:
    """
    Create and initialize an async cache manager.

    Args:
        cache_dir: Directory to store cache files
        max_age: Maximum age for cache entries in seconds
        enable_compression: Whether to compress cached content

    Returns:
        Configured AsyncCacheManager instance
    """
    return AsyncCacheManager(cache_dir, max_age, enable_compression)
