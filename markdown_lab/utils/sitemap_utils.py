"""
Utility module for parsing XML sitemaps to map website structure before scraping.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from xml.etree.ElementTree import ParseError

import requests

from markdown_lab.core.throttle import RequestThrottler

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
        requests_per_second: float = 1.0,
        max_retries: int = 3,
        timeout: int = 30,
        respect_robots_txt: bool = True,
    ):
        """
        Initialize the sitemap parser.

        Args:
            requests_per_second: Maximum number of requests per second
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Request timeout in seconds
            respect_robots_txt: Whether to check robots.txt for sitemap location
        """
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        self.throttler = RequestThrottler(requests_per_second)
        self.max_retries = max_retries
        self.timeout = timeout
        self.respect_robots_txt = respect_robots_txt
        self.discovered_urls: List[SitemapURL] = []
        self.processed_sitemaps: Set[str] = set()

    def _make_request(self, url: str) -> Optional[str]:
        """
        Make an HTTP request with retry logic.

        Args:
            url: The URL to request

        Returns:
            The response text or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                self.throttler.throttle()
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except (
                requests.exceptions.RequestException,
                requests.exceptions.HTTPError,
            ) as e:
                logger.warning(
                    f"Request error on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Failed to retrieve {url} after {self.max_retries} attempts"
                    )
                    return None
                time.sleep(2**attempt)  # Exponential backoff
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
        Parse sitemap XML content.

        Args:
            content: The XML content to parse

        Returns:
            Tuple containing list of SitemapURLs and list of sitemap index URLs
        """
        try:
            # Setup XML parsing with namespace support
            namespace = self._extract_namespace(content)
            ns_map = {"sm": namespace} if namespace else {}
            root = ET.fromstring(content)
            
            # Determine if this is a sitemap index or a regular sitemap
            if root.tag.endswith("sitemapindex"):
                return self._handle_sitemap_index(root, namespace, ns_map)
            else:
                return self._handle_sitemap(root, namespace, ns_map)
                
        except ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return [], []
        except Exception as e:
            logger.error(f"Error parsing sitemap XML: {e}")
            return [], []
            
    def _extract_namespace(self, content: str) -> Optional[str]:
        """Extract XML namespace from content."""
        ns_match = re.search(r'xmlns\s*=\s*["\']([^"\']+)["\']', content)
        return ns_match[1] if ns_match else None
        
    def _handle_sitemap_index(self, root: ET.Element, namespace: Optional[str], ns_map: Dict[str, str]) -> Tuple[List[SitemapURL], List[str]]:
        """Process a sitemap index, extracting child sitemap URLs."""
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
        
    def _handle_sitemap(self, root: ET.Element, namespace: Optional[str], ns_map: Dict[str, str]) -> Tuple[List[SitemapURL], List[str]]:
        """Process a regular sitemap, extracting URLs and their metadata."""
        sitemap_urls = []
        
        for url in root.findall(".//sm:url" if namespace else ".//url", ns_map):
            if sitemap_url := self._extract_url_data(url, namespace, ns_map):
                sitemap_urls.append(sitemap_url)
                
        logger.info(f"Parsed sitemap with {len(sitemap_urls)} URLs")
        return sitemap_urls, []
        
    def _extract_url_data(self, url_elem: ET.Element, namespace: Optional[str], ns_map: Dict[str, str]) -> Optional[SitemapURL]:
        """Extract data for a single URL from a sitemap."""
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
        
    def _get_element_text(self, parent: ET.Element, element_name: str, namespace: Optional[str], ns_map: Dict[str, str]) -> Optional[str]:
        """Get text from a child element if it exists."""
        prefixed_name = f"sm:{element_name}" if namespace else element_name
        elem = parent.find(prefixed_name, ns_map)
        return elem.text.strip() if elem is not None and elem.text else None
        
    def _get_priority(self, url_elem: ET.Element, namespace: Optional[str], ns_map: Dict[str, str]) -> Optional[float]:
        """Extract and convert priority value."""
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
    Convenience function to discover and filter URLs from a website.

    Args:
        base_url: The base URL of the website
        min_priority: Minimum priority value (0.0-1.0)
        include_patterns: List of regex patterns to include
        exclude_patterns: List of regex patterns to exclude
        limit: Maximum number of URLs to return
        respect_robots_txt: Whether to check robots.txt for sitemap location

    Returns:
        List of filtered URL strings
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