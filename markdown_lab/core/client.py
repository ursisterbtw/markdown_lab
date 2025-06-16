"""
HTTP client with caching, throttling, and retry logic.

This module provides a unified HTTP client that replaces the scattered
request handling logic from the original MarkdownScraper class.
"""

import logging
import time
from typing import Optional

import requests

from markdown_lab.core.cache import RequestCache
from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.throttle import RequestThrottler

logger = logging.getLogger(__name__)


class HttpClient:
    """Lightweight HTTP client with built-in caching, throttling, and retry logic."""

    def __init__(self, config: Optional[MarkdownLabConfig] = None):
        """
        Initialize HTTP client with configuration.

        Args:
            config: MarkdownLabConfig instance. If None, uses default config.
        """
        from markdown_lab.core.config import get_config

        self.config = config or get_config()

        # Initialize session with headers
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})

        # Initialize throttling and caching
        self.throttler = RequestThrottler(self.config.requests_per_second)
        self.cache = (
            RequestCache(max_age=self.config.cache_ttl)
            if self.config.cache_enabled
            else None
        )

    def get(self, url: str, skip_cache: bool = False) -> str:
        """
        Fetch content from URL with caching, throttling, and retry logic.

        Args:
            url: The URL to fetch
            skip_cache: If True, bypass cache and force fresh request

        Returns:
            The response content as a string

        Raises:
            requests.exceptions.RequestException: If all retry attempts fail
        """
        # Check cache first
        if not skip_cache and self.cache:
            cached_content = self.cache.get(url)
            if cached_content is not None:
                logger.info(f"Using cached content for {url}")
                return cached_content

        logger.info(f"Fetching: {url}")

        # Fetch with retries
        content = self._fetch_with_retries(url)

        # Cache the response
        if self.cache:
            self.cache.set(url, content)

        return content

    def _fetch_with_retries(self, url: str) -> str:
        """
        Fetch URL with retry logic and exponential backoff.

        Args:
            url: The URL to fetch

        Returns:
            The response content as a string

        Raises:
            requests.exceptions.RequestException: If all retry attempts fail
        """
        for attempt in range(self.config.max_retries):
            try:
                self.throttler.throttle()
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()

                logger.info(
                    f"Successfully retrieved {url} (status: {response.status_code})"
                )
                logger.debug(
                    f"Network latency: {response.elapsed.total_seconds():.2f}s"
                )

                return response.text

            except requests.exceptions.HTTPError as e:
                self._handle_retry(url, attempt, e, "HTTP error")
            except requests.exceptions.ConnectionError as e:
                self._handle_retry(url, attempt, e, "Connection error")
            except requests.exceptions.Timeout as e:
                self._handle_retry(url, attempt, e, "Timeout")
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                raise

        raise requests.exceptions.RequestException(
            f"Failed to retrieve {url} after {self.config.max_retries} attempts"
        )

    def _handle_retry(
        self, url: str, attempt: int, error: Exception, error_type: str
    ) -> None:
        """
        Handle retry logic with exponential backoff.

        Args:
            url: The URL being requested
            attempt: Current attempt number
            error: The exception that occurred
            error_type: String description of error type
        """
        logger.warning(
            f"{error_type} on attempt {attempt+1}/{self.config.max_retries} for {url}: {error}"
        )

        if attempt == self.config.max_retries - 1:
            logger.error(
                f"{error_type} persisted for {url} after {self.config.max_retries} attempts"
            )
            raise error

        # Exponential backoff
        time.sleep(2**attempt)
