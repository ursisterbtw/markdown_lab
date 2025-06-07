"""
Markdown Lab - A powerful and modular web scraper that converts web content into
well-structured Markdown files with RAG-ready chunking capabilities.
"""

__version__ = "0.1.0"

import importlib.util

# Try to import Rust implementations if the module is available
if importlib.util.find_spec("markdown_lab.markdown_lab_rs") is not None:
    # Import will happen in __all__ section if RUST_AVAILABLE is True
    RUST_AVAILABLE = True
else:
    RUST_AVAILABLE = False
    try:
        # Just check if the module can be imported
        import importlib.util

        if importlib.util.find_spec(".markdown_lab_rs", __name__) is not None:
            RUST_AVAILABLE = True
    except ImportError:
        import logging
        import traceback

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Rust extension not available, falling back to Python implementation.\n{traceback.format_exc()}"
        )
        RUST_AVAILABLE = False

from .chunk_utils import Chunk, ContentChunker, create_semantic_chunks

# Import public API
from .main import MarkdownScraper
from .sitemap_utils import SitemapParser, SitemapURL, discover_site_urls
from .throttle import RequestThrottler

# Define what's available through public API
__all__ = [
    "MarkdownScraper",
    "Chunk",
    "ContentChunker",
    "create_semantic_chunks",
    "SitemapParser",
    "SitemapURL",
    "discover_site_urls",
    "RequestThrottler",
    "RUST_AVAILABLE",
]

# Add Rust functions if available
if RUST_AVAILABLE:
    __all__.extend(
        [
            "convert_html_to_markdown",
            "chunk_markdown",
            "render_js_page",
        ]
    )
