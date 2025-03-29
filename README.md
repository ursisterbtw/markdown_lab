![Markdown Lab](github-banner.svg)

# Markdown Lab 🔄📝

This is a web scraping and conversion tool called Markdown Lab that combines Python and Rust components to scrape websites and convert HTML content to markdown, JSON, or XML formats. It supports sitemap parsing, semantic chunking for RAG
  (Retrieval-Augmented Generation), and includes performance optimizations through Rust integration.

  Key features include HTML-to-markdown/JSON/XML conversion with support for various elements (headers, links, images, lists, code blocks), intelligent content chunking that preserves document structure, and systematic content discovery
  through sitemap parsing. The hybrid architecture uses Python for high-level operations and Rust for performance-critical tasks.

[![Python CI](https://github.com/ursisterbtw/markdown_lab/actions/workflows/CI.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/CI.yml)
[![Rust](https://github.com/ursisterbtw/markdown_lab/actions/workflows/rust.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/rust.yml)
[![Release](https://github.com/ursisterbtw/markdown_lab/actions/workflows/release.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/release.yml)

## Features

- 🌐 Scrapes any accessible website with robust error handling and rate limiting
- 🗺️ Parses sitemap.xml to discover and scrape the most relevant content
- 📝 Converts HTML to clean Markdown, JSON, or XML formats
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

### Basic Conversion

```bash
# Convert to Markdown (default)
python main.py https://www.example.com -o output.md

# Convert to JSON
python main.py https://www.example.com -o output.json -f json

# Convert to XML
python main.py https://www.example.com -o output.xml -f xml
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
| `-o, --output` | Output file/directory | `output.md` |
| `-f, --format` | Output format (markdown, json, xml) | `markdown` |
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

# Using default Markdown format
scraper = MarkdownScraper()
html_content = scraper.scrape_website("https://example.com")
markdown_content = scraper.convert_to_markdown(html_content, "https://example.com")
scraper.save_content(markdown_content, "output.md")

# Using JSON or XML format with the Rust implementation
from markdown_lab_rs import convert_html, OutputFormat

html_content = scraper.scrape_website("https://example.com")
# Convert to JSON
json_content = convert_html(html_content, "https://example.com", OutputFormat.JSON)
scraper.save_content(json_content, "output.json")
# Convert to XML
xml_content = convert_html(html_content, "https://example.com", OutputFormat.XML)
scraper.save_content(xml_content, "output.xml")
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
- [x] Add JSON and XML output formats
- [ ] Add support for JavaScript-rendered pages
- [ ] Implement custom markdown templates
- [ ] Add concurrent scraping for multiple URLs
- [ ] Include CSS selector support
- [ ] Add configuration file support

## Author

🐍🦀 ursister

---

## Creating an Official Release

To create an official release, follow these steps:

1. **Update Version Numbers**:
   - Update the version number in `Cargo.toml` and `pyproject.toml` to the new release version.

2. **Commit Changes**:
   - Commit the changes to the version numbers and any other updates.

3. **Tag the Release**:
   - Create a new Git tag for the release:
     ```bash
     git tag -a v1.0.0 -m "Release version 1.0.0"
     git push origin v1.0.0
     ```

4. **Create Release Notes**:
   - Create release notes that include the following updates and changes:
     * Added `.editorconfig` file for consistent coding styles across different editors.
     * Added GitHub Actions workflows for continuous integration:
       * `CI.yml` (`.github/workflows/CI.yml`) for Python CI.
       * `rust.yml` (`.github/workflows/rust.yml`) for Rust CI.
     * Updated `.gitignore` to include various files and directories to be ignored by Git.
     * Added `.python-version` file specifying Python version 3.12.
     * Added `.vscode/settings.json` for VS Code settings.
     * Added `Cargo.toml` for Rust project configuration.
     * Added `CLAUDE.md` with commands and guidelines for the project.
     * Added `demo_output/output.json`, `demo_output/output.md`, and `demo_output/output.xml` as examples of output formats.
     * Added `JS_RENDERING.md` for JavaScript rendering support documentation.
     * Updated `README.md` with project details, features, installation, usage, and more.
     * Added `test_data/sample.md` as a sample markdown file for testing.

5. **Push Changes**:
   - Push the changes to the main branch:
     ```bash
     git push origin main
     ```

6. **Create GitHub Release**:
   - Go to the GitHub repository and create a new release using the tag created in step 3. Include the release notes created in step 4.

7. **Verify Release**:
   - Verify that the release has been created successfully and that the release notes are accurate.
