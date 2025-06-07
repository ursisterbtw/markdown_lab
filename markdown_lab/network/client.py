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
        """Initialize HTTP client with configuration.

        Args:
            config: MarkdownLab configuration object
        """
        self.config = config
        self.throttler = RequestThrottler(config.requests_per_second)
        self.session = self._create_session()

        logger.debug(
            f"Initialized HTTP client with {config.requests_per_second} req/sec limit"
        )

    def _create_session(self) -> requests.Session:
        """Create configured requests session with connection pooling and retry strategy."""
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
        """Make GET request with retry logic and error handling.

        Args:
            url: URL to request
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            Response text content

        Raises:
            NetworkError: For all network-related failures
        """
        return self._request_with_retries("GET", url, **kwargs)

    def head(self, url: str, **kwargs) -> requests.Response:
        """Make HEAD request with retry logic.

        Args:
            url: URL to request
            **kwargs: Additional arguments passed to requests.head()

        Returns:
            Response object (for accessing headers, status, etc.)

        Raises:
            NetworkError: For all network-related failures
        """
        return self._request_with_retries(
            "HEAD", url, return_response=True, **kwargs
        )

    def get_many(self, urls: List[str], **kwargs) -> Dict[str, str]:
        """Make multiple GET requests sequentially with rate limiting.

        Args:
            urls: List of URLs to request
            **kwargs: Additional arguments passed to each request

        Returns:
            Dictionary mapping URLs to response content
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
        """Make HTTP request with retry logic and exponential backoff.

        Args:
            method: HTTP method (GET, HEAD, etc.)
            url: URL to request
            return_response: If True, return Response object instead of text
            **kwargs: Additional arguments passed to session.request()

        Returns:
            Response text content or Response object

        Raises:
            NetworkError: For all network-related failures
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
        """Close the HTTP session and clean up resources."""
        if self.session:
            self.session.close()
            logger.debug("HTTP client session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class CachedHttpClient(HttpClient):
    """HTTP client with caching capabilities.

    Extends the base HttpClient to add request/response caching for improved
    performance when processing multiple similar requests.
    """

    def __init__(self, config: MarkdownLabConfig, cache=None):
        """Initialize cached HTTP client.

        Args:
            config: MarkdownLab configuration object
            cache: Optional cache instance (defaults to creating one from config)
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
        """Make GET request with optional caching.

        Args:
            url: URL to request
            use_cache: Whether to check cache before making request
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            Response text content
        """
        if use_cache and self.cache:
            # Check cache first
            cached_content = self.cache.get(url)
            if cached_content:
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
        """Clear the request cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Request cache cleared")


# Convenience functions for creating pre-configured clients
def create_http_client(config: Optional[MarkdownLabConfig] = None) -> HttpClient:
    """Create a standard HTTP client with default or provided configuration."""
    from ..core.config import get_config

    if config is None:
        config = get_config()

    return HttpClient(config)


def create_cached_http_client(
    config: Optional[MarkdownLabConfig] = None, cache=None
) -> CachedHttpClient:
    """Create a cached HTTP client with default or provided configuration."""
    from ..core.config import get_config

    if config is None:
        config = get_config()

    return CachedHttpClient(config, cache)
