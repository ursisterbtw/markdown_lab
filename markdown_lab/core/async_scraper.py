"""
Async web scraper for converting HTML to various formats using httpx.

This module provides async scraping capabilities with concurrent request handling,
advanced caching, and integration with Rust-based HTML processing.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union

from ..core.config import MarkdownLabConfig
from ..core.errors import MarkdownLabError, ProcessingError
from ..markdown_lab_rs import html_to_json, html_to_markdown, html_to_xml
from ..network.async_client import (
    CachedAsyncHttpClient,
)

logger = logging.getLogger(__name__)


class AsyncMarkdownScraper:
    """Async web scraper with concurrent processing and format conversion."""

    def __init__(self, config: Optional[MarkdownLabConfig] = None):
        """
        Initialize async scraper with configuration.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        if config is None:
            from ..core.config import get_config

            config = get_config()

        self.config = config
        self._client: Optional[CachedAsyncHttpClient] = None

        logger.debug(f"Initialized AsyncMarkdownScraper with config: {config}")

    async def _ensure_client(self) -> CachedAsyncHttpClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = CachedAsyncHttpClient(self.config)
        return self._client

    async def scrape_to_markdown(
        self,
        url: str,
        use_cache: bool = True,
        chunk_size: Optional[int] = None,
        chunk_overlap: int = 0,
    ) -> Union[str, List[str]]:
        """
        Scrape URL and convert to Markdown asynchronously.

        Args:
            url: URL to scrape
            use_cache: Whether to use cache
            chunk_size: Optional size for content chunking
            chunk_overlap: Overlap between chunks (for RAG)

        Returns:
            Markdown content as string or list of chunks

        Raises:
            MarkdownLabError: If scraping or conversion fails
        """
        try:
            # Get HTML content
            client = await self._ensure_client()
            html_content = await client.get(url, use_cache=use_cache)

            # Convert to Markdown using Rust
            markdown = html_to_markdown(html_content)

            # Apply chunking if requested
            if chunk_size:
                from ..utils.chunk_utils import chunk_text

                return chunk_text(markdown, chunk_size, chunk_overlap)

            return markdown

        except Exception as e:
            logger.error(f"Failed to scrape {url} to markdown: {e}")
            raise ProcessingError(
                f"Failed to convert {url} to markdown",
                url=url,
                error_code="MARKDOWN_CONVERSION_ERROR",
            ) from e

    async def scrape_to_json(
        self, url: str, use_cache: bool = True, include_metadata: bool = True
    ) -> Dict:
        """
        Scrape URL and convert to structured JSON.

        Args:
            url: URL to scrape
            use_cache: Whether to use cache
            include_metadata: Include document metadata

        Returns:
            Structured JSON representation

        Raises:
            MarkdownLabError: If scraping or conversion fails
        """
        try:
            # Get HTML content
            client = await self._ensure_client()
            html_content = await client.get(url, use_cache=use_cache)

            # Convert to JSON using Rust
            json_data = html_to_json(html_content)

            # Add metadata if requested
            if include_metadata:
                json_data["metadata"] = {
                    "source_url": url,
                    "scraper": "AsyncMarkdownScraper",
                    "version": "1.0.0",
                }

            return json_data

        except Exception as e:
            logger.error(f"Failed to scrape {url} to JSON: {e}")
            raise ProcessingError(
                f"Failed to convert {url} to JSON",
                url=url,
                error_code="JSON_CONVERSION_ERROR",
            ) from e

    async def scrape_to_xml(self, url: str, use_cache: bool = True) -> str:
        """
        Scrape URL and convert to XML format.

        Args:
            url: URL to scrape
            use_cache: Whether to use cache

        Returns:
            XML representation

        Raises:
            MarkdownLabError: If scraping or conversion fails
        """
        try:
            # Get HTML content
            client = await self._ensure_client()
            html_content = await client.get(url, use_cache=use_cache)

            # Convert to XML using Rust
            return html_to_xml(html_content)

        except Exception as e:
            logger.error(f"Failed to scrape {url} to XML: {e}")
            raise ProcessingError(
                f"Failed to convert {url} to XML",
                url=url,
                error_code="XML_CONVERSION_ERROR",
            ) from e

    async def scrape_many(
        self,
        urls: List[str],
        format: str = "markdown",
        use_cache: bool = True,
        max_concurrent: Optional[int] = None,
    ) -> Dict[str, Union[str, Dict]]:
        """
        Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            format: Output format (markdown, json, xml)
            use_cache: Whether to use cache
            max_concurrent: Max concurrent requests (uses config default if None)

        Returns:
            Dictionary mapping URLs to their converted content

        Raises:
            ValueError: If format is invalid
        """
        if format not in ["markdown", "json", "xml"]:
            raise ValueError(f"Invalid format: {format}")

        # Determine scraping method
        if format == "markdown":
            scrape_method = self.scrape_to_markdown
        elif format == "json":
            scrape_method = self.scrape_to_json
        else:
            scrape_method = self.scrape_to_xml

        # Set concurrency limit
        if max_concurrent is None:
            max_concurrent = self.config.max_concurrent_requests

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(
            url: str,
        ) -> tuple[str, Optional[Union[str, Dict]]]:
            async with semaphore:
                try:
                    result = await scrape_method(url, use_cache=use_cache)
                    return url, result
                except MarkdownLabError as e:
                    logger.warning(f"Failed to scrape {url}: {e}")
                    return url, None

        # Create tasks
        tasks = [scrape_with_semaphore(url) for url in urls]

        # Execute concurrently
        results = await asyncio.gather(*tasks)

        # Filter out failures
        return {url: content for url, content in results if content is not None}

    async def scrape_sitemap(
        self,
        sitemap_url: str,
        format: str = "markdown",
        min_priority: float = 0.5,
        limit: Optional[int] = None,
        use_cache: bool = True,
    ) -> Dict[str, Union[str, Dict]]:
        """
        Discover and scrape URLs from a sitemap.

        Args:
            sitemap_url: URL of the sitemap
            format: Output format
            min_priority: Minimum priority for URLs to include
            limit: Maximum number of URLs to process
            use_cache: Whether to use cache

        Returns:
            Dictionary mapping URLs to converted content
        """
        from ..utils.sitemap_utils import AsyncSitemapParser

        # Parse sitemap
        parser = AsyncSitemapParser(self.config)
        urls = await parser.get_urls_from_sitemap(
            sitemap_url, min_priority=min_priority, limit=limit
        )

        logger.info(f"Found {len(urls)} URLs in sitemap")

        # Scrape all URLs
        return await self.scrape_many(urls, format=format, use_cache=use_cache)

    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._client:
            await self._client.close()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience functions
