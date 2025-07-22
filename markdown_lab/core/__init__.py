"""Core functionality for Markdown Lab."""

from markdown_lab.core.client import HttpClient, CachedHttpClient, create_http_client, create_cached_http_client
from markdown_lab.core.config import MarkdownLabConfig, get_config
from markdown_lab.core.converter import Converter
from markdown_lab.core.rust_backend import RustBackend, get_rust_backend

# Legacy
from markdown_lab.core.scraper import MarkdownScraper

__all__ = [
    "Converter",
    "HttpClient",
    "CachedHttpClient", 
    "create_http_client",
    "create_cached_http_client",
    "MarkdownLabConfig",
    "get_config",
    "RustBackend",
    "get_rust_backend",
    "MarkdownScraper",  # Legacy
]
