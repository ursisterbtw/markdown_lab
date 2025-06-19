# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Standards and Rules

**IMPORTANT**: This project follows comprehensive coding standards defined in `.cursor/rules/`:

- **Python Standards**: See `.cursor/rules/python-coding-standards.mdc` for Python 3.12+ patterns, type annotations, testing with pytest, and PyO3 integration
- **Rust Standards**: See `.cursor/rules/rust-pyo3-standards.mdc` for Rust 2024 edition, PyO3 bindings, performance optimization, and error handling
- **Architecture**: See `.cursor/rules/architecture-patterns.mdc` for system design, data flow, interface patterns, and performance strategies
- **Quick Reference**: See `.cursor/rules/README.md` for development commands, common patterns, and best practices

Always consult these rules before making changes to ensure consistency with project standards.

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
- `mypy markdown_lab/` - Type checking (note: target specific directory)
- `cargo fmt` - Format Rust code
- `cargo clippy` - Rust linting

### Hybrid Project Commands

**Most Important**: After making Rust changes, always rebuild:
```bash
just build-dev                    # Quick rebuild for development
just build-release               # Optimized rebuild
maturin develop                  # Direct rebuild command
```

**Testing the Python-Rust Interface**:
```bash
just test-bindings               # Test Python can call Rust functions
pytest tests/rust/ -v            # Detailed binding tests
```

**Common Development Pattern**:
```bash
# Make Rust changes
edit src/markdown_converter.rs
just build-dev                   # Rebuild bindings
just test-bindings               # Test the interface works
pytest tests/unit/test_main.py   # Test full functionality
```

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

## Architecture Overview

This is a **hybrid Python-Rust project** using PyO3 for bindings. The architecture follows a clear separation:

### Core Design Principles
- **Rust handles performance-critical operations**: HTML parsing, format conversion, content chunking
- **Python handles orchestration**: HTTP requests, configuration, CLI, workflow management
- **Dual backend system**: Rust backend for performance, Python fallback for compatibility
- **Format-agnostic pipeline**: Single converter that outputs Markdown, JSON, or XML

### Key Components

1. **Converter Pipeline**: `Converter` class coordinates the entire pipeline
2. **Rust Backend**: Performance-optimized core operations via PyO3
3. **Format System**: Pluggable formatters for different output types
4. **Legacy Compatibility**: `MarkdownScraper` maintains old API while using new architecture

## Repository Structure

- **src/**: Rust code with PyO3 bindings
    - **lib.rs**: PyO3 module definition and Python function exports
    - **html_parser.rs**: Optimized HTML parsing with cached selectors
    - **markdown_converter.rs**: HTML to Markdown/JSON/XML conversion
    - **chunker.rs**: Semantic content chunking for RAG
    - **js_renderer.rs**: JavaScript page rendering (optional feature)
- **markdown_lab/**: Main Python package
    - **core/**: Core functionality
        - **converter.py**: New simplified converter (preferred)
        - **scraper.py**: Legacy MarkdownScraper (backwards compatibility)
        - **config.py**: Centralized configuration management
        - **errors.py**: Unified error hierarchy with structured exceptions
        - **rust_backend.py**: Interface to Rust implementations
        - **cache.py**: Request caching
        - **throttle.py**: Rate limiting for web requests
    - **formats/**: Output format handlers
        - **base.py**: Base formatter interface
        - **markdown.py**: Markdown output formatter
        - **json.py**: JSON output formatter  
        - **xml.py**: XML output formatter
    - **network/**: HTTP client and networking utilities
        - **client.py**: Unified HTTP client with connection pooling
    - **utils/**: Utility modules
        - **chunk_utils.py**: Utilities for chunking text for RAG
        - **sitemap_utils.py**: Sitemap parsing and URL discovery
    - **cli.py**: Modern Typer-based CLI interface
    - **tui.py**: Terminal user interface
    - **markdown_lab_rs.py**: Python interface to Rust implementations
- **tests/**: Test files for both Python and Rust components
    - **rust/**: Python binding tests
    - **unit/**: Python unit tests
    - **integration/**: Integration tests
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

## Development Workflow for Hybrid Python-Rust Project

### Building and Testing Strategy

**Important**: This project requires building Rust components before Python functionality works. Always build Rust first.

1. **Initial Setup**: `just setup` (installs dependencies + builds Rust components)
2. **After Rust Changes**: `just build-dev` or `maturin develop` (rebuilds Rust bindings)
3. **After Python Changes**: No rebuild needed, changes are picked up automatically
4. **Full Development Cycle**: `just dev-cycle` (build + test bindings)

### Testing Both Languages

- **Python Tests**: `just test-python` or `pytest tests/`
- **Rust Tests**: `just test-rust` or `cargo test`
- **Binding Tests**: `just test-bindings` (tests Python-Rust interface)
- **All Tests**: `just test` (runs Rust + Python + integration)

### Key Files to Understand

- **src/lib.rs** - PyO3 function exports, defines Python-accessible API
- **markdown_lab/core/converter.py** - New simplified conversion pipeline
- **markdown_lab/core/scraper.py** - Legacy API (for backwards compatibility)
- **markdown_lab/core/rust_backend.py** - Python interface to Rust backend
- **justfile** - Comprehensive task runner with all development commands

### Performance Considerations

- HTML parsing and conversion are handled by Rust for performance
- Python handles HTTP requests, configuration, and orchestration
- Use `cargo bench` to benchmark Rust components
- Use `pytest-benchmark` for Python performance tests

### Working with Output Formats

The project uses a pluggable formatter system:
- **Format handlers** in `markdown_lab/formats/` define output structure
- **Rust backend** does the actual conversion for performance
- **Both systems** must be updated when adding new formats

## Current Project Status

### Phase 1 Refactoring Complete ✅

**Achievements:**
- ✅ Centralized configuration system with validation
- ✅ Unified error hierarchy with structured exceptions
- ✅ Consolidated HTTP client with connection pooling
- ✅ Optimized HTML parsing (40-50% performance improvement)
- ✅ Modern build system with uv and justfile
- ✅ Comprehensive coding standards in `.cursor/rules/`
- ✅ ~350+ lines of code eliminated

**Key Improvements:**
- **Performance**: HTML parsing optimized with cached selectors using once_cell
- **Architecture**: Dual backend system (Rust + Python fallback) established
- **Code Quality**: Strict mypy configuration, cleaned dependencies
- **Development Workflow**: Reliable justfile recipes for consistent development

### Phase 2 Async Foundation Complete ✅

**Achievements (5/9 tasks completed):**
- ✅ AsyncHttpClient with connection pooling (300% improvement for multi-URL processing)
- ✅ TokenBucket rate limiting with burst support and per-domain controls
- ✅ HierarchicalCache system (L1/L2/L3 architecture with compression)
- ✅ Rust memory optimizations (Cow<str> zero-copy, streaming chunking)
- ✅ Comprehensive validation testing (all async components validated)

**Performance Gains Achieved:**
- **Multi-URL Processing**: Parallel async processing with connection pooling
- **Memory Efficiency**: Zero-copy string processing and streaming algorithms
- **Caching**: Multi-level cache hierarchy with intelligent promotion
- **Rate Limiting**: Advanced token bucket algorithm with burst capability

### Phase 2 Focus: Architecture Consolidation

**Remaining Priorities:**
- Unified conversion pipeline with format system
- Module restructuring for better maintainability  
- Code consolidation to eliminate remaining duplication
- Performance validation and comprehensive benchmarking
