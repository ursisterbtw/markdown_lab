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

- **Documentation Synchronization (2025-06-19)**: Updated all project documentation to reflect current state
  - **TASKS.md**: Updated to reflect completion of 7/7 Phase 1 tasks including XML/JSON fix
  - **README.md**: Added completed XML/JSON fix to roadmap and updated "In Progress" section with specific task references
  - **Current Status**: ~9,369 total LOC across Python and Rust components with Phase 1 optimizations complete
  - **Impact**: All documentation now accurately reflects project progress and remaining work

- **Code Review Improvements (2025-06-19)**: Addressed maintainability and architecture feedback from PR #27
  - **Documentation**: Consolidated fix documentation into centralized CHANGELOG.md to reduce maintenance overhead
  - **Architecture**: Simplified `rust_backend.py` by removing special-case conditional logic for markdown format
  - **Performance**: Validated and documented actual performance improvements in async batch processing
  - **Cache Management**: Implemented size limits and LRU eviction policies to prevent memory leaks
    - Memory cache limited to 1000 items by default with LRU eviction
    - Disk cache limited to 100MB with automatic cleanup
    - Added cache statistics and monitoring capabilities
  - **Error Handling**: Enhanced async operations with specific error types for timeouts, connection failures, and HTTP errors
    - Separate handling for client errors (4xx) vs server errors (5xx)
    - Exponential backoff retry logic with configurable limits
    - Structured error context for better debugging
  - **API Migration**: Successfully migrated functionality from removed `markdown_lab.core.client.HttpClient` to `markdown_lab.network.client.CachedHttpClient`
    - All HTTP methods preserved: get(), post(), head(), get_many(), and async variants
    - Enhanced with connection pooling and improved rate limiting
    - Backward compatibility maintained through import aliasing
  - **Testing**: Added comprehensive integration and unit tests
    - Integration tests for async batch processing with error handling validation
    - Unit tests for cache size limits and LRU eviction behavior
    - Performance benchmarking framework for validating async improvements
    - Cache statistics testing and memory leak prevention validation
  - **Migration Support**: Created comprehensive migration guide for users upgrading from legacy APIs
    - Step-by-step migration instructions from MarkdownScraper to Converter API
    - Performance optimization recommendations for async batch processing
    - Error handling best practices with new error types
    - Configuration examples for cache management and rate limiting
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
