"""
Tests for streaming HTML parser.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.errors import ParsingError
from markdown_lab.processing.streaming_parser import (
    StreamingElement,
    StreamingHTMLParser,
)


@pytest.fixture
def config():
    """Create test configuration."""
    return MarkdownLabConfig(requests_per_second=10.0, timeout=30)


@pytest.fixture
def parser(config):
    """Create streaming parser instance."""
    return StreamingHTMLParser(config)


@pytest.fixture
def mock_html_response():
    """Create mock HTML response chunks."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Main Title</h1>
        <p class="intro">This is an introduction paragraph.</p>
        <div class="content">
            <h2>Section 1</h2>
            <p>Content paragraph 1</p>
            <p>Content paragraph 2</p>
            <a href="/link1">Link 1</a>
            <a href="/link2" title="Link Title">Link 2</a>
        </div>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
    </body>
    </html>
    """

    # Split into chunks to simulate streaming
    chunk_size = 100
    return [
        html_content[i : i + chunk_size].encode()
        for i in range(0, len(html_content), chunk_size)
    ]


class TestStreamingElement:
    """Test StreamingElement class."""

    def test_basic_element(self):
        """Test basic element creation."""
        elem = StreamingElement(tag="p", text="Hello world", attrib={"class": "intro"})

        assert elem.tag == "p"
        assert elem.text == "Hello world"
        assert elem.attrib["class"] == "intro"

    def test_to_dict(self):
        """Test dictionary conversion."""
        elem = StreamingElement(tag="div", text="Parent", attrib={"id": "main"})
        child = StreamingElement(tag="p", text="Child")
        elem.children.append(child)

        result = elem.to_dict()
        assert result["tag"] == "div"
        assert result["text"] == "Parent"
        assert result["attrib"]["id"] == "main"
        assert len(result["children"]) == 1
        assert result["children"][0]["tag"] == "p"


def setup_mock_client(mock_html_response):
    """Helper function to set up mock httpx client."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()

    # Create async iterator for chunks
    async def aiter_bytes(chunk_size):
        for chunk in mock_html_response:
            yield chunk

    mock_response.aiter_bytes = aiter_bytes

    # Mock the stream context manager
    stream_context = AsyncMock()
    stream_context.__aenter__.return_value = mock_response
    stream_context.__aexit__.return_value = None
    mock_client.stream.return_value = stream_context

    return mock_client