async def scrape_to_markdown(
    url: str, config: Optional[MarkdownLabConfig] = None, **kwargs
) -> str:
    """
    Convenience function to scrape a single URL to Markdown.

    Args:
        url: URL to scrape
        config: Optional configuration
        **kwargs: Additional arguments passed to scraper

    Returns:
        Markdown content
    """
    async with AsyncMarkdownScraper(config) as scraper:
        return await scraper.scrape_to_markdown(url, **kwargs)


async def scrape_to_json(
    url: str, config: Optional[MarkdownLabConfig] = None, **kwargs
) -> Dict:
    """
    Convenience function to scrape a single URL to JSON.

    Args:
        url: URL to scrape
        config: Optional configuration
        **kwargs: Additional arguments passed to scraper

    Returns:
        JSON data
    """
    async with AsyncMarkdownScraper(config) as scraper:
        return await scraper.scrape_to_json(url, **kwargs)


async def scrape_many(
    urls: List[str],
    format: str = "markdown",
    config: Optional[MarkdownLabConfig] = None,
    **kwargs,
) -> Dict[str, Union[str, Dict]]:
    """
    Convenience function to scrape multiple URLs concurrently.

    Args:
        urls: List of URLs to scrape
        format: Output format
        config: Optional configuration
        **kwargs: Additional arguments passed to scraper

    Returns:
        Dictionary mapping URLs to content
    """
    async with AsyncMarkdownScraper(config) as scraper:
        return await scraper.scrape_many(urls, format=format, **kwargs)


# Synchronous wrappers for backward compatibility
def scrape_to_markdown_sync(url: str, **kwargs) -> str:
    """Synchronous wrapper for scrape_to_markdown."""
    return asyncio.run(scrape_to_markdown(url, **kwargs))


def scrape_to_json_sync(url: str, **kwargs) -> Dict:
    """Synchronous wrapper for scrape_to_json."""
    return asyncio.run(scrape_to_json(url, **kwargs))


def scrape_many_sync(urls: List[str], **kwargs) -> Dict[str, Union[str, Dict]]:
    """Synchronous wrapper for scrape_many."""
    return asyncio.run(scrape_many(urls, **kwargs))
