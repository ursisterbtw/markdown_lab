"""
Markdown format handler for markdown_lab.
"""

from typing import Any, Dict, Optional

from markdown_lab.formats.base import BaseFormatter


class MarkdownFormatter(BaseFormatter):
    """Formatter for Markdown output."""

    def format(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Format content as Markdown.

        Args:
            content: The markdown content (already converted by Rust backend)
            metadata: Optional metadata (title, source URL, etc.)

        Returns:
            Formatted markdown content
        """
        if not self.validate_content(content):
            return ""

        formatted_content = content

        # Add metadata header if requested and metadata provided
        if self.config.get("include_metadata", True) and metadata:
            header_lines = []

            if metadata.get("title"):
                header_lines.append(f"# {metadata['title']}")

            if metadata.get("source_url"):
                header_lines.append(f"\n*Source: {metadata['source_url']}*")

            if metadata.get("generated_at"):
                header_lines.append(f"*Generated: {metadata['generated_at']}*")

            if header_lines:
                formatted_content = "\n".join(header_lines) + "\n\n" + content

        return formatted_content

    def get_file_extension(self) -> str:
        """Get the file extension for Markdown files."""
        return ".md"

    def validate_content(self, content: str) -> bool:
        """Validate markdown content."""
        return bool(super().validate_content(content))