class TestStreamingHTMLParser:
    """Test StreamingHTMLParser functionality."""

    @pytest.mark.asyncio
    async def test_count_elements(self, parser, mock_html_response):
        """Test element counting."""
        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = setup_mock_client(mock_html_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Count elements
            counts = await parser.count_elements("https://example.com")

            # Verify counts
            assert "html" in counts
            assert "body" in counts
            assert "p" in counts
            assert counts["p"] >= 3  # Should have at least 3 paragraphs
            assert counts["h1"] == 1
            assert counts["h2"] == 1

    @pytest.mark.asyncio
    async def test_extract_content_blocks(self, parser, mock_html_response):
        """Test content block extraction."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            async def aiter_bytes(chunk_size):
                for chunk in mock_html_response:
                    yield chunk

            mock_response.aiter_bytes = aiter_bytes
            mock_client.stream.return_value.__aenter__.return_value = mock_response

            # Extract content blocks
            blocks = []
            async for tag, text in parser.extract_content_blocks("https://example.com"):
                blocks.append((tag, text))

            # Verify content
            assert blocks

            # Check for expected content
            h1_blocks = [b for b in blocks if b[0] == "h1"]
            assert h1_blocks
            assert any("Main Title" in b[1] for b in h1_blocks)

            p_blocks = [b for b in blocks if b[0] == "p"]
            assert len(p_blocks) >= 3
            assert any("introduction" in b[1] for b in p_blocks)

    @pytest.mark.asyncio
    async def test_extract_links(self, parser, mock_html_response):
        """Test link extraction."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            async def aiter_bytes(chunk_size):
                for chunk in mock_html_response:
                    yield chunk

            mock_response.aiter_bytes = aiter_bytes
            mock_client.stream.return_value.__aenter__.return_value = mock_response

            # Extract links
            links = []
            async for link in parser.extract_links("https://example.com"):
                links.append(link)

            # Verify links
            assert len(links) >= 2
            assert any(link["href"] == "/link1" for link in links)
            assert any(link["href"] == "/link2" for link in links)

            # Check link with title
            link2 = next((l for l in links if l["href"] == "/link2"), None)
            assert link2 is not None
            assert link2["text"] in ["Link 2", "Link Title"]

    @pytest.mark.asyncio
    async def test_find_elements_by_class(self, parser, mock_html_response):
        """Test finding elements by class."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            async def aiter_bytes(chunk_size):
                for chunk in mock_html_response:
                    yield chunk

            mock_response.aiter_bytes = aiter_bytes
            mock_client.stream.return_value.__aenter__.return_value = mock_response

            # Find elements with class 'intro'
            elements = []
            async for elem in parser.find_elements_by_class(
                "https://example.com", "intro"
            ):
                elements.append(elem)

            # Verify results
            assert elements
            assert any(elem.tag == "p" for elem in elements)
            assert any("intro" in elem.attrib.get("class", "") for elem in elements)

    @pytest.mark.asyncio
    async def test_network_error_handling(self, parser):
        """Test network error handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock network error
            mock_client.stream.side_effect = Exception("Network error")

            # Should raise NetworkError
            with pytest.raises(ParsingError) as exc_info:
                await parser.count_elements("https://example.com")

            assert "Failed to parse HTML stream" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parsing_error_recovery(self, parser):
        """Test recovery from parsing errors."""
        # Create malformed HTML chunks
        bad_html_chunks = [
            b"<html><body>",
            b"<p>Good paragraph</p>",
            b"<div><p>Unclosed div",  # Missing closing tags
            b"<p>Another good paragraph</p>",
            b"</body></html>",
        ]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            async def aiter_bytes(chunk_size):
                for chunk in bad_html_chunks:
                    yield chunk

            mock_response.aiter_bytes = aiter_bytes
            mock_client.stream.return_value.__aenter__.return_value = mock_response

            # Should handle parsing errors gracefully
            blocks = []
            async for tag, text in parser.extract_content_blocks("https://example.com"):
                blocks.append((tag, text))

            # Should still extract valid content
            assert len(blocks) >= 2  # At least the good paragraphs
            p_blocks = [b for b in blocks if b[0] == "p"]
            assert any("Good paragraph" in b[1] for b in p_blocks)
            assert any("Another good paragraph" in b[1] for b in p_blocks)


class TestMemoryEfficiency:
    """Test memory efficiency of streaming parser."""

    @pytest.mark.asyncio
    async def test_large_document_streaming(self, parser):
        """Test streaming of large documents."""
        # Create a large HTML document
        large_html_parts = [
            b"<html><body>",
        ]

        # Add 1000 paragraphs
        for i in range(1000):
            large_html_parts.append(
                f"<p>This is paragraph {i} with some content to make it larger.</p>".encode()
            )

        large_html_parts.append(b"</body></html>")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            async def aiter_bytes(chunk_size):
                # Yield in small chunks to simulate streaming
                for part in large_html_parts:
                    yield part

            mock_response.aiter_bytes = aiter_bytes
            mock_client.stream.return_value.__aenter__.return_value = mock_response

            # Count paragraphs without loading entire document
            p_count = 0
            async for tag, text in parser.extract_content_blocks("https://example.com"):
                if tag == "p":
                    p_count += 1
                    # Verify we're getting content
                    assert "paragraph" in text
                    assert str(p_count - 1) in text or str(p_count) in text

            # Should have processed all paragraphs
            assert p_count == 1000
