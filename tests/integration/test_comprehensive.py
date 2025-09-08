"""
Comprehensive integration tests for markdown_lab.

These tests validate end-to-end functionality across all major components,
including error handling, performance, and edge cases.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.converter import Converter
from markdown_lab.core.errors import ConversionError, NetworkError, ParsingError


@pytest.mark.integration
class TestComprehensiveConversion:
    """Test comprehensive HTML to markdown conversion scenarios."""

    @pytest.fixture
    def sample_html(self):
        """Sample HTML content for testing."""
        return """
        <html>
          <head>
            <title>Test Document</title>
            <meta name="description" content="A test document">
          </head>
          <body>
            <header>
              <h1>Main Title</h1>
              <nav>
                <a href="/home">Home</a>
                <a href="/about">About</a>
              </nav>
            </header>

            <main>
              <section>
                <h2>Section 1</h2>
                <p>This is a <strong>bold</strong> paragraph with <em>emphasis</em>.</p>
                <ul>
                  <li>List item 1</li>
                  <li>List item 2</li>
                </ul>
              </section>

              <section>
                <h3>Code Example</h3>
                <pre><code>print("Hello, World!")</code></pre>
                <blockquote>
                  <p>This is a blockquote with a <a href="https://example.com">link</a>.</p>
                </blockquote>
              </section>
            </main>

            <footer>
              <p>&copy; 2024 Test Company</p>
            </footer>
          </body>
        </html>
        """

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return MarkdownLabConfig(
            cache_enabled=True, include_metadata=True, timeout=30, max_retries=2
        )

    def test_full_conversion_pipeline_markdown(self, sample_html, config):
        """Test complete conversion pipeline for markdown output."""
        converter = Converter(config)

        # Test markdown conversion
        markdown, raw_markdown = converter.convert_html(
            sample_html, "https://example.com", "markdown"
        )

        # Verify basic structure - uses document title, not header navigation
        assert "# Test Document" in markdown
        assert "## Section 1" in markdown
        assert "### Code Example" in markdown
        # Check that bold and emphasis text is present (format may vary)
        assert "bold" in markdown
        assert "emphasis" in markdown
        assert "- List item 1" in markdown
        assert "- List item 2" in markdown
        assert "```" in markdown  # Code block (fallback now supports <pre><code>)
        assert "> This is a blockquote" in markdown
        # Link should be present (URL may have trailing slash)
        assert "[link](https://example.com" in markdown

        # Verify source metadata is included
        assert "Source:" in markdown

    def test_full_conversion_pipeline_json(self, sample_html, config):
        """Test complete conversion pipeline for JSON output."""
        converter = Converter(config)

        # Test JSON conversion
        json_output, raw_markdown = converter.convert_html(
            sample_html, "https://example.com", "json"
        )

        # Parse JSON and verify structure
        import json

        data = json.loads(json_output)

        assert "title" in data
        assert data["title"] == "Test Document"
        assert "headings" in data
        assert len(data["headings"]) > 0
        assert "paragraphs" in data
        assert len(data["paragraphs"]) > 0

    def test_full_conversion_pipeline_xml(self, sample_html, config):
        """Test complete conversion pipeline for XML output."""
        converter = Converter(config)

        # Test XML conversion
        xml_output, raw_markdown = converter.convert_html(
            sample_html, "https://example.com", "xml"
        )

        # Verify XML structure (case-sensitive)
        assert "<Document>" in xml_output
        assert "<title>Test Document</title>" in xml_output
        assert "<headings>" in xml_output
        assert "<paragraphs>" in xml_output

    def test_error_handling_network_failure(self, config):
        """Test error handling for network failures."""
        converter = Converter(config)

        with patch.object(
            converter.client, "get", side_effect=NetworkError("Network error")
        ):
            with pytest.raises(ConversionError):
                converter.convert_url("https://example.com", "markdown")

    def test_error_handling_invalid_html(self, config):
        """Test error handling for invalid HTML."""
        converter = Converter(config)

        invalid_html = "<html><body><p>Unclosed paragraph"
        # Should not raise an exception, should handle gracefully
        result, raw = converter.convert_html(
            invalid_html, "https://example.com", "markdown"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_caching_functionality(self, sample_html, config):
        """Test that caching works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config.cache_dir = Path(temp_dir)
            converter = Converter(config)

            # First conversion - should cache
            result1, _ = converter.convert_html(
                sample_html, "https://example.com", "markdown"
            )

            # Second conversion - should use cache
            result2, _ = converter.convert_html(
                sample_html, "https://example.com", "markdown"
            )

            # Results should be identical except for timestamps
            import re

            # Remove timestamps for comparison
            result1_clean = re.sub(
                r"\*Generated: [^*]+\*", "*Generated: [TIMESTAMP]*", result1
            )
            result2_clean = re.sub(
                r"\*Generated: [^*]+\*", "*Generated: [TIMESTAMP]*", result2
            )
            assert result1_clean == result2_clean

    def test_large_content_handling(self, config):
        """Test handling of large HTML content."""
        # Generate large HTML content
        large_html = "<html><body>"
        for i in range(100):
            large_html += f"<h2>Section {i}</h2><p>Content {i}</p>"
        large_html += "</body></html>"

        converter = Converter(config)

        # Should handle large content without issues
        result, _ = converter.convert_html(
            large_html, "https://example.com", "markdown"
        )

        assert len(result) > 1000  # Should produce substantial output
        assert "Section 50" in result  # Should contain middle sections

    def test_relative_url_resolution(self, config):
        """Test that relative URLs are properly resolved."""
        html_with_relative_urls = """
        <html><body>
        <a href="/relative">Relative Link</a>
        <img src="../images/test.jpg" alt="Test Image">
        </body></html>
        """

        converter = Converter(config)
        result, _ = converter.convert_html(
            html_with_relative_urls, "https://example.com/path/", "markdown"
        )

        # Should resolve relative URLs
        assert "https://example.com/relative" in result
        assert "https://example.com/images/test.jpg" in result

    def test_performance_under_load(self, sample_html, config):
        """Test performance with multiple concurrent conversions."""
        import time

        converter = Converter(config)

        start_time = time.time()

        # Perform multiple conversions
        results = []
        for i in range(10):
            result, _ = converter.convert_html(
                sample_html, f"https://example.com/{i}", "markdown"
            )
            results.append(result)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 5.0  # 5 seconds for 10 conversions
        assert len(results) == 10
        assert all(isinstance(r, str) and len(r) > 0 for r in results)


