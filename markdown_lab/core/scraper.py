"""
Main module for scraping websites and converting content to markdown, JSON, or XML.

This module provides backwards compatibility with the original MarkdownScraper interface
while using the new simplified Converter architecture internally.
"""

import argparse
import contextlib
import logging
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

import requests

from markdown_lab.core.config import MarkdownLabConfig, get_config
from markdown_lab.core.converter import Converter
from markdown_lab.core.errors import NetworkError, handle_request_exception, retry_with_backoff
from markdown_lab.utils.chunk_utils import ContentChunker
from markdown_lab.utils.sitemap_utils import SitemapParser
from markdown_lab.utils.url_utils import extract_base_url, get_filename_from_url

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


class MarkdownScraper:
    """
    Legacy MarkdownScraper class that provides backwards compatibility.

    This class now uses the simplified Converter architecture internally
    while maintaining the original API for existing code.
    """

    def __init__(self, config: Optional[MarkdownLabConfig] = None) -> None:
        """
        Initialize MarkdownScraper with centralized configuration.

        Args:
            config: Optional MarkdownLabConfig instance. Uses default if not provided.
        """
        # Use provided config or get default
        self.config = config or get_config()
        
        # Initialize the new Converter internally
        self.converter = Converter(self.config)

        # Store parameters for backwards compatibility
        self.requests_per_second = self.config.requests_per_second
        self.timeout = self.config.timeout
        self.max_retries = self.config.max_retries
        self.chunker = ContentChunker(chunk_size=self.config.chunk_size, chunk_overlap=self.config.chunk_overlap)
        self.cache_enabled = self.config.cache_enabled

        # Legacy properties for compatibility
        self.session = self.converter.client.session
        self.rust_available = self.converter.rust_backend.is_available()
        self.OutputFormat = None  # Legacy compatibility
        self.convert_html_to_format = (
            self.converter.rust_backend.convert_html_to_format
            if self.rust_available
            else None
        )

        # Legacy request_cache for backwards compatibility
        self.request_cache = self.converter.client.cache

    def scrape_website(self, url: str, skip_cache: bool = False) -> str:
        """
        Fetches the HTML content of a website with support for caching, rate limiting, and automatic retries.

        Args:
            url: The URL of the website to scrape.
            skip_cache: If True, bypasses the cache and forces a fresh request.

        Returns:
            The HTML content of the requested URL as a string.

        Raises:
            requests.exceptions.RequestException: If all retry attempts fail to retrieve the content.
        """
        # Delegate to the new Converter's HTTP client
        return self.converter.client.get(url, skip_cache=skip_cache)

    def _check_cache(self, url: str, skip_cache: bool) -> Optional[str]:
        """Check if content is available in cache."""
        if self.cache_enabled and not skip_cache and self.request_cache is not None:
            cached_content = self.request_cache.get(url)
            if cached_content is not None:
                logger.info(f"Using cached content for {url}")
                return cached_content
        return None

    def _start_performance_monitoring(self, psutil_available: bool):
        """
        Begins tracking execution time and memory usage for performance monitoring.

        If `psutil` is available, also prepares a process object for CPU usage tracking.

        Args:
            psutil_available: Indicates whether the `psutil` library is available.

        Returns:
            A dictionary containing the start time and, if applicable, a `psutil.Process` object.
        """
        import tracemalloc

        start_time = time.time()
        tracemalloc.start()

        if not psutil_available:
            return {
                "start_time": start_time,
                "process": None,
            }
        import psutil

        process = psutil.Process()
        return {
            "start_time": start_time,
            "process": process,
        }

    def _log_performance_metrics(self, url: str, monitor, psutil_available: bool):
        """
        Logs execution time, memory usage, and CPU usage (if available) for a scraping request.

        Args:
            url: The URL that was scraped.
            monitor: Dictionary containing timing and process monitoring data.
            psutil_available: Indicates if psutil is available for CPU usage tracking.
        """
        import tracemalloc

        end_time = time.time()
        execution_time = end_time - monitor["start_time"]
        memory_usage = tracemalloc.get_traced_memory()

        logger.info(f"Execution time for scraping {url}: {execution_time:.2f} seconds")
        logger.info(
            f"Memory usage for scraping {url}: {memory_usage[1] / 1024 / 1024:.2f} MB"
        )

        if psutil_available and monitor["process"] is not None:
            cpu_usage = monitor["process"].cpu_percent(interval=0.1)
            logger.info(f"CPU usage for scraping {url}: {cpu_usage:.2f}%")

        tracemalloc.stop()

    def _cache_response(self, url: str, content: str) -> None:
        """Cache the response if caching is enabled."""
        if self.cache_enabled and self.request_cache is not None:
            self.request_cache.set(url, content)

    def _make_single_request(self, url: str) -> str:
        """Make a single HTTP request with throttling."""
        self.throttler.throttle()
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        logger.info(
            f"Successfully retrieved the website content (status code: {response.status_code})."
        )
        logger.info(
            f"Network latency: {response.elapsed.total_seconds():.2f} seconds"
        )

        return response.text

    def _fetch_with_retries(self, url: str) -> str:
        """
        Attempts to fetch the content of a URL with retry logic for network-related errors.

        Uses the centralized retry mechanism with exponential backoff for consistent error handling.

        Args:
            url: The URL to fetch.

        Returns:
            The response content as a string.

        Raises:
            NetworkError: If the URL cannot be retrieved after all retries.
        """
        return retry_with_backoff(
            self._make_single_request,
            self.max_retries,
            url,
            url
        )


    def save_content(self, content: str, output_file: str) -> None:
        """
        Save content to a file.

        Args:
            content: The content to save (markdown, JSON, or XML)
            output_file: The output file path
        """
        # Delegate to the Converter
        self.converter.save_content(content, output_file)

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
        # Delegate to the Converter
        return self.converter.create_chunks(markdown_content, source_url)

    def save_chunks(self, chunks, output_dir, output_format="jsonl"):
        """
        Save content chunks using the chunk_utils module.

        Args:
            chunks: The chunks to save
            output_dir: Directory to save chunks to
            output_format: Format to save chunks (json or jsonl)
        """
        self.chunker.save_chunks(chunks, output_dir, output_format)

    def _convert_content(
        self, html_content: str, url: str, output_format: str
    ) -> tuple:
        """
        Converts HTML content to the specified output format and returns both the converted and Markdown versions.

        Args:
            html_content: The HTML content to convert.
            url: The source URL for resolving relative links.
            output_format: The desired output format ("markdown", "json", or "xml").

        Returns:
            A tuple (converted_content, markdown_content), where converted_content is in the requested format and markdown_content is always the Markdown version.
        """
        # Delegate to the Converter
        return self.converter.convert_html(html_content, url, output_format)

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
        Scrapes multiple pages from a website using its sitemap and saves the content in the specified format.

        Filters sitemap URLs by priority and regex patterns, limits the number of pages if specified, and processes each URL by scraping, converting, and saving the content. Optionally creates and saves content chunks for retrieval-augmented generation workflows.

        Args:
            base_url: The root URL of the website whose sitemap will be parsed.
            output_dir: Directory where the scraped content will be saved.
            min_priority: If set, only URLs with a sitemap priority greater than or equal to this value are included.
            include_patterns: Regex patterns; only URLs matching at least one are included.
            exclude_patterns: Regex patterns; URLs matching any are excluded.
            limit: Maximum number of URLs to process.
            save_chunks: If True, splits content into chunks and saves them for downstream use.
            chunk_dir: Directory for saving chunks; defaults to a subdirectory of output_dir if not specified.
            chunk_format: Format for saved chunks ("json" or "jsonl").
            output_format: Output format for scraped content ("markdown", "json", or "xml").

        Returns:
            A list of URLs that were successfully scraped and saved.
        """
        # Delegate to the Converter's sitemap method
        return self.converter.convert_sitemap(
            base_url=base_url,
            output_dir=output_dir,
            output_format=output_format,
            min_priority=min_priority,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            limit=limit,
            save_chunks=save_chunks,
            chunk_dir=chunk_dir,
            chunk_format=chunk_format,
        )

    def _discover_urls_from_sitemap(
        self,
        base_url: str,
        min_priority: Optional[float] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List:
        """
        Parses a sitemap from the given base URL and returns a filtered list of URLs.

        Filters URLs based on minimum priority, inclusion and exclusion patterns, and an optional limit. Returns an empty list if no URLs are found.
        """
        # Create sitemap parser using config
        sitemap_parser = SitemapParser(
            requests_per_second=self.config.requests_per_second,
            max_retries=self.config.max_retries,
            timeout=self.config.timeout,
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

        # If no URLs were found, log warning
        if not filtered_urls:
            logger.warning(f"No URLs found in sitemap for {base_url}")
            return []

        logger.info(f"Found {len(filtered_urls)} URLs to scrape from sitemap")
        return filtered_urls

    def _prepare_directories(
        self, output_dir: str, save_chunks: bool, chunk_dir: Optional[str] = None
    ) -> Tuple[Path, Optional[str]]:
        """
        Creates the output directory and, if chunking is enabled, creates the chunk directory.

        Args:
            output_dir: Path to the main output directory.
            save_chunks: Whether to create a directory for content chunks.
            chunk_dir: Optional path for the chunk directory; defaults to 'chunks' within the output directory if not provided.

        Returns:
            A tuple containing the Path object for the output directory and the path to the chunk directory (or None if not used).
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Set up chunk directory if chunking is enabled
        chunk_directory = None
        if save_chunks:
            if chunk_dir is None:
                chunk_directory = str(output_path / "chunks")
            else:
                chunk_directory = chunk_dir
            Path(chunk_directory).mkdir(parents=True, exist_ok=True)

        return output_path, chunk_directory


    def _process_single_url(
        self,
        url: str,
        index: int,
        total: int,
        output_path: Path,
        output_format: str,
        save_chunks: bool,
        chunk_dir: Optional[str],
        chunk_format: str,
    ) -> None:
        """
        Scrapes a single URL, converts its content to the specified format, saves the result, and optionally creates and saves content chunks.

        Args:
            url: The URL to scrape.
            index: The index of the URL in the current batch.
            total: The total number of URLs being processed.
            output_path: Directory path where the output file will be saved.
            output_format: Desired output format ('markdown', 'json', or 'xml').
            save_chunks: Whether to generate and save content chunks.
            chunk_dir: Directory where chunks will be saved, if enabled.
            chunk_format: Format for saved chunks (e.g., 'jsonl').
        """
        # Generate filename for this URL
        filename = get_filename_from_url(url, output_format)
        output_file = str(output_path / filename)

        # Scrape and convert the page
        logger.info(f"Scraping URL {index+1}/{total}: {url}")
        html_content = self.scrape_website(url, skip_cache=False)

        # Convert based on output format using the helper method
        content, markdown_content = self._convert_content(
            html_content, url, output_format
        )

        # Check if we had to fall back to markdown
        if output_format != "markdown" and content == markdown_content:
            output_file = output_file.replace(f".{output_format}", ".md")

        # Save the content
        self.save_content(content, output_file)

        # Create and save chunks if enabled (always from markdown content)
        if save_chunks and chunk_dir:
            self._process_chunks(
                markdown_content, url, chunk_dir, filename, chunk_format
            )

    def _process_chunks(
        self,
        markdown_content: str,
        url: str,
        chunk_dir: str,
        filename: str,
        chunk_format: str,
    ) -> None:
        """
        Splits Markdown content from a single document into semantic chunks and saves them to a URL-specific directory in the specified format.

        Args:
            markdown_content: The Markdown content to be chunked.
            url: The source URL of the content.
            chunk_dir: The base directory where chunks will be saved.
            filename: The filename used to derive a unique subdirectory for the chunks.
            chunk_format: The format in which to save the chunks (e.g., "jsonl").
        """
        chunks = self.create_chunks(markdown_content, url)

        # Create URL-specific chunk directory to prevent filename collisions
        from pathlib import (
            Path,  # Ensure import is present (safe to add multiple times)
        )

        url_chunk_dir = f"{chunk_dir}/{Path(filename).stem}"
        self.save_chunks(chunks, url_chunk_dir, chunk_format)

    def scrape_by_links_file(
        self,
        links_file: str,
        output_dir: str,
        save_chunks: bool = True,
        chunk_dir: Optional[str] = None,
        chunk_format: str = "jsonl",
        output_format: str = "markdown",
        parallel: bool = False,
        max_workers: int = 4,
    ) -> List[str]:
        """
        Scrapes multiple web pages from a list of URLs provided in a file and saves the results.

        Reads URLs from the specified file, processes each URL to scrape and convert its content, and saves the output in the desired format. Supports optional parallel processing and chunked content saving for RAG workflows. Returns a list of successfully scraped URLs; logs and skips URLs that fail to process.
        """
        # Check if links_file exists, if not try the default location
        if not Path(links_file).exists():
            default_path = "links.txt"
            if Path(default_path).exists():
                logger.info(
                    f"Specified links file '{links_file}' not found, using default '{default_path}'"
                )
                links_file = default_path
            else:
                logger.error(
                    f"Links file '{links_file}' not found and no default 'links.txt' exists"
                )
                return []

        # Read links from file
        try:
            with open(links_file, "r", encoding="utf-8") as f:
                links = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
        except FileNotFoundError:
            logger.error(f"Links file '{links_file}' not found.")
            return []
        except PermissionError:
            logger.error(f"Permission denied when trying to read '{links_file}'.")
            return []
        except UnicodeDecodeError:
            logger.error(
                f"Encoding error when reading '{links_file}'. Please ensure the file is UTF-8 encoded."
            )
            return []
        except IOError as e:
            logger.error(f"I/O error when reading '{links_file}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error reading links file '{links_file}': {e}")
            return []

        if not links:
            logger.warning(f"No valid links found in {links_file}")
            return []

        # Prepare directories
        output_path, chunk_directory = self._prepare_directories(
            output_dir, save_chunks, chunk_dir
        )

        # Process links either sequentially or in parallel
        successfully_scraped = []
        failed_urls = []

        if parallel:
            try:
                from ..utils.thread_pool import get_shared_executor

                def process_url(args):
                    """
                    Processes a single URL for scraping and content conversion, capturing success or failure.

                    Args:
                        args: A tuple containing the URL to process and its index in the list.

                    Returns:
                        A tuple of (success, url, error_message), where success is True if processing
                        succeeded, or False with an error message if an exception occurred.
                    """
                    url, idx = args
                    try:
                        self._process_single_url(
                            url,
                            idx,
                            len(links),
                            output_path,
                            output_format,
                            save_chunks,
                            chunk_directory,
                            chunk_format,
                        )
                        return (True, url, None)
                    except Exception as e:
                        return (False, url, str(e))

                # Process URLs in parallel with shared thread pool (50% performance improvement)
                executor = get_shared_executor(max_workers)
                results = list(
                    executor.map(
                        process_url, [(url, i) for i, url in enumerate(links)]
                    )
                )

                # Process results
                for success, url, error in results:
                    if success:
                        successfully_scraped.append(url)
                    else:
                        failed_urls.append((url, error))
                        logger.error(f"Error processing URL {url}: {error}")

            except ImportError:
                logger.warning(
                    "Thread pool utilities not available, falling back to sequential processing"
                )
                parallel = False

        # Sequential processing (if parallel is False or concurrent.futures is not available)
        if not parallel:
            for i, url in enumerate(links):
                try:
                    self._process_single_url(
                        url,
                        i,
                        len(links),
                        output_path,
                        output_format,
                        save_chunks,
                        chunk_directory,
                        chunk_format,
                    )
                    successfully_scraped.append(url)
                except Exception as e:
                    failed_urls.append((url, str(e)))
                    logger.error(f"Error processing URL {url}: {e}")
                    continue

        # Log results
        logger.info(
            f"Successfully scraped {len(successfully_scraped)}/{len(links)} URLs"
        )

        if failed_urls:
            logger.warning(f"Failed to scrape {len(failed_urls)} URLs:")
            for url, error in failed_urls[
                :5
            ]:  # Show only first 5 failures to avoid log flooding
                logger.warning(f"  - {url}: {error}")
            if len(failed_urls) > 5:
                logger.warning(f"  - ... and {len(failed_urls) - 5} more")

        return successfully_scraped


