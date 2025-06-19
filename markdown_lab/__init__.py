"""Markdown Lab - HTML to Markdown converter with multiple output formats."""

__version__ = "1.0.0"

from markdown_lab.core.config import MarkdownLabConfig, get_config

# Main API - modern Converter
from markdown_lab.core.converter import Converter

# Format handlers
from markdown_lab.formats import JsonFormatter, MarkdownFormatter, XmlFormatter

__all__ = [
    "Converter",
    "MarkdownLabConfig",
    "get_config",
    "MarkdownFormatter",
    "JsonFormatter",
    "XmlFormatter",
    # CLI/TUI components (optional imports)
]

# Optional CLI/TUI imports
try:
    from markdown_lab.cli import app as cli_app

    __all__.append("cli_app")
except ImportError:
    pass

try:
    from markdown_lab.tui import MarkdownLabTUI

    __all__.append("MarkdownLabTUI")
except ImportError:
    pass
