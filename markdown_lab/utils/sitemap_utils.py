"""
Utility module for parsing XML sitemaps to map website structure before scraping.
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from xml.etree.ElementTree import ParseError

from markdown_lab.core.client import HttpClient
from markdown_lab.core.config import MarkdownLabConfig, get_config
from markdown_lab.core.errors import NetworkError, retry_with_backoff

logger = logging.getLogger("sitemap_parser")


@dataclass
class SitemapURL:
    """Represents a URL entry from a sitemap."""

    loc: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None


class SitemapParser:
    """Parser for XML sitemaps that discovers and extracts URLs from a website."""

    def __init__(
        self,
        config: Optional[MarkdownLabConfig] = None,
        requests_per_second: Optional[float] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        respect_robots_txt: bool = True,
    ):
        """
        Initialize the sitemap parser with centralized configuration.

        Args:
            config: Optional MarkdownLabConfig instance. Uses default if not provided.
            requests_per_second: Override requests per second (deprecated, use config)
            max_retries: Override max retries (deprecated, use config)
            timeout: Override timeout (deprecated, use config)
            respect_robots_txt: Whether to check robots.txt for sitemap location
        """
        # Use provided config or get default, with optional parameter overrides for backward compatibility
        self.config = config or get_config()

        # Apply parameter overrides to config if provided (for backward compatibility)
        if requests_per_second is not None:
            self.config.requests_per_second = requests_per_second
        if max_retries is not None:
            self.config.max_retries = max_retries
        if timeout is not None:
            self.config.timeout = timeout

        # Use unified HTTP client instead of creating separate session and throttler
        self.client = HttpClient(self.config)
        self.respect_robots_txt = respect_robots_txt
        self.discovered_urls: List[SitemapURL] = []
        self.processed_sitemaps: Set[str] = set()

    def _make_single_request(self, url: str) -> str:
        """Make a single HTTP request using the unified client."""
        return self.client.get(url)

    def _make_request(self, url: str) -> Optional[str]:
        """
        Make an HTTP request with retry logic.

        Uses the centralized retry mechanism but returns None instead of raising
        exceptions to maintain compatibility with sitemap discovery logic.

        Args:
            url: The URL to request

        Returns:
            The response text or None if failed
        """
        try:
            return retry_with_backoff(
                self._make_single_request, self.config.max_retries, url, url
            )
        except NetworkError:
            # Sitemap parsing should continue even if individual requests fail
            return None

    def _find_sitemaps_in_robots(self, base_url: str) -> List[str]:
        """
        Find sitemap URLs in robots.txt.

        Args:
            base_url: The base URL of the website

        Returns:
            List of sitemap URLs found
        """
        parsed_url = urlparse(base_url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

        logger.info(f"Checking robots.txt at {robots_url}")
        robots_content = self._make_request(robots_url)

        if not robots_content:
            logger.warning(f"Could not retrieve robots.txt from {robots_url}")
            return []

        sitemap_urls = []
        for line in robots_content.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_url = line[8:].strip()
                sitemap_urls.append(sitemap_url)

        if sitemap_urls:
            logger.info(f"Found {len(sitemap_urls)} sitemaps in robots.txt")
        else:
            logger.info("No sitemaps found in robots.txt")

        return sitemap_urls

    def _parse_sitemap_xml(self, content: str) -> Tuple[List[SitemapURL], List[str]]:
        """
        Parses XML sitemap content and extracts URLs and sitemap index references.

        Args:
            content: The XML sitemap content as a string.

        Returns:
            A tuple containing a list of SitemapURL objects and a list of sitemap index URLs.
        """
        try:
            # Setup XML parsing with namespace support
            namespace = self._extract_namespace(content)
            ns_map = {"sm": namespace} if namespace else {}
            root = ET.fromstring(content)

            # Determine if this is a sitemap index or a regular sitemap
            if root.tag.endswith("sitemapindex"):
                return self._handle_sitemap_index(root, namespace, ns_map)
            return self._handle_sitemap(root, namespace, ns_map)

        except ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return [], []
        except Exception as e:
            logger.error(f"Error parsing sitemap XML: {e}")
            return [], []

    def _extract_namespace(self, content: str) -> Optional[str]:
        """
        Extracts the XML namespace URI from the given XML content string.

        Args:
            content: The XML content as a string.

        Returns:
            The namespace URI if found, otherwise None.
        """
        ns_match = re.search(r'xmlns\s*=\s*["\']([^"\']+)["\']', content)
        return ns_match[1] if ns_match else None

    def _handle_sitemap_index(
        self, root: ET.Element, namespace: Optional[str], ns_map: Dict[str, str]
    ) -> Tuple[List[SitemapURL], List[str]]:
        """
        Extracts sitemap URLs from a sitemap index XML element.

        Returns:
            A tuple containing an empty list of SitemapURL objects and a list of sitemap index URLs found within the sitemap index.
        """
        sitemap_index_urls = [
            sitemap.text.strip()
            for sitemap in root.findall(
                ".//sm:sitemap/sm:loc" if namespace else ".//sitemap/loc",
                ns_map,
            )
            if sitemap is not None and sitemap.text is not None
        ]

        logger.info(f"Found sitemap index with {len(sitemap_index_urls)} sitemaps")
        return [], sitemap_index_urls

    def _handle_sitemap(
        self, root: ET.Element, namespace: Optional[str], ns_map: Dict[str, str]
    ) -> Tuple[List[SitemapURL], List[str]]:
        """
        Extracts URLs and associated metadata from a regular sitemap XML element.

        Args:
            root: The root XML element of the sitemap.
            namespace: The XML namespace URI, if present.
            ns_map: Mapping of XML namespace prefixes to URIs.

        Returns:
            A tuple containing a list of SitemapURL objects extracted from the sitemap and an empty list (since regular sitemaps do not contain sitemap indices).
        """
        sitemap_urls = []

        for url in root.findall(".//sm:url" if namespace else ".//url", ns_map):
            if sitemap_url := self._extract_url_data(url, namespace, ns_map):
                sitemap_urls.append(sitemap_url)

        logger.info(f"Parsed sitemap with {len(sitemap_urls)} URLs")
        return sitemap_urls, []

    def _extract_url_data(
        self, url_elem: ET.Element, namespace: Optional[str], ns_map: Dict[str, str]
    ) -> Optional[SitemapURL]:
        """
        Extracts URL location and metadata from a sitemap URL element.

        Parses a single <url> element from a sitemap XML, retrieving the URL, last modified date, change frequency, and priority if available. Returns a SitemapURL object or None if the location is missing.
        """
        loc_elem = url_elem.find("sm:loc" if namespace else "loc", ns_map)
        if loc_elem is None or not loc_elem.text:
            return None

        url_loc = loc_elem.text.strip()
        lastmod = self._get_element_text(url_elem, "lastmod", namespace, ns_map)
        changefreq = self._get_element_text(url_elem, "changefreq", namespace, ns_map)
        priority = self._get_priority(url_elem, namespace, ns_map)

        return SitemapURL(
            loc=url_loc,
            lastmod=lastmod,
            changefreq=changefreq,
            priority=priority,
        )

    def _get_element_text(
        self,
        parent: ET.Element,
        element_name: str,
        namespace: Optional[str],
        ns_map: Dict[str, str],
    ) -> Optional[str]:
        """
        Retrieves the stripped text content of a specified child element, considering XML namespace.

        Args:
            parent: The parent XML element.
            element_name: The name of the child element to search for.
            namespace: The XML namespace URI, if present.
            ns_map: Mapping of namespace prefixes to URIs.

        Returns:
            The stripped text content of the child element, or None if not found or empty.
        """
        prefixed_name = f"sm:{element_name}" if namespace else element_name
        elem = parent.find(prefixed_name, ns_map)
        return elem.text.strip() if elem is not None and elem.text else None

    def _get_priority(
        self, url_elem: ET.Element, namespace: Optional[str], ns_map: Dict[str, str]
    ) -> Optional[float]:
        """
        Extracts the priority value from a sitemap URL element as a float.

        Returns:
            The priority as a float if present and valid, otherwise None.
        """
        priority_text = self._get_element_text(url_elem, "priority", namespace, ns_map)
        if not priority_text:
            return None

        try:
            return float(priority_text)
        except (ValueError, TypeError):
            return None

    def _process_sitemap(self, sitemap_url: str) -> List[SitemapURL]:
        """
        Process a sitemap URL, handling both regular sitemaps and sitemap indices.

        Args:
            sitemap_url: The URL of the sitemap to process

        Returns:
            List of SitemapURLs found
        """
        if sitemap_url in self.processed_sitemaps:
            logger.info(f"Already processed sitemap: {sitemap_url}")
            return []

        logger.info(f"Processing sitemap: {sitemap_url}")
        self.processed_sitemaps.add(sitemap_url)

        content = self._make_request(sitemap_url)
        if not content:
            logger.warning(f"Could not retrieve sitemap from {sitemap_url}")
            return []

        urls, sitemap_indices = self._parse_sitemap_xml(content)

        # Process any sitemap indices recursively
        for index_url in sitemap_indices:
            urls.extend(self._process_sitemap(index_url))

        return urls

    def parse_sitemap(self, base_url: str) -> List[SitemapURL]:
        """
        Parse sitemaps for a website and extract all URLs.

        Args:
            base_url: The base URL of the website

        Returns:
            List of SitemapURLs found across all sitemaps
        """
        self.discovered_urls = []
        self.processed_sitemaps = set()
        parsed_url = urlparse(base_url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # List of potential sitemap locations to try
        sitemap_locations = []

        # First check robots.txt if configured to do so
        if self.respect_robots_txt:
            sitemap_locations.extend(self._find_sitemaps_in_robots(base_url))

        # Add common sitemap locations if none found in robots.txt
        if not sitemap_locations:
            sitemap_locations.extend(
                [
                    f"{base_domain}/sitemap.xml",
                    f"{base_domain}/sitemap_index.xml",
                    f"{base_domain}/sitemap/sitemap.xml",
                    f"{base_domain}/sitemaps/sitemap.xml",
                ]
            )

        # Process each potential sitemap
        for sitemap_url in sitemap_locations:
            if urls := self._process_sitemap(sitemap_url):
                logger.info(f"Found {len(urls)} URLs in sitemap {sitemap_url}")
                self.discovered_urls.extend(urls)
                # If we found URLs in this sitemap, we can stop looking
                break

        logger.info(f"Total URLs discovered from sitemaps: {len(self.discovered_urls)}")
        return self.discovered_urls

    def filter_urls(
        self,
        min_priority: Optional[float] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[SitemapURL]:
        """
        Filter the discovered URLs based on various criteria.

        Args:
            min_priority: Minimum priority value (0.0-1.0)
            include_patterns: List of regex patterns to include
            exclude_patterns: List of regex patterns to exclude
            limit: Maximum number of URLs to return

        Returns:
            Filtered list of SitemapURLs
        """
        filtered_urls = self.discovered_urls.copy()

        # Filter by priority
        if min_priority is not None:
            filtered_urls = [
                url
                for url in filtered_urls
                if url.priority is None or url.priority >= min_priority
            ]

        # Filter by inclusion patterns
        if include_patterns:
            include_compiled = [re.compile(pattern) for pattern in include_patterns]
            filtered_urls = [
                url
                for url in filtered_urls
                if any(pattern.search(url.loc) for pattern in include_compiled)
            ]

        # Filter by exclusion patterns
        if exclude_patterns:
            exclude_compiled = [re.compile(pattern) for pattern in exclude_patterns]
            filtered_urls = [
                url
                for url in filtered_urls
                if not any(pattern.search(url.loc) for pattern in exclude_compiled)
            ]

        # Apply limit
        if limit is not None:
            filtered_urls = filtered_urls[:limit]

        logger.info(
            f"Filtered {len(self.discovered_urls)} URLs down to {len(filtered_urls)}"
        )
        return filtered_urls

    def export_urls_to_file(self, urls: List[SitemapURL], output_file: str) -> None:
        """
        Export the list of URLs to a file.

        Args:
            urls: List of SitemapURLs to export
            output_file: Path to the output file
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                for url in urls:
                    priority_str = (
                        f",{url.priority}" if url.priority is not None else ""
                    )
                    lastmod_str = f",{url.lastmod}" if url.lastmod is not None else ""
                    f.write(f"{url.loc}{priority_str}{lastmod_str}\n")

            logger.info(f"Exported {len(urls)} URLs to {output_file}")
        except Exception as e:
            logger.error(f"Error exporting URLs to file: {e}")


def discover_site_urls(
    base_url: str,
    min_priority: Optional[float] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    limit: Optional[int] = None,
    respect_robots_txt: bool = True,
) -> List[str]:
    """
    Discovers and filters URLs from a website's sitemap based on specified criteria.

    Parses the website's sitemap(s), applies filtering by priority and regex patterns, and returns a list of URL strings. Optionally checks robots.txt for sitemap locations.

    Args:
        base_url: The website's base URL to start sitemap discovery.
        min_priority: Minimum priority value (0.0–1.0) for included URLs.
        include_patterns: List of regex patterns; only URLs matching at least one are included.
        exclude_patterns: List of regex patterns; URLs matching any are excluded.
        limit: Maximum number of URLs to return.
        respect_robots_txt: If True, attempts to discover sitemaps via robots.txt.

    Returns:
        A list of URL strings matching the filtering criteria.
    """
    parser = SitemapParser(respect_robots_txt=respect_robots_txt)

    # Parse sitemaps
    parser.parse_sitemap(base_url)

    # Filter URLs
    filtered_urls = parser.filter_urls(
        min_priority=min_priority,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        limit=limit,
    )

    # Extract URL strings
    return [url.loc for url in filtered_urls]