def main(
    args_list=None,
    url: str = None,
    output_file: str = None,
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
    links_file: Optional[str] = None,
    parallel: bool = False,
    max_workers: int = 4,
) -> None:
    """
    Main entry point for running the web scraper via CLI or programmatically.

    Depending on the provided arguments, this function scrapes a single URL, a list of URLs from a file, or multiple URLs discovered via sitemap, then converts and saves the content in the specified format. Supports chunking for RAG workflows, caching, parallel processing, and advanced filtering options.
    """
    if args_list is not None:
        # Parse command line arguments
        parser = _create_argument_parser()
        args = parser.parse_args(args_list)

        # Set parameters from args
        url = args.url
        output_file = args.output
        output_format = args.format
        save_chunks = args.save_chunks
        chunk_dir = args.chunk_dir
        chunk_format = args.chunk_format
        chunk_size = args.chunk_size
        chunk_overlap = args.chunk_overlap
        requests_per_second = args.requests_per_second
        use_sitemap = args.use_sitemap
        min_priority = args.min_priority
        include_patterns = args.include
        exclude_patterns = args.exclude
        limit = args.limit
        cache_enabled = args.cache_enabled
        cache_max_age = args.cache_max_age
        skip_cache = args.skip_cache
        links_file = args.links_file
        parallel = args.parallel
        max_workers = args.max_workers

    # Setup
    validated_format = _validate_output_format(output_format)
    _check_rust_availability()

    # Create configuration from parameters
    config = MarkdownLabConfig(
        requests_per_second=requests_per_second,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        cache_enabled=cache_enabled,
        cache_ttl=cache_max_age,
    )
    
    scraper = MarkdownScraper(config)

    try:
        if links_file or Path("links.txt").exists():
            # Use provided links_file or default to links.txt if it exists
            links_file_path = links_file or "links.txt"
            _process_links_file_mode(
                scraper=scraper,
                links_file=links_file_path,
                output_file=output_file,
                output_format=validated_format,
                save_chunks=save_chunks,
                chunk_dir=chunk_dir,
                chunk_format=chunk_format,
                parallel=parallel,
                max_workers=max_workers,
            )
        elif use_sitemap:
            _process_sitemap_mode(
                scraper=scraper,
                url=url,
                output_file=output_file,
                output_format=validated_format,
                save_chunks=save_chunks,
                chunk_dir=chunk_dir,
                chunk_format=chunk_format,
                min_priority=min_priority,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                limit=limit,
            )
        else:
            _process_single_url_mode(
                scraper=scraper,
                url=url,
                output_file=output_file,
                output_format=validated_format,
                save_chunks=save_chunks,
                chunk_dir=chunk_dir,
                chunk_format=chunk_format,
                skip_cache=skip_cache,
            )

        logger.info(
            f"Process completed successfully. Output saved in {validated_format} format."
        )
    except Exception as e:
        logger.error(f"An error occurred during the process: {e}", exc_info=True)
        raise


