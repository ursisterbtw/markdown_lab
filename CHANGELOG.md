# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **XML/JSON Conversion Error (2025-06-19)**: Fixed `AttributeError: module 'markdown_lab.markdown_lab_rs' has no attribute 'convert_html'` that prevented XML and JSON output formats from working
  - **Root Cause**: Function name mismatch between Python backend calling `convert_html()` and Rust module exporting `convert_html_to_format()`
  - **Solution**: Updated `markdown_lab/core/rust_backend.py:76` to call correct function name
  - **Impact**: All three output formats (Markdown, JSON, XML) now work correctly
  - **Files Changed**: `markdown_lab/core/rust_backend.py`

- **Criterion Benchmark Configuration (2025-06-19)**: Verified and confirmed proper setup of Rust benchmark infrastructure
  - **Status**: Benchmarks are correctly located in `benches/` directory with proper Cargo.toml configuration
  - **Dependencies**: Criterion is properly configured under `[dev-dependencies]` with HTML reports enabled
  - **Test Coverage**: Benchmarks cover HTML processing, markdown conversion, and text chunking functionality
  - **Note**: Any CI/CD failures related to benchmarks are likely environment-specific rather than code issues

### Changed

- **Code Review Improvements (2025-06-19)**: Addressed maintainability and architecture feedback
  - **Documentation**: Consolidated fix documentation into centralized CHANGELOG.md to reduce maintenance overhead
  - **Architecture**: Simplified `rust_backend.py` by removing special-case conditional logic for markdown format
  - **Impact**: Cleaner codebase with unified format conversion logic, easier to extend for future formats

## [1.0.0] - Initial Release

### Added

- HTML to Markdown conversion with Rust backend
- Multiple output formats: Markdown, JSON, XML
- Modern CLI interface with Typer and Rich
- Batch processing capabilities
- Sitemap-based URL discovery
- Content chunking for RAG applications
- Parallel processing support
- Interactive Terminal User Interface (TUI)
- Comprehensive configuration management
- HTTP client with connection pooling and caching
- Rate limiting and throttling
- Content validation and error handling
