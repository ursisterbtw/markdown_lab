"""Network utilities for markdown_lab."""

from .async_client import (
    AsyncCachedHttpClient,
    AsyncHttpClient,
    create_async_cached_client,
    create_async_client,
    fetch_urls_by_domain,
    fetch_urls_parallel,
)
from .cache import (
    CacheBackend,
    CacheStats,
    HierarchicalCache,
    L1MemoryCache,
    L2DiskCache,
    L3NetworkCache,
    RequestCache,
    create_cache,
)
from .client import (
    CachedHttpClient,
    HttpClient,
    create_cached_http_client,
    create_http_client,
)
from .throttle import (
    AGGRESSIVE_CONFIG,
    CONSERVATIVE_CONFIG,
    DEFAULT_CONFIG,
    AsyncTokenBucket,
    AsyncTokenBucketThrottler,
    RequestThrottler,
    TokenBucket,
    TokenBucketConfig,
    TokenBucketThrottler,
    create_async_throttler,
    create_throttler,
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
