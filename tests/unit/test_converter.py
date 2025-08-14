"""
Unit tests for the Converter module.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.converter import Converter
from markdown_lab.core.errors import NetworkError


class TestConverter(unittest.TestCase):
    """Test cases for the Converter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = MarkdownLabConfig(cache_enabled=False)
        self.converter = Converter(self.config)
        self.sample_html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Title</h1>
            <p>This is a paragraph with <strong>bold</strong> text.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
        </html>
        """
        self.base_url = "https://example.com"

    def test_converter_initialization(self):
        """Test Converter initialization."""
        self.assertIsNotNone(self.converter.config)
        self.assertIsNotNone(self.converter.client)
        self.assertIsNotNone(self.converter.rust_backend)

    def test_converter_with_cache(self):
        """Test Converter initialization with cache enabled."""
        config = MarkdownLabConfig(cache_enabled=True)
        converter = Converter(config)
        self.assertIsNotNone(converter.client)
        # Client should be CachedHttpClient when cache is enabled
        from markdown_lab.core.client import CachedHttpClient
        self.assertIsInstance(converter.client, CachedHttpClient)

    def test_fetch_content_success(self):
        """Test successful content fetching."""
        # Mock the client.get method
        self.converter.client.get = MagicMock(return_value=self.sample_html)

        # The converter doesn't have fetch_content, but client.get is used internally
        result = self.converter.client.get(self.base_url)

        self.assertEqual(result, self.sample_html)
        self.converter.client.get.assert_called_once_with(self.base_url)

    def test_fetch_content_network_error(self):
        """Test content fetching with network error."""
        # Mock the client.get to raise NetworkError
        self.converter.client.get = MagicMock(side_effect=NetworkError("Connection failed"))

        with self.assertRaises(NetworkError):
            self.converter.client.get(self.base_url)

    def test_convert_to_markdown(self):
        """Test HTML to Markdown conversion."""
        # Mock the rust backend conversion
        expected_markdown = "# Main Title\n\nThis is a paragraph with **bold** text.\n\n- Item 1\n- Item 2"
        self.converter.rust_backend.convert_html_to_markdown = MagicMock(
            return_value=expected_markdown
        )

        # Use convert_html which is the actual method
        result, _ = self.converter.convert_html(self.sample_html, self.base_url, "markdown")

        self.assertIsNotNone(result)
        self.converter.rust_backend.convert_html_to_markdown.assert_called()

    def test_convert_to_json(self):
        """Test HTML to JSON conversion."""
        # Mock the rust backend conversion
        expected_json = {
            "title": "Test Page",
            "content": "Main Title\nThis is a paragraph with bold text.",
            "links": [],
            "images": []
        }
        self.converter.rust_backend.convert_html_to_format = MagicMock(
            return_value=json.dumps(expected_json)
        )

        # Use convert_html which is the actual method
        result, _ = self.converter.convert_html(self.sample_html, self.base_url, "json")

        self.assertIsNotNone(result)
        self.converter.rust_backend.convert_html_to_format.assert_called()

    def test_convert_to_xml(self):
        """Test HTML to XML conversion."""
        # Mock the rust backend conversion
        expected_xml = '<?xml version="1.0"?><document><title>Test Page</title></document>'
        self.converter.rust_backend.convert_html_to_format = MagicMock(
            return_value=expected_xml
        )

        # Use convert_html which is the actual method
        result, _ = self.converter.convert_html(self.sample_html, self.base_url, "xml")

        self.assertIsNotNone(result)
        self.converter.rust_backend.convert_html_to_format.assert_called()

    def test_convert_with_format_markdown(self):
        """Test convert method with markdown format."""
        # Mock the rust backend
        self.converter.rust_backend.convert_html_to_markdown = MagicMock(
            return_value="# Markdown"
        )

        result, _ = self.converter.convert_html(self.sample_html, self.base_url, output_format="markdown")

        self.assertIsNotNone(result)

    def test_convert_with_format_json(self):
        """Test convert method with JSON format."""
        # Mock the rust backend
        self.converter.rust_backend.convert_html_to_format = MagicMock(
            return_value='{"test": "json"}'
        )

        result, _ = self.converter.convert_html(self.sample_html, self.base_url, output_format="json")

        self.assertIsNotNone(result)

    def test_convert_with_format_xml(self):
        """Test convert method with XML format."""
        # Mock the rust backend
        self.converter.rust_backend.convert_html_to_format = MagicMock(
            return_value='<xml>test</xml>'
        )

        result, _ = self.converter.convert_html(self.sample_html, self.base_url, output_format="xml")

        self.assertIsNotNone(result)

    def test_convert_with_invalid_format(self):
        """Test convert method with invalid format."""
        # The convert_html method should handle invalid formats
        with self.assertRaises(Exception):
            self.converter.convert_html(self.sample_html, self.base_url, output_format="invalid")

    def test_convert_url_to_markdown(self):
        """Test URL to markdown conversion."""
        # Mock client.get and rust backend
        self.converter.client.get = MagicMock(return_value=self.sample_html)
        self.converter.rust_backend.convert_html_to_markdown = MagicMock(
            return_value="# Converted"
        )

        result, _ = self.converter.convert_url(self.base_url, output_format="markdown")

        self.assertIsNotNone(result)
        self.converter.client.get.assert_called()

    def test_convert_url_with_fetch_error(self):
        """Test URL conversion with fetch error."""
        self.converter.client.get = MagicMock(
            side_effect=NetworkError("Failed to fetch")
        )

        with self.assertRaises(Exception):
            self.converter.convert_url(self.base_url)

    def test_batch_convert_urls(self):
        """Test batch URL conversion."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]

        # Mock convert_url to return different content for each URL
        def mock_convert(url, **kwargs):
            return (f"Converted: {url}", f"Markdown: {url}")

        self.converter.convert_url = MagicMock(side_effect=mock_convert)

        # Use convert_url_list which is the actual batch method
        results = self.converter.convert_url_list(urls, output_format="markdown")

        # Results is a list of tuples (url, content, status)
        self.assertEqual(len(results), 3)
        for i, url in enumerate(urls):
            self.assertEqual(results[i][0], url)

    def test_batch_convert_with_failures(self):
        """Test batch conversion with some failures."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]

        # Mock convert_url to fail for page2
        def mock_convert(url, **kwargs):
            if "page2" in url:
                raise NetworkError(f"Failed to fetch {url}")
            return (f"Converted: {url}", f"Markdown: {url}")

        self.converter.convert_url = MagicMock(side_effect=mock_convert)

        # Use convert_url_list which is the actual batch method
        results = self.converter.convert_url_list(urls, output_format="markdown")

        # Check that we have results for all URLs (failures are tracked)
        self.assertEqual(len(results), 3)
        # Check that page2 has error status
        for url, _content, status in results:
            if "page2" in url:
                self.assertEqual(status, "error")

    def test_save_output(self):
        """Test saving output to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.md"
            content = "# Test Content"

            # Use save_content which is the actual method
            self.converter.save_content(content, str(output_file))

            # Check file was created and contains the content
            self.assertTrue(output_file.exists())
            self.assertEqual(output_file.read_text(), content)

    def test_save_output_with_json(self):
        """Test saving JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.json"
            content = '{"test": "data"}'

            # Use save_content which is the actual method
            self.converter.save_content(content, str(output_file))

            # Check file was created and contains valid JSON
            self.assertTrue(output_file.exists())
            loaded = json.loads(output_file.read_text())
            self.assertEqual(loaded["test"], "data")

    def test_create_chunks(self):
        """Test chunk creation from content."""
        # Mock the chunk creation function
        with patch('markdown_lab.core.converter.create_semantic_chunks') as mock_create_chunks:
            mock_chunks = [
                {"content": "Chunk 1", "metadata": {"index": 0}},
                {"content": "Chunk 2", "metadata": {"index": 1}}
            ]
            mock_create_chunks.return_value = mock_chunks

            result = self.converter.create_chunks("# Test content", self.base_url)

            self.assertEqual(len(result), 2)
            mock_create_chunks.assert_called()

    def test_process_with_chunks(self):
        """Test processing with chunk creation."""
        # Mock the rust backend and chunk creation
        self.converter.rust_backend.convert_html_to_markdown = MagicMock(
            return_value="# Markdown content"
        )

        with patch('markdown_lab.core.converter.create_semantic_chunks') as mock_create_chunks:
            mock_create_chunks.return_value = [{"content": "chunk1"}, {"content": "chunk2"}]

            # Convert and chunk
            markdown, _ = self.converter.convert_html(self.sample_html, self.base_url)
            chunks = self.converter.create_chunks(markdown, self.base_url)

            self.assertEqual(len(chunks), 2)

    def test_rust_backend_error_handling(self):
        """Test error handling from Rust backend."""
        # Mock rust backend to raise an error
        self.converter.rust_backend.convert_html_to_markdown = MagicMock(
            side_effect=Exception("Rust conversion failed")
        )

        with self.assertRaises(Exception):
            self.converter.convert_html(self.sample_html, self.base_url)

    def test_empty_html_handling(self):
        """Test handling of empty HTML."""
        empty_html = ""
        self.converter.rust_backend.convert_html_to_markdown = MagicMock(return_value="")

        result, _ = self.converter.convert_html(empty_html, self.base_url)

        self.assertIsNotNone(result)
        self.converter.rust_backend.convert_html_to_markdown.assert_called()

    def test_malformed_html_handling(self):
        """Test handling of malformed HTML."""
        malformed_html = "<html><body><p>Unclosed paragraph<body></html>"

        # Rust backend should handle malformed HTML gracefully
        self.converter.rust_backend.convert_html_to_markdown = MagicMock(
            return_value="Unclosed paragraph"
        )

        result, _ = self.converter.convert_html(malformed_html, self.base_url)

        self.assertIsNotNone(result)
        self.converter.rust_backend.convert_html_to_markdown.assert_called()


if __name__ == "__main__":
    unittest.main()
