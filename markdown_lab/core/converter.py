"""
Lightweight converter for HTML to various formats.

This module provides a simplified Converter class that replaces the
over-engineered MarkdownScraper with a focused, single-responsibility approach.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from markdown_lab.core.client import HttpClient
from markdown_lab.core.config import MarkdownLabConfig, get_config
from markdown_lab.core.errors import ConversionError
from markdown_lab.core.rust_backend import get_rust_backend
from markdown_lab.formats import JsonFormatter, MarkdownFormatter, XmlFormatter
from markdown_lab.utils.chunk_utils import create_semantic_chunks
from markdown_lab.utils.sitemap_utils import SitemapParser

logger = logging.getLogger(__name__)


class Converter:
    """
    Lightweight converter for HTML content to markdown, JSON, or XML formats.

    This class coordinates the conversion pipeline without complex state management
    or performance monitoring overhead, focusing on simplicity and performance.
    """

    def __init__(self, config: Optional[MarkdownLabConfig] = None):
        """
        Initialize the converter with configuration.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        self.config = config or get_config()
        self.client = HttpClient(self.config)

        # Initialize format-specific handlers
        format_config = {
            "include_metadata": self.config.include_metadata,
            "indent": 2,
            "pretty_print": True,
        }
        self.formatters = {
            "markdown": MarkdownFormatter(format_config),
            "json": JsonFormatter(format_config),
            "xml": XmlFormatter(format_config),
        }

        # Initialize Rust backend
        self.rust_backend = get_rust_backend(
            fallback_enabled=self.config.fallback_to_python
        )

    def convert_url(
        self, url: str, output_format: str = "markdown", skip_cache: bool = False
    ) -> Tuple[str, str]:
        """
        Convert content from a URL to the specified format.

        Args:
            url: The URL to convert
            output_format: Target format ("markdown", "json", "xml")
            skip_cache: Whether to bypass cache

        Returns:
            Tuple of (converted_content, markdown_content)

        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Fetch HTML content
            html_content = self.client.get(url, skip_cache=skip_cache)

            # Convert to target format
            return self.convert_html(html_content, url, output_format)

        except Exception as e:
            raise ConversionError(
                f"Failed to convert URL {url}",
                source_format="html",
                target_format=output_format,
                conversion_stage="url_fetch",
                cause=e,
            ) from e

    def convert_html(
        self, html_content: str, base_url: str, output_format: str = "markdown"
    ) -> Tuple[str, str]:
        """
        Convert HTML content to the specified format.

        Args:
            html_content: Raw HTML content
            base_url: Base URL for resolving relative links
            output_format: Target format ("markdown", "json", "xml")

        Returns:
            Tuple of (converted_content, markdown_content)

        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Get raw converted content from Rust backend
            raw_content = self.rust_backend.convert_html_to_format(
                html_content, base_url, output_format
            )

            # Also get markdown version for chunking if needed
            markdown_content = (
                self.rust_backend.convert_html_to_format(
                    html_content, base_url, "markdown"
                )
                if output_format != "markdown"
                else raw_content
            )

            if formatter := self.formatters.get(output_format):
                metadata = {
                    "source_url": base_url,
                    "generated_at": self._get_timestamp(),
                    "title": self._extract_title(html_content),
                }
                converted_content = formatter.format(raw_content, metadata)
            else:
                converted_content = raw_content

            return converted_content, markdown_content

        except Exception as e:
            raise ConversionError(
                "Rust conversion failed",
                source_format="html",
                target_format=output_format,
                conversion_stage="rust_conversion",
                cause=e,
            ) from e

    def create_chunks(self, markdown_content: str, source_url: str) -> List:
        """
        Create semantic chunks from markdown content.

        Args:
            markdown_content: The markdown content to chunk
            source_url: Source URL for metadata

        Returns:
            List of content chunks
        """
        try:
            return create_semantic_chunks(
                content=markdown_content,
                source_url=source_url,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
            )
        except Exception as e:
            logger.error(f"Failed to create chunks: {e}")
            return []

    def save_content(self, content: str, output_file: str) -> None:
        """
        Save content to a file.

        Args:
            content: The content to save
            output_file: Output file path

        Raises:
            IOError: If file cannot be written
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Content saved to {output_file}")

        except Exception as e:
            logger.error(f"Failed to save content to {output_file}: {e}")
            raise

    def get_filename_from_url(self, url: str, output_format: str) -> str:
        """
        Generate a safe filename from a URL.

        Args:
            url: The source URL
            output_format: The output format for extension

        Returns:
            A safe filename with appropriate extension
        """
        import re

        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip("/").split("/")

        # Handle empty paths
        if not path_parts or path_parts[0] == "":
            filename = "index"
        else:
            filename = "_".join(path_parts)

        # Remove invalid characters
        filename = re.sub(r'[\\/*?:"<>|]', "_", filename)

        # Add correct extension
        output_ext = ".md" if output_format == "markdown" else f".{output_format}"
        if not filename.endswith(output_ext):
            if "." in filename:
                filename = filename.rsplit(".", 1)[0] + output_ext
            else:
                filename += output_ext

        return filename

    def convert_sitemap(
        self,
        base_url: str,
        output_dir: str,
        output_format: str = "markdown",
        min_priority: Optional[float] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        save_chunks: bool = True,
        chunk_dir: Optional[str] = None,
        chunk_format: str = "jsonl",
    ) -> List[str]:
        """
        Convert multiple pages from a sitemap.

        Args:
            base_url: The base URL to discover sitemap from
            output_dir: Directory to save converted files
            output_format: Output format ("markdown", "json", or "xml")
            min_priority: Minimum sitemap priority to include
            include_patterns: Regex patterns for URLs to include
            exclude_patterns: Regex patterns for URLs to exclude
            limit: Maximum number of URLs to process
            save_chunks: Whether to create and save chunks
            chunk_dir: Directory to save chunks (defaults to subdirectory)
            chunk_format: Format for chunks ("json" or "jsonl")

        Returns:
            List of successfully processed URLs
        """
        # Discover URLs from sitemap
        sitemap_parser = SitemapParser(
            requests_per_second=self.config.requests_per_second,
            max_retries=self.config.max_retries,
            timeout=self.config.timeout,
        )

        logger.info(f"Discovering URLs from sitemap for {base_url}")
        sitemap_parser.parse_sitemap(base_url)
        filtered_urls = sitemap_parser.filter_urls(
            min_priority=min_priority,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            limit=limit,
        )

        if not filtered_urls:
            logger.warning(f"No URLs found in sitemap for {base_url}")
            return []

        logger.info(f"Found {len(filtered_urls)} URLs to process")

        # Prepare directories
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        chunk_directory = None
        if save_chunks:
            chunk_directory = chunk_dir or str(output_path / "chunks")
            Path(chunk_directory).mkdir(parents=True, exist_ok=True)

        # Process URLs
        successfully_processed = []
        for i, url_info in enumerate(filtered_urls):
            url = url_info.loc
            try:
                self._process_single_url(
                    url,
                    i,
                    len(filtered_urls),
                    output_path,
                    output_format,
                    save_chunks,
                    chunk_directory,
                    chunk_format,
                )
                successfully_processed.append(url)
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                continue

        logger.info(
            f"Successfully processed {len(successfully_processed)}/{len(filtered_urls)} URLs"
        )
        return successfully_processed

    def convert_url_list(
        self,
        urls: List[str],
        output_dir: str,
        output_format: str = "markdown",
        save_chunks: bool = True,
        chunk_dir: Optional[str] = None,
        chunk_format: str = "jsonl",
    ) -> List[str]:
        """
        Convert multiple URLs from a list.

        Args:
            urls: List of URLs to convert
            output_dir: Directory to save converted files
            output_format: Output format ("markdown", "json", or "xml")
            save_chunks: Whether to create and save chunks
            chunk_dir: Directory to save chunks (defaults to subdirectory)
            chunk_format: Format for chunks ("json" or "jsonl")

        Returns:
            List of successfully processed URLs
        """
        # Prepare directories
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        chunk_directory = None
        if save_chunks:
            chunk_directory = chunk_dir or str(output_path / "chunks")
            Path(chunk_directory).mkdir(parents=True, exist_ok=True)

        # Process URLs
        successfully_processed = []
        for i, url in enumerate(urls):
            try:
                self._process_single_url(
                    url,
                    i,
                    len(urls),
                    output_path,
                    output_format,
                    save_chunks,
                    chunk_directory,
                    chunk_format,
                )
                successfully_processed.append(url)
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                continue

        logger.info(
            f"Successfully processed {len(successfully_processed)}/{len(urls)} URLs"
        )
        return successfully_processed

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
        """Process a single URL: fetch, convert, save, and optionally chunk."""
        logger.info(f"Processing URL {index+1}/{total}: {url}")

        filename = self._generate_output_filename(url, output_format, output_path)
        content, markdown_content = self.convert_url(url, output_format)
        self.save_content(content, filename)

        if save_chunks and chunk_dir:
            self._save_content_chunks(
                markdown_content, url, filename, chunk_dir, chunk_format
            )

    def _generate_output_filename(
        self, url: str, output_format: str, output_path: Path
    ) -> str:
        """Generate the full output file path for a URL."""
        filename = self.get_filename_from_url(url, output_format)
        return str(output_path / filename)

    def _save_content_chunks(
        self,
        markdown_content: str,
        url: str,
        output_filename: str,
        chunk_dir: str,
        chunk_format: str,
    ) -> None:
        """Save content chunks if chunks are generated successfully."""
        if chunks := self.create_chunks(markdown_content, url):
            from markdown_lab.utils.chunk_utils import ContentChunker

            url_chunk_dir = f"{chunk_dir}/{Path(output_filename).stem}"
            chunker = ContentChunker(self.config.chunk_size, self.config.chunk_overlap)
            chunker.save_chunks(chunks, url_chunk_dir, chunk_format)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.now().isoformat()

    def _extract_title(self, html_content: str) -> Optional[str]:
        """Extract title from HTML content."""
        import re

        if title_match := re.search(
            r"<title[^>]*>([^<]+)</title>", html_content, re.IGNORECASE
        ):
            return title_match.group(1).strip()

        if h1_match := re.search(r"<h1[^>]*>([^<]+)</h1>", html_content, re.IGNORECASE):
            return h1_match.group(1).strip()

        return None

    def close(self):
        """Clean up resources."""
        if hasattr(self, "client"):
            self.client.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