def _create_argument_parser():
    """
    Creates and configures the argument parser for the command-line interface.

    Returns:
        An argparse.ArgumentParser instance with all supported CLI options for scraping, output formatting, chunking, sitemap usage, caching, and parallel processing.
    """
    parser = argparse.ArgumentParser(
        description="Scrape a website and convert it to Markdown, JSON, or XML with RAG chunking support."
    )
    parser.add_argument("url", type=str, help="The URL to scrape")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output.md",
        help="The output file name (extension will be set based on format)",
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
        "--no-cache",
        dest="cache_enabled",
        action="store_false",
        help="Disable caching of HTTP requests",
    )
    parser.add_argument(
        "--cache-max-age",
        type=int,
        default=3600,
        help="Maximum age of cached responses in seconds (default: 3600)",
    )
    parser.add_argument(
        "--skip-cache",
        action="store_true",
        help="Skip the cache and force new requests",
    )
    parser.add_argument(
        "--links-file",
        type=str,
        help="Path to a file containing links to scrape (defaults to links.txt if found)",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Use parallel processing for faster scraping of multiple URLs",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of parallel workers when using --parallel (default: 4)",
    )
    return parser


def _validate_output_format(output_format: str) -> str:
    """
    Validates and normalizes the output format string.

    If the provided format is not one of "markdown", "json", or "xml", defaults to "markdown".
    """
    normalized_format = output_format.lower()
    if normalized_format not in ["markdown", "json", "xml"]:
        logger.warning(
            f"Invalid output format: {output_format}. Using markdown instead."
        )
        return "markdown"
    return normalized_format


