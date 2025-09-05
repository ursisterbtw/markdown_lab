"""
Base formatter class for all output formats.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseFormatter(ABC):
    """Abstract base class for format-specific converters."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize formatter with configuration.

        Args:
            config: Format-specific configuration options
        """
        self.config = config or {}

    @abstractmethod
    def format(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Format content according to the specific output format.

        Args:
            content: The content to format
            metadata: Optional metadata for the content

        Returns:
            Formatted content as a string
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """
        Get the file extension for this format.

        Returns:
            File extension including the dot (e.g., ".md", ".json")
        """
        pass

    def validate_content(self, content: str) -> bool:
        """
        Validate that content is suitable for this format.

        Args:
            content: Content to validate

        Returns:
            True if content is valid for this format
        """
        return bool(content and content.strip())
