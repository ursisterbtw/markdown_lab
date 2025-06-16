# Commands & Guidelines for markdown_lab

## Modern CLI Interface (Recommended)

The project now features a modern CLI built with Typer and Rich, providing beautiful terminal output, progress bars, and interactive features.

### CLI Commands

- `python -m markdown_lab --help` - Main help and command overview
- `python -m markdown_lab convert <url>` - Convert single URL to Markdown/JSON/XML
- `python -m markdown_lab batch <links_file>` - Batch convert URLs from file
- `python -m markdown_lab sitemap <base_url>` - Convert URLs discovered via sitemap
- `python -m markdown_lab tui` - Launch interactive Terminal User Interface
- `python -m markdown_lab status` - Show system status and configuration
- `python -m markdown_lab config` - Manage configuration settings

### Short Command Aliases

- `mlab convert <url>` - Direct CLI access
- `mlab-tui` - Launch TUI directly
- `mlab-legacy` - Use legacy CLI interface

### CLI Features

- 🎨 Rich terminal output with colors and progress bars
- 🎯 Interactive mode with live progress updates
- 📊 Real-time status and statistics display
- ⚙️ Advanced configuration management
- 🔍 Comprehensive help system with examples
- 📦 Content chunking for RAG applications
- 🌐 Multiple output formats (Markdown, JSON, XML)
- ⚡ Parallel processing support for batch operations

### Example Usage

```bash
# Convert single URL with interactive progress
mlab convert "https://example.com" --interactive --output article.md

# Batch convert with parallel processing
mlab batch links.txt --output batch_results --parallel --max-workers 8

# Convert to JSON with chunking for RAG
mlab convert "https://docs.example.com" --format json --chunks --chunk-size 1500

# Discover and convert via sitemap
mlab sitemap "https://example.com" --min-priority 0.7 --limit 50

# Launch full TUI interface
mlab-tui
```

## Justfile Workflow (Alternative)

The project uses `justfile` for streamlined development workflows. Run `just` to see all available commands.

### Essential Commands

- `just setup` - Install dependencies and set up development environment
- `just test` - Run all tests (Rust + Python + integration)
- `just test-python` - Run Python tests only
- `just test-rust` - Run Rust tests only
- `just build-dev` - Build Rust components for development
- `just build-release` - Build optimized Rust components
- `just lint` - Run all linting and formatting
- `just demo` - Run format conversion demo
- `just status` - Show project status and environment info

### Development Workflow

- `just dev` - Quick development setup (build + activate environment)
- `just dev-cycle` - Build + test bindings (for active development)
- `just full-cycle` - Build + lint + test (comprehensive check)
- `just fix` - Fix common issues (clear caches, rebuild components)

### Testing & Quality

- `just test-bindings` - Run Python binding tests specifically
- `just test-integration` - Run integration tests
- `just test-coverage` - Run tests with coverage reporting
- `just typecheck` - Run type checking
- `just bench` - Run all benchmarks

## Legacy CLI Commands (Fallback)

The original argparse-based CLI is still available for compatibility. Use `MARKDOWN_LAB_LEGACY=1` or `mlab-legacy` to access it:

```bash
# Use legacy CLI directly
MARKDOWN_LAB_LEGACY=1 python -m markdown_lab "https://example.com" --output article.md
# or
mlab-legacy "https://example.com" --output article.md
```

## Raw Development Commands (Alternative)

If you prefer direct commands without justfile or the modern CLI:

### Build & Test Commands

- `cargo build` - Build Rust components
- `cargo build --release --features real_rendering` - Build with JS rendering support
- `uv sync` - Sync dependencies with uv package manager
- `source .venv/bin/activate && maturin develop` - Build Rust module for Python development
- `source .venv/bin/activate && pytest` - Run all Python tests
- `source .venv/bin/activate && pytest tests/rust/test_python_bindings.py -v` - Run Python binding tests
- `source .venv/bin/activate && pytest test_main.py::test_convert_to_markdown -v` - Run specific Python test
- `source .venv/bin/activate && pytest test_main.py::test_format_conversion -v` - Test JSON and XML output formats
- `cargo test` - Run Rust tests
- `RUST_LOG=debug cargo test -- --nocapture` - Run Rust tests with logging
- `cargo bench` - Run all benchmarks
- `cargo bench html_to_markdown` - Run specific benchmark
- `python demo_formats.py` - Demonstrate all output formats (markdown, JSON, XML)
- `mypy *.py` - Type checking

### Code Quality Commands

- `ruff check . --fix` - Run linter and auto-fix issues
- `ruff check . --fix --unsafe-fixes` - Run linter with more aggressive fixes
- `black .` - Format Python code
- `isort .` - Sort imports
- `sourcery review . --fix` - Analyze and improve code quality
- `mypy *.py` - Type checking

## Code Style Guidelines

- **Python**: Python 3.12+ with type annotations
- **Imports**: Group imports (stdlib, third-party, local)
- **Formatting**: Follow PEP 8 guidelines
- **Error handling**: Use exception handling with specific exceptions
- **Naming**: snake_case for Python, snake_case for Rust
- **Testing**: Use pytest fixtures and mocks
- **Documentation**: Docstrings for public functions and classes
- **Rust**: Follow Rust 2024 edition idioms and use thiserror for errors
- **Type annotations**: Required for all new code

## Repository Structure

- **src/**: Rust code with PyO3 bindings
    - **html_parser.rs**: Optimized HTML parsing with cached selectors
    - **markdown_converter.rs**: HTML to Markdown/JSON/XML conversion
    - **chunker.rs**: Semantic content chunking for RAG
    - **lib.rs**: PyO3 bindings and Python module exports
- **markdown_lab/**: Main Python package
    - **core/**: Core functionality
        - **config.py**: Centralized configuration management
        - **errors.py**: Unified error hierarchy with structured exceptions
        - **scraper.py**: Main scraper implementation
        - **cache.py**: Request caching
        - **throttle.py**: Rate limiting for web requests
    - **network/**: HTTP client and networking utilities
        - **client.py**: Unified HTTP client with connection pooling
    - **utils/**: Utility modules
        - **chunk_utils.py**: Utilities for chunking text for RAG
        - **sitemap_utils.py**: Sitemap parsing and URL discovery
    - **markdown_lab_rs.py**: Python interface to Rust implementations
- **tests/**: Test files for both Python and Rust components
- **benches/**: Performance benchmarks

## Output Format Features

- **Markdown**: Human-readable plain text format (default)
- **JSON**: Structured data format for programmatic usage
    - Document structure with title, headers, paragraphs, links, images, etc.
    - Serialized with proper indentation for readability
- **XML**: Markup format for document interchange
    - Document structure with proper XML tags and hierarchy
    - Includes XML declaration and proper escaping
- Use `-f/--format` CLI argument to specify output format
- All formats support the same HTML elements and content structure
