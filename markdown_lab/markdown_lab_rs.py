"""
Python interface to the Rust implementation of markdown_lab components.
fallback to Python implementations if Rust extension not available

To build the Rust extension:
1. Install maturin: pip install maturin
2. Build the extension: maturin develop
"""

import json
import logging
import xml.etree.ElementTree as ET
from enum import Enum
from typing import Dict, List, Optional
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

    # Remove remaining HTML tags
    html = re.sub(r"<[^>]+>", "", html)

    # Clean up whitespace
    html = re.sub(r"\n\s*\n", "\n\n", html)
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

    # parse markdown into document structure
    doc_structure = parse_markdown_to_document(markdown_content, base_url)

    if output_format == OutputFormat.JSON:
        return json.dumps(doc_structure, indent=2)
    if output_format == OutputFormat.XML:
        return document_to_xml(doc_structure)

    # Fallback to markdown if format not recognized
    return markdown_content


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
    document = {
        "title": "No Title",
        "base_url": base_url,
        "headings": [],
        "paragraphs": [],
        "links": [],
        "images": [],
        "lists": [],
        "code_blocks": [],
        "blockquotes": [],
    }

    # Extract title (first h1)
    for line in lines:
        if line.startswith("# "):
            document["title"] = line[2:].strip()
            break

    # Process other elements with a very simple parser
    # This is just a fallback implementation
    current_block = []
    in_code_block = False
    code_lang = ""

    for line in lines:
        # Skip title line which we already processed
        if line.strip() == f"# {document['title']}":
            continue

        # Handle headings
        if line.startswith("#") and not in_code_block:
            level = 0
            while level < len(line) and line[level] == "#":
                level += 1
            if level <= 6 and level < len(line) and line[level] == " ":
                document["headings"].append(
                    {"level": level, "text": line[level + 1 :].strip()}
                )

        # Handle code blocks
        elif line.startswith("```") and not in_code_block:
            in_code_block = True
            code_lang = line[3:].strip()
            current_block = []
        elif line.startswith("```") and in_code_block:
            in_code_block = False
            document["code_blocks"].append(
                {"language": code_lang, "code": "\n".join(current_block)}
            )
            current_block = []

        # Collect code block content
        elif in_code_block:
            current_block.append(line)

        # Handle blockquotes
        elif line.startswith(">") and not in_code_block:
            document["blockquotes"].append(line[1:].strip())

        # Handle paragraphs (very simplified)
        elif line.strip() and not in_code_block:
            document["paragraphs"].append(line.strip())

    return document


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


def render_js_page(url: str, wait_time_ms: Optional[int] = None) -> str:
    """
    Renders a JavaScript-enabled web page and returns the resulting HTML content.

    If the Rust extension is available, uses it to render the page. Otherwise, logs a warning and returns None, as Python fallback is not implemented.
    """
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
