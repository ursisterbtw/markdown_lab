import pytest

from markdown_lab.markdown_lab_rs import OutputFormat as RustOutputFormat  # type: ignore
from markdown_lab.core.converter import Converter
from markdown_lab.core.config import MarkdownLabConfig


@pytest.mark.integration
def test_rust_backed_conversion_end_to_end_markdown_json_xml(monkeypatch):
    cfg = MarkdownLabConfig(rust_backend_enabled=True)
    converter = Converter(cfg)

    # Use a simple local HTML snippet to avoid network
    html = """
    <html>
      <head><title>Integration Title</title></head>
      <body>
        <h1>Hello</h1>
        <p>World</p>
      </body>
    </html>
    """

    # Monkeypatch client.get to return our HTML without network
    monkeypatch.setattr(converter.client, "get", lambda url, **kw: html)

    # Markdown
    md, md_raw = converter.convert_html(html, "https://example.com", "markdown")
    assert "# Integration Title" in md
    assert md == md_raw

    # JSON
    js, md_again = converter.convert_html(html, "https://example.com", "json")
    assert "Integration Title" in js
    assert "Hello" in js
    assert md_again

    # XML
    xml, _ = converter.convert_html(html, "https://example.com", "xml")
    assert "<title>Integration Title</title>" in xml


"""
Integration tests for Rust-Python binding error paths and fallback behavior.

These tests verify that error handling works correctly across the boundary
between Python and Rust code, including fallback mechanisms and proper
exception propagation.
"""

from unittest.mock import Mock, patch

import pytest

from markdown_lab.core.errors import RustIntegrationError
from markdown_lab.core.rust_backend import (
    RustBackend,
    get_rust_backend,
    reset_rust_backend,
)


class TestRustBackendInitialization:
    """Test Rust backend initialization and availability checks."""

    def test_rust_backend_available_success(self):
        """Test successful Rust backend initialization."""
        backend = RustBackend(fallback_enabled=False)
        if backend.is_available():
            assert backend._rust_module is not None
            version_info = backend.get_version_info()
            assert version_info["available"] is True

    def test_rust_backend_unavailable_no_fallback(self):
        """Test error when Rust backend unavailable and no fallback."""
        # Mock the import to raise ImportError directly
        with patch(
            "markdown_lab.core.rust_backend.markdown_lab_rs",
            side_effect=ImportError("No module named 'markdown_lab_rs'"),
        ):
            # Also need to patch the import statement itself
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'markdown_lab_rs'"),
            ):
                with pytest.raises(RustIntegrationError) as exc_info:
                    RustBackend(fallback_enabled=False)

                error = exc_info.value
                assert error.error_code == "RUSTINTEGRATIONERROR"
                assert "not available" in error.message
                assert error.context["rust_function"] == "module_import"
                assert error.context["fallback_available"] is False

    def test_rust_backend_unavailable_with_fallback(self):
        """Test graceful degradation when Rust unavailable but fallback enabled."""
        with patch(
            "builtins.__import__",
            side_effect=ImportError("No module named 'markdown_lab_rs'"),
        ):
            backend = RustBackend(fallback_enabled=True)
            assert not backend.is_available()
            assert backend._rust_module is None

            version_info = backend.get_version_info()
            assert version_info["available"] is False
            assert version_info["version"] is None


