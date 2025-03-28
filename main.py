import argparse
import hashlib
import logging
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from chunk_utils import ContentChunker, create_semantic_chunks
from sitemap_utils import SitemapParser
from throttle import RequestThrottler

# Configure logging with more detailed formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("markdown_scraper.log", mode="a"),
    ],
)

logger = logging.getLogger("markdown_scraper")


class RequestCache:
    """Simple cache for HTTP requests to avoid repeated network calls."""
    
    def __init__(self, cache_dir: str = ".request_cache", max_age: int = 3600):
        """
        Initialize the request cache.
        
        Args:
            cache_dir: Directory to store cached responses
            max_age: Maximum age of cached responses in seconds (default: 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = max_age
        self.memory_cache: Dict[str, Tuple[str, float]] = {}  # url -> (content, timestamp)
        
    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from a URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_path(self, url: str) -> Path:
        """Get the path to the cache file for a URL."""
        key = self._get_cache_key(url)
        return self.cache_dir / key
    
    def get(self, url: str) -> Optional[str]:
        """
        Get a cached response for a URL if it exists and is not expired.
        
        Args:
            url: The URL to get from cache
            
        Returns:
            The cached content or None if not in cache or expired
        """
        # First check memory cache
        if url in self.memory_cache:
            content, timestamp = self.memory_cache[url]
            if time.time() - timestamp <= self.max_age:
                return content
            # Remove expired item from memory cache
            del self.memory_cache[url]
        
        # Check disk cache
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            # Check if cache is expired
            if time.time() - cache_path.stat().st_mtime <= self.max_age:
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Add to memory cache
                    self.memory_cache[url] = (content, time.time())
                    return content
                except IOError:
                    pass
            
            # Remove expired cache file
            try:
                cache_path.unlink()
            except OSError:
                pass
                
        return None
    
    def set(self, url: str, content: str) -> None:
        """
        Cache a response for a URL.
        
        Args:
            url: The URL to cache
            content: The content to cache
        """
        # Update memory cache
        self.memory_cache[url] = (content, time.time())
        
        # Update disk cache
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(content)
        except IOError as e:
            logging.warning(f"Failed to save response to cache: {e}")
    
    def clear(self, max_age: Optional[int] = None) -> int:
        """
        Clear expired cache entries.
        
        Args:
            max_age: Maximum age in seconds (defaults to instance max_age)
            
        Returns:
            Number of cache entries removed
        """
        if max_age is None:
            max_age = self.max_age
            
        # Clear memory cache
        current_time = time.time()
        expired_keys = [
            k for k, (_, timestamp) in self.memory_cache.items() 
            if current_time - timestamp > max_age
        ]
        for k in expired_keys:
            del self.memory_cache[k]
            
        # Clear disk cache
        count = 0
        for cache_file in self.cache_dir.glob("*"):
            if current_time - cache_file.stat().st_mtime > max_age:
                try:
                    cache_file.unlink()
                    count += 1
                except OSError:
                    pass
                    
        return count + len(expired_keys)


class MarkdownScraper:
    """Scrapes websites and converts content to markdown, JSON, or XML with chunking support."""

    def __init__(
        self,
        requests_per_second: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        cache_enabled: bool = True,
        cache_max_age: int = 3600,
    ) -> None:
        """
        Args:
            requests_per_second: Maximum number of requests per second
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
            chunk_size: Maximum size of content chunks in characters
            chunk_overlap: Overlap between consecutive chunks in characters
            cache_enabled: Whether to enable request caching
            cache_max_age: Maximum age of cached responses in seconds
        """
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        self.throttler = RequestThrottler(requests_per_second)
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunker = ContentChunker(chunk_size, chunk_overlap)
        self.requests_per_second = requests_per_second
        
        # Initialize request cache
        self.cache_enabled = cache_enabled
        self.request_cache = RequestCache(max_age=cache_max_age) if cache_enabled else None
        
        # Try to use the Rust implementation if available
        try:
            from markdown_lab_rs import convert_html, OutputFormat
            self.rust_available = True
            self.OutputFormat = OutputFormat
            self.convert_html = convert_html
        except ImportError:
            self.rust_available = False

    def scrape_website(self, url: str, skip_cache: bool = False) -> str:
        """
        Scrape a website with retry logic, rate limiting, and caching.

        Args:
            url: The URL to scrape
            skip_cache: Whether to skip the cache and force a new request

        Returns:
            The HTML content as a string

        Raises:
            requests.exceptions.RequestException: If the request fails after retries
        """
        import time
        import tracemalloc

        import psutil  # type: ignore

        # Check cache first if enabled and not explicitly skipped
        if self.cache_enabled and not skip_cache and self.request_cache is not None:
            cached_content = self.request_cache.get(url)
            if cached_content is not None:
                logger.info(f"Using cached content for {url}")
                return cached_content

        logger.info(f"Attempting to scrape the website: {url}")

        start_time = time.time()
        tracemalloc.start()
        process = psutil.Process()

        for attempt in range(self.max_retries):
            try:
                self.throttler.throttle()
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                logger.info(
                    f"Successfully retrieved the website content (status code: {response.status_code})."
                )

                end_time = time.time()
                execution_time = end_time - start_time
                memory_usage = tracemalloc.get_traced_memory()
                cpu_usage = process.cpu_percent(interval=0.1)
                network_latency = response.elapsed.total_seconds()

                logger.info(
                    f"Execution time for scraping {url}: {execution_time:.2f} seconds"
                )
                logger.info(
                    f"Memory usage for scraping {url}: {memory_usage[1] / 1024 / 1024:.2f} MB"
                )
                logger.info(f"CPU usage for scraping {url}: {cpu_usage:.2f}%")
                logger.info(
                    f"Network latency for scraping {url}: {network_latency:.2f} seconds"
                )

                tracemalloc.stop()
                
                html_content = response.text
                
                # Cache the response if caching is enabled
                if self.cache_enabled and self.request_cache is not None:
                    self.request_cache.set(url, html_content)
                
                return html_content
            except requests.exceptions.HTTPError as http_err:
                logger.warning(
                    f"HTTP error on attempt {attempt+1}/{self.max_retries}: {http_err}"
                )
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Failed to retrieve {url} after {self.max_retries} attempts."
                    )
                    raise
                time.sleep(2**attempt)  # Exponential backoff
            except requests.exceptions.ConnectionError as conn_err:
                logger.warning(
                    f"Connection error on attempt {attempt+1}/{self.max_retries}: {conn_err}"
                )
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Connection error persisted for {url} after {self.max_retries} attempts."
                    )
                    raise
                time.sleep(2**attempt)
            except requests.exceptions.Timeout as timeout_err:
                logger.warning(
                    f"Timeout on attempt {attempt+1}/{self.max_retries}: {timeout_err}"
                )
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Request to {url} timed out after {self.max_retries} attempts."
                    )
                    raise
                time.sleep(2**attempt)
            except Exception as err:
                logger.error(f"An unexpected error occurred: {err}")
                raise

        # This line should never be reached due to the raise statements above,
        # but adding it to satisfy the linter's "missing return statement" warning
        raise requests.exceptions.RequestException(
            f"Failed to retrieve {url} after {self.max_retries} attempts"
        )

    def _get_text_from_element(self, element: Optional[Tag]) -> str:
        """Extract clean text from a BeautifulSoup element."""
        if element is None:
            return ""
        return re.sub(r"\s+", " ", element.get_text().strip())

    def _get_element_markdown(self, element: Tag, base_url: str) -> str:
        """Convert a single HTML element to markdown."""
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(element.name[1])
            return f"{'#' * level} {self._get_text_from_element(element)}"

        elif element.name == "p":
            return self._get_text_from_element(element)

        elif element.name == "a" and element.get("href"):
            href = element.get("href", "")
            # Ensure href is a string
            if isinstance(href, list):
                href = href[0] if href else ""
            if (
                href
                and not href.startswith("http://")
                and not href.startswith("https://")
            ):
                href = urljoin(base_url, href)
            return f"[{self._get_text_from_element(element)}]({href})"

        elif element.name == "img" and element.get("src"):
            src = element.get("src", "")
            # Ensure src is a string
            if isinstance(src, list):
                src = src[0] if src else ""
            if src and not src.startswith("http://") and not src.startswith("https://"):
                src = urljoin(base_url, src)
            alt = element.get("alt", "image")
            return f"![{alt}]({src})"

        elif element.name == "ul":
            items = [
                f"- {self._get_text_from_element(li)}"
                for li in element.find_all("li", recursive=False)
            ]
            return "\n".join(items)

        elif element.name == "ol":
            items = [
                f"{i}. {self._get_text_from_element(li)}"
                for i, li in enumerate(element.find_all("li", recursive=False), 1)
            ]
            return "\n".join(items)

        elif element.name == "blockquote":
            lines = self._get_text_from_element(element).split("\n")
            return "\n".join([f"> {line}" for line in lines])

        elif element.name in ["pre", "code"]:
            code = self._get_text_from_element(element)
            lang = element.get("class", [""])[0] if element.get("class") else ""
            if lang.startswith("language-"):
                lang = lang[9:]
            return f"```{lang}\n{code}\n```"

        else:
            return self._get_text_from_element(element)

    def convert_to_markdown(self, html_content: str, url: str = "") -> str:
        """
        Convert HTML content to well-structured Markdown.

        Args:
            html_content: The HTML content to convert
            url: The source URL for resolving relative links

        Returns:
            The converted Markdown content
        """
        logger.info("Converting HTML content to Markdown.")
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract base URL for resolving relative links
        base_url_str = url
        base_tag = soup.find("base")
        if (
            not base_url_str
            and base_tag
            and isinstance(base_tag, Tag)
            and base_tag.get("href")
        ):
            base_href = base_tag.get("href")
            if isinstance(base_href, list):
                base_href = base_href[0] if base_href else ""
            base_url_str = base_href or base_url_str

        # Ensure we have a string for base_url
        base_url = str(base_url_str) if base_url_str is not None else ""

        # Extract page title
        title = self._get_text_from_element(soup.title) if soup.title else "No Title"

        # Initialize markdown content with the title
        markdown_content = f"# {title}\n\n"

        # Get the main content area (try common content containers)
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id="content")
            or soup.find(class_="content")
            or soup.body
        )

        if main_content and hasattr(main_content, "find_all"):
            # Process each element in the main content
            # Make sure we only process Tag objects
            for element in [
                e
                for e in main_content.find_all(
                    [
                        "h1",
                        "h2",
                        "h3",
                        "h4",
                        "h5",
                        "h6",
                        "p",
                        "ul",
                        "ol",
                        "blockquote",
                        "pre",
                        "img",
                    ],
                    recursive=True,
                )
                if isinstance(e, Tag)
            ]:
                if element_markdown := self._get_element_markdown(element, base_url):
                    markdown_content += element_markdown + "\n\n"

        logger.info("Conversion to Markdown completed.")
        return markdown_content.strip()

    def save_content(self, content: str, output_file: str) -> None:
        """
        Save content to a file.

        Args:
            content: The content to save (markdown, JSON, or XML)
            output_file: The output file path
        """
        try:
            # Create directories if they don't exist
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"File '{output_file}' has been created successfully.")
        except IOError as e:
            logger.error(f"Failed to save content to {output_file}: {e}")
            raise
            
    def save_markdown(self, markdown_content: str, output_file: str) -> None:
        """
        Save markdown content to a file (legacy method).

        Args:
            markdown_content: The markdown content to save
            output_file: The output file path
        """
        self.save_content(markdown_content, output_file)

    def create_chunks(self, markdown_content: str, source_url: str):
        """
        Create chunks from the markdown content using the chunk_utils module.

        Args:
            markdown_content: The markdown content to chunk
            source_url: The source URL of the content

        Returns:
            List of chunks for RAG
        """
        return create_semantic_chunks(
            content=markdown_content,
            source_url=source_url,
            chunk_size=self.chunker.chunk_size,
            chunk_overlap=self.chunker.chunk_overlap,
        )

    def save_chunks(self, chunks, output_dir, output_format="jsonl"):
        """
        Save content chunks using the chunk_utils module.

        Args:
            chunks: The chunks to save
            output_dir: Directory to save chunks to
            output_format: Format to save chunks (json or jsonl)
        """
        self.chunker.save_chunks(chunks, output_dir, output_format)

    def scrape_by_sitemap(
        self,
        base_url: str,
        output_dir: str,
        min_priority: Optional[float] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        save_chunks: bool = True,
        chunk_dir: Optional[str] = None,
        chunk_format: str = "jsonl",
        output_format: str = "markdown",
    ) -> List[str]:
        """
        Scrape multiple pages from a website based on its sitemap.

        Args:
            base_url: The base URL of the website
            output_dir: Directory to save markdown files
            min_priority: Minimum priority value for URLs (0.0-1.0)
            include_patterns: List of regex patterns to include
            exclude_patterns: List of regex patterns to exclude
            limit: Maximum number of URLs to scrape
            save_chunks: Whether to save chunks for RAG
            chunk_dir: Directory to save chunks (defaults to output_dir/chunks)
            chunk_format: Format to save chunks (json or jsonl)

        Returns:
            List of successfully scraped URLs
        """
        # Create sitemap parser
        sitemap_parser = SitemapParser(
            requests_per_second=self.requests_per_second,
            max_retries=self.max_retries,
            timeout=self.timeout,
        )

        # Parse sitemap and get filtered URLs
        logger.info(f"Discovering URLs from sitemap for {base_url}")
        sitemap_parser.parse_sitemap(base_url)
        filtered_urls = sitemap_parser.filter_urls(
            min_priority=min_priority,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            limit=limit,
        )

        # If no URLs were found, return empty list
        if not filtered_urls:
            logger.warning(f"No URLs found in sitemap for {base_url}")
            return []

        logger.info(f"Found {len(filtered_urls)} URLs to scrape from sitemap")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Set up chunk directory if chunking is enabled
        if save_chunks:
            if chunk_dir is None:
                chunk_dir = str(output_path / "chunks")
            Path(chunk_dir).mkdir(parents=True, exist_ok=True)

        # Scrape each URL
        successfully_scraped = []
        for i, url_info in enumerate(filtered_urls):
            url = url_info.loc
            try:
                # Create filename from URL
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.strip("/").split("/")
                if not path_parts or path_parts[0] == "":
                    filename = "index"
                else:
                    filename = "_".join(path_parts)

                # Remove or replace invalid characters
                filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
                if not filename.endswith(".md"):
                    filename += ".md"

                # Ensure correct file extension based on output format
                output_ext = f".{output_format}"
                if not filename.endswith(output_ext):
                    filename = filename.rsplit(".", 1)[0] + output_ext
                    
                output_file = str(output_path / filename)

                # Scrape and convert the page
                logger.info(f"Scraping URL {i+1}/{len(filtered_urls)}: {url}")
                html_content = self.scrape_website(url, skip_cache=False)
                
                # Convert based on output format
                if self.rust_available:
                    # Use Rust implementation if available
                    rust_format = getattr(self.OutputFormat, output_format.upper())
                    content = self.convert_html(html_content, url, rust_format)
                    markdown_content = self.convert_html(html_content, url, self.OutputFormat.MARKDOWN) if output_format != "markdown" else content
                else:
                    # Fall back to Python implementation
                    if output_format == "markdown":
                        content = self.convert_to_markdown(html_content, url)
                        markdown_content = content
                    else:
                        # For JSON and XML, first convert to markdown
                        markdown_content = self.convert_to_markdown(html_content, url)
                        
                        # Then convert to the requested format
                        try:
                            # Try to use functions from markdown_lab_rs for conversion
                            from markdown_lab_rs import parse_markdown_to_document, document_to_xml
                            document = parse_markdown_to_document(markdown_content, url)
                            
                            if output_format == "json":
                                import json
                                content = json.dumps(document, indent=2)
                            elif output_format == "xml":
                                content = document_to_xml(document)
                        except ImportError:
                            # Fallback to markdown if conversion functions are not available
                            logger.warning(f"Could not convert to {output_format}, using markdown instead")
                            content = markdown_content
                            output_file = output_file.replace(f".{output_format}", ".md")
                
                # Save the content
                self.save_content(content, output_file)

                # Create and save chunks if enabled (always from markdown content)
                if save_chunks:
                    chunks = self.create_chunks(markdown_content, url)
                    # Create URL-specific chunk directory to prevent filename collisions
                    url_chunk_dir = f"{chunk_dir}/{filename.split('.')[-2]}"
                    self.save_chunks(chunks, url_chunk_dir, chunk_format)

                successfully_scraped.append(url)

            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                continue

        logger.info(
            f"Successfully scraped {len(successfully_scraped)}/{len(filtered_urls)} URLs"
        )
        return successfully_scraped


def main(
    url: str,
    output_file: str,
    output_format: str = "markdown",
    save_chunks: bool = True,
    chunk_dir: str = "chunks",
    chunk_format: str = "jsonl",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    requests_per_second: float = 1.0,
    use_sitemap: bool = False,
    min_priority: Optional[float] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    limit: Optional[int] = None,
    cache_enabled: bool = True,
    cache_max_age: int = 3600,
    skip_cache: bool = False,
) -> None:
    """
    Main entry point for the scraper.

    Args:
        url: The URL to scrape
        output_file: Path to save the output
        output_format: Format of the output (markdown, json, or xml)
        save_chunks: Whether to save chunks for RAG
        chunk_dir: Directory to save chunks
        chunk_format: Format to save chunks (json or jsonl)
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        requests_per_second: Maximum number of requests per second
        use_sitemap: Whether to use sitemap.xml for discovering URLs
        min_priority: Minimum priority value for sitemap URLs
        include_patterns: Regex patterns for URLs to include
        exclude_patterns: Regex patterns for URLs to exclude
        limit: Maximum number of URLs to scrape from sitemap
        cache_enabled: Whether to enable request caching
        cache_max_age: Maximum age of cached responses in seconds
        skip_cache: Whether to skip the cache and force new requests
    """
    # Validate output format
    output_format = output_format.lower()
    if output_format not in ["markdown", "json", "xml"]:
        logger.warning(f"Invalid output format: {output_format}. Using markdown instead.")
        output_format = "markdown"
    
    # Try to use the optimized Rust implementation if available
    try:
        from markdown_lab_rs import convert_html, OutputFormat
        use_rust = True
        if output_format == "json":
            rust_format = OutputFormat.JSON
        elif output_format == "xml":
            rust_format = OutputFormat.XML
        else:
            rust_format = OutputFormat.MARKDOWN
    except ImportError:
        use_rust = False
    
    scraper = MarkdownScraper(
        requests_per_second=requests_per_second,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        cache_enabled=cache_enabled,
        cache_max_age=cache_max_age,
    )

    try:
        if use_sitemap:
            # Parse base URL
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # Get output directory from output_file
            output_path = Path(output_file)
            output_dir = (
                str(output_path.parent) if output_path.is_file() else output_file
            )
            # Scrape by sitemap
            logger.info(f"Scraping website using sitemap: {base_url}")
            
            # Update the sitemap scraper to handle different output formats
            # This is simplified - in a real implementation you'd refactor
            # scrape_by_sitemap to handle different output formats
            scraper.scrape_by_sitemap(
                base_url=base_url,
                output_dir=output_dir,
                min_priority=min_priority,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                limit=limit,
                save_chunks=save_chunks,
                chunk_dir=chunk_dir,
                chunk_format=chunk_format,
                output_format=output_format,
            )
        else:
            # Single URL scrape
            html_content = scraper.scrape_website(url, skip_cache=skip_cache)
            
            # Use the appropriate conversion based on format
            if use_rust:
                # Use the Rust implementation if available
                content = convert_html(html_content, url, rust_format)
            else:
                # Fall back to Python implementation
                if output_format == "markdown":
                    content = scraper.convert_to_markdown(html_content, url)
                else:
                    # For JSON and XML, first convert to markdown
                    markdown_content = scraper.convert_to_markdown(html_content, url)
                    if output_format == "json":
                        from markdown_lab_rs import parse_markdown_to_document
                        document = parse_markdown_to_document(markdown_content, url)
                        import json
                        content = json.dumps(document, indent=2)
                    elif output_format == "xml":
                        from markdown_lab_rs import parse_markdown_to_document, document_to_xml
                        document = parse_markdown_to_document(markdown_content, url)
                        content = document_to_xml(document)
            
            # Make sure the output file has the correct extension
            if not output_file.endswith(f".{output_format}"):
                base_output = output_file.rsplit(".", 1)[0] if "." in output_file else output_file
                output_file = f"{base_output}.{output_format}"
            
            # Save the content
            scraper.save_content(content, output_file)

            # Only create chunks from markdown content
            if save_chunks:
                if output_format != "markdown" and use_rust:
                    # If we're using Rust and not outputting markdown, we need to get markdown first
                    markdown_content = convert_html(html_content, url, OutputFormat.MARKDOWN)
                elif output_format != "markdown":
                    # If we're not using Rust, we already have markdown_content from above
                    pass
                else:
                    # If output_format is markdown, content is already markdown
                    markdown_content = content
                
                chunks = scraper.create_chunks(markdown_content, url)
                scraper.save_chunks(chunks, chunk_dir, chunk_format)

        logger.info(f"Process completed successfully. Output saved in {output_format} format.")
    except Exception as e:
        logger.error(f"An error occurred during the process: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape a website and convert it to Markdown, JSON, or XML with RAG chunking support."
    )
    parser.add_argument("url", type=str, help="The URL to scrape")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output.md",
        help="The output file name",
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=["markdown", "json", "xml"],
        default="markdown",
        help="Output format (markdown, json, or xml)",
    )
    parser.add_argument(
        "--save-chunks", action="store_true", help="Save content chunks for RAG"
    )
    parser.add_argument(
        "--chunk-dir",
        type=str,
        default="chunks",
        help="Directory to save content chunks",
    )
    parser.add_argument(
        "--chunk-format",
        type=str,
        choices=["json", "jsonl"],
        default="jsonl",
        help="Format to save chunks",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=1000, help="Maximum chunk size in characters"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Overlap between chunks in characters",
    )
    parser.add_argument(
        "--requests-per-second",
        type=float,
        default=1.0,
        help="Maximum requests per second",
    )
    parser.add_argument(
        "--use-sitemap", action="store_true", help="Use sitemap.xml to discover URLs"
    )
    parser.add_argument(
        "--min-priority", type=float, help="Minimum priority for sitemap URLs (0.0-1.0)"
    )
    parser.add_argument(
        "--include", type=str, nargs="+", help="Regex patterns for URLs to include"
    )
    parser.add_argument(
        "--exclude", type=str, nargs="+", help="Regex patterns for URLs to exclude"
    )
    parser.add_argument(
        "--limit", type=int, help="Maximum number of URLs to scrape from sitemap"
    )
    parser.add_argument(
        "--no-cache", dest="cache_enabled", action="store_false", 
        help="Disable caching of HTTP requests"
    )
    parser.add_argument(
        "--cache-max-age", type=int, default=3600,
        help="Maximum age of cached responses in seconds (default: 3600)"
    )
    parser.add_argument(
        "--skip-cache", action="store_true",
        help="Skip the cache and force new requests"
    )

    args = parser.parse_args()
    main(
        url=args.url,
        output_file=args.output,
        output_format=args.format,
        save_chunks=args.save_chunks,
        chunk_dir=args.chunk_dir,
        chunk_format=args.chunk_format,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        requests_per_second=args.requests_per_second,
        use_sitemap=args.use_sitemap,
        min_priority=args.min_priority,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        limit=args.limit,
        cache_enabled=args.cache_enabled,
        cache_max_age=args.cache_max_age,
        skip_cache=args.skip_cache,
    )
