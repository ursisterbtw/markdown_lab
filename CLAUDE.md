# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Building & Testing
```bash
# Quick development build with Rust bindings
just build-dev
# or directly:
source .venv/bin/activate && maturin develop

# Run all tests (Rust + Python + integration)
just test

# Run specific test suites
just test-python          # Python tests only
just test-rust            # Rust tests only  
just test-bindings        # Python binding tests
pytest tests/rust/test_python_bindings.py -v  # Direct binding tests

# Run single test
pytest tests/unit/test_main.py::test_convert_to_markdown -v

# Test with coverage
just test-coverage
```

### Code Quality
```bash
# Run all linting and formatting
just lint

# Python linting
ruff check . --fix
black .
mypy markdown_lab/

# Rust linting
cargo fmt -- --check
cargo clippy -- -D warnings

# Type checking
just typecheck
```

### CLI Development
```bash
# Modern CLI (Typer-based)
mlab convert "https://example.com" --output article.md
mlab batch links.txt --parallel --max-workers 8
mlab-tui  # Launch TUI

# Legacy CLI (argparse-based) 
MARKDOWN_LAB_LEGACY=1 python -m markdown_lab "https://example.com"
mlab-legacy "https://example.com"

# Test format conversion
python examples/demo_formats.py
```

## High-Level Architecture

### Hybrid Python-Rust Design
The codebase uses a dual-backend architecture where performance-critical operations are implemented in Rust with PyO3 bindings, while high-level orchestration remains in Python.

**Rust Core (`src/`):**
- `html_parser.rs`: HTML parsing with cached selectors using once_cell for 40-50% performance gains
- `markdown_converter.rs`: HTML to Markdown/JSON/XML conversion with format-specific serialization
- `chunker.rs`: Semantic content chunking for RAG applications
- `lib.rs`: PyO3 bindings exposing Rust functions to Python

**Python Orchestration (`markdown_lab/`):**
- `core/converter.py`: Unified converter that automatically selects Rust or Python backend
- `core/rust_backend.py`: Wrapper for Rust bindings with automatic fallback
- `core/scraper.py`: Legacy interface maintained for backwards compatibility
- `core/client.py`: HTTP client with connection pooling and exponential backoff
- `core/config.py`: Centralized configuration management

### Key Design Patterns

1. **Automatic Backend Selection**: The `Converter` class transparently uses Rust when available, falling back to Python implementations without code changes.

2. **Cached Selectors**: Rust HTML parser pre-compiles and caches CSS selectors using `once_cell::sync::Lazy`, providing significant performance improvements on repeated operations.

3. **Unified Error Hierarchy**: All errors inherit from `MarkdownLabError` with structured exception types for network, parsing, configuration, and conversion errors.

4. **Connection Pooling**: HTTP client maintains persistent connections with configurable pool sizes and automatic retry logic.

### Format Support Architecture

The system supports multiple output formats through a pluggable architecture:
- **Markdown**: Default human-readable format
- **JSON**: Structured document representation with headers, paragraphs, links, images
- **XML**: Hierarchical document structure with proper escaping

Format selection happens at the Rust level for performance, with Python providing the interface.

### CLI Architecture

Two CLI systems coexist:
1. **Modern CLI (`cli.py`)**: Typer-based with Rich output, progress bars, and TUI support
2. **Legacy CLI (`scraper.py:main`)**: Argparse-based for backwards compatibility

The modern CLI is the default, with `MARKDOWN_LAB_LEGACY=1` environment variable enabling legacy mode.

### Testing Strategy

- **Unit Tests**: Isolated component testing in `tests/unit/`
- **Integration Tests**: End-to-end workflows in `tests/integration/`
- **Rust Binding Tests**: PyO3 interface validation in `tests/rust/`
- **Benchmarks**: Performance testing with criterion (Rust) and pytest-benchmark (Python)

### Performance Optimizations

1. **Cached Selectors**: CSS selectors compiled once and reused
2. **Connection Pooling**: Reuses HTTP connections across requests
3. **Rust Processing**: Critical paths implemented in Rust
4. **Chunking Algorithm**: Optimized for semantic coherence with minimal overhead

## Development Notes

- Always run `maturin develop` after modifying Rust code
- The project supports Python 3.12+ only
- Use `uv` for dependency management (faster than pip)
- JavaScript rendering available with `--features real_rendering` (requires headless Chrome)
- Centralized configuration in `MarkdownLabConfig` class - avoid scattered config parameters
- Legacy `MarkdownScraper` class wraps new `Converter` for backwards compatibility