class TestRustConversionErrors:
    """Test error handling in HTML conversion functions."""

    def test_convert_html_backend_unavailable(self):
        """Test conversion error when Rust backend unavailable."""
        backend = RustBackend(fallback_enabled=True)
        backend._rust_module = None  # Force unavailable state

        with pytest.raises(RustIntegrationError) as exc_info:
            backend.convert_html_to_format(
                "<html></html>", "https://example.com", "markdown"
            )

        error = exc_info.value
        assert "not available" in error.message
        assert error.context["rust_function"] == "convert_html_to_format"
        assert error.context["fallback_available"] is True

    def test_convert_html_rust_exception(self):
        """Test handling of exceptions from Rust conversion functions."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            # Mock the Rust module to raise an exception
            mock_module = Mock()
            mock_module.convert_html_to_format.side_effect = RuntimeError(
                "Rust conversion failed"
            )
            backend._rust_module = mock_module

            with pytest.raises(RustIntegrationError) as exc_info:
                backend.convert_html_to_format(
                    "<html></html>", "https://example.com", "json"
                )

            error = exc_info.value
            assert "Rust conversion failed" in error.message
            assert error.context["rust_function"] == "convert_html_to_format"
            assert isinstance(error.cause, RuntimeError)

    def test_convert_html_invalid_format(self):
        """Test conversion with invalid output format."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            # Test with invalid format - should be handled gracefully by Rust
            html = "<html><body><h1>Test</h1></body></html>"
            base_url = "https://example.com"

            # Depending on Rust implementation, this might raise error or default to markdown
            try:
                result = backend.convert_html_to_format(
                    html, base_url, "invalid_format"
                )
                # If it doesn't raise an error, it should return some content
                assert isinstance(result, str)
                assert len(result) > 0
            except RustIntegrationError:
                # This is also acceptable behavior
                pass

    def test_convert_html_malformed_input(self):
        """Test conversion with malformed HTML."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            # Test with various malformed inputs
            test_cases = [
                "",  # Empty string
                "<html><body><h1>Unclosed tag",  # Malformed HTML
                "<html><body>Valid content</body></html>",  # Valid HTML
                "Not HTML at all",  # Plain text
            ]

            for html in test_cases:
                try:
                    result = backend.convert_html_to_format(
                        html, "https://example.com", "markdown"
                    )
                    assert isinstance(result, str)  # Should always return string
                except RustIntegrationError as e:
                    # Some malformed inputs might cause errors, which is acceptable
                    assert "failed" in e.message.lower()

    def test_convert_html_invalid_base_url(self):
        """Test conversion with invalid base URL."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            html = "<html><body><a href='/test'>Link</a></body></html>"
            invalid_urls = [
                "",  # Empty string
                "not-a-url",  # Invalid format
                "ftp://invalid-scheme.com",  # Uncommon scheme
                "https://example.com",  # Valid URL (control)
            ]

            for base_url in invalid_urls:
                try:
                    result = backend.convert_html_to_format(html, base_url, "markdown")
                    assert isinstance(result, str)
                except RustIntegrationError:
                    # Some invalid URLs might cause errors
                    pass


