"""Unit tests for rust_backend module."""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from markdown_lab.core.errors import RustIntegrationError
from markdown_lab.core.rust_backend import (
    RustBackend,
    get_rust_backend,
    reset_rust_backend,
)


@pytest.fixture
def rust_backend():
    """Create a RustBackend instance for testing."""
    # Reset the global instance to ensure clean state
    reset_rust_backend()
    return RustBackend(fallback_enabled=True)


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <html>
        <head><title>Test Document</title></head>
        <body>
            <h1>Main Title</h1>
            <p>This is a test paragraph with <a href="https://example.com">a link</a>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
    </html>
    """


@pytest.fixture
def sample_markdown():
    """Sample markdown content for testing."""
    return """# Main Title

This is a test paragraph with [a link](https://example.com).

* Item 1
* Item 2
"""


class TestRustBackendInitialization:
    """Test RustBackend initialization and configuration."""

    def test_init_with_fallback_enabled(self):
        """Test successful initialization with fallback enabled."""
        backend = RustBackend(fallback_enabled=True)
        assert backend.fallback_enabled is True
        assert hasattr(backend, '_rust_module')

    def test_init_with_fallback_disabled(self):
        """Test initialization with fallback disabled."""
        # This might raise RustIntegrationError if Rust module is not available
        try:
            backend = RustBackend(fallback_enabled=False)
            assert backend.fallback_enabled is False
        except RustIntegrationError:
            # This is expected if Rust backend is not available
            pass

    def test_init_default_fallback(self):
        """Test initialization with default fallback setting."""
        backend = RustBackend()
        assert backend.fallback_enabled is False  # Default is False


class TestRustBackendConversion:
    """Test RustBackend HTML conversion methods."""

    def test_convert_html_to_format_success(self, rust_backend, sample_html):
        """Test successful HTML to format conversion."""
        mock_rust_module = MagicMock()
        mock_rust_module.convert_html_to_format.return_value = "# Converted Content"
        rust_backend._rust_module = mock_rust_module

        result = rust_backend.convert_html_to_format(sample_html, "https://example.com", "markdown")

        assert result == "# Converted Content"
        mock_rust_module.convert_html_to_format.assert_called_once_with(
            sample_html, "https://example.com", "markdown"
        )

    def test_convert_html_to_format_no_rust_module(self, rust_backend, sample_html):
        """Test conversion when Rust module is not available."""
        rust_backend._rust_module = None

        with pytest.raises(RustIntegrationError) as exc_info:
            rust_backend.convert_html_to_format(sample_html, "https://example.com", "markdown")

        error = exc_info.value
        assert isinstance(error, RustIntegrationError)
        assert "Rust backend not available" in str(error)
        assert error.context["rust_function"] == "convert_html_to_format"

    def test_convert_html_to_format_rust_error(self, rust_backend, sample_html):
        """Test handling of Rust conversion errors."""
        mock_rust_module = MagicMock()
        mock_rust_module.convert_html_to_format.side_effect = Exception("Rust conversion failed")
        rust_backend._rust_module = mock_rust_module

        with pytest.raises(RustIntegrationError) as exc_info:
            rust_backend.convert_html_to_format(sample_html, "https://example.com", "markdown")

        error = exc_info.value
        assert isinstance(error, RustIntegrationError)
        assert "Rust conversion failed" in str(error)
        assert error.context["rust_function"] == "convert_html_to_format"

    def test_convert_html_to_markdown_legacy(self, rust_backend, sample_html):
        """Test legacy HTML to markdown conversion method."""
        mock_rust_module = MagicMock()
        mock_rust_module.convert_html_to_format.return_value = "# Converted Markdown"
        rust_backend._rust_module = mock_rust_module

        result = rust_backend.convert_html_to_markdown(sample_html, "https://example.com")

        assert result == "# Converted Markdown"
        mock_rust_module.convert_html_to_format.assert_called_once_with(
            sample_html, "https://example.com", "markdown"
        )

    @pytest.mark.parametrize("output_format", ["markdown", "json", "xml"])
    def test_convert_different_formats(self, rust_backend, sample_html, output_format):
        """Test conversion to different output formats."""
        expected_result = f"Converted {output_format} content"
        mock_rust_module = MagicMock()
        mock_rust_module.convert_html_to_format.return_value = expected_result
        rust_backend._rust_module = mock_rust_module

        result = rust_backend.convert_html_to_format(sample_html, "https://example.com", output_format)

        assert result == expected_result
        mock_rust_module.convert_html_to_format.assert_called_once_with(
            sample_html, "https://example.com", output_format
        )


class TestRustBackendChunking:
    """Test RustBackend markdown chunking functionality."""

    def test_chunk_markdown_success(self, rust_backend, sample_markdown):
        """Test successful markdown chunking."""
        expected_chunks = ["# Main Title\n\nThis is a test", "paragraph with a link", "* Item 1\n* Item 2"]
        mock_rust_module = MagicMock()
        mock_rust_module.chunk_markdown.return_value = expected_chunks
        rust_backend._rust_module = mock_rust_module

        result = rust_backend.chunk_markdown(sample_markdown, chunk_size=100, chunk_overlap=20)

        assert result == expected_chunks
        mock_rust_module.chunk_markdown.assert_called_once_with(sample_markdown, 100, 20)

    def test_chunk_markdown_no_rust_module(self, rust_backend, sample_markdown):
        """Test chunking when Rust module is not available."""
        rust_backend._rust_module = None

        with pytest.raises(RustIntegrationError) as exc_info:
            rust_backend.chunk_markdown(sample_markdown)

        error = exc_info.value
        assert isinstance(error, RustIntegrationError)
        assert "Rust backend not available" in str(error)
        assert error.context["rust_function"] == "chunk_markdown"

    def test_chunk_markdown_default_params(self, rust_backend, sample_markdown):
        """Test chunking with default parameters."""
        mock_rust_module = MagicMock()
        mock_rust_module.chunk_markdown.return_value = ["chunk1", "chunk2"]
        rust_backend._rust_module = mock_rust_module

        rust_backend.chunk_markdown(sample_markdown)

        mock_rust_module.chunk_markdown.assert_called_once_with(sample_markdown, 1000, 200)

    def test_chunk_markdown_rust_error(self, rust_backend, sample_markdown):
        """Test handling of Rust chunking errors."""
        mock_rust_module = MagicMock()
        mock_rust_module.chunk_markdown.side_effect = Exception("Chunking failed")
        rust_backend._rust_module = mock_rust_module

        with pytest.raises(RustIntegrationError) as exc_info:
            rust_backend.chunk_markdown(sample_markdown)

        assert "Rust chunking failed" in str(exc_info.value)


class TestRustBackendJSRendering:
    """Test RustBackend JavaScript rendering functionality."""

    def test_render_js_page_success(self, rust_backend):
        """Test successful JavaScript page rendering."""
        expected_html = "<html>Rendered with JS</html>"
        mock_rust_module = MagicMock()
        mock_rust_module.render_js_page.return_value = expected_html
        rust_backend._rust_module = mock_rust_module

        result = rust_backend.render_js_page("https://example.com", wait_time=5000)

        assert result == expected_html
        mock_rust_module.render_js_page.assert_called_once_with("https://example.com", 5000)

    def test_render_js_page_no_rust_module(self, rust_backend):
        """Test JS rendering when Rust module is not available."""
        rust_backend._rust_module = None

        with pytest.raises(RustIntegrationError) as exc_info:
            rust_backend.render_js_page("https://example.com")

        error = exc_info.value
        assert isinstance(error, RustIntegrationError)
        assert "Rust backend not available" in str(error)
        assert error.context["rust_function"] == "render_js_page"
        assert error.context["fallback_available"] is False  # No Python fallback for JS rendering

    def test_render_js_page_default_wait_time(self, rust_backend):
        """Test JS rendering with default wait time."""
        mock_rust_module = MagicMock()
        mock_rust_module.render_js_page.return_value = "<html>Rendered</html>"
        rust_backend._rust_module = mock_rust_module

        rust_backend.render_js_page("https://example.com")

        mock_rust_module.render_js_page.assert_called_once_with("https://example.com", None)


class TestRustBackendUtilities:
    """Test utility methods and helper functions."""

    def test_is_available_with_rust_module(self, rust_backend):
        """Test is_available when Rust module is loaded."""
        rust_backend._rust_module = MagicMock()
        assert rust_backend.is_available() is True

    def test_is_available_without_rust_module(self, rust_backend):
        """Test is_available when Rust module is not loaded."""
        rust_backend._rust_module = None
        assert rust_backend.is_available() is False

    def test_get_version_info_with_rust_module(self, rust_backend):
        """Test version info when Rust module is available."""
        mock_module = MagicMock()
        mock_module.__version__ = "1.0.0"
        rust_backend._rust_module = mock_module

        version_info = rust_backend.get_version_info()

        assert version_info["available"] is True
        assert version_info["version"] == "1.0.0"

    def test_get_version_info_without_rust_module(self, rust_backend):
        """Test version info when Rust module is not available."""
        rust_backend._rust_module = None

        version_info = rust_backend.get_version_info()

        assert version_info["available"] is False
        assert version_info["version"] is None

    def test_get_version_info_no_version_attribute(self, rust_backend):
        """Test version info when Rust module has no version attribute."""
        rust_backend._rust_module = MagicMock()
        del rust_backend._rust_module.__version__  # Remove version attribute

        version_info = rust_backend.get_version_info()

        assert version_info["available"] is True
        assert version_info["version"] == "unknown"


class TestRustBackendGlobalInstance:
    """Test global instance management."""

    def test_get_rust_backend_creates_instance(self):
        """Test that get_rust_backend creates a new instance."""
        reset_rust_backend()  # Ensure clean state

        backend = get_rust_backend(fallback_enabled=True)

        assert isinstance(backend, RustBackend)
        assert backend.fallback_enabled is True

    def test_get_rust_backend_returns_same_instance(self):
        """Test that get_rust_backend returns the same instance on subsequent calls."""
        reset_rust_backend()  # Ensure clean state

        backend1 = get_rust_backend(fallback_enabled=True)
        backend2 = get_rust_backend(fallback_enabled=False)  # Different params, but should return same instance

        assert backend1 is backend2

    def test_reset_rust_backend(self):
        """Test that reset_rust_backend clears the global instance."""
        backend1 = get_rust_backend(fallback_enabled=True)
        reset_rust_backend()
        backend2 = get_rust_backend(fallback_enabled=True)

        assert backend1 is not backend2


class TestRustBackendErrorHandling:
    """Test error handling scenarios."""

    def test_rust_integration_error_context(self, rust_backend):
        """Test that RustIntegrationError includes proper context."""
        mock_rust_module = MagicMock()
        mock_rust_module.convert_html_to_format.side_effect = ValueError("Test error")
        rust_backend._rust_module = mock_rust_module

        with pytest.raises(RustIntegrationError) as exc_info:
            rust_backend.convert_html_to_format("<html></html>", "https://example.com")

        error = exc_info.value
        assert isinstance(error, RustIntegrationError)
        assert error.context["rust_function"] == "convert_html_to_format"
        assert error.context["fallback_available"] is True
        assert error.cause is not None
        assert isinstance(error.cause, ValueError)

    def test_fallback_available_context(self, sample_html):
        """Test that fallback_available is correctly set in error context."""
        # Test with fallback enabled
        backend_with_fallback = RustBackend(fallback_enabled=True)
        backend_with_fallback._rust_module = None

        with pytest.raises(RustIntegrationError) as exc_info:
            backend_with_fallback.convert_html_to_format(sample_html, "https://example.com")

        error = exc_info.value
        assert isinstance(error, RustIntegrationError)
        assert error.context["fallback_available"] is True

        # Test with fallback disabled
        backend_no_fallback = RustBackend(fallback_enabled=False)
        backend_no_fallback._rust_module = None

        with pytest.raises(RustIntegrationError) as exc_info:
            backend_no_fallback.render_js_page("https://example.com")

        error = exc_info.value
        assert isinstance(error, RustIntegrationError)
        assert error.context["fallback_available"] is False


class TestRustBackendParameterized:
    """Parameterized tests for comprehensive coverage."""

    @pytest.mark.parametrize("fallback_enabled", [True, False])
    def test_initialization_with_different_fallback_settings(self, fallback_enabled):
        """Test initialization with different fallback settings."""
        try:
            backend = RustBackend(fallback_enabled=fallback_enabled)
            assert backend.fallback_enabled == fallback_enabled
        except RustIntegrationError:
            # Expected when fallback is disabled and Rust module is not available
            if fallback_enabled:
                raise

    @pytest.mark.parametrize("chunk_size,chunk_overlap", [
        (500, 100),
        (1000, 200),
        (2000, 400),
        (100, 0),
    ])
    def test_chunk_markdown_different_params(self, rust_backend, sample_markdown, chunk_size, chunk_overlap):
        """Test chunking with different parameter combinations."""
        mock_rust_module = MagicMock()
        mock_rust_module.chunk_markdown.return_value = ["chunk1", "chunk2"]
        rust_backend._rust_module = mock_rust_module

        rust_backend.chunk_markdown(sample_markdown, chunk_size, chunk_overlap)

        mock_rust_module.chunk_markdown.assert_called_once_with(sample_markdown, chunk_size, chunk_overlap)