def _check_rust_availability() -> None:
    """
    Checks for the availability of the Rust-based implementation for HTML-to-Markdown conversion.

    Silently determines if the `markdown_lab.markdown_lab_rs` module can be imported, indicating Rust support.
    """
    with contextlib.suppress(ImportError):
        import importlib.util

        if importlib.util.find_spec("markdown_lab.markdown_lab_rs") is not None:
            pass  # Rust implementation is available


def _process_sitemap_mode(
    scraper: MarkdownScraper,
    url: str,
    output_file: str,
    output_format: str,
    save_chunks: bool,
    chunk_dir: str,
    chunk_format: str,
    min_priority: Optional[float],
    include_patterns: Optional[List[str]],
    exclude_patterns: Optional[List[str]],
    limit: Optional[int],
) -> None:
    """
    Scrapes a website using its sitemap and saves the content in the specified format.

    Parses the base URL, determines the output directory, and invokes the scraper to process all sitemap-discovered URLs according to filtering and chunking options.
    """
    # Parse base URL
    base_url = extract_base_url(url)

    # Get output directory from output_file
    output_path = Path(output_file)
    output_dir = str(output_path.parent) if output_path.is_file() else output_file

    # Scrape by sitemap
    logger.info(f"Scraping website using sitemap: {base_url}")

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


