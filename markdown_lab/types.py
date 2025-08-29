"""
Shared type definitions for markdown_lab.

This module contains type definitions that are shared between Python and Rust components
to avoid circular import issues.
"""

from enum import Enum


class OutputFormat(str, Enum):
    """Output format for HTML conversion"""

    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"
