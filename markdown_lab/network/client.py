"""
Unified HTTP client for markdown_lab.

This module provides a consolidated HTTP client that eliminates duplicate request
handling logic found in scraper.py and sitemap_utils.py. It includes retry logic,
rate limiting, caching, and consistent error handling.
"""

import logging
import time
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter

from ..core.config import MarkdownLabConfig
from ..core.errors import NetworkError, handle_request_exception
from ..core.throttle import RequestThrottler

logger = logging.getLogger(__name__)


class HttpClient:
    """Unified HTTP client with retry logic, rate limiting, and error handling.

    This client consolidates all HTTP request functionality that was previously
    duplicated across scraper.py and sitemap_utils.py modules.
    """

    def __init__(self, config: MarkdownLabConfig):
        """
        Initializes the HTTP client with the provided configuration.

        Sets up rate limiting and prepares a requests session for making HTTP requests.
        """
        self.config = config
        self.throttler = RequestThrottler(config.requests_per_second)
        self.session = self._create_session()

        logger.debug(
            f"Initialized HTTP client with {config.requests_per_second} req/sec limit"
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

    def __init__(self, config: MarkdownLabConfig, cache=None):
        """
        Initializes a CachedHttpClient with optional caching.

        If a cache instance is not provided and caching is enabled in the configuration, a new cache is created; otherwise, caching is disabled.
        """
        super().__init__(config)

        if cache is None:
            from ..core.cache import RequestCache

            self.cache = RequestCache() if config.cache_enabled else None
        else:
            self.cache = cache

        logger.debug(
            f"Initialized cached HTTP client (cache_enabled: {config.cache_enabled})"
        )

    def get(self, url: str, use_cache: bool = True, **kwargs) -> str:
        """
        Fetches the content of a URL via a GET request, using cached data if available and enabled.
        
        If caching is enabled and a cached response exists for the URL, returns the cached content. Otherwise, performs the GET request, stores the result in the cache if applicable, and returns the response body as text.
        
        Parameters:
            url (str): The URL to fetch.
            use_cache (bool): If True, attempts to use and update the cache for this request.
        
        Returns:
            str: The response body as text.
        """
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


# Convenience functions for creating pre-configured clients
def create_http_client(config: Optional[MarkdownLabConfig] = None) -> HttpClient:
    """
    Creates and returns an HttpClient instance with the specified or default configuration.

    If no configuration is provided, the default MarkdownLabConfig is used.
    """
    from ..core.config import get_config

    if config is None:
        config = get_config()

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
    from ..core.config import get_config

    if config is None:
        config = get_config()

    return CachedHttpClient(config, cache)
