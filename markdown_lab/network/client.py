"""
Unified HTTP client for markdown_lab.

This module provides a consolidated HTTP client that eliminates duplicate request
handling logic found in scraper.py and sitemap_utils.py. It includes retry logic,
rate limiting, caching, and consistent error handling.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional

import aiohttp
import requests
from requests.adapters import HTTPAdapter

from ..core.config import MarkdownLabConfig, get_config
from ..core.errors import NetworkError, handle_request_exception
from ..core.throttle import RequestThrottler

logger = logging.getLogger(__name__)


class HttpClient:
    """Unified HTTP client with retry logic, rate limiting, and error handling.

    This client consolidates all HTTP request functionality that was previously
    duplicated across scraper.py and sitemap_utils.py modules.
    """

    def __init__(self, config: Optional[MarkdownLabConfig] = None):
        """
        Initializes the HTTP client with the provided configuration.

        Sets up rate limiting and prepares a requests session for making HTTP requests.

        Args:
            config: MarkdownLabConfig instance. If None, uses default config.
        """
        self.config = config or get_config()
        self.throttler = RequestThrottler(self.config.requests_per_second)
        self.session = self._create_session()

        logger.debug(
            f"Initialized HTTP client with {self.config.requests_per_second} req/sec limit"
        )

    def _create_session(self) -> requests.Session:
        """
        Creates and configures a requests.Session with custom headers and connection pooling.

        The session is set up with a specific User-Agent, standard HTTP headers, and an HTTPAdapter
        for connection pooling. Built-in retries are disabled to allow manual retry handling.
        Returns the configured requests.Session instance.
        """
        session = requests.Session()

        # Configure headers
        session.headers.update(
            {
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=self.config.max_concurrent_requests,
            pool_maxsize=self.config.max_concurrent_requests * 2,
            max_retries=0,  # We handle retries manually for better control
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def get(self, url: str, **kwargs) -> str:
        """
        Performs a GET request to the specified URL with retry logic and error handling.

        Args:
            url: The URL to send the GET request to.
            **kwargs: Additional arguments forwarded to the underlying requests.get() call.

        Returns:
            The response body as a string.

        Raises:
            NetworkError: If the request fails after all retry attempts.
        """
        return self._request_with_retries("GET", url, **kwargs)

    def head(self, url: str, **kwargs) -> requests.Response:
        """
        Performs a HEAD request to the specified URL with retry and error handling.

        Args:
            url: The target URL for the HEAD request.
            **kwargs: Additional arguments forwarded to the underlying requests.head() call.

        Returns:
            The Response object containing headers and status information.

        Raises:
            NetworkError: If the request fails after all retry attempts.
        """
        return self._request_with_retries("HEAD", url, return_response=True, **kwargs)

    def get_many(self, urls: List[str], **kwargs) -> Dict[str, str]:
        """
        Performs sequential GET requests on a list of URLs with rate limiting.

        Each URL is requested in order; if a request fails, the error is logged and processing continues with the next URL. Returns a dictionary mapping each URL to its response content for successful requests.
        """
        results = {}

        for url in urls:
            try:
                content = self.get(url, **kwargs)
                results[url] = content
                logger.debug(f"Successfully retrieved content from {url}")
            except NetworkError as e:
                logger.warning(f"Failed to retrieve {url}: {e}")
                # Continue with other URLs instead of failing completely

        return results

    def _request_with_retries(
        self, method: str, url: str, return_response: bool = False, **kwargs
    ) -> str | requests.Response:
        """
        Performs an HTTP request with retry logic, exponential backoff, and rate limiting.

        Attempts the specified HTTP method on the given URL, retrying on failure up to the configured maximum number of retries. Applies exponential backoff between attempts and raises a NetworkError if all attempts fail. Optionally returns the full Response object if requested.

        Args:
            method: The HTTP method to use (e.g., "GET", "HEAD").
            url: The target URL for the request.
            return_response: If True, returns the Response object; otherwise, returns the response text.
            **kwargs: Additional arguments passed to the underlying session.request().

        Returns:
            The response text content, or the Response object if return_response is True.

        Raises:
            NetworkError: If the request fails after all retry attempts.
        """
        # Set default timeout if not provided
        kwargs.setdefault("timeout", self.config.timeout)

        last_exception = None

        for attempt in range(self.config.max_retries + 1):  # +1 for initial attempt
            try:
                # Apply rate limiting
                self.throttler.throttle()

                # Make request
                start_time = time.time()
                response = self.session.request(method, url, **kwargs)
                elapsed = time.time() - start_time

                # Check for HTTP errors
                response.raise_for_status()

                # Log successful request
                logger.info(
                    f"Successfully retrieved {url} "
                    f"(status: {response.status_code}, "
                    f"latency: {elapsed:.2f}s, "
                    f"attempt: {attempt + 1})"
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
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed for {url} after {self.config.max_retries + 1} attempts: "
                        f"{network_error.message}"
                    )
                    raise network_error from e

        # This should never be reached, but just in case
        if last_exception:
            raise handle_request_exception(last_exception, url, self.config.max_retries)
        raise NetworkError(
            f"Failed to retrieve {url} after {self.config.max_retries + 1} attempts",
            url=url,
            error_code="MAX_RETRIES_EXCEEDED",
        )

    # Async methods for high-performance concurrent operations

    async def get_async(self, url: str, **kwargs) -> str:
        """
        Performs an async GET request to the specified URL with retry logic.

        Args:
            url: The URL to send the GET request to.
            **kwargs: Additional arguments forwarded to the underlying aiohttp request.

        Returns:
            The response body as a string.

        Raises:
            NetworkError: If the request fails after all retry attempts.
        """
        return await self._request_with_retries_async("GET", url, **kwargs)

    async def get_many_async(self, urls: List[str], **kwargs) -> Dict[str, str]:
        """
        Performs concurrent async GET requests on a list of URLs.

        This method provides massive performance improvements over sequential requests
        by making all requests concurrently while respecting rate limits.

        Args:
            urls: List of URLs to fetch concurrently
            **kwargs: Additional arguments forwarded to aiohttp requests

        Returns:
            Dictionary mapping URLs to their response content
        """
        # Create semaphore to limit concurrent requests
        max_concurrent = min(self.config.max_concurrent_requests, len(urls))
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_one(url: str) -> tuple[str, Optional[str]]:
            async with semaphore:
                try:
                    # Add throttling delay
                    await asyncio.sleep(1.0 / self.config.requests_per_second)
                    content = await self.get_async(url, **kwargs)
                    return url, content
                except Exception as e:
                    logger.warning(f"Failed to retrieve {url}: {e}")
                    return url, None

        # Execute all requests concurrently
        tasks = [fetch_one(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and filter out failures
        successful_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                continue
            url, content = result
            if content is not None:
                successful_results[url] = content

        return successful_results

    async def _request_with_retries_async(self, method: str, url: str, **kwargs) -> str:
        """
        Performs an async HTTP request with retry logic and exponential backoff.

        Args:
            method: The HTTP method to use (e.g., "GET", "HEAD").
            url: The target URL for the request.
            **kwargs: Additional arguments passed to aiohttp.

        Returns:
            The response text content.

        Raises:
            NetworkError: If the request fails after all retry attempts.
        """
        # Set default timeout if not provided
        timeout = aiohttp.ClientTimeout(
            total=kwargs.pop("timeout", self.config.timeout)
        )

        last_exception = None

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": self.config.user_agent},
            connector=aiohttp.TCPConnector(limit=self.config.max_concurrent_requests),
        ) as session:
            for attempt in range(self.config.max_retries + 1):
                try:
                    start_time = time.time()
                    async with session.request(method, url, **kwargs) as response:
                        response.raise_for_status()
                        content = await response.text()
                        elapsed = time.time() - start_time

                        logger.info(
                            f"Successfully retrieved {url} "
                            f"(status: {response.status}, "
                            f"latency: {elapsed:.2f}s, "
                            f"attempt: {attempt + 1})"
                        )

                        return content

                except Exception as e:
                    last_exception = e

                    if attempt < self.config.max_retries:
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            f"Async request failed for {url} on attempt {attempt + 1}/{self.config.max_retries + 1}: "
                            f"{str(e)}. Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"Async request failed for {url} after {self.config.max_retries + 1} attempts: "
                            f"{str(e)}"
                        )
                        raise NetworkError(
                            f"Failed to retrieve {url} after {self.config.max_retries + 1} attempts: {str(e)}",
                            url=url,
                            error_code="MAX_RETRIES_EXCEEDED",
                        ) from e

        # This should never be reached, but just in case
        if last_exception:
            raise NetworkError(
                f"Failed to retrieve {url}: {str(last_exception)}",
                url=url,
                error_code="UNKNOWN_ERROR",
            ) from last_exception
        return None

    def close(self) -> None:
        """
        Closes the HTTP session and releases associated resources.
        """
        if self.session:
            self.session.close()
            logger.debug("HTTP client session closed")

    def __enter__(self):
        """
        Enters the context manager and returns the HttpClient instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the HTTP client session when exiting a context manager block.
        """
        self.close()


class CachedHttpClient(HttpClient):
    """HTTP client with caching capabilities.

    Extends the base HttpClient to add request/response caching for improved
    performance when processing multiple similar requests.
    """

    def __init__(self, config: Optional[MarkdownLabConfig] = None, cache=None):
        """
        Initializes a CachedHttpClient with optional caching.

        If a cache instance is not provided and caching is enabled in the configuration, a new cache is created; otherwise, caching is disabled.

        Args:
            config: MarkdownLabConfig instance. If None, uses default config.
            cache: Optional cache instance. If None and caching enabled, creates new cache.
        """
        config = config or get_config()
        super().__init__(config)

        if cache is None:
            from ..core.cache import RequestCache

            self.cache = (
                RequestCache(max_age=config.cache_ttl) if config.cache_enabled else None
            )
        else:
            self.cache = cache

        logger.debug(
            f"Initialized cached HTTP client (cache_enabled: {config.cache_enabled})"
        )

    def get(
        self, url: str, use_cache: bool = True, skip_cache: bool = False, **kwargs
    ) -> str:
        """
        Retrieve the content of a URL using a GET request, utilizing cache if enabled.

        If caching is enabled and a cached response exists for the URL, returns the cached content. Otherwise, performs the GET request, stores the result in the cache if applicable, and returns the response content.

        Parameters:
            url (str): The URL to fetch.
            use_cache (bool): Whether to use and update the cache for this request.
            skip_cache (bool): If True, bypass cache and force fresh request (alias for use_cache=False).

        Returns:
            str: The response body as text.
        """
        # Handle skip_cache parameter for backward compatibility
        if skip_cache:
            use_cache = False

        if use_cache and self.cache and (cached_content := self.cache.get(url)):
            logger.debug(f"Cache hit for {url}")
            return cached_content

        # Make request
        content = super().get(url, **kwargs)

        # Store in cache
        if use_cache and self.cache:
            self.cache.set(url, content)
            logger.debug(f"Cached content for {url}")

        return content

    def clear_cache(self) -> None:
        """
        Clears all entries from the request cache if caching is enabled.
        """
        if self.cache:
            self.cache.clear()
            logger.info("Request cache cleared")

    # Async methods with caching support

    async def get_async(
        self, url: str, use_cache: bool = True, skip_cache: bool = False, **kwargs
    ) -> str:
        """
        Async version of get() with caching support.

        Parameters:
            url (str): The URL to fetch.
            use_cache (bool): Whether to use and update the cache for this request.
            skip_cache (bool): If True, bypass cache and force fresh request.

        Returns:
            str: The response body as text.
        """
        # Handle skip_cache parameter for backward compatibility
        if skip_cache:
            use_cache = False

        if use_cache and self.cache and (cached_content := self.cache.get(url)):
            logger.debug(f"Cache hit for {url}")
            return cached_content

        # Make async request
        content = await super().get_async(url, **kwargs)

        # Store in cache
        if use_cache and self.cache:
            self.cache.set(url, content)
            logger.debug(f"Cached content for {url}")

        return content

    async def get_many_async(
        self, urls: List[str], use_cache: bool = True, **kwargs
    ) -> Dict[str, str]:
        """
        Async version of get_many with intelligent caching.

        This method checks cache for each URL first, then only makes network requests
        for URLs not in cache, providing massive performance improvements.

        Parameters:
            urls: List of URLs to fetch concurrently
            use_cache: Whether to use and update the cache

        Returns:
            Dictionary mapping URLs to their response content
        """
        if not use_cache or not self.cache:
            # No caching, use parent's async method directly
            return await super().get_many_async(urls, **kwargs)

        # Check cache for each URL
        cached_results = {}
        uncached_urls = []

        for url in urls:
            if cached_content := self.cache.get(url):
                cached_results[url] = cached_content
                logger.debug(f"Cache hit for {url}")
            else:
                uncached_urls.append(url)

        # Fetch uncached URLs concurrently
        if uncached_urls:
            logger.info(
                f"Fetching {len(uncached_urls)} uncached URLs out of {len(urls)} total"
            )
            fresh_results = await super().get_many_async(uncached_urls, **kwargs)

            # Cache the fresh results
            for url, content in fresh_results.items():
                self.cache.set(url, content)
                logger.debug(f"Cached content for {url}")

            # Combine cached and fresh results
            cached_results.update(fresh_results)
        else:
            logger.info(f"All {len(urls)} URLs found in cache")

        return cached_results


# Convenience functions for creating pre-configured clients
def create_http_client(config: Optional[MarkdownLabConfig] = None) -> HttpClient:
    """
    Creates and returns an HttpClient instance with the specified or default configuration.

    If no configuration is provided, the default MarkdownLabConfig is used.
    """
    return HttpClient(config)


def create_cached_http_client(
    config: Optional[MarkdownLabConfig] = None, cache=None
) -> CachedHttpClient:
    """
    Creates a CachedHttpClient instance with optional configuration and cache.

    If no configuration is provided, the default MarkdownLabConfig is used. An optional cache instance can be supplied; otherwise, caching behavior is determined by the configuration.

    Returns:
        A CachedHttpClient configured for HTTP requests with caching support.
    """
    return CachedHttpClient(config, cache)
