"""Core functionality for Markdown Lab."""

from markdown_lab.core.client import HttpClient
from markdown_lab.core.config import MarkdownLabConfig, get_config
from markdown_lab.core.converter import Converter
from markdown_lab.core.rust_backend import RustBackend, get_rust_backend

# Legacy
from markdown_lab.core.scraper import MarkdownScraper

__all__ = [
    "Converter",
    "HttpClient",
    "MarkdownLabConfig",
    "get_config",
    "RustBackend",
    "get_rust_backend",
    "MarkdownScraper",  # Legacy
]
