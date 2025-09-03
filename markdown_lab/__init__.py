"""Markdown Lab - HTML to Markdown converter with multiple output formats."""

__version__ = "1.0.0"

from markdown_lab.core.config import MarkdownLabConfig, get_config

# Main API - prefer the new simplified Converter
from markdown_lab.core.converter import Converter

# Legacy API - for backward compatibility
from markdown_lab.core.scraper import MarkdownScraper

# Format handlers
from markdown_lab.formats import JsonFormatter, MarkdownFormatter, XmlFormatter

__all__ = [
    "Converter",
    "MarkdownLabConfig",
    "get_config",
    "MarkdownScraper",  # Legacy
    "MarkdownFormatter",
    "JsonFormatter",
    "XmlFormatter",
    # CLI/TUI components (optional imports)
]

# Optional CLI/TUI imports are handled dynamically at runtime
# to avoid import errors when optional dependencies are not available
