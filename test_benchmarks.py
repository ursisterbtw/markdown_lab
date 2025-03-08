import pytest
from main import MarkdownScraper

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
