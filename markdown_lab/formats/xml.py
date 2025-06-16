"""
XML format handler for markdown_lab.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict
from xml.dom import minidom

from markdown_lab.formats.base import BaseFormatter


class XmlFormatter(BaseFormatter):
    """Formatter for XML output."""

    def format(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Format content as XML.

        Args:
            content: The XML content (already converted by Rust backend)
            metadata: Optional metadata to include in XML

        Returns:
            Formatted XML content
        """
        if not self.validate_content(content):
            return '<?xml version="1.0" encoding="UTF-8"?>\n<document></document>'

        try:
            # Parse the XML content from Rust backend
            root = ET.fromstring(content)

            # Add metadata if requested and provided
            if self.config.get("include_metadata", True) and metadata:
                metadata_elem = ET.SubElement(root, "metadata")

                if metadata.get("title"):
                    title_elem = ET.SubElement(metadata_elem, "title")
                    title_elem.text = metadata["title"]

                if metadata.get("source_url"):
                    source_elem = ET.SubElement(metadata_elem, "source_url")
                    source_elem.text = metadata["source_url"]

                if metadata.get("generated_at"):
                    generated_elem = ET.SubElement(metadata_elem, "generated_at")
                    generated_elem.text = metadata["generated_at"]

                format_elem = ET.SubElement(metadata_elem, "format")
                format_elem.text = "xml"

            # Format with proper indentation if requested
            if self.config.get("pretty_print", True):
                return self._pretty_print_xml(root)
            return ET.tostring(root, encoding="unicode", xml_declaration=True)

        except ET.ParseError as e:
            # If content is not valid XML, wrap it in a basic structure
            root = ET.Element("document")

            error_elem = ET.SubElement(root, "error")
            error_elem.text = f"Invalid XML from converter: {str(e)}"

            content_elem = ET.SubElement(root, "raw_content")
            content_elem.text = content

            if metadata:
                metadata_elem = ET.SubElement(root, "metadata")
                for key, value in metadata.items():
                    if value:
                        elem = ET.SubElement(metadata_elem, key)
                        elem.text = str(value)

            return self._pretty_print_xml(root)

    def _pretty_print_xml(self, root: ET.Element) -> str:
        """
        Pretty print XML with proper formatting.

        Args:
            root: The root XML element

        Returns:
            Pretty-printed XML string
        """
        # Convert to string
        rough_string = ET.tostring(root, encoding="unicode")

        # Parse and pretty print
        parsed = minidom.parseString(rough_string)
        pretty = parsed.toprettyxml(indent="  ", encoding=None)

        # Remove extra blank lines
        lines = [line for line in pretty.split("\n") if line.strip()]
        return "\n".join(lines)

    def get_file_extension(self) -> str:
        """Get the file extension for XML files."""
        return ".xml"

    def validate_content(self, content: str) -> bool:
        """Validate XML content."""
        if not super().validate_content(content):
            return False

        # Try to parse as XML
        try:
            ET.fromstring(content)
            return True
        except ET.ParseError:
            # Still allow non-XML content to be wrapped
            return True
