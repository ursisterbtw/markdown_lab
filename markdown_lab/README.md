# Markdown Lab Python Package

This directory contains the Python components of the Markdown Lab project.

## Components

- `__init__.py`: Package initialization and version information
- `__main__.py`: CLI entry point for running as a module
- `main.py`: Contains the core `MarkdownScraper` class for scraping websites
- `chunk_utils.py`: Utilities for chunking content for RAG applications
- `sitemap_utils.py`: Tools for working with XML sitemaps
- `throttle.py`: Request throttling to avoid overloading servers
- `markdown_lab_rs.py`: Python interface to the Rust implementation
- `bs4.pyi`: Type stubs for BeautifulSoup

## Architecture

The package follows a hybrid Python/Rust architecture:

1. Python code provides high-level functionality, user interfaces, and fallbacks
2. Rust code (via PyO3 bindings) provides performance-critical components
3. Runtime feature detection determines whether to use Rust or Python implementations

## Example Usage

```python
from markdown_lab.main import MarkdownScraper

# Create a scraper instance
scraper = MarkdownScraper()

# Scrape a website and convert to markdown
html_content = scraper.scrape_website("https://example.com")
markdown_content = scraper.convert_to_markdown(html_content)

# Save the markdown content
scraper.save_markdown(markdown_content, "output.md")
```
