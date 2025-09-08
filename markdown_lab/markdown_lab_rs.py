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
    # basic html to markdown conversion using regex
    import re
    import html as html_module
    from urllib.parse import urljoin

    # 1) Decode HTML entities BEFORE any tag removal to prevent obfuscated scripts
    #    and ensure we work with canonicalized HTML text.
    try:
        html = html_module.unescape(html)
    except Exception:
        # If decoding fails for any reason, continue with original content
        pass

    # 2) Remove script and style tags (and their content) aggressively
    html = re.sub(
        r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE
    )

    if title_match := re.search(
        r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE
    ):
        title = f"# {title_match.group(1).strip()}\n\n"
    else:
        title = ""
    # remove title tag after extracting content
    html = re.sub(r"<title[^>]*>.*?</title>", "", html, flags=re.IGNORECASE)

    # convert headers
    html = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n\n", html, flags=re.IGNORECASE)

    # convert code blocks: <pre><code>...</code></pre> -> fenced code block
    def _replace_code_block(match: re.Match[str]) -> str:
        code = match.group(1)
        # Normalize line endings
        code = code.replace("\r\n", "\n").replace("\r", "\n")
        return f"\n```\n{code}\n```\n\n"

    html = re.sub(
        r"<pre[^>]*>\s*<code[^>]*>([\s\S]*?)</code>\s*</pre>",
        _replace_code_block,
        html,
        flags=re.IGNORECASE,
    )

    # convert paragraphs
    html = re.sub(
        r"<p[^>]*>(.*?)</p>", r"\1\n\n", html, flags=re.DOTALL | re.IGNORECASE
    )

    # convert links with base URL resolution
    def _replace_link(match: re.Match[str]) -> str:
        href = match.group(1)
        text = match.group(2)
        try:
            absolute_href = urljoin(base_url, href) if base_url else href
        except Exception:
            absolute_href = href
        return f"[{text}]({absolute_href})"

    html = re.sub(
        r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        _replace_link,
        html,
        flags=re.IGNORECASE,
    )

    # convert images with base URL resolution
    def _replace_img_with_alt(match: re.Match[str]) -> str:
        src = match.group(1)
        alt = match.group(2)
        try:
            absolute_src = urljoin(base_url, src) if base_url else src
        except Exception:
            absolute_src = src
        return f"![{alt}]({absolute_src})"

    def _replace_img_no_alt(match: re.Match[str]) -> str:
        src = match.group(1)
        try:
            absolute_src = urljoin(base_url, src) if base_url else src
        except Exception:
            absolute_src = src
        return f"![]({absolute_src})"

    # convert images with alt text
    html = re.sub(
        r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*>',
        _replace_img_with_alt,
        html,
        flags=re.IGNORECASE,
    )
    # handle images without alt text
    html = re.sub(
        r'<img[^>]*src=["\']([^"\']*)["\'][^>]*>',
        _replace_img_no_alt,
        html,
        flags=re.IGNORECASE,
    )

    # convert blockquotes to Markdown (after links/images so anchor text is preserved)
    def _replace_blockquote(match: re.Match[str]) -> str:
        inner_html = match.group(1)
        # Remove any remaining HTML tags inside blockquote but keep markdown link syntax
        inner_text = re.sub(r"<[^>]+>", "", inner_html)
        lines = [line.strip() for line in inner_text.splitlines() if line.strip()]
        if not lines:
            return ""
        return "\n" + "\n".join("> " + line for line in lines) + "\n\n"

    html = re.sub(
        r"<blockquote[^>]*>([\s\S]*?)</blockquote>",
        _replace_blockquote,
        html,
        flags=re.IGNORECASE,
    )

    # convert list items (basic handling)
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html, flags=re.IGNORECASE)

    # remove list container tags
    html = re.sub(r"</?[uo]l[^>]*>", "", html, flags=re.IGNORECASE)

    # remove remaining html tags
    html = re.sub(r"<[^>]+>", "", html)

    # clean up whitespace
    html = re.sub(r"\n\s*\n", "\n\n", html)

    # combine title with body content
    return title + html.strip()


class OutputFormat(str, Enum):
    """Output format for HTML conversion"""

    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"


# try to import the rust extension (namespaced by maturin)
# Note: Avoid circular import by not importing from markdown_lab package
try:
    import markdown_lab_rs as _rust_module

    _rs_chunk_markdown = _rust_module.chunk_markdown
    _rs_convert_html_to_format = _rust_module.convert_html_to_format
    _rs_render_js_page = _rust_module.render_js_page

    RUST_AVAILABLE = True
    logger.info("Using Rust implementation for improved performance")
except ImportError:
    RUST_AVAILABLE = False
    _rs_chunk_markdown = None
    _rs_convert_html_to_format = None
    _rs_render_js_page = None
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
    return convert_html_to_format(html, base_url, OutputFormat.MARKDOWN)


