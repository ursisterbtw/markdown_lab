"""Edge case tests for markdown_lab."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from markdown_lab.core.client import HttpClient
from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.converter import Converter
from markdown_lab.core.errors import ConversionError, NetworkError, ParsingError


class TestMalformedHTML:
    """Test handling of malformed HTML."""

    def test_unclosed_tags(self):
        """Test handling of unclosed HTML tags."""
        converter = Converter()
        malformed_html = "<div><p>Unclosed paragraph<div>Another div</div>"

        # Should handle gracefully without crashing
        result, _ = converter.convert_html(malformed_html, "http://example.com")
        assert result is not None
        assert isinstance(result, str)

    def test_nested_tags_overflow(self):
        """Test deeply nested tags that could cause stack overflow."""
        converter = Converter()
        # Create deeply nested HTML
        nested_html = "<div>" * 100 + "Content" + "</div>" * 100

        result, _ = converter.convert_html(nested_html, "http://example.com")
        assert result is not None
        assert "Content" in result

    def test_invalid_encoding(self):
        """Test handling of HTML with invalid encoding."""
        converter = Converter()
        # HTML with mixed/invalid encoding
        invalid_html = b"<html><body>\xff\xfe Invalid bytes </body></html>".decode('utf-8', errors='replace')

        result, _ = converter.convert_html(invalid_html, "http://example.com")
        assert result is not None

    def test_empty_html(self):
        """Test handling of empty HTML."""
        converter = Converter()

        for empty in ["", " ", "\n", "\t\n"]:
            result, _ = converter.convert_html(empty, "http://example.com")
            assert result is not None

    def test_html_bomb(self):
        """Test protection against HTML bombs (exponential entity expansion)."""
        converter = Converter()
        # Simple HTML bomb pattern
        html_bomb = """
        <!DOCTYPE html>
        <html>
        <body>
        """ + "<div>" * 10000 + "x" + "</div>" * 10000 + """
        </body>
        </html>
        """

        # Should handle without consuming excessive memory
        result, _ = converter.convert_html(html_bomb[:50000], "http://example.com")  # Limit input size
        assert result is not None

    def test_special_characters(self):
        """Test handling of special characters and entities."""
        converter = Converter()
        html = """
        <html>
        <body>
        <p>&lt;script&gt;alert('XSS')&lt;/script&gt;</p>
        <p>Unicode: 你好世界 🚀</p>
        <p>Entities: &amp; &quot; &apos; &nbsp;</p>
        </body>
        </html>
        """

        result, _ = converter.convert_html(html, "http://example.com")
        assert result is not None
        assert "script" not in result or "&lt;script" in result  # Should escape or remove
        assert "你好世界" in result  # Should preserve Unicode


class TestNetworkFailures:
    """Test handling of network failures."""

    def test_connection_timeout(self):
        """Test handling of connection timeouts."""
        config = MarkdownLabConfig(timeout=0.001)  # Very short timeout
        client = HttpClient(config)

        with pytest.raises(NetworkError) as exc_info:
            # This should timeout
            client.get("http://httpbin.org/delay/10")

        assert "timeout" in str(exc_info.value).lower() or "timed out" in str(exc_info.value).lower()

    def test_dns_resolution_failure(self):
        """Test handling of DNS resolution failures."""
        client = HttpClient()

        with pytest.raises(NetworkError) as exc_info:
            client.get("http://this-domain-definitely-does-not-exist-12345.com")

        assert exc_info.value.url == "http://this-domain-definitely-does-not-exist-12345.com"

    def test_connection_refused(self):
        """Test handling of connection refused errors."""
        client = HttpClient()

        with pytest.raises(NetworkError) as exc_info:
            # Port 1 is typically closed/refused
            client.get("http://localhost:1")

        assert "connection" in str(exc_info.value).lower() or "refused" in str(exc_info.value).lower()

    def test_http_error_codes(self):
        """Test handling of HTTP error codes."""
        client = HttpClient()

        # Test 404
        with pytest.raises(NetworkError) as exc_info:
            client.get("http://httpbin.org/status/404")
        assert exc_info.value.status_code == 404

        # Test 500
        with pytest.raises(NetworkError) as exc_info:
            client.get("http://httpbin.org/status/500")
        assert exc_info.value.status_code == 500

    def test_ssl_certificate_error(self):
        """Test handling of SSL certificate errors."""
        client = HttpClient()

        with pytest.raises(NetworkError) as exc_info:
            # This domain has certificate issues
            client.get("https://expired.badssl.com/")

        assert "ssl" in str(exc_info.value).lower() or "certificate" in str(exc_info.value).lower()

    @patch('requests.Session.request')
    def test_max_retries_exhausted(self, mock_request):
        """Test that max retries are properly exhausted."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")

        config = MarkdownLabConfig(max_retries=2)
        client = HttpClient(config)

        with pytest.raises(NetworkError) as exc_info:
            client.get("http://example.com")

        # Should have tried initial + 2 retries = 3 total
        assert mock_request.call_count == 3
        assert "MAX_RETRIES" in exc_info.value.error_code or "retries" in str(exc_info.value).lower()

    @patch('requests.Session.request')
    def test_partial_response(self, mock_request):
        """Test handling of partial/interrupted responses."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = "Partial cont"  # Incomplete content
        mock_response.headers = {'Content-Length': '1000'}  # Claims more content
        mock_request.return_value = mock_response

        client = HttpClient()
        # Should not crash on partial content
        result = client.get("http://example.com")
        assert result == "Partial cont"


class TestMemoryLimits:
    """Test memory limit handling."""

    def test_large_response_handling(self):
        """Test handling of very large responses."""
        converter = Converter()

        # Create a large HTML document (but not too large to process)
        large_html = "<html><body>" + "<p>Large content block</p>" * 10000 + "</body></html>"

        # Should handle without memory issues
        result, _ = converter.convert_html(large_html, "http://example.com")
        assert result is not None
        assert len(result) > 0

    def test_chunk_size_limits(self):
        """Test chunking with size limits."""
        from markdown_lab.core.chunker import create_semantic_chunks

        # Create large markdown
        large_markdown = "# Section\n\n" + "This is a paragraph. " * 1000

        # Should chunk appropriately
        chunks = create_semantic_chunks(large_markdown, chunk_size=500, chunk_overlap=50)
        assert len(chunks) > 1
        assert all(len(chunk) <= 600 for chunk in chunks)  # Allow some overflow for complete sentences

    @patch('markdown_lab.core.converter.Converter._fetch_url')
    def test_memory_limit_enforcement(self, mock_fetch):
        """Test that memory limits are enforced."""
        converter = Converter()

        # Simulate a response that's too large
        huge_response = "x" * (converter.config.max_file_size + 1)
        mock_fetch.return_value = huge_response

        with pytest.raises(ConversionError) as exc_info:
            converter.convert_url("http://example.com")

        assert "size" in str(exc_info.value).lower() or "large" in str(exc_info.value).lower()

    def test_concurrent_processing_memory(self):
        """Test memory handling during concurrent processing."""
        from concurrent.futures import ThreadPoolExecutor
        converter = Converter()

        def process_html():
            html = "<html><body><p>Test content</p></body></html>"
            return converter.convert_html(html, "http://example.com")

        # Process multiple conversions concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_html) for _ in range(20)]
            results = [f.result() for f in futures]

        assert len(results) == 20
        assert all(r is not None for r in results)


class TestBoundaryConditions:
    """Test boundary conditions."""

    def test_zero_length_inputs(self):
        """Test handling of zero-length inputs."""
        converter = Converter()

        # Zero-length HTML
        result, _ = converter.convert_html("", "http://example.com")
        assert result is not None

        # Zero-length URL (should fail gracefully)
        with pytest.raises((ConversionError, NetworkError, ValueError)):
            converter.convert_url("")

    def test_maximum_url_length(self):
        """Test handling of extremely long URLs."""
        converter = Converter()

        # Create a very long URL (most browsers limit ~2000 chars)
        long_url = "http://example.com/" + "x" * 3000

        with pytest.raises((ConversionError, NetworkError)):
            converter.convert_url(long_url)

    def test_null_bytes_in_input(self):
        """Test handling of null bytes in input."""
        converter = Converter()

        # HTML with null bytes
        html_with_nulls = "<html>\x00<body>\x00<p>Test</p>\x00</body>\x00</html>"

        # Should handle gracefully
        result, _ = converter.convert_html(html_with_nulls, "http://example.com")
        assert result is not None
        assert "\x00" not in result  # Null bytes should be removed

    def test_recursive_redirects(self):
        """Test handling of recursive redirects."""
        with patch('requests.Session.request') as mock_request:
            # Simulate infinite redirect
            mock_response = MagicMock()
            mock_response.status_code = 301
            mock_response.headers = {'Location': 'http://example.com/redirect'}
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
            mock_request.return_value = mock_response

            client = HttpClient()
            with pytest.raises(NetworkError):
                client.get("http://example.com/redirect")
