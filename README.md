![Markdown Lab](docs/assets/github-banner.svg)

# Markdown Lab

Markdown Lab combines Python and Rust components to scrape websites and convert HTML content to markdown, JSON, or XML formats. It supports sitemap parsing, semantic chunking for RAG
(Retrieval-Augmented Generation), and includes performance optimizations through Rust integration.

Key features include HTML-to-markdown/JSON/XML conversion with support for various elements (headers, links, images, lists, code blocks), intelligent content chunking that preserves document structure, and systematic content discovery
through sitemap parsing. The hybrid architecture uses Python for high-level operations and Rust for performance-critical tasks.

Check out [deepwiki](https://deepwiki.com/ursisterbtw/markdown_lab/) for a detailed breakdown of the repository.

[![CI](https://github.com/ursisterbtw/markdown_lab/actions/workflows/ci.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/ci.yml)
[![Release](https://github.com/ursisterbtw/markdown_lab/actions/workflows/release.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/release.yml)

## Features

- **CLI Interface**: Terminal output with Typer and Rich, progress bars, and interactive features
- **Terminal User Interface (TUI)**: Interactive interface for complex operations
- **Web Scraping**: Scrapes accessible websites with error handling and rate limiting
- **Sitemap Integration**: Parses sitemap.xml to discover and scrape relevant content
- **Multiple Output Formats**: Converts HTML to Markdown, JSON, or XML formats
- **RAG Chunking**: Implements chunking for Retrieval-Augmented Generation systems
- **Parallel Processing**: Batch URL processing with configurable worker threads
- **HTML Support**:
  - Headers (h1-h6)
  - Paragraphs
  - Links with resolved relative URLs
  - Images with resolved relative URLs
  - Ordered and unordered lists
  - Blockquotes
  - Code blocks
- **Real-time Progress**: Live progress tracking with terminal output
- **Document Structure Preservation**: Maintains semantic structure during conversion
- **Logging**: Detailed logging with configurable levels
- **Error Handling**: Exponential backoff and graceful failure recovery
- **Performance**: Rust-powered HTML parsing with cached selectors
- **Configuration**: Unified configuration management system
- **Connection Pooling**: Efficient HTTP client with connection reuse

## Installation

```bash
git clone https://github.com/ursisterbtw/markdown_lab.git
cd markdown_lab

# Quick setup with justfile (recommended)
just setup

# Or manual setup using UV (Python 3.12+ required)
uv sync
source .venv/bin/activate
maturin develop
```

## Usage

### Modern CLI Interface (Recommended)

The project features a modern CLI built with Typer and Rich for terminal output:

```bash
# Convert single URLs
mlab convert "https://example.com" --output article.md --format markdown
mlab convert "https://docs.example.com" --format json --chunks --chunk-size 1500

# Batch convert with progress bars
mlab batch links.txt --output batch_results --parallel --max-workers 8

# Convert via sitemap discovery
mlab sitemap "https://example.com" --min-priority 0.7 --limit 50

# Launch interactive Terminal User Interface
mlab-tui

# Show system status
mlab status

# Manage configuration
mlab config
```

### Interactive Features

```bash
# Convert with live progress updates
mlab convert "https://example.com" --interactive --output article.md

# Batch processing with rich progress bars
mlab batch links.txt --output results --interactive --parallel

# Content chunking for RAG applications
mlab convert "https://docs.example.com" --chunks --chunk-size 1500 --chunk-overlap 200
```

### Legacy CLI Interface

The original interface is still available for compatibility:

```bash
# Using legacy CLI directly
MARKDOWN_LAB_LEGACY=1 python -m markdown_lab "https://example.com" --output article.md
# or
mlab-legacy "https://example.com" --output article.md

# Convert to different formats
mlab-legacy "https://example.com" --output output.json --format json
mlab-legacy "https://example.com" --output output.xml --format xml
```

### Advanced Usage Examples

```bash
# Comprehensive sitemap scraping with modern CLI
mlab sitemap "https://example.com" \
    --min-priority 0.5 \
    --include "blog/*" "products/*" \
    --exclude "*.pdf" "temp/*" \
    --limit 50 \
    --chunks \
    --chunk-dir my_chunks \
    --rate-limit 2.0

# Parallel batch processing with progress tracking
mlab batch urls.txt \
    --output results \
    --parallel \
    --max-workers 8 \
    --format json \
    --interactive
```

### Modern CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `mlab convert <url>` | Convert single URL | `mlab convert "https://example.com" --output article.md` |
| `mlab batch <file>` | Batch convert URLs from file | `mlab batch links.txt --parallel --max-workers 8` |
| `mlab sitemap <url>` | Convert via sitemap discovery | `mlab sitemap "https://example.com" --limit 50` |
| `mlab-tui` | Launch Terminal User Interface | `mlab-tui` |
| `mlab status` | Show system status | `mlab status` |
| `mlab config` | Manage configuration | `mlab config` |

### Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output, -o` | Output file/directory | auto-generated |
| `--format, -f` | Output format (markdown, json, xml) | `markdown` |
| `--chunks` | Enable content chunking for RAG | False |
| `--chunk-size` | Maximum chunk size (characters) | 1500 |
| `--chunk-overlap` | Overlap between chunks (characters) | 200 |
| `--chunk-dir` | Directory to save chunks | `chunks` |
| `--interactive, -i` | Enable interactive progress display | False |
| `--parallel` | Use parallel processing | False |
| `--max-workers` | Maximum parallel workers | 4 |
| `--rate-limit` | Rate limit for requests (req/sec) | 2.0 |
| `--min-priority` | Minimum sitemap URL priority | 0.5 |
| `--include` | URL patterns to include | None |
| `--exclude` | URL patterns to exclude | None |
| `--limit` | Maximum URLs to process | None |

### As a Module

#### Basic Scraping and Conversion

```python
from markdown_lab.core.scraper import MarkdownScraper
from markdown_lab.core.config import MarkdownLabConfig

# Using centralized configuration
config = MarkdownLabConfig(
    requests_per_second=2.0,
    timeout=30,
    cache_enabled=True
)

# Using default Markdown format
scraper = MarkdownScraper(config)
html_content = scraper.scrape_website("https://example.com")
markdown_content = scraper.convert_to_markdown(html_content, "https://example.com")
scraper.save_content(markdown_content, "output.md")

# Using JSON or XML format with the Rust implementation
from markdown_lab import markdown_lab_rs

html_content = scraper.scrape_website("https://example.com")

# Convert to Markdown (legacy helper)
markdown_content = markdown_lab_rs.convert_html_to_markdown(
    html_content, "https://example.com"
)
scraper.save_content(markdown_content, "output.md")

# Convert to JSON or XML using string format names
json_content = markdown_lab_rs.convert_html_to_format(
    html_content, "https://example.com", "json"
)
scraper.save_content(json_content, "output.json")

xml_content = markdown_lab_rs.convert_html_to_format(
    html_content, "https://example.com", "xml"
)
scraper.save_content(xml_content, "output.xml")

# Note: An OutputFormat enum is exposed for convenience:
# from markdown_lab import markdown_lab_rs
# fmt = markdown_lab_rs.OutputFormat.from_str("json")  # returns an enum value
# The current Python bindings accept string names ("markdown"|"json"|"xml").
```

#### With Sitemap Discovery

```python
from markdown_lab.core.scraper import MarkdownScraper

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

#### Using Links File

```python
from markdown_lab.core.scraper import MarkdownScraper

scraper = MarkdownScraper(requests_per_second=2.0)
# Scrape URLs from a links file
scraper.scrape_by_links_file(
    links_file="links.txt",        # File containing URLs to scrape
    output_dir="output_dir",       # Directory to save output files
    save_chunks=True,              # Enable chunking
    output_format="markdown",      # Output format (markdown, json, xml)
    parallel=True,                 # Enable parallel processing
    max_workers=8                  # Use 8 parallel workers
)
```

#### Direct Sitemap Access

```python
from markdown_lab.utils.sitemap_utils import SitemapParser, discover_site_urls

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

### Using Justfile (Recommended)

```bash
# Run all tests (Rust + Python + integration)
just test

# Run specific test suites
just test-python          # Python tests only
just test-rust            # Rust tests only
just test-bindings        # Python binding tests
just test-integration     # Integration tests
just test-coverage        # Tests with coverage reporting

# Development workflow
just dev-cycle            # Quick build + test cycle
just full-cycle           # Complete build + lint + test
```

### Raw Commands

```bash
# All tests
pytest -m "not integration"  # unit tests

# Run integration tests (Rust-backed path)
pytest -m integration

# Rust tests
cargo test
RUST_LOG=debug cargo test -- --nocapture

# Python binding tests
pytest tests/rust/test_python_bindings.py -v

# Unit tests
pytest tests/unit/
```

## Running Benchmarks

```bash
# Using justfile
just bench                # All benchmarks
just bench-html          # HTML parsing benchmark
just bench-chunk         # Chunking benchmark
just bench-viz           # Visualize results

# Raw commands
cargo bench
cargo bench html_to_markdown
cargo bench chunk_markdown

# Visualize results
python scripts/visualize_benchmarks.py
```

## Development

### Justfile Commands

The project uses `justfile` for development workflows. Run `just` to see all commands:

```bash
# Setup and environment
just setup               # Complete development setup
just status              # Check project status
just clean               # Clean build artifacts
just update              # Update dependencies

# Building
just build-dev           # Development build
just build-release       # Optimized build
just build-js            # Build with JavaScript support

# Development workflows
just dev                 # Quick development mode
just dev-cycle           # Build + test bindings
just full-cycle          # Build + lint + test
just fix                 # Fix common issues

# Code quality
just lint                # Run all linting
just lint-python         # Python linting only
just lint-rust           # Rust linting only
just typecheck           # Type checking

# Demos and examples
just demo                # Format conversion demo
just hello               # Hello world example
just cli-test            # Test CLI functionality
```

### Code Organization

- `markdown_lab/`: Main Python package

  - `__init__.py`: Package initialization
  - `__main__.py`: Command-line entry point
  - `core/`: Core functionality
    - `scraper.py`: Main scraper implementation
    - `cache.py`: Request caching
    - `throttle.py`: Rate limiting for web requests
  - `utils/`: Utility modules
    - `chunk_utils.py`: Utilities for chunking text for RAG
    - `sitemap_utils.py`: Sitemap parsing and URL discovery
    - `version.py`: Version information
  - `markdown_lab_rs.py`: Python interface to Rust components

- `src/`: Rust source code

  - `lib.rs`: Main library and Python bindings
  - `html_parser.rs`: HTML parsing utilities
  - `markdown_converter.rs`: HTML to Markdown conversion
  - `chunker.rs`: Markdown chunking logic
  - `js_renderer.rs`: JavaScript page rendering

- `tests/`: Test files

  - `unit/`: Python unit tests
  - `integration/`: Integration tests
  - `rust/`: Rust and Python binding tests

- `benches/`: Benchmark files

  - Performance tests for core operations

- `examples/`: Example scripts and demos

  - `demo_formats.py`: Demo of different output formats
  - `hello.py`: Simple hello world example

- `docs/`: Documentation
  - Various documentation files and guides
  - `assets/`: Documentation assets like images

### Running with Real JavaScript Rendering

To enable real JavaScript rendering with headless Chrome:

```bash
cargo build --release --features real_rendering
```

See `docs/JS_RENDERING.md` for more details.

### Rust-Python module naming

The PyO3 extension is built and imported as `markdown_lab.markdown_lab_rs` (namespaced module).

- In Python, import via `from markdown_lab import markdown_lab_rs`.
- The internal wrapper `markdown_lab/markdown_lab_rs.py` calls functions on this module and provides Python fallbacks.
- Do not import a top-level `markdown_lab_rs` package; it will fail to resolve.

## Performance Considerations

- HTML to Markdown conversion is optimized for medium to large documents with cached selectors
- Chunking algorithm balances semantic coherence with performance
- JavaScript rendering can be CPU and memory intensive
- Unified HTTP client provides connection pooling and efficient request handling
- Centralized configuration management reduces overhead and improves consistency

## Dependencies

### Core Dependencies

- **Python 3.12+**: Required minimum Python version
- **requests**: Web scraping and HTTP requests
- **beautifulsoup4**: HTML parsing fallback
- **typer**: Modern CLI framework with rich terminal output
- **rich**: Terminal formatting and progress bars
- **textual**: Terminal User Interface framework

### Development Dependencies

- **pytest**: Testing framework with benchmarking support
- **mypy**: Type checking with strict configuration
- **ruff**: Fast Python linter and formatter
- **maturin**: Rust-Python integration
- **uv**: Fast Python package manager

### Rust Dependencies

- **pyo3**: Python bindings
- **scraper**: High-performance HTML parsing with cached selectors
- **serde**: Serialization for JSON/XML output
- **once_cell**: Cached selector compilation

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE file](LICENSE) for details.

## Roadmap

### ✅ Completed

- [x] Add support for more HTML elements
- [x] Implement chunking for RAG
- [x] Add sitemap.xml parsing for systematic scraping
- [x] Add JSON and XML output formats
- [x] **Optimize HTML parsing with cached selectors** (40-50% performance improvement)
- [x] **Centralized configuration management**
- [x] **Unified error hierarchy with structured exceptions**
- [x] **Unified HTTP client with connection pooling**
- [x] **Remove dead dependencies and fix version conflicts**

### 🚧 In Progress

- [ ] Async HTTP operations for parallel processing
- [ ] Memory usage optimization in chunking algorithms
- [ ] Module restructuring for better maintainability

### 📋 Planned

- [ ] Add support for JavaScript-rendered pages
- [ ] Implement custom markdown templates
- [ ] Include CSS selector support
- [ ] Enhanced caching with LRU eviction
- [ ] Token bucket rate limiting

## Author

ursister

---

## Creating an Official Release

To create an official release, follow these steps:

1. **Update Version Numbers**:

    - Update the version number in `Cargo.toml`, `pyproject.toml`, and `markdown_lab/__init__.py` to the new release version.

2. **Commit Changes**:

    - Commit the changes to the version numbers and any other updates.

3. **Tag the Release**:

    - Create a new Git tag for the release:

        ```bash
        git tag -a v1.0.0 -m "Release version 1.0.0"
        git push origin v1.0.0
        ```

4. **Push Changes**:

    - Push the changes to the main branch:

        ```bash
        git push origin main
        ```

5. **Create GitHub Release**:

    - Go to the GitHub repository and create a new release using the tag created in step 3.

6. **Verify Release**:
    - Verify that the release has been created successfully and that all components are working as expected.
