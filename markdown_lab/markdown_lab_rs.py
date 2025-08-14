"""
Python interface to the Rust implementation of markdown_lab components.
This module provides a fallback to Python implementations if the Rust extension is not available.

To build the Rust extension:
1. Install maturin: pip install maturin
2. Build the extension: maturin develop
"""

import json
import logging
import xml.etree.ElementTree as ET
from enum import Enum
from typing import Any, Dict, List, Optional
from xml.dom import minidom

logger = logging.getLogger(__name__)


def _python_html_to_markdown(html: str, base_url: str = "") -> str:
    """
    Simple Python fallback for HTML to markdown conversion.
    This is a basic implementation that should be sufficient for testing.
    """
    # Very basic HTML to markdown conversion using regex
    import re

    # Remove script and style tags
    html = re.sub(
        r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Extract <title> and promote to top-level heading
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    page_title = title_match.group(1).strip() if title_match else None

    # Convert headers
    html = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n", html, flags=re.IGNORECASE)

    # Convert paragraphs
    html = re.sub(
        r"<p[^>]*>(.*?)</p>", r"\1\n\n", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Convert links
    html = re.sub(
        r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        html,
        flags=re.IGNORECASE,
    )

    # Convert images to markdown
    html = re.sub(
        r"<img[^>]*alt=[\"']([^\"']*)[\"'][^>]*src=[\"']([^\"']*)[\"'][^>]*>",
        r"![\1](\2)",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r"<img[^>]*src=[\"']([^\"']*)[\"'][^>]*alt=[\"']([^\"']*)[\"'][^>]*>",
        r"![\2](\1)",
        html,
        flags=re.IGNORECASE,
    )

    # Remove remaining HTML tags
    html = re.sub(r"<[^>]+>", "", html)

    # Clean up whitespace
    html = re.sub(r"\n\s*\n", "\n\n", html)

    # Prepend title as H1 if available and not already present
    if page_title:
        title_heading = f"# {page_title}"
        if not html.lstrip().startswith("# ") or not html.splitlines()[0].strip() == title_heading:
            html = f"{title_heading}\n\n" + html

    return html.strip()


class OutputFormat(str, Enum):
    """Output format for HTML conversion"""

    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"


# Try to import the Rust extension
try:
    from .markdown_lab_rs import chunk_markdown as _rs_chunk_markdown
    from .markdown_lab_rs import convert_html_to_format as _rs_convert_html_to_format
    from .markdown_lab_rs import render_js_page as _rs_render_js_page

    RUST_AVAILABLE = True
    logger.info("Using Rust implementation for improved performance")
except ImportError:
    RUST_AVAILABLE = False
    logger.warning(
        "Rust extension not available, falling back to Python implementation"
    )


def convert_html_to_markdown(html: str, base_url: str = "") -> str:
    """
    Convert HTML to markdown using the Rust implementation if available,
    otherwise fall back to the Python implementation.

    Args:
        html: HTML content to convert
        base_url: Base URL for resolving relative links

    Returns:
        Markdown content
    """
    return convert_html(html, base_url, OutputFormat.MARKDOWN)


def convert_html(
    html: str, base_url: str = "", output_format: OutputFormat = OutputFormat.MARKDOWN
) -> str:
    """
    Converts HTML content to markdown, JSON, or XML format.

    Uses a Rust implementation for conversion if available; otherwise, falls back to a Python-based approach. For JSON and XML outputs, the HTML is first converted to markdown, then parsed into a structured document before serialization.

    Args:
        html: The HTML content to convert.
        base_url: The base URL used for resolving relative links.
        output_format: The desired output format (markdown, json, or xml).

    Returns:
        The converted content in the specified format as a string.
    """
    if RUST_AVAILABLE:
        try:
            return _rs_convert_html_to_format(html, base_url, output_format.value)
        except Exception as e:
            logger.warning(
                f"Error in Rust HTML conversion to {output_format}, falling back to Python: {e}"
            )

    # Fall back to Python implementation - use a simple HTML to markdown converter
    logger.warning("Using basic Python HTML to markdown conversion fallback")

    if output_format == OutputFormat.MARKDOWN:
        return _python_html_to_markdown(html, base_url)

    # For JSON and XML, first convert to markdown to get structured content
    # This is a simplified implementation - the real one would parse the HTML directly
    markdown_content = _python_html_to_markdown(html, base_url)

    # Parse markdown into our document structure
    document = parse_markdown_to_document(markdown_content, base_url)

    if output_format == OutputFormat.JSON:
        return json.dumps(document, indent=2)
    if output_format == OutputFormat.XML:
        return document_to_xml(document)

    # Fallback to markdown if format not recognized
    return markdown_content


def _extract_title_from_lines(lines: List[str]) -> str:
    """Extract title from markdown lines (first h1 heading)."""
    return next(
        (line[2:].strip() for line in lines if line.startswith("# ")),
        "No Title",
    )


def _parse_heading(line: str) -> Optional[dict[str, Any]]:
    """Parse a heading line and return heading info if valid."""
    if not line.startswith("#"):
        # Treat simple underlined headings (Setext): text followed by ===== or -----
        # This improves fallback detection for titles/headings
        if line.strip() and all(ch == "=" for ch in line.strip()):
            return {"level": 1, "text": ""}
        if line.strip() and all(ch == "-" for ch in line.strip()):
            return {"level": 2, "text": ""}
        return None

    level = 0
    while level < len(line) and line[level] == "#":
        level += 1

    if level <= 6 and level < len(line) and line[level] == " ":
        return {"level": level, "text": line[level + 1 :].strip()}

    return None


def _process_markdown_lines(lines: List[str], title: str) -> Dict[str, List]:
    """Process markdown lines and extract content into document sections."""
    content_sections = {
        "headings": [],
        "paragraphs": [],
        "code_blocks": [],
        "blockquotes": [],
    }

    current_block: List[str] = []
    in_code_block = False
    code_lang = ""
    title_line = f"# {title}"

    previous_line = ""
    for line in lines:
        # Skip title line which we already processed
        if line.strip() == title_line:
            continue

        # Handle code blocks
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = line[3:].strip()
            else:
                in_code_block = False
                content_sections["code_blocks"].append(
                    {"language": code_lang, "code": "\n".join(current_block)}
                )
            current_block = []
            continue

        # Collect code block content
        if in_code_block:
            current_block.append(line)
            continue

        if heading := _parse_heading(line):
            if heading["text"] == "" and previous_line.strip():
                # Setext style heading: use previous line as text
                level = 1 if set(line.strip()) == {"="} else 2
                content_sections["headings"].append({"level": level, "text": previous_line.strip()})
            else:
                content_sections["headings"].append(heading)
        elif line.startswith(">"):
            content_sections["blockquotes"].append(line[1:].strip())
        elif line.strip():
            content_sections["paragraphs"].append(line.strip())
        previous_line = line

    return content_sections


def parse_markdown_to_document(markdown: str, base_url: str) -> Dict:
    """
    Parse markdown into a document structure that can be serialized to different formats.
    This is a simplified implementation for the Python fallback.

    Args:
        markdown: Markdown content
        base_url: Base URL for resolving relative links

    Returns:
        Document structure as a dictionary
    """
    lines = markdown.split("\n")
    title = _extract_title_from_lines(lines)
    content_sections = _process_markdown_lines(lines, title)

    return {
        "title": title,
        "base_url": base_url,
        "links": [],  # Not implemented in fallback
        "images": [],  # Not implemented in fallback
        "lists": [],  # Not implemented in fallback
        **content_sections,
    }


def document_to_xml(document: Dict) -> str:
    """
    Convert document structure to XML.

    Args:
        document: Document structure

    Returns:
        XML string
    """
    root = ET.Element("document")

    # Add title
    title = ET.SubElement(root, "title")
    title.text = document["title"]

    # Add base URL
    base_url = ET.SubElement(root, "base_url")
    base_url.text = document["base_url"]

    # Add headings
    headings = ET.SubElement(root, "headings")
    for h in document["headings"]:
        heading = ET.SubElement(headings, "heading")
        heading.set("level", str(h["level"]))
        heading.text = h["text"]

    # Add paragraphs
    paragraphs = ET.SubElement(root, "paragraphs")
    for p in document["paragraphs"]:
        paragraph = ET.SubElement(paragraphs, "paragraph")
        paragraph.text = p

    # Add other elements similarly
    # This is simplified for brevity

    # Convert to string with pretty formatting
    rough_string = ET.tostring(root, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def chunk_markdown(
    markdown: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> List[str]:
    """
    Chunk markdown content using the Rust implementation if available,
    otherwise fall back to the Python implementation.

    Args:
        markdown: Markdown content to chunk
        chunk_size: Maximum size of chunks in characters
        chunk_overlap: Overlap between chunks in characters

    Returns:
        List of markdown content chunks
    """
    if RUST_AVAILABLE:
        try:
            return _rs_chunk_markdown(markdown, chunk_size, chunk_overlap)
        except Exception as e:
            logger.warning(f"Error in Rust chunking, falling back to Python: {e}")

    # Fall back to Python implementation
    from markdown_lab.utils.chunk_utils import create_semantic_chunks

    chunks = create_semantic_chunks(
        content=markdown,
        source_url="",  # Not used for content
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return [chunk.content for chunk in chunks]


def render_js_page(url: Optional[str], wait_time_ms: Optional[int] = None) -> str:
    """
    Renders a JavaScript-enabled web page and returns the resulting HTML content.

    If the Rust extension is available, uses it to render the page. Otherwise, logs a warning and returns None, as Python fallback is not implemented.
    """
    if url is None:
        raise TypeError("url must be a string")

    if RUST_AVAILABLE:
        try:
            return _rs_render_js_page(url, wait_time_ms)
        except Exception as e:
            logger.warning(f"Error in Rust JS rendering, falling back to Python: {e}")

    # Fall back to Python implementation
    # This would require a JS renderer like Playwright or Selenium
    # For now, we'll just log a warning and return None
    logger.warning(
        "JS rendering requires the Rust extension or an external browser automation tool"
    )
    return None
