"""
JSON format handler for markdown_lab.
"""

import json
from typing import Any, Dict

from markdown_lab.formats.base import BaseFormatter


class JsonFormatter(BaseFormatter):
    """Formatter for JSON output."""

    def format(self, content: str, metadata: Dict[str, Any] = None) -> str:
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

        except json.JSONDecodeError as e:
            # If content is not valid JSON, wrap it
            wrapped_content = {
                "content": content,
                "error": f"Invalid JSON from converter: {str(e)}",
            }

            if metadata:
                wrapped_content["metadata"] = metadata

            return json.dumps(wrapped_content, indent=2, ensure_ascii=False)

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
