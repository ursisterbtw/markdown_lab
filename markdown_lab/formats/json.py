"""
JSON format handler for markdown_lab.
"""

import json
from typing import Any, Dict, Optional

from markdown_lab.formats.base import BaseFormatter


class JsonFormatter(BaseFormatter):
    """Formatter for JSON output."""

    def format(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Format content as JSON.

        Args:
            content: The JSON content (already converted by Rust backend)
            metadata: Optional metadata to include in JSON

        Returns:
            Formatted JSON content
        """
        if not self.validate_content(content):
            return "{}"

        try:
            # Parse the JSON content from Rust backend
            content_data = json.loads(content)

            # Add metadata if requested and provided
            if self.config.get("include_metadata", True) and metadata:
                content_data["metadata"] = {
                    "title": metadata.get("title"),
                    "source_url": metadata.get("source_url"),
                    "generated_at": metadata.get("generated_at"),
                    "format": "json",
                }

            # Format with proper indentation
            indent = self.config.get("indent", 2)
            return json.dumps(content_data, indent=indent, ensure_ascii=False)

        except json.JSONDecodeError:
            # Fallback: build a minimal JSON document from markdown-derived structure
            from markdown_lab.markdown_lab_rs import (
                parse_markdown_to_document,
                _python_html_to_markdown,
            )

            # If we received non-JSON (likely markdown or xml), normalize to markdown and parse
            markdown_guess = content
            if content.strip().startswith("<"):
                # XML/HTML path: convert to markdown first
                html_like = content
                markdown_guess = _python_html_to_markdown(html_like)

            base_url = metadata.get("source_url", "") if metadata else ""
            if metadata and metadata.get("markdown_raw"):
                markdown_guess = metadata["markdown_raw"]
            doc = parse_markdown_to_document(markdown_guess, base_url)
            if self.config.get("include_metadata", True) and metadata:
                doc["metadata"] = {
                    "title": metadata.get("title"),
                    "source_url": metadata.get("source_url"),
                    "generated_at": metadata.get("generated_at"),
                    "format": "json",
                }
            return json.dumps(doc, indent=self.config.get("indent", 2), ensure_ascii=False)

    def get_file_extension(self) -> str:
        """Get the file extension for JSON files."""
        return ".json"

    def validate_content(self, content: str) -> bool:
        """Validate JSON content."""
        if not super().validate_content(content):
            return False

        # Try to parse as JSON
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            # Still allow non-JSON content to be wrapped
            return True
