"""Test main functionality without mocking - using real components."""

import tempfile
from pathlib import Path

import pytest
import requests

from markdown_lab.core.cache import RequestCache
from markdown_lab.core.scraper import MarkdownScraper
from tests.fixtures.html_samples import (
    BLOG_POST_WITH_IMAGES,
    DOCUMENTATION_PAGE,
    ECOMMERCE_PRODUCT_PAGE,
    GITHUB_README_STYLE,
    NEWS_ARTICLE,
)
from tests.integration.test_http_server import TestHTTPServer


@pytest.fixture
def test_server():
    """Provide a real HTTP test server."""
    server = TestHTTPServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def scraper():
    """Create a scraper with caching disabled for predictable tests."""
    return MarkdownScraper(cache_enabled=False)


@pytest.fixture
def scraper_with_cache():
    """Create a scraper with caching enabled."""
    return MarkdownScraper(cache_enabled=True)


class TestScraperWithRealServer:
    """Test MarkdownScraper with real HTTP server."""

    def test_scrape_website_success(self, scraper, test_server):
        """Test successful website scraping."""
        result = scraper.scrape_website(f"{test_server.url}/")
        assert result is not None
        assert "markdown_lab" in result
        assert "<h1>markdown_lab</h1>" in result

    def test_scrape_documentation_page(self, scraper, test_server):
        """Test scraping documentation page."""
        result = scraper.scrape_website(f"{test_server.url}/docs")
        assert "HttpClient Class" in result
        assert "<h3>__init__" in result
        assert "MarkdownLabConfig" in result

    def test_scrape_with_http_error(self, scraper, test_server):
        """Test handling of HTTP errors during scraping."""
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            scraper.scrape_website(f"{test_server.url}/error?code=404")
        assert "404" in str(exc_info.value)

    def test_scrape_nonexistent_server(self, scraper):
        """Test handling of connection errors."""
        with pytest.raises(requests.exceptions.ConnectionError):
            scraper.scrape_website("http://localhost:59999/")


class TestMarkdownConversion:
    """Test HTML to Markdown conversion with real content."""

    def test_convert_github_readme_style(self, scraper):
        """Test conversion of GitHub README-style HTML."""
        result = scraper.convert_html_to_format(
            GITHUB_README_STYLE, "https://github.com/example/markdown_lab", "markdown"
        )

        # Check title conversion
        assert "# markdown_lab" in result

        # Check that features are preserved
        assert "⚡ Rust-powered HTML parsing" in result
        assert "🔄 Multiple output formats" in result

        # Check code blocks
        assert "```bash" in result
        assert "pip install markdown-lab" in result

        # Check table conversion
        assert "Parse 1MB HTML" in result
        assert "12.5" in result  # Time value

    def test_convert_documentation_page(self, scraper):
        """Test conversion of API documentation HTML."""
        result = scraper.convert_html_to_format(
            DOCUMENTATION_PAGE, "https://docs.example.com/api/http-client", "markdown"
        )

        # Check navigation links
        assert "[Overview](#overview)" in result or "Overview" in result

        # Check method documentation
        assert "__init__" in result
        assert "get(url: str" in result

        # Check code examples
        assert "from markdown_lab.network.client import HttpClient" in result

    def test_convert_blog_post_with_images(self, scraper):
        """Test conversion of blog post with images."""
        result = scraper.convert_html_to_format(
            BLOG_POST_WITH_IMAGES,
            "https://blog.example.com/posts/web-scraping",
            "markdown",
        )

        # Check title and metadata
        assert "Building Fast Web Scrapers with Rust and Python" in result
        assert "January 15, 2024" in result
        assert "Sarah Chen" in result

        # Check image conversion
        assert "![Rust and Python logos combined]" in result
        assert "![Performance comparison chart" in result

        # Check blockquote
        assert ">" in result
        assert "best of both worlds" in result

    def test_convert_ecommerce_product(self, scraper):
        """Test conversion of e-commerce product page."""
        result = scraper.convert_html_to_format(
            ECOMMERCE_PRODUCT_PAGE,
            "https://shop.example.com/products/scraper-toolkit",
            "markdown",
        )

        # Check product info
        assert "Professional Web Scraping Toolkit" in result
        assert "$299.99" in result
        assert "★★★★★" in result

        # Check features list
        assert "✓ Multi-threaded scraping engine" in result
        assert "✓ JavaScript rendering support" in result

        # Check specifications table
        assert "Supported OS" in result
        assert "Windows 10+, macOS 10.15+, Linux" in result

    def test_convert_news_article(self, scraper):
        """Test conversion of news article."""
        result = scraper.convert_html_to_format(
            NEWS_ARTICLE,
            "https://news.example.com/2024/01/tech-ai-investment",
            "markdown",
        )

        # Check headline
        assert "Tech Giants Invest Billions in AI Infrastructure" in result

        # Check article structure
        assert "Breaking Down the Numbers" in result
        assert "MegaCorp: $35 billion" in result

        # Check timeline
        assert "2020" in result
        assert "$15 billion" in result


