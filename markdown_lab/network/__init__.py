"""Network utilities for markdown_lab."""

from .client import HttpClient, CachedHttpClient, create_http_client, create_cached_http_client
from .async_client import (
    AsyncHttpClient,
    AsyncCachedHttpClient,
    create_async_client,
    create_async_cached_client,
    fetch_urls_parallel,
    fetch_urls_by_domain,
)
from .throttle import (
    TokenBucketConfig,
    TokenBucket,
    AsyncTokenBucket,
    TokenBucketThrottler,
    AsyncTokenBucketThrottler,
    RequestThrottler,
    create_throttler,
    create_async_throttler,
    DEFAULT_CONFIG,
    CONSERVATIVE_CONFIG,
    AGGRESSIVE_CONFIG,
)
from .cache import (
    CacheStats,
    CacheBackend,
    L1MemoryCache,
    L2DiskCache,
    L3NetworkCache,
    HierarchicalCache,
    RequestCache,
    create_cache,
)

__all__ = [
    # Sync clients
    "HttpClient",
    "CachedHttpClient", 
    "create_http_client",
    "create_cached_http_client",
    # Async clients
    "AsyncHttpClient",
    "AsyncCachedHttpClient",
    "create_async_client", 
    "create_async_cached_client",
    # Utility functions
    "fetch_urls_parallel",
    "fetch_urls_by_domain",
    # Rate limiting
    "TokenBucketConfig",
    "TokenBucket",
    "AsyncTokenBucket", 
    "TokenBucketThrottler",
    "AsyncTokenBucketThrottler",
    "RequestThrottler",
    "create_throttler",
    "create_async_throttler",
    "DEFAULT_CONFIG",
    "CONSERVATIVE_CONFIG", 
    "AGGRESSIVE_CONFIG",
    # Caching
    "CacheStats",
    "CacheBackend",
    "L1MemoryCache",
    "L2DiskCache", 
    "L3NetworkCache",
    "HierarchicalCache",
    "RequestCache",
    "create_cache",
]