def convert_html_to_format(
    html: str,
    base_url: str = "",
    output_format: str | OutputFormat | None = OutputFormat.MARKDOWN,
) -> str:
    """
    Converts HTML content to markdown, JSON, or XML format.

    Uses the Rust implementation if available; otherwise, falls back to a
    lightweight Python implementation. Accepts either a string ("markdown",
    "json", "xml") or the local OutputFormat enum.
    """
    # normalize to string value
    if isinstance(output_format, OutputFormat):
        fmt_value = output_format.value
    else:
        fmt_value = (output_format or "markdown").lower()

    if RUST_AVAILABLE:
        try:
            return _rs_convert_html_to_format(html, base_url, fmt_value)
        except Exception as e:
            logger.warning(
                f"Error in Rust HTML conversion to {fmt_value}, falling back to Python: {e}"
            )

    # fall back to python implementation - use a simple html to markdown converter
    logger.warning("Using basic Python HTML to markdown conversion fallback")

    if fmt_value == "markdown":
        return _python_html_to_markdown(html, base_url)

    # for json and xml, first convert to markdown to get structured content
    markdown_content = _python_html_to_markdown(html, base_url)
    doc_structure = parse_markdown_to_document(markdown_content, base_url)

    if fmt_value == "json":
        return json.dumps(doc_structure, indent=2)
    if fmt_value == "xml":
        return document_to_xml(doc_structure)

    # fallback to markdown if format not recognized
    return markdown_content


def convert_html(
    html: str, base_url: str = "", output_format: OutputFormat = OutputFormat.MARKDOWN
) -> str:
    """Backward-compatible wrapper that delegates to convert_html_to_format."""
    return convert_html_to_format(html, base_url, output_format)


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

    # extract title (first h1)
    for line in lines:
        if line.startswith("# "):
            document["title"] = line[2:].strip()
            break

    # process other elements with a very simple parser
    # this is just a fallback implementation
    current_block: list[str] = []
    in_code_block = False
    code_lang = ""

    for line in lines:
        # skip title line which we already processed
        if line.strip() == f"# {document['title']}":
            continue

        # handle headings
        if line.startswith("#") and not in_code_block:
            level = 0
            while level < len(line) and line[level] == "#":
                level += 1
            if level <= 6 and level < len(line) and line[level] == " ":
                document["headings"].append(
                    {"level": level, "text": line[level + 1 :].strip()}
                )

        # handle code blocks
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

        # collect code block content
        elif in_code_block:
            current_block.append(line)

        # handle blockquotes
        elif line.startswith(">") and not in_code_block:
            document["blockquotes"].append(line[1:].strip())

        # handle paragraphs (very simplified)
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
    # Root tag is capitalized to match current integration test expectations.
    # Consider updating tests to match the intended API design instead of changing implementation for tests.
    root = ET.Element("Document")

    # add title
    title = ET.SubElement(root, "title")
    title.text = document["title"]

    # add base url
    base_url = ET.SubElement(root, "base_url")
    base_url.text = document["base_url"]

    # add headings
    headings = ET.SubElement(root, "headings")
    for h in document["headings"]:
        heading = ET.SubElement(headings, "heading")
        heading.set("level", str(h["level"]))
        heading.text = h["text"]

    # add paragraphs
    paragraphs = ET.SubElement(root, "paragraphs")
    for p in document["paragraphs"]:
        paragraph = ET.SubElement(paragraphs, "paragraph")
        paragraph.text = p

    # add other elements similarly
    # this is simplified for brevity

    # convert to string with pretty formatting
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
    # Basic input validation to mirror strict Rust bindings behavior
    if not isinstance(markdown, str):
        raise TypeError("markdown must be a string")
    if not isinstance(chunk_size, int) or not isinstance(chunk_overlap, int):
        raise TypeError("chunk_size and chunk_overlap must be integers")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    if RUST_AVAILABLE:
        try:
            return _rs_chunk_markdown(markdown, chunk_size, chunk_overlap)
        except Exception as e:
            logger.warning(f"Error in Rust chunking, falling back to Python: {e}")

    # fall back to python implementation
    from markdown_lab.utils.chunk_utils import create_semantic_chunks

    chunks = create_semantic_chunks(
        content=markdown,
        source_url="",  # not used for content
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return [chunk.content for chunk in chunks]


def render_js_page(url: str, wait_time_ms: Optional[int] = None) -> Optional[str]:
    """
    Renders a JavaScript-enabled web page and returns the resulting HTML content.

    If the Rust extension is available, uses it to render the page. Otherwise, logs a warning and returns None, as Python fallback is not implemented.
    """
    # Input validation to align with Rust bindings
    if not isinstance(url, str):
        raise TypeError("url must be a string")
    if wait_time_ms is not None and not isinstance(wait_time_ms, int):
        raise TypeError("wait_time_ms must be an integer or None")

    if RUST_AVAILABLE:
        try:
            return _rs_render_js_page(url, wait_time_ms)
        except Exception as e:
            logger.warning(f"Error in Rust JS rendering, falling back to Python: {e}")

    # fall back to python implementation
    # this would require a js renderer like playwright or selenium
    # for now, we'll just log a warning and return none
    logger.warning(
        "JS rendering requires the Rust extension or an external browser automation tool"
    )
    return None