class TestFormatConversion:
    """Test conversion to different output formats with real content."""

    def test_json_output_format(self, scraper, test_server):
        """Test JSON output format with real server content."""
        html = scraper.scrape_website(f"{test_server.url}/blog")

        # Convert to JSON using Rust implementation
        json_result = scraper.convert_html_to_format(
            html, f"{test_server.url}/blog", "json"
        )

        # Verify JSON structure
        assert '"title":' in json_result
        assert '"headers":' in json_result
        assert '"paragraphs":' in json_result
        assert '"links":' in json_result
        assert '"images":' in json_result

        # Verify content is preserved
        assert "Building Fast Web Scrapers" in json_result
        assert "Sarah Chen" in json_result

    def test_xml_output_format(self, scraper, test_server):
        """Test XML output format with real server content."""
        html = scraper.scrape_website(f"{test_server.url}/product")

        # Convert to XML
        xml_result = scraper.convert_html_to_format(
            html, f"{test_server.url}/product", "xml"
        )

        # Verify XML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_result
        assert "<document>" in xml_result
        assert "</document>" in xml_result
        assert "<title>" in xml_result
        assert "<headers>" in xml_result

        # Verify content is preserved and properly escaped
        assert "Professional Web Scraping Toolkit" in xml_result
        assert (
            "&lt;" not in xml_result or "&gt;" not in xml_result
        )  # Check for proper escaping


class TestCachingBehavior:
    """Test request caching with real HTTP requests."""

    def test_cache_reduces_requests(self, scraper_with_cache, test_server):
        """Test that caching reduces number of HTTP requests."""
        url = f"{test_server.url}/news"

        # First request
        test_server.clear_requests()
        result1 = scraper_with_cache.scrape_website(url)
        assert len(test_server.get_requests()) == 1

        # Second request - should use cache
        test_server.clear_requests()
        result2 = scraper_with_cache.scrape_website(url)
        assert result1 == result2
        assert len(test_server.get_requests()) == 0

    def test_cache_file_operations(self, scraper_with_cache, test_server):
        """Test cache file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create scraper with specific cache directory
            cache = RequestCache(cache_dir=temp_dir, max_age_days=1)
            scraper = MarkdownScraper(cache=cache)

            # Make request
            url = f"{test_server.url}/"
            scraper.scrape_website(url)

            # Check cache file was created
            cache_files = list(Path(temp_dir).glob("*.cache"))
            assert cache_files

            # Verify cached content
            cached_content = cache_files[0].read_text()
            assert len(cached_content) > 0


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    def test_scrape_and_convert_workflow(self, scraper, test_server):
        """Test complete workflow: scrape -> convert -> verify."""
        # URLs to test
        test_urls = [
            f"{test_server.url}/",
            f"{test_server.url}/docs",
            f"{test_server.url}/blog",
        ]

        for url in test_urls:
            # Scrape
            html = scraper.scrape_website(url)
            assert html is not None

            # Convert to markdown
            markdown = scraper.convert_html_to_format(html, url, "markdown")
            assert len(markdown) > 100  # Should have substantial content

            # Convert to JSON
            json_output = scraper.convert_html_to_format(html, url, "json")
            assert '"title":' in json_output

            # Convert to XML
            xml_output = scraper.convert_html_to_format(html, url, "xml")
            assert "<?xml" in xml_output

    def test_batch_processing(self, scraper, test_server):
        """Test batch processing of multiple URLs."""
        urls = [
            f"{test_server.url}/",
            f"{test_server.url}/docs",
            f"{test_server.url}/blog",
            f"{test_server.url}/news",
            f"{test_server.url}/product",
        ]

        results = {}
        for url in urls:
            try:
                html = scraper.scrape_website(url)
                markdown = scraper.convert_html_to_format(html, url, "markdown")
                results[url] = {
                    "success": True,
                    "length": len(markdown),
                    "has_content": len(markdown) > 100,
                }
            except Exception as e:
                results[url] = {"success": False, "error": str(e)}

        # All URLs should succeed
        assert all(r["success"] for r in results.values())
        assert all(r["has_content"] for r in results.values())


@pytest.mark.parametrize("format_type", ["markdown", "json", "xml"])
def test_all_formats_with_all_samples(scraper, format_type):
    """Test all output formats with all HTML samples."""
    samples = [
        ("github", GITHUB_README_STYLE),
        ("docs", DOCUMENTATION_PAGE),
        ("blog", BLOG_POST_WITH_IMAGES),
        ("ecommerce", ECOMMERCE_PRODUCT_PAGE),
        ("news", NEWS_ARTICLE),
    ]

    for name, html in samples:
        result = scraper.convert_html_to_format(
            html, f"https://example.com/{name}", format_type
        )

        assert result is not None
        assert len(result) > 100  # Should have content

        if format_type == "json":
            assert '"title":' in result
        elif format_type == "xml":
            assert "<?xml" in result
            assert "<document>" in result
        else:  # markdown
            assert "#" in result or "*" in result  # Headers or emphasis
