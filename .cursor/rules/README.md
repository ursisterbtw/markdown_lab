# Coding Rules for markdown_lab

This directory contains comprehensive coding standards and architecture guidelines for the markdown_lab project - a high-performance Python-Rust hybrid tool for converting HTML content to Markdown, JSON, and XML formats.

## Rule Files Overview

### 🐍 [python-coding-standards.mdc](./python-coding-standards.mdc)

Python-specific coding standards including:

- **Language Standards**: Python 3.12+ with modern syntax and type annotations
- **Package Management**: Using `uv` for dependencies, `bun` for JS/TS packaging
- **Code Organization**: Module structure, class design, function patterns
- **Type Safety**: Comprehensive type hints and error handling
- **Testing**: pytest patterns, fixtures, mocking strategies
- **Documentation**: Google-style docstrings and code comments
- **Performance**: Async/await usage, resource management, structured logging
- **Integration**: PyO3 bindings and Rust backend integration

### 🦀 [rust-pyo3-standards.mdc](./rust-pyo3-standards.mdc)

Rust and PyO3 integration standards including:

- **Language Standards**: Rust 2024 edition with modern idioms
- **PyO3 Integration**: Module definition, function signatures, error handling
- **Performance**: HTML parsing optimization, memory efficiency, parallel processing
- **Code Organization**: Module structure, configuration management
- **Testing**: Unit tests, integration tests, benchmarks
- **Documentation**: Comprehensive function and module documentation
- **Build Configuration**: Cargo.toml optimization, feature flags
- **Code Quality**: Clippy configuration, formatting standards

### 🏗️ [architecture-patterns.mdc](./architecture-patterns.mdc)

System architecture and design patterns including:

- **Hybrid Design**: Python-Rust integration architecture
- **Core Principles**: Separation of concerns, dual backend strategy
- **Module Organization**: Package structure for both Python and Rust
- **Data Flow**: Conversion pipeline and error handling flow
- **Interface Design**: Converter patterns, backend abstraction, format system
- **Configuration**: Hierarchical configuration management
- **Performance**: Caching strategies, parallel processing patterns
- **Testing Architecture**: Test organization and patterns
- **Deployment**: Package distribution, container support
- **Monitoring**: Structured logging and metrics collection

## Quick Reference Guide

### Project Structure
```
markdown_lab/
├── src/                    # Rust source code
├── markdown_lab/           # Python package
│   ├── core/              # Core functionality
│   ├── formats/           # Output formatters
│   ├── network/           # HTTP client
│   └── utils/             # Utilities
├── tests/                 # Test suites
└── .cursor/rules/         # This directory
```

### Key Technologies
- **Python**: 3.12+ with Typer, Rich, httpx, Pydantic
- **Rust**: 2024 edition with PyO3, scraper, pulldown-cmark
- **Build**: maturin for Python-Rust bindings
- **Package Management**: uv (Python), Cargo (Rust)
- **Testing**: pytest (Python), cargo test (Rust)
- **Linting**: ruff (Python), clippy (Rust)

### Development Commands
```bash
# Setup and build
just setup                 # Initial setup
just build-dev             # Build for development
just build-release         # Optimized build

# Testing
just test                  # Run all tests
just test-python           # Python tests only
just test-rust             # Rust tests only
just test-bindings         # Python-Rust integration

# Code quality
just lint                  # Run all linting
just typecheck             # Type checking
ruff check . --fix         # Python linting
cargo clippy               # Rust linting

# Usage
mlab convert <url>         # Convert single URL
mlab batch <file>          # Batch conversion
mlab-tui                   # Terminal UI
```

### Architecture Overview
```
URL/HTML → HTTP Client → Cache → HTML Parser → Content Extract → Format Convert → Output
   ↑           ↑          ↑         ↑             ↑              ↑
 Python     Python    Python     Rust          Rust           Rust
```

## Code Quality Standards

### Python Requirements
- Type annotations for all functions and classes
- Google-style docstrings for public APIs
- pytest for testing with fixtures and mocks
- Error handling with specific exception types
- Structured logging with contextual information
- Async/await patterns for concurrent operations

### Rust Requirements
- Comprehensive error handling with thiserror
- PyO3 integration with proper type conversions
- Performance optimization with cached selectors
- Memory-efficient processing patterns
- Extensive unit and integration testing
- Clear documentation with examples

### Integration Requirements
- Graceful fallback from Rust to Python backends
- Consistent error handling across language boundaries
- Proper resource management and cleanup
- Performance monitoring and metrics collection
- Comprehensive test coverage for bindings

## Common Patterns

### Error Handling
```python
# Python
try:
    result = converter.convert(url)
except NetworkError as e:
    logger.error("Network error", url=url, error=str(e))
    raise
```

```rust
// Rust
pub fn convert_html(html: &str) -> Result<String, ConversionError> {
    html_to_markdown(html, &ConversionOptions::default())
        .map_err(|e| ConversionError::ParseError(e.to_string()))
}
```

### Configuration
```python
# Hierarchical configuration loading
config = AppConfig.load_from_multiple_sources([
    system_config_path,
    user_config_path,
    project_config_path,
    environment_variables
])
```

### Async Processing
```python
# Parallel batch processing
async def process_urls(urls: List[str]) -> List[Result]:
    async with httpx.AsyncClient() as client:
        tasks = [process_single_url(client, url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

## Best Practices

### Performance
- Use Rust backend for CPU-intensive operations
- Implement caching for repeated operations
- Process items in parallel when possible
- Monitor memory usage for large documents
- Use efficient data structures and algorithms

### Maintainability
- Keep functions small and focused
- Use descriptive names and comprehensive documentation
- Write tests before implementing features
- Follow consistent code style and formatting
- Regular refactoring to improve code quality

### Reliability
- Handle all error cases gracefully
- Provide meaningful error messages
- Implement proper logging and monitoring
- Use type checking to catch errors early
- Maintain high test coverage

## Getting Started

1. **Read Architecture Patterns**: Understand the overall system design
2. **Review Python Standards**: Learn Python coding conventions
3. **Study Rust Standards**: Understand PyO3 integration patterns
4. **Run Development Setup**: Use `just setup` to prepare environment
5. **Write Tests First**: Follow TDD approach for new features
6. **Use Modern Tooling**: Leverage ruff, mypy, clippy for code quality

These rules ensure consistent, maintainable, and high-performance code across the entire markdown_lab project.