# Commands & Guidelines for markdown_lab

## Build & Test Commands
- `cargo build` - Build Rust components
- `cargo build --release --features real_rendering` - Build with JS rendering support
- `pip install -r requirements.txt` - Install Python dependencies
- `pytest` - Run all Python tests
- `pytest tests/test_python_bindings.py -v` - Run Python binding tests
- `pytest test_main.py::test_convert_to_markdown -v` - Run specific Python test
- `pytest test_main.py::test_format_conversion -v` - Test JSON and XML output formats
- `cargo test` - Run Rust tests
- `RUST_LOG=debug cargo test -- --nocapture` - Run Rust tests with logging
- `cargo bench` - Run all benchmarks
- `cargo bench html_to_markdown` - Run specific benchmark
- `python demo_formats.py` - Demonstrate all output formats (markdown, JSON, XML)
- `mypy *.py` - Type checking

## Code Quality Commands
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
  - **markdown_converter.rs**: HTML to Markdown/JSON/XML conversion
  - **lib.rs**: PyO3 bindings and Python module exports
- **Python modules**: Main functionality (main.py, chunk_utils.py, etc.)
  - **markdown_lab_rs.py**: Python interface to Rust implementations
  - **main.py**: CLI interface and MarkdownScraper implementation
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