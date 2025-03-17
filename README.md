![Markdown Lab](github-banner.svg)

# Markdown Lab 🔄📝

A powerful and modular web scraper that converts web content into well-structured Markdown files with RAG-ready chunking capabilities.

[![Python CI](https://github.com/ursisterbtw/markdown_lab/actions/workflows/CI.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/CI.yml)
[![Rust](https://github.com/ursisterbtw/markdown_lab/actions/workflows/rust.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/rust.yml)

## Features

- 🌐 Scrapes any accessible website with robust error handling and rate limiting
- 🗺️ Parses sitemap.xml to discover and scrape the most relevant content
- 📝 Converts HTML to clean Markdown format
- 🧩 Implements intelligent chunking for RAG (Retrieval-Augmented Generation) systems
- 🔄 Handles various HTML elements:
  - Headers (h1-h6)
  - Paragraphs
  - Links with resolved relative URLs
  - Images with resolved relative URLs
  - Ordered and unordered lists
  - Blockquotes
  - Code blocks
- 📋 Preserves document structure
- 🪵 Comprehensive logging
- ✅ Robust error handling with exponential backoff
- 🏎️ Performance optimizations and best practices

## Installation

```bash
git clone https://github.com/ursisterbtw/markdown_lab.git
cd markdown_lab
pip install -r requirements.txt

# Build the Rust library
cargo build --release
```

## Usage

### Basic Markdown Conversion

```bash
python main.py https://www.example.com -o output.md
```

### With RAG Chunking

```bash
python main.py https://www.example.com -o output.md --save-chunks --chunk-dir my_chunks
```

### Scraping with Sitemap

```bash
python main.py https://www.example.com -o output_dir --use-sitemap --save-chunks
```

### Advanced Sitemap Scraping

```bash
python main.py https://www.example.com -o output_dir \
    --use-sitemap \
    --min-priority 0.5 \
    --include "blog/*" "products/*" \
    --exclude "*.pdf" "temp/*" \
    --limit 50 \
    --save-chunks \
    --chunk-dir my_chunks \
    --requests-per-second 2.0
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `url` | The URL to scrape | (required) |
| `-o, --output` | Output markdown file/directory | `output.md` |
| `--save-chunks` | Save content chunks for RAG | False |
| `--chunk-dir` | Directory to save chunks | `chunks` |
| `--chunk-format` | Format for chunks (`json`, `jsonl`) | `jsonl` |
| `--chunk-size` | Maximum chunk size (chars) | 1000 |
| `--chunk-overlap` | Overlap between chunks (chars) | 200 |
| `--requests-per-second` | Rate limit for requests | 1.0 |
| `--use-sitemap` | Use sitemap.xml to discover URLs | False |
| `--min-priority` | Minimum priority for sitemap URLs | None |
| `--include` | Regex patterns for URLs to include | None |
| `--exclude` | Regex patterns for URLs to exclude | None |
| `--limit` | Maximum number of URLs to scrape | None |

### As a Module

#### Basic Scraping and Conversion

```python
from main import MarkdownScraper

scraper = MarkdownScraper()
html_content = scraper.scrape_website("https://example.com")
markdown_content = scraper.convert_to_markdown(html_content, "https://example.com")
scraper.save_markdown(markdown_content, "output.md")
```

#### With Sitemap Discovery

```python
from main import MarkdownScraper

scraper = MarkdownScraper(requests_per_second=2.0)
# Scrape using sitemap discovery
scraped_urls = scraper.scrape_by_sitemap(
    base_url="https://example.com",
    output_dir="output_dir",
    min_priority=0.5,                  # Only URLs with priority >= 0.5
    include_patterns=["blog/*"],       # Only blog URLs
    exclude_patterns=["temp/*"],       # Exclude temporary pages
    limit=20,                          # Maximum 20 URLs
    save_chunks=True,                  # Enable chunking
    chunk_dir="my_chunks",             # Save chunks here
    chunk_format="jsonl"               # Use JSONL format
)
print(f"Successfully scraped {len(scraped_urls)} URLs")
```

#### Direct Sitemap Access

```python
from sitemap_utils import SitemapParser, discover_site_urls

# Quick discovery of URLs from sitemap
urls = discover_site_urls(
    base_url="https://example.com",
    min_priority=0.7,
    include_patterns=["products/*"],
    limit=10
)

# Or with more control
parser = SitemapParser()
parser.parse_sitemap("https://example.com")
urls = parser.filter_urls(min_priority=0.5)
parser.export_urls_to_file(urls, "sitemap_urls.txt")
```

## Sitemap Integration Features

The library intelligently discovers and parses XML sitemaps to scrape exactly what you need:

- **Automatic Discovery**: Finds sitemaps through robots.txt or common locations
- **Sitemap Index Support**: Handles multi-level sitemap index files
- **Priority-Based Filtering**: Choose URLs based on their priority in the sitemap
- **Pattern Matching**: Include or exclude URLs with regex patterns
- **Optimized Scraping**: Only scrape the pages that matter most
- **Structured Organization**: Creates meaningful filenames based on URL paths

## RAG Chunking Capabilities

The library implements intelligent chunking designed specifically for RAG (Retrieval-Augmented Generation) systems:

- **Semantic Chunking**: Preserves the semantic structure of documents by chunking based on headers
- **Content-Aware**: Large sections are split into overlapping chunks for better context preservation
- **Metadata-Rich**: Each chunk contains detailed metadata for better retrieval
- **Multiple Formats**: Save chunks as individual JSON files or as a single JSONL file
- **Customizable**: Control chunk size and overlap to balance between precision and context

## Testing

The project includes comprehensive unit tests. To run them:

```bash
pytest
```

## Running Tests

### Rust Tests
```bash
# Run unit and integration tests
cargo test

# Run tests with logging
RUST_LOG=debug cargo test -- --nocapture
```

### Python Tests
```bash
# Run Python binding tests
pytest tests/test_python_bindings.py -v
```

## Running Benchmarks

```bash
# Run all benchmarks
cargo bench

# Run specific benchmark
cargo bench html_to_markdown
cargo bench chunk_markdown
```

## Visualizing Benchmark Results

After running the benchmarks, you can visualize the results:

```bash
python scripts/visualize_benchmarks.py
```

This will create a `benchmark_results.png` file with a bar chart showing the performance of each operation.

## Development

### Code Organization

- `src/`: Rust source code
  - `lib.rs`: Main library and Python bindings
  - `html_parser.rs`: HTML parsing utilities
  - `markdown_converter.rs`: HTML to Markdown conversion
  - `chunker.rs`: Markdown chunking logic
  - `js_renderer.rs`: JavaScript page rendering

- `tests/`: Test files
  - Rust integration tests
  - Python binding tests

- `benches/`: Benchmark files
  - Performance tests for core operations

### Running with Real JavaScript Rendering

To enable real JavaScript rendering with headless Chrome:

```bash
cargo build --release --features real_rendering
```

## Performance Considerations

- HTML to Markdown conversion is optimized for medium to large documents
- Chunking algorithm balances semantic coherence with performance
- JavaScript rendering can be CPU and memory intensive

## Dependencies

- requests: Web scraping and HTTP requests
- beautifulsoup4: HTML parsing
- pytest: Testing framework
- typing-extensions: Additional type checking support
- pathlib: Object-oriented filesystem paths
- python-dateutil: Powerful extensions to the standard datetime module

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE file](LICENSE) for details.

## Project Structure

- `main.py`: The main scraper implementation
- `chunk_utils.py`: Utilities for chunking text for RAG
- `sitemap_utils.py`: Sitemap parsing and URL discovery
- `throttle.py`: Rate limiting for web requests
- `test_*.py`: Unit tests

## Roadmap

- [x] Add support for more HTML elements
- [x] Implement chunking for RAG
- [x] Add sitemap.xml parsing for systematic scraping
- [ ] Add support for JavaScript-rendered pages
- [ ] Implement custom markdown templates
- [ ] Add concurrent scraping for multiple URLs
- [ ] Include CSS selector support
- [ ] Add configuration file support

## Author

🐍🦀 ursister

---
