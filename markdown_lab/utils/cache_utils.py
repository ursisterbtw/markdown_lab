"""
Shared cache utilities for consistent cache key generation and path handling.
"""

import hashlib
from pathlib import Path


def get_cache_key(url: str) -> str:
    """
    Generate a consistent cache key from a URL using MD5 hashing.

    Args:
        url: The URL to generate a cache key for

    Returns:
        MD5 hexdigest of the URL
    """
    return hashlib.md5(url.encode()).hexdigest()


def get_cache_path(cache_dir: Path, url: str, suffix: str = "") -> Path:
    """
    Generate a cache file path for a given URL.

    Args:
        cache_dir: Base cache directory
        url: The URL to cache
        suffix: Optional file suffix (e.g., ".gz", ".txt")

    Returns:
        Path object for the cache file
    """
    key = get_cache_key(url)
    filename = f"{key}{suffix}" if suffix else key
    return cache_dir / filename


def get_cache_path_with_compression(
    cache_dir: Path,
    url: str,
    enable_compression: bool = True
) -> Path:
    """
    Generate a cache file path with appropriate compression suffix.

    Args:
        cache_dir: Base cache directory
        url: The URL to cache
        enable_compression: Whether to use compression

    Returns:
        Path object for the cache file with appropriate suffix
    """
    suffix = ".gz" if enable_compression else ".txt"
    return get_cache_path(cache_dir, url, suffix)
