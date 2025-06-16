import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from markdown_lab.core.cache import RequestCache
from markdown_lab.core.scraper import MarkdownScraper


@pytest.mark.benchmark(group="scrape_website")
def test_scrape_website_benchmark(benchmark):
    scraper = MarkdownScraper()
    url = "http://example.com"
    benchmark(scraper.scrape_website, url)


@pytest.mark.benchmark(group="convert_to_markdown")
def test_convert_to_markdown_benchmark(benchmark):
    scraper = MarkdownScraper()
    html_content = "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"
    benchmark(scraper.convert_to_markdown, html_content)


@pytest.mark.benchmark(group="save_markdown")
def test_save_markdown_benchmark(benchmark, tmp_path):
    scraper = MarkdownScraper()
    markdown_content = "# Test Markdown"
    output_file = tmp_path / "output.md"
    benchmark(scraper.save_markdown, markdown_content, str(output_file))


@pytest.mark.benchmark(group="create_chunks")
def test_create_chunks_benchmark(benchmark):
    scraper = MarkdownScraper()
    markdown_content = "# Test\n\nThis is a test."
    url = "http://example.com"
    benchmark(scraper.create_chunks, markdown_content, url)


@pytest.mark.benchmark(group="save_chunks")
def test_save_chunks_benchmark(benchmark, tmp_path):
    scraper = MarkdownScraper()
    markdown_content = "# Test\n\nThis is a test."
    url = "http://example.com"
    chunks = scraper.create_chunks(markdown_content, url)
    output_dir = tmp_path / "chunks"
    benchmark(scraper.save_chunks, chunks, str(output_dir))


@pytest.mark.benchmark(group="caching")
def test_benchmark_scrape_with_cache_enabled(benchmark):
    """
    Benchmarks the performance of scraping a website with caching enabled.

    This test uses a temporary cache directory and mocks HTTP GET requests to ensure consistent responses. The initial scrape populates the cache, and the benchmark measures subsequent scrapes that utilize the cache.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("markdown_lab.network.client.requests.Session.get") as mock_get:
            # Setup mock response for first call
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = """<html><head><title>Benchmark Test</title></head>
            <body><h1>This is a test heading</h1><p>This is a test paragraph with some content.</p></body></html>"""
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_get.return_value = mock_response

            # Create scraper with cache enabled
            scraper = MarkdownScraper(cache_enabled=True)
            scraper.request_cache.cache_dir = Path(temp_dir)  # Override cache directory

            # Trigger initial request to populate cache
            url = "http://example.com/benchmark"
            scraper.scrape_website(url)

            # Benchmark subsequent requests
            def scrape():
                return scraper.scrape_website(url)

            benchmark(scrape)


@pytest.mark.benchmark(group="caching")
def test_benchmark_scrape_with_cache_disabled(benchmark):
    """
    Benchmarks the performance of scraping a website with caching disabled.

    Mocks HTTP GET requests to return a fixed HTML response and measures the execution time of the `scrape_website` method in `MarkdownScraper` when cache is turned off.
    """
    with patch("markdown_lab.network.client.requests.Session.get") as mock_get:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<html><head><title>Benchmark Test</title></head>
        <body><h1>This is a test heading</h1><p>This is a test paragraph with some content.</p></body></html>"""
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_response

        # Create scraper with cache disabled
        scraper = MarkdownScraper(cache_enabled=False)

        # Benchmark requests
        def scrape():
            return scraper.scrape_website("http://example.com/benchmark")

        benchmark(scrape)


@pytest.mark.benchmark(group="caching")
def test_benchmark_cache_set(benchmark):
    """Benchmark the cache set operation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = RequestCache(cache_dir=temp_dir, max_age=3600)
        url = "http://example.com/benchmark/set"
        content = (
            "<html><body>Test content for benchmarking cache set</body></html>" * 10
        )

        def cache_set():
            cache.set(url, content)

        benchmark(cache_set)


@pytest.mark.benchmark(group="caching")
def test_benchmark_cache_get(benchmark):
    """Benchmark the cache get operation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = RequestCache(cache_dir=temp_dir, max_age=3600)
        url = "http://example.com/benchmark/get"
        content = (
            "<html><body>Test content for benchmarking cache get</body></html>" * 10
        )

        # Pre-populate cache
        cache.set(url, content)

        def cache_get():
            return cache.get(url)

        benchmark(cache_get)
