"""
Python interface to the Rust implementation of markdown_lab components.
This module provides a fallback to Python implementations if the Rust extension is not available.

To build the Rust extension:
1. Install maturin: pip install maturin
2. Build the extension: maturin develop
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Try to import the Rust extension
try:
    from .markdown_lab_rs import chunk_markdown as _rs_chunk_markdown
    from .markdown_lab_rs import (
        convert_html_to_markdown as _rs_convert_html_to_markdown,
    )
    from .markdown_lab_rs import render_js_page as _rs_render_js_page

    RUST_AVAILABLE = True
    logger.info("Using Rust implementation for improved performance")
except ImportError:
    RUST_AVAILABLE = False
    logger.warning(
        "Rust extension not available, falling back to Python implementation"
    )


def convert_html_to_markdown(html: str, base_url: str = "") -> str:
    """
    Convert HTML to markdown using the Rust implementation if available,
    otherwise fall back to the Python implementation.

    Args:
        html: HTML content to convert
        base_url: Base URL for resolving relative links

    Returns:
        Markdown content
    """
    if RUST_AVAILABLE:
        try:
            return _rs_convert_html_to_markdown(html, base_url)
        except Exception as e:
            logger.warning(
                f"Error in Rust HTML-to-markdown conversion, falling back to Python: {e}"
            )

    # Fall back to Python implementation
    from main1 import MarkdownScraper

    scraper = MarkdownScraper()
    return scraper.convert_to_markdown(html, base_url)


def chunk_markdown(
    markdown: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> List[str]:
    """
    Chunk markdown content using the Rust implementation if available,
    otherwise fall back to the Python implementation.

    Args:
        markdown: Markdown content to chunk
        chunk_size: Maximum size of chunks in characters
        chunk_overlap: Overlap between chunks in characters

    Returns:
        List of markdown content chunks
    """
    if RUST_AVAILABLE:
        try:
            return _rs_chunk_markdown(markdown, chunk_size, chunk_overlap)
        except Exception as e:
            logger.warning(f"Error in Rust chunking, falling back to Python: {e}")

    # Fall back to Python implementation
    from chunk_utils import create_semantic_chunks

    chunks = create_semantic_chunks(
        content=markdown,
        source_url="",  # Not used for content
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return [chunk.content for chunk in chunks]


def render_js_page(url: str, wait_time_ms: Optional[int] = None) -> str:
    """
    Render a JavaScript-enabled page and return the HTML content
    using the Rust implementation if available, otherwise fall back
    to a Python implementation.

    Args:
        url: URL to render
        wait_time_ms: Time to wait for JavaScript execution in milliseconds

    Returns:
        HTML content after JavaScript execution
    """
    if RUST_AVAILABLE:
        try:
            return _rs_render_js_page(url, wait_time_ms)
        except Exception as e:
            logger.warning(f"Error in Rust JS rendering, falling back to Python: {e}")

    # Fall back to Python implementation
    # This would require a JS renderer like Playwright or Selenium
    # For now, we'll just log a warning and return None
    logger.warning(
        "JS rendering requires the Rust extension or an external browser automation tool"
    )
    return None
