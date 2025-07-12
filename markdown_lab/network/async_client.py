"""
Async HTTP client for markdown_lab using httpx.

This module provides an async HTTP client that replaces the synchronous requests-based
implementation with modern async capabilities using httpx. Includes HTTP/2 support,
connection pooling, rate limiting, caching, and consistent error handling.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import httpx

from ..core.config import MarkdownLabConfig
from ..core.errors import NetworkError, handle_request_exception
from ..core.throttle import AsyncRequestThrottler
from .advanced_cache import get_advanced_cache
from .rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class AsyncHttpClient:
    """Async HTTP client with retry logic, rate limiting, and error handling.

    This client provides modern async HTTP capabilities with HTTP/2 support,
    connection pooling, and efficient concurrent request handling.
    """

    def __init__(self, config: MarkdownLabConfig):
        """Initialize the async HTTP client with the provided configuration."""
        self.config = config
        self.throttler = AsyncRequestThrottler(config.requests_per_second)
        self._client: Optional[httpx.AsyncClient] = None

        # Registry to deduplicate in-flight requests per cache key
        self._inflight_requests: Dict[str, asyncio.Task] = {}

        # Configure token bucket rate limiter
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.configure_bucket(
            "http_client",
            rate=config.requests_per_second,
            capacity=int(config.requests_per_second * 10),  # 10 second burst
        )

        # Configure advanced cache
        self.cache = get_advanced_cache(config)

        logger.debug(
            f"Initialized async HTTP client with {config.requests_per_second} req/sec limit"
        )

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure the async client is initialized and return it."""
        if self._client is None:
            self._client = await self._create_client()
        return self._client

    async def _create_client(self) -> httpx.AsyncClient:
        """Create and configure an httpx.AsyncClient with custom settings."""
        # Configure connection limits
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=self.config.max_concurrent_requests * 2,
            keepalive_expiry=30.0,
        )

        # Configure timeout
        timeout = httpx.Timeout(
            timeout=self.config.timeout,
            connect=10.0,
            pool=10.0,
        )

        # Configure headers
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Create client with HTTP/2 support
        client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            headers=headers,
            http2=True,
            follow_redirects=True,
            max_redirects=10,
        )

        logger.debug("Created async HTTP client with HTTP/2 support")
        return client

    async def get(
        self,
        url: str,
        use_cache: bool = True,
        cache_ttl: Optional[float] = 3600,
        **kwargs,
    ) -> str:
        """
        Perform an async GET request to the specified URL with retry logic and caching.

        Implements in-flight request deduplication to prevent cache stampede.

        Args:
            url: The URL to send the GET request to.
            use_cache: Whether to use caching for this request.
            cache_ttl: Cache time-to-live in seconds (default: 1 hour).
            **kwargs: Additional arguments passed to httpx.

        Returns:
            The response body as a string.

        Raises:
            NetworkError: If the request fails after all retry attempts.
        """
        if not use_cache:
            # No caching, make direct request
            return await self._request_with_retries("GET", url, **kwargs)
        # Create cache key from URL and relevant kwargs
        cache_key = self._create_cache_key(url, kwargs)

        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for URL: {url}")
            return cached_result

        # Deduplicate in-flight requests for the same cache key
        inflight = self._inflight_requests.get(cache_key)
        if inflight is not None and not inflight.done():
            logger.debug(f"Awaiting in-flight request for URL: {url}")
            try:
                return await inflight
            except Exception:
                # If in-flight request failed, continue to make our own request
                pass

        # Create task for this request
        task = asyncio.create_task(self._get_and_cache(url, cache_key, cache_ttl, **kwargs))
        self._inflight_requests[cache_key] = task

        try:
            return await task
        finally:
            # Clean up the registry
            self._inflight_requests.pop(cache_key, None)

    async def _get_and_cache(self, url: str, cache_key: str, cache_ttl: float, **kwargs) -> str:
        """
        Helper method to perform GET request and cache the result.
        
        Args:
            url: The URL to request
            cache_key: Cache key for storing the result
            cache_ttl: Cache time-to-live in seconds
            **kwargs: Additional arguments passed to httpx
            
        Returns:
            The response body as a string
        """
        # Perform the actual request
        result = await self._request_with_retries("GET", url, **kwargs)

        # Cache successful result
        if result:
            await self.cache.set(cache_key, result, ttl=cache_ttl)
            logger.debug(f"Cached response for URL: {url}")

        return result

    async def head(self, url: str, **kwargs) -> httpx.Response:
        """
        Perform an async HEAD request to the specified URL.

        Args:
            url: The target URL for the HEAD request.
            **kwargs: Additional arguments passed to httpx.

        Returns:
            The Response object containing headers and status information.

        Raises:
            NetworkError: If the request fails after all retry attempts.
        """
        return await self._request_with_retries(
            "HEAD", url, return_response=True, **kwargs
        )

    async def get_many(self, urls: List[str], use_cache: bool = True, **kwargs) -> Dict[str, str]:
        """
        Perform concurrent GET requests on a list of URLs with rate limiting.

        Checks the cache for each URL before making network requests to avoid redundant calls.

        Uses asyncio.gather for efficient concurrent processing. Failed requests
        are logged and skipped rather than failing the entire batch.

        Args:
            urls: List of URLs to fetch.
            use_cache: Whether to use caching for requests.
            **kwargs: Additional arguments passed to each request.

        Returns:
            Dictionary mapping successful URLs to their response content.
        """
        cached_results = {}
        urls_to_fetch = []

        if use_cache:
            # Check cache for each URL
            for url in urls:
                cache_key = self._create_cache_key(url, kwargs)
                cached = await self.cache.get(cache_key)
                if cached is not None:
                    cached_results[url] = cached
                    logger.debug(f"Cache hit for URL: {url}")
                else:
                    urls_to_fetch.append(url)
        else:
            urls_to_fetch = urls

        if not urls_to_fetch:
            # All URLs were cached
            return cached_results

        # Configure batch rate limiter with higher burst capacity
        self.rate_limiter.configure_bucket(
            "batch_http",
            rate=self.config.requests_per_second * 5,  # 5x rate for batches
            capacity=min(len(urls_to_fetch), 50),  # Allow burst up to 50 or number of URLs
        )

        async def get_with_error_handling(url: str) -> tuple[str, Optional[str]]:
            try:
                # Use the main get method to leverage cache stampede prevention
                content = await self.get(url, use_cache=use_cache, **kwargs)
                logger.debug(f"Successfully retrieved content from {url}")
                return url, content
            except Exception as e:
                logger.warning(f"Failed to retrieve {url}: {e}")
                return url, None

        # Create tasks for concurrent execution
        tasks = [get_with_error_handling(url) for url in urls_to_fetch]

        # Execute concurrently with gather
        results = await asyncio.gather(*tasks)

        # Filter out failed requests and merge with cached results
        fetched_results = {url: content for url, content in results if content is not None}
        return cached_results | fetched_results

    async def _request_with_retries(
        self, method: str, url: str, return_response: bool = False, **kwargs
    ) -> str | httpx.Response:
        """
        Perform an async HTTP request with retry logic and exponential backoff.

        Args:
            method: The HTTP method to use.
            url: The target URL for the request.
            return_response: If True, returns the Response object.
            **kwargs: Additional arguments passed to httpx.

        Returns:
            The response text or Response object.

        Raises:
            NetworkError: If the request fails after all retry attempts.
        """
        client = await self._ensure_client()
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Apply token bucket rate limiting
                async with self.rate_limiter.limit("http_client"):
                    # Make async request
                    start_time = time.time()
                    response = await client.request(method, url, **kwargs)
                    elapsed = time.time() - start_time

                # Check for HTTP errors
                response.raise_for_status()

                # Log successful request
                logger.info(
                    f"Successfully retrieved {url} "
                    f"(status: {response.status_code}, "
                    f"latency: {elapsed:.2f}s, "
                    f"attempt: {attempt + 1}, "
                    f"http2: {response.http_version == 'HTTP/2'})"
                )

                return response if return_response else response.text

            except Exception as e:
                last_exception = e
                network_error = handle_request_exception(e, url, attempt)

                # Log the attempt
                if attempt < self.config.max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Request failed for {url} on attempt {attempt + 1}/{self.config.max_retries + 1}: "
                        f"{network_error.message}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed for {url} after {self.config.max_retries + 1} attempts: "
                        f"{network_error.message}"
                    )
                    raise network_error from e

        # This should never be reached
        if last_exception:
            raise handle_request_exception(last_exception, url, self.config.max_retries)
        raise NetworkError(
            f"Failed to retrieve {url} after {self.config.max_retries + 1} attempts",
            url=url,
            error_code="MAX_RETRIES_EXCEEDED",
        )

    def _create_cache_key(self, url: str, kwargs: Dict) -> str:
        """
        Create a robust cache key from URL and request parameters.

        Includes all relevant parameters that could affect the response:
        headers, params, auth, cookies, proxy settings, etc.

        Args:
            url: The request URL
            kwargs: Request parameters

        Returns:
            A unique cache key string
            
        Note:
            This implementation normalizes headers and includes comprehensive
            request parameters to avoid cache misses/incorrect hits.
        """
        import hashlib

        # Normalize headers (lowercase keys, sorted)
        headers = kwargs.get("headers", {})
        normalized_headers = {
            str(k).lower(): str(v) for k, v in headers.items()
        } if headers else {}

        # Extract auth type and presence (not actual credentials)
        auth = kwargs.get("auth")
        auth_info = None
        if auth is not None:
            if hasattr(auth, '__class__'):
                auth_info = f"{auth.__class__.__name__}"
            else:
                auth_info = "custom_auth"

        # Include relevant parameters that affect response
        cache_params = {
            "url": url.strip(),
            "headers": sorted(normalized_headers.items()),
            "params": sorted((kwargs.get("params", {}) or {}).items()),
            "auth": auth_info,
            "cookies": sorted((kwargs.get("cookies", {}) or {}).items()),
            "proxies": str(kwargs.get("proxies")) if kwargs.get("proxies") else None,
            "verify": kwargs.get("verify", True),
            "cert": bool(kwargs.get("cert")),
            "timeout": kwargs.get("timeout"),
            "allow_redirects": kwargs.get("follow_redirects", True),
        }

        # Create stable string representation
        param_str = str(sorted(cache_params.items()))

        # Use full hash to avoid collisions (32 chars for good distribution)
        cache_hash = hashlib.sha256(param_str.encode()).hexdigest()[:32]

        return f"http_get_{cache_hash}"

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("Async HTTP client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class CachedAsyncHttpClient(AsyncHttpClient):
    """Async HTTP client with caching capabilities.

    Extends the base AsyncHttpClient to add request/response caching with
    support for batch operations and LRU eviction.
    """

    def __init__(self, config: MarkdownLabConfig, cache=None):
        """Initialize a CachedAsyncHttpClient with optional caching."""
        super().__init__(config)

        if cache is None:
            from ..core.cache import AsyncRequestCache

            self.cache = AsyncRequestCache() if config.cache_enabled else None
        else:
            self.cache = cache

        logger.debug(
            f"Initialized cached async HTTP client (cache_enabled: {config.cache_enabled})"
        )

    async def get(self, url: str, use_cache: bool = True, **kwargs) -> str:
        """
        Retrieve content with async cache support.

        Args:
            url: The URL to fetch.
            use_cache: Whether to use and update the cache.
            **kwargs: Additional arguments passed to the request.

        Returns:
            The response body as text.
        """
        if use_cache and self.cache:
            cached_content = await self.cache.get(url)
            if cached_content:
                logger.debug(f"Cache hit for {url}")
                return cached_content

        # Make request
        content = await super().get(url, **kwargs)

        # Store in cache
        if use_cache and self.cache:
            await self.cache.set(url, content)
            logger.debug(f"Cached content for {url}")

        return content

    async def get_many(
        self, urls: List[str], use_cache: bool = True, **kwargs
    ) -> Dict[str, str]:
        """
        Perform concurrent GET requests with cache support.

        Checks cache for all URLs first, then fetches missing ones concurrently.

        Args:
            urls: List of URLs to fetch.
            use_cache: Whether to use and update the cache.
            **kwargs: Additional arguments for requests.

        Returns:
            Dictionary mapping URLs to their content.
        """
        results = {}
        urls_to_fetch = []

        # Check cache first if enabled
        if use_cache and self.cache:
            for url in urls:
                cached_content = await self.cache.get(url)
                if cached_content:
                    results[url] = cached_content
                    logger.debug(f"Cache hit for {url}")
                else:
                    urls_to_fetch.append(url)
        else:
            urls_to_fetch = urls

        # Fetch missing URLs
        if urls_to_fetch:
            fetched = await super().get_many(urls_to_fetch, **kwargs)

            # Update cache and results
            for url, content in fetched.items():
                results[url] = content
                if use_cache and self.cache:
                    await self.cache.set(url, content)
                    logger.debug(f"Cached content for {url}")

        return results

    async def clear_cache(self) -> None:
        """Clear all entries from the request cache."""
        if self.cache:
            await self.cache.clear()
            logger.info("Async request cache cleared")


# Convenience functions for creating pre-configured clients
@asynccontextmanager
async def create_async_http_client(config: Optional[MarkdownLabConfig] = None):
    """
    Create an async HTTP client as a context manager.

    Args:
        config: Optional configuration. Uses default if not provided.

    Yields:
        Configured AsyncHttpClient instance.
    """
    from ..core.config import get_config

    if config is None:
        config = get_config()

    client = AsyncHttpClient(config)
    try:
        yield client
    finally:
        await client.close()


@asynccontextmanager
async def create_cached_async_http_client(
    config: Optional[MarkdownLabConfig] = None, cache=None
):
    """
    Create a cached async HTTP client as a context manager.

    Args:
        config: Optional configuration. Uses default if not provided.
        cache: Optional cache instance.

    Yields:
        Configured CachedAsyncHttpClient instance.
    """
    from ..core.config import get_config

    if config is None:
        config = get_config()

    client = CachedAsyncHttpClient(config, cache)
    try:
        yield client
    finally:
        await client.close()


# Synchronous wrappers for backward compatibility
def sync_get(url: str, config: Optional[MarkdownLabConfig] = None, **kwargs) -> str:
    """
    Synchronous wrapper for async GET request.

    Args:
        url: The URL to fetch.
        config: Optional configuration.
        **kwargs: Additional arguments for the request.

    Returns:
        The response body as text.
    """

    async def _get():
        async with create_async_http_client(config) as client:
            return await client.get(url, **kwargs)

    return asyncio.run(_get())


def sync_get_many(
    urls: List[str], config: Optional[MarkdownLabConfig] = None, **kwargs
) -> Dict[str, str]:
    """
    Synchronous wrapper for async concurrent GET requests.

    Args:
        urls: List of URLs to fetch.
        config: Optional configuration.
        **kwargs: Additional arguments for requests.

    Returns:
        Dictionary mapping URLs to their content.
    """

    async def _get_many():
        async with create_async_http_client(config) as client:
            return await client.get_many(urls, **kwargs)

    return asyncio.run(_get_many())