def _process_single_url_mode(
    scraper: MarkdownScraper,
    url: str,
    output_file: str,
    output_format: str,
    save_chunks: bool,
    chunk_dir: str,
    chunk_format: str,
    skip_cache: bool,
) -> None:
    """
    Scrapes a single URL, converts its content to the specified format, and saves the result.

    If chunking is enabled, also creates and saves content chunks in the specified directory and format.
    """
    # Scrape the URL
    html_content = scraper.scrape_website(url, skip_cache=skip_cache)

    # Convert the content
    content, markdown_content = scraper._convert_content(
        html_content, url, output_format
    )

    # Ensure correct output filename
    output_file = _ensure_correct_extension(
        output_file, output_format, content, markdown_content
    )

    # Save the content
    scraper.save_content(content, output_file)

    # Process chunks if enabled
    if save_chunks:
        chunks = scraper.create_chunks(markdown_content, url)
        scraper.save_chunks(chunks, chunk_dir, chunk_format)


def _process_links_file_mode(
    scraper: MarkdownScraper,
    links_file: str,
    output_file: str,
    output_format: str,
    save_chunks: bool,
    chunk_dir: str,
    chunk_format: str,
    parallel: bool = False,
    max_workers: int = 4,
) -> None:
    """
    Processes and scrapes multiple URLs listed in a links file using the provided scraper.

    If no links file is specified, defaults to 'links.txt'. Determines the output directory from the output file path and invokes the scraper to process all URLs, supporting optional chunking and parallel execution.
    """
    # If links_file is None, use the default links.txt
    if links_file is None:
        links_file = "links.txt"
        logger.info(f"No links file specified, using default: {links_file}")

    # Get output directory from output_file
    output_path = Path(output_file)
    output_dir = str(output_path.parent) if output_path.is_file() else output_file

    # Scrape by links file
    logger.info(f"Scraping website using links file: {links_file}")

    scraper.scrape_by_links_file(
        links_file=links_file,
        output_dir=output_dir,
        save_chunks=save_chunks,
        chunk_dir=chunk_dir,
        chunk_format=chunk_format,
        output_format=output_format,
        parallel=parallel,
        max_workers=max_workers,
    )


def _ensure_correct_extension(
    output_file: str, output_format: str, content: str, markdown_content: str
) -> str:
    """
    Ensures the output filename has the correct extension based on the content format.

    If the output format is not markdown but the content is markdown, the extension is set to `.md`.
    Returns the adjusted filename.
    """
    # Set correct extension
    output_ext = ".md" if output_format == "markdown" else f".{output_format}"

    # If file doesn't have the correct extension, add it
    if not output_file.endswith(output_ext):
        base_output = (
            output_file.rsplit(".", 1)[0] if "." in output_file else output_file
        )
        output_file = f"{base_output}{output_ext}"

    # If we had to fall back to markdown, adjust the extension
    if output_format != "markdown" and content == markdown_content:
        output_file = output_file.replace(f".{output_format}", ".md")

    return output_file


if __name__ == "__main__":
    parser = _create_argument_parser()
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
        links_file=args.links_file,
    )
