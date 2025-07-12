"""
Async sitemap parsing utilities using httpx.

Provides async functionality for discovering and parsing sitemaps to extract URLs
for batch processing.
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import List, Optional

from ..core.config import MarkdownLabConfig
from ..core.errors import NetworkError
from ..network.async_client import AsyncHttpClient

logger = logging.getLogger(__name__)


class AsyncSitemapParser:
    """Async parser for XML sitemaps with support for nested sitemap indices."""

    def __init__(self, config: Optional[MarkdownLabConfig] = None):
        """
        Initialize async sitemap parser.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        if config is None:
            from ..core.config import get_config

            config = get_config()

        self.config = config
        self._client: Optional[AsyncHttpClient] = None

    async def _ensure_client(self) -> AsyncHttpClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = AsyncHttpClient(self.config)
        return self._client

    async def get_urls_from_sitemap(
        self, sitemap_url: str, min_priority: float = 0.0, limit: Optional[int] = None
    ) -> List[str]:
        """
        Extract URLs from a sitemap with filtering options.

        Args:
            sitemap_url: URL of the sitemap
            min_priority: Minimum priority for URLs (0.0-1.0)
            limit: Maximum number of URLs to return

        Returns:
            List of discovered URLs
        """
        try:
            # Try common sitemap locations if base URL provided
            sitemap_url = await self._resolve_sitemap_url(sitemap_url)

            # Fetch and parse sitemap
            client = await self._ensure_client()
            content = await client.get(sitemap_url)

            # Parse XML
            urls = await self._parse_sitemap_content(
                content, sitemap_url, min_priority, limit
            )

            logger.info(f"Found {len(urls)} URLs in sitemap {sitemap_url}")
            return urls

        except Exception as e:
            logger.error(f"Failed to parse sitemap {sitemap_url}: {e}")
            raise NetworkError(
                "Failed to parse sitemap",
                url=sitemap_url,
                error_code="SITEMAP_PARSE_ERROR",
            ) from e

    async def _resolve_sitemap_url(self, url: str) -> str:
        """
        Resolve sitemap URL from base URL or direct sitemap URL.

        Args:
            url: Base URL or sitemap URL

        Returns:
            Resolved sitemap URL
        """
        # If already looks like a sitemap URL, return as-is
        if url.endswith(".xml") or "sitemap" in url.lower():
            return url

        # Try common sitemap locations
        base_url = url.rstrip("/")
        sitemap_urls = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemap-index.xml",
            f"{base_url}/sitemap1.xml",
        ]

        client = await self._ensure_client()

        # Try each URL
        for sitemap_url in sitemap_urls:
            try:
                response = await client.head(sitemap_url)
                if response.status_code == 200:
                    logger.debug(f"Found sitemap at {sitemap_url}")
                    return sitemap_url
            except NetworkError:
                continue

        # Default to first option if none found
        logger.warning(f"No sitemap found, trying {sitemap_urls[0]}")
        return sitemap_urls[0]

    async def _parse_sitemap_content(
        self, content: str, base_url: str, min_priority: float, limit: Optional[int]
    ) -> List[str]:
        """
        Parse sitemap XML content and extract URLs.

        Args:
            content: XML content
            base_url: Base URL for resolving relative URLs
            min_priority: Minimum priority filter
            limit: Maximum URLs to return

        Returns:
            List of URLs
        """
        try:
            root = ET.fromstring(content)

            # Detect sitemap type
            if "sitemapindex" in root.tag:
                # This is a sitemap index
                return await self._parse_sitemap_index(
                    root, base_url, min_priority, limit
                )
            # Regular sitemap
            return self._parse_urlset(root, min_priority, limit)

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            raise NetworkError(
                "Invalid sitemap XML", url=base_url, error_code="XML_PARSE_ERROR"
            ) from e

    async def _parse_sitemap_index(
        self, root: ET.Element, base_url: str, min_priority: float, limit: Optional[int]
    ) -> List[str]:
        """
        Parse sitemap index and fetch nested sitemaps.

        Args:
            root: XML root element
            base_url: Base URL
            min_priority: Priority filter
            limit: URL limit

        Returns:
            Aggregated list of URLs from all sitemaps
        """
        all_urls = []
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Extract nested sitemap URLs
        sitemap_urls = []
        for sitemap in root.findall("ns:sitemap", namespace):
            loc = sitemap.find("ns:loc", namespace)
            if loc is not None and loc.text:
                sitemap_urls.append(loc.text.strip())

        logger.debug(f"Found {len(sitemap_urls)} nested sitemaps")

        # Fetch nested sitemaps concurrently
        client = await self._ensure_client()
        tasks = []

        for sitemap_url in sitemap_urls:
            if limit and len(all_urls) >= limit:
                break

            task = self._fetch_and_parse_sitemap(
                client,
                sitemap_url,
                min_priority,
                limit - len(all_urls) if limit else None,
            )
            tasks.append(task)

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_urls.extend(result)
                if limit and len(all_urls) >= limit:
                    all_urls = all_urls[:limit]
                    break
            else:
                logger.warning(f"Failed to parse nested sitemap: {result}")

        return all_urls

    async def _fetch_and_parse_sitemap(
        self,
        client: AsyncHttpClient,
        url: str,
        min_priority: float,
        limit: Optional[int],
    ) -> List[str]:
        """Fetch and parse a single sitemap."""
        try:
            content = await client.get(url)
            root = ET.fromstring(content)
            return self._parse_urlset(root, min_priority, limit)
        except Exception as e:
            logger.error(f"Failed to parse sitemap {url}: {e}")
            return []

    def _parse_urlset(
        self, root: ET.Element, min_priority: float, limit: Optional[int]
    ) -> List[str]:
        """
        Parse standard urlset sitemap.

        Args:
            root: XML root element
            min_priority: Priority filter
            limit: URL limit

        Returns:
            List of URLs
        """
        urls = []
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        for url in root.findall("ns:url", namespace):
            # Get URL location
            loc = url.find("ns:loc", namespace)
            if loc is None or not loc.text:
                continue

            # Check priority
            priority = url.find("ns:priority", namespace)
            if priority is not None and priority.text:
                try:
                    if float(priority.text) < min_priority:
                        continue
                except ValueError:
                    pass

            urls.append(loc.text.strip())

            # Check limit
            if limit and len(urls) >= limit:
                break

        return urls

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.close()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience function
async def get_urls_from_sitemap(
    sitemap_url: str, config: Optional[MarkdownLabConfig] = None, **kwargs
) -> List[str]:
    """
    Convenience function to extract URLs from a sitemap.

    Args:
        sitemap_url: URL of the sitemap
        config: Optional configuration
        **kwargs: Additional arguments passed to parser

    Returns:
        List of URLs
    """
    async with AsyncSitemapParser(config) as parser:
        return await parser.get_urls_from_sitemap(sitemap_url, **kwargs)
