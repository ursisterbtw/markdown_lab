# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Building & Testing
```bash
# Setup development environment (installs uv and builds Rust)
just setup

# Quick development build with Rust bindings
just build
# or directly:
uv run maturin develop

# Run all tests (Rust + Python + integration)
just test

# Run single test
pytest tests/unit/test_main.py::test_convert_to_markdown -v
uv run pytest tests/rust/test_python_bindings.py -v  # Direct binding tests

# Test with coverage
just test-coverage

# Run benchmarks
just bench
```

### Code Quality
```bash
# Run all linting and formatting (Python + Rust)
just lint

# Python linting individually
uv run ruff check . --fix
uv run ruff format .
uv run mypy markdown_lab/

# Rust linting individually
cargo fmt && cargo clippy -- -D warnings

# Type checking
just typecheck

# Clean build artifacts
just clean
```

### CLI Development & Testing
```bash
# Modern CLI (Typer-based) - Available commands:
mlab convert "https://example.com" --output article.md --interactive
mlab sitemap "https://example.com" --output docs/ --parallel
mlab batch links.txt --parallel --max-workers 8
mlab status  # Show system status
mlab tui     # Launch interactive TUI
mlab config --show  # Show configuration

# Legacy CLI (argparse-based)
MARKDOWN_LAB_LEGACY=1 python -m markdown_lab "https://example.com"
mlab-legacy "https://example.com"

# Examples and demos
just demo  # Run format conversion examples
uv run python examples/demo_formats.py

# Update dependencies
just update
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

Three interface layers provide different user experiences:
1. **Modern CLI (`cli.py`)**: Typer-based with Rich output, progress bars, interactive modes, and comprehensive commands (`convert`, `sitemap`, `batch`, `status`, `config`, `tui`)
2. **TUI (`tui.py`)**: Full-screen terminal interface using Textual for interactive website conversion with real-time progress and logs
3. **Legacy CLI (`scraper.py:main`)**: Argparse-based interface maintained for backwards compatibility

The modern CLI is the default, with `MARKDOWN_LAB_LEGACY=1` environment variable enabling legacy mode. The TUI can be launched via `mlab tui` command.

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

- Always run `uv run maturin develop` or `just build` after modifying Rust code
- The project supports Python 3.12+ only
- Use `uv` for dependency management (faster than pip) - all commands should be prefixed with `uv run`
- JavaScript rendering available with `--features real_rendering` (requires headless Chrome)
- Centralized configuration in `MarkdownLabConfig` class - avoid scattered config parameters
- Legacy `MarkdownScraper` class wraps new `Converter` for backwards compatibility
- Use `just setup` for initial development environment setup
- The TUI requires `textual` dependency; modern CLI requires `typer` and `rich`
- Build profiles: `--release` for optimized builds, `--features real_rendering` for JS support
