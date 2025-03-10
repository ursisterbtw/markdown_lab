"""
Markdown Lab - A powerful and modular web scraper that converts web content into
well-structured Markdown files with RAG-ready chunking capabilities.
"""

__version__ = "0.1.0"

# Try to import Rust implementations
try:
    from .markdown_lab_rs import (
        convert_html_to_markdown,
        chunk_markdown,
        render_js_page,
    )

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

# Import public API
from .main import MarkdownScraper
from .chunk_utils import Chunk, ContentChunker, create_semantic_chunks
from .sitemap_utils import SitemapParser, SitemapURL, discover_site_urls
from .throttle import RequestThrottler

# Define what's available through public API
__all__ = [
    'MarkdownScraper',
    'Chunk',
    'ContentChunker',
    'create_semantic_chunks',
    'SitemapParser',
    'SitemapURL',
    'discover_site_urls',
    'RequestThrottler',
    'RUST_AVAILABLE',
]

# Add Rust functions if available
if RUST_AVAILABLE:
    __all__.extend([
        'convert_html_to_markdown',
        'chunk_markdown',
        'render_js_page',
    ])