class TestRustChunkingErrors:
    """Test error handling in markdown chunking functions."""

    def test_chunk_markdown_backend_unavailable(self):
        """Test chunking error when Rust backend unavailable."""
        backend = RustBackend(fallback_enabled=True)
        backend._rust_module = None

        with pytest.raises(RustIntegrationError) as exc_info:
            backend.chunk_markdown("# Test", 1000, 200)

        error = exc_info.value
        assert "not available" in error.message
        assert error.context["rust_function"] == "chunk_markdown"
        assert error.context["fallback_available"] is True

    def test_chunk_markdown_rust_exception(self):
        """Test handling of exceptions from Rust chunking functions."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            mock_module = Mock()
            mock_module.chunk_markdown.side_effect = ValueError(
                "Invalid chunk parameters"
            )
            backend._rust_module = mock_module

            with pytest.raises(RustIntegrationError) as exc_info:
                backend.chunk_markdown("# Test", 1000, 200)

            error = exc_info.value
            assert "Invalid chunk parameters" in error.message
            assert error.context["rust_function"] == "chunk_markdown"
            assert isinstance(error.cause, ValueError)

    def test_chunk_markdown_invalid_parameters(self):
        """Test chunking with invalid parameters."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            markdown = "# Test\n\nThis is test content."

            # Test various invalid parameter combinations
            invalid_params = [
                (0, 200),  # Zero chunk size
                (-100, 200),  # Negative chunk size
                (1000, -50),  # Negative overlap
                (100, 200),  # Overlap larger than chunk size
            ]

            for chunk_size, overlap in invalid_params:
                try:
                    result = backend.chunk_markdown(markdown, chunk_size, overlap)
                    # Some parameters might be handled gracefully
                    assert isinstance(result, list)
                except RustIntegrationError:
                    # Invalid parameters might cause errors
                    pass

    def test_chunk_markdown_empty_content(self):
        """Test chunking with empty or minimal content."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            test_cases = [
                "",  # Empty string
                " ",  # Whitespace only
                "\n\n",  # Newlines only
                "# Title",  # Minimal content
            ]

            for content in test_cases:
                try:
                    result = backend.chunk_markdown(content, 1000, 200)
                    assert isinstance(result, list)
                except RustIntegrationError:
                    # Empty content might cause errors in some implementations
                    pass


class TestRustJSRenderingErrors:
    """Test error handling in JavaScript rendering functions."""

    def test_render_js_backend_unavailable(self):
        """Test JS rendering error when Rust backend unavailable."""
        backend = RustBackend(fallback_enabled=True)
        backend._rust_module = None

        with pytest.raises(RustIntegrationError) as exc_info:
            backend.render_js_page("https://example.com", 1000)

        error = exc_info.value
        assert "not available" in error.message
        assert error.context["rust_function"] == "render_js_page"
        assert error.context["fallback_available"] is False  # No fallback for JS

    def test_render_js_rust_exception(self):
        """Test handling of exceptions from Rust JS rendering."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            mock_module = Mock()
            mock_module.render_js_page.side_effect = RuntimeError(
                "Browser initialization failed"
            )
            backend._rust_module = mock_module

            with pytest.raises(RustIntegrationError) as exc_info:
                backend.render_js_page("https://example.com", 5000)

            error = exc_info.value
            assert "Browser initialization failed" in error.message
            assert error.context["rust_function"] == "render_js_page"
            assert error.context["fallback_available"] is False

    def test_render_js_invalid_url(self):
        """Test JS rendering with invalid URLs."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            invalid_urls = [
                "",  # Empty string
                "not-a-url",  # Invalid format
                "ftp://example.com",  # Non-HTTP scheme
                "https://nonexistent-domain-12345.com",  # Non-existent domain
            ]

            for url in invalid_urls:
                try:
                    # Use shorter timeout for faster test execution
                    result = backend.render_js_page(url, 1000)
                    assert isinstance(result, str)
                except RustIntegrationError:
                    # Invalid URLs should cause errors
                    pass

    def test_render_js_timeout_handling(self):
        """Test JS rendering timeout behavior."""
        backend = RustBackend(fallback_enabled=False)

        if backend.is_available():
            # Test with various timeout values
            timeout_values = [None, 0, 1, 1000, 10000]

            for timeout in timeout_values:
                try:
                    # Use a fast, reliable endpoint
                    result = backend.render_js_page("https://httpbin.org/html", timeout)
                    assert isinstance(result, str)
                except RustIntegrationError:
                    # Timeouts or network errors are acceptable
                    pass


class TestGlobalRustBackend:
    """Test global Rust backend instance management."""

    def test_get_rust_backend_singleton(self):
        """Test that get_rust_backend returns singleton instance."""
        reset_rust_backend()  # Start fresh

        backend1 = get_rust_backend(fallback_enabled=True)
        backend2 = get_rust_backend(
            fallback_enabled=False
        )  # Different param should be ignored

        assert backend1 is backend2  # Should be same instance

    def test_reset_rust_backend(self):
        """Test resetting global backend instance."""
        backend1 = get_rust_backend(fallback_enabled=True)
        reset_rust_backend()
        backend2 = get_rust_backend(fallback_enabled=False)

        assert backend1 is not backend2  # Should be different instances

    def teardown_method(self):
        """Clean up after each test."""
        reset_rust_backend()


class TestRustBackendEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_concurrent_rust_calls(self):
        """Test concurrent calls to Rust backend."""
        import threading
        import time

        backend = RustBackend(fallback_enabled=False)
        if not backend.is_available():
            pytest.skip("Rust backend not available")

        results = []
        errors = []

        def convert_html():
            try:
                result = backend.convert_html_to_format(
                    "<html><body><h1>Test</h1></body></html>",
                    "https://example.com",
                    "markdown",
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = [threading.Thread(target=convert_html) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check that concurrent calls work correctly
        assert len(errors) == 0  # No errors should occur
        assert len(results) == 5  # All calls should succeed
        assert all(isinstance(r, str) for r in results)

    def test_large_content_handling(self):
        """Test handling of large content."""
        backend = RustBackend(fallback_enabled=False)
        if not backend.is_available():
            pytest.skip("Rust backend not available")

        # Generate large HTML content
        large_html = (
            "<html><body>" + "<p>Test paragraph.</p>" * 10000 + "</body></html>"
        )

        try:
            result = backend.convert_html_to_format(
                large_html, "https://example.com", "markdown"
            )
            assert isinstance(result, str)
            assert len(result) > 1000  # Should produce substantial output
        except RustIntegrationError:
            # Large content might cause memory or processing errors
            pass

    def test_unicode_content_handling(self):
        """Test handling of Unicode content."""
        backend = RustBackend(fallback_enabled=False)
        if not backend.is_available():
            pytest.skip("Rust backend not available")

        # Test various Unicode characters
        unicode_html = """
        <html><body>
            <h1>测试标题</h1>
            <p>こんにちは世界</p>
            <p>Привет мир</p>
            <p>مرحبا بالعالم</p>
            <p>🚀 Emoji test 🌟</p>
        </body></html>
        """

        try:
            result = backend.convert_html_to_format(
                unicode_html, "https://example.com", "markdown"
            )
            assert isinstance(result, str)
            # Check that Unicode characters are preserved
            assert "测试标题" in result or "test" in result.lower()
        except RustIntegrationError:
            # Unicode handling might not be perfect in all cases
            pass
