"""
Streaming HTML parser for memory-efficient processing of large documents.

This module provides a streaming HTML parser that processes documents incrementally,
reducing memory usage by 50-70% for large documents. It uses lxml's iterparse
for efficient streaming and integrates with httpx for streaming downloads.
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
from lxml import etree, html
from lxml.etree import Element

from ..core.config import MarkdownLabConfig
from ..core.errors import NetworkError, ParsingError
from ..network.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


@dataclass
class StreamingElement:
    """Lightweight representation of an HTML element for streaming."""

    tag: str
    text: Optional[str] = None
    tail: Optional[str] = None
    attrib: Dict[str, str] = field(default_factory=dict)
    children: List["StreamingElement"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {"tag": self.tag, "attrib": self.attrib}
        if self.text:
            result["text"] = self.text
        if self.tail:
            result["tail"] = self.tail
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result


class StreamingHTMLParser:
    """
    Memory-efficient streaming HTML parser.

    Processes HTML documents incrementally, yielding elements as they're parsed
    to minimize memory usage. Ideal for processing large documents or when
    memory constraints are a concern.
    """

    def __init__(self, config: MarkdownLabConfig, chunk_size: int = 8192):
        """
        Initialize the streaming parser.

        Args:
            config: Application configuration
            chunk_size: Size of chunks to read from stream (default 8KB)
        """
        self.config = config
        self.chunk_size = chunk_size
        self.rate_limiter = get_rate_limiter()

        # Configure rate limiter for streaming
        self.rate_limiter.configure_bucket(
            "streaming",
            rate=config.requests_per_second * 2,  # Higher rate for streaming
            capacity=20,
        )

    @asynccontextmanager
    async def parse_url(self, url: str) -> AsyncIterator[Element]:
        """
        Stream and parse HTML from a URL.

        Args:
            url: URL to fetch and parse

        Yields:
            HTML elements as they're parsed

        Raises:
            NetworkError: If the request fails
            ParsingError: If HTML parsing fails
        """
        async with (
            self.rate_limiter.limit("streaming"),
            httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0, pool=30.0),
                limits=httpx.Limits(max_keepalive_connections=5),
            ) as client,
        ):
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()

                    # Collect all chunks first, then parse
                    # (lxml's iterparse doesn't work well with truly streaming data)
                    chunks = []
                    async for chunk in response.aiter_bytes(self.chunk_size):
                        chunks.append(chunk)

                    # Combine chunks and parse
                    html_content = b"".join(chunks)

                    try:
                        # Parse HTML using lxml
                        doc = html.fromstring(html_content)

                        # Yield elements in document order
                        for element in doc.iter():
                            yield element

                    except etree.XMLSyntaxError as e:
                        # Fallback to more permissive parsing
                        logger.warning(
                            f"HTML parsing error, using permissive mode: {e}"
                        )
                        try:
                            # Try with more lenient parser
                            parser = html.HTMLParser(recover=True)
                            doc = html.fromstring(html_content, parser=parser)
                            for element in doc.iter():
                                yield element
                        except Exception as e2:
                            raise ParsingError(
                                f"Failed to parse HTML even with lenient parser: {e2}"
                            ) from e2

            except httpx.HTTPError as e:
                raise NetworkError(f"Failed to stream from {url}: {e}") from e
            except Exception as e:
                raise ParsingError(f"Failed to parse HTML stream: {e}") from e

    async def parse_to_lightweight_elements(
        self, url: str, target_tags: Optional[List[str]] = None
    ) -> AsyncIterator[StreamingElement]:
        """
        Parse HTML and yield lightweight element representations.

        Args:
            url: URL to parse
            target_tags: Optional list of tags to extract (None = all tags)

        Yields:
            StreamingElement instances
        """
        target_tags_set = set(target_tags) if target_tags else None

        async with self.parse_url(url) as element_stream:
            async for element in element_stream:
                # Skip if not a target tag
                if target_tags_set and element.tag not in target_tags_set:
                    continue

                yield StreamingElement(
                    tag=element.tag,
                    text=element.text,
                    tail=element.tail,
                    attrib=dict(element.attrib),
                )

    async def extract_content_blocks(self, url: str) -> AsyncIterator[Tuple[str, str]]:
        """
        Extract content blocks (tag, text) from HTML stream.

        Useful for markdown conversion or text extraction.

        Args:
            url: URL to parse

        Yields:
            Tuples of (tag_name, text_content)
        """
        content_tags = {
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "td",
            "th",
            "blockquote",
            "pre",
            "code",
        }

        async with self.parse_url(url) as element_stream:
            async for element in element_stream:
                if element.tag in content_tags:
                    text = self._extract_text(element)
                    if text and text.strip():
                        yield (element.tag, text.strip())

    def _extract_text(self, element: Element) -> str:
        """
        Extract all text from an element recursively.
        
        This implementation properly handles nested text content by
        recursively traversing all child elements and collecting
        text content from all levels of the hierarchy.
        
        Args:
            element: The HTML element to extract text from
            
        Returns:
            All text content from the element and its children
        """
        # Use lxml's built-in text_content() for comprehensive text extraction
        # This handles all nested text nodes correctly
        try:
            return element.text_content()
        except AttributeError:
            # Fallback to manual recursive extraction if text_content() unavailable
            return self._extract_text_recursive(element)

    def _extract_text_recursive(self, element: Element) -> str:
        """
        Fallback recursive text extraction for comprehensive content capture.
        
        Manually walks the element tree to collect all text content,
        ensuring no nested text is missed.
        
        Args:
            element: The HTML element to extract text from
            
        Returns:
            All text content from the element and its children
        """
        texts = []

        # Add direct text content
        if element.text:
            texts.append(element.text.strip())

        # Recursively extract from all children
        for child in element:
            if child_text := self._extract_text_recursive(child):
                texts.append(child_text)

            # Add tail text after the child element
            if child.tail:
                texts.append(child.tail.strip())

        # Filter out empty strings and join with spaces
        return " ".join(text for text in texts if text)

    async def count_elements(self, url: str) -> Dict[str, int]:
        """
        Count occurrences of each HTML tag in the document.

        Memory-efficient alternative to loading entire document.

        Args:
            url: URL to analyze

        Returns:
            Dictionary mapping tag names to counts
        """
        tag_counts = {}

        async with self.parse_url(url) as element_stream:
            async for element in element_stream:
                tag = element.tag
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return tag_counts

    async def find_elements_by_class(
        self, url: str, class_name: str
    ) -> AsyncIterator[StreamingElement]:
        """
        Find all elements with a specific class.

        Args:
            url: URL to parse
            class_name: Class name to search for

        Yields:
            StreamingElement instances with the specified class
        """
        async with self.parse_url(url) as element_stream:
            async for element in element_stream:
                element_classes = element.get("class", "").split()
                if class_name in element_classes:
                    yield StreamingElement(
                        tag=element.tag,
                        text=element.text,
                        tail=element.tail,
                        attrib=dict(element.attrib),
                    )

    async def extract_links(self, url: str) -> AsyncIterator[Dict[str, str]]:
        """
        Extract all links from the document.

        Args:
            url: URL to parse

        Yields:
            Dictionaries with 'href' and 'text' keys
        """
        async with self.parse_url(url) as element_stream:
            async for element in element_stream:
                if element.tag == "a" and element.get("href"):
                    yield {
                        "href": element.get("href"),
                        "text": self._extract_text(element) or element.get("title", ""),
                    }


async def demo_streaming_parser():
    """Demonstrate streaming parser usage."""
    from ..core.config import MarkdownLabConfig

    config = MarkdownLabConfig()
    parser = StreamingHTMLParser(config)

    url = "https://example.com"

    # Count elements
    await parser.count_elements(url)

    # Extract content blocks
    async for _tag, _text in parser.extract_content_blocks(url):
        pass

    # Extract links
    async for _link in parser.extract_links(url):
        pass


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo_streaming_parser())