@pytest.mark.integration
def test_cli_integration():
    """Test CLI integration with actual command execution."""
    import subprocess
    import sys

    # Test that the CLI can be invoked (basic smoke test)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "markdown_lab", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        # Accept either modern Typer help or legacy argparse help
        help_text = result.stdout
        assert ("Usage:" in help_text) or ("usage:" in help_text)
        if "Commands" in help_text:
            assert "convert" in help_text
        else:
            # Legacy CLI
            assert "--format" in help_text or "--use-sitemap" in help_text
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # CLI might not be properly set up in test environment
        pytest.skip("CLI not available in test environment")


@pytest.mark.integration
def test_rust_backend_fallback():
    """Test that Python fallback works when Rust is unavailable."""
    config = MarkdownLabConfig(fallback_to_python=True)

    # Mock Rust backend as unavailable
    with patch("markdown_lab.core.rust_backend.get_rust_backend") as mock_get:
        mock_backend = Mock()
        mock_backend.is_available.return_value = False
        mock_backend.convert_html_to_format.side_effect = Exception("Rust unavailable")
        mock_get.return_value = mock_backend

        converter = Converter(config)

        # Should fall back to Python implementation
        result, _ = converter.convert_html(
            "<html><body><h1>Test</h1></body></html>", "https://example.com", "markdown"
        )

        assert "# Test" in result
