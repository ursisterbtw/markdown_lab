# TASKS.md - Comprehensive Refactoring Task List

## Overview

This document extends the existing refactoring roadmap with aggressive performance optimization and code consolidation tasks. The goal is to achieve **40-50% LOC reduction** and **2-5x performance improvement** while maintaining all existing functionality.

## Phase 1: Foundation Tasks ✅ COMPLETED

### Status: 7/7 Tasks Complete (100%)

**LOC Reduction Achieved**: ~350 lines (10% of total target)
**Performance Improvements**: 40-50% HTML parsing improvement
**Critical Bug Fixes**: XML/JSON conversion error resolved

✅ **TASK-001**: Core Configuration System - Centralized config with validation and environment overrides  
✅ **TASK-002**: Unified Error Hierarchy - Structured exception handling with context data  
✅ **TASK-003**: HTTP Client Consolidation - Eliminated duplicate request logic with connection pooling  
✅ **TASK-004**: Dead Dependencies Cleanup - Removed unused packages, fixed version mismatches  
✅ **TASK-005**: HTML Processing Optimization - 40-50% performance improvement with cached selectors  
✅ **TASK-017**: Justfile Build System - Fixed development workflow with reliable virtual environment handling  
✅ **TASK-035**: XML/JSON Conversion Fix - Fixed function name mismatch causing AttributeError in format conversion  

---

## Phase 2: Major Consolidation & Performance (Weeks 2-4)

### Priority 1: Critical Duplications (Target: 400+ LOC reduction)

**TASK-018**: **Complete HTTP Client Unification** ⚡ HIGH IMPACT

- **Status**: 🔄 In Progress (partial completion from TASK-003)
- **Priority**: P0 - Critical
- **Estimated LOC Reduction**: 200+ lines
- **Performance Impact**: 50-100% network operation improvement
- **Files**:
  - `markdown_lab/core/client.py` (145 lines) - REMOVE entirely
  - `markdown_lab/network/client.py` (319 lines) - ENHANCE as single source
  - Update all imports throughout codebase
- **Requirements**:
  - Merge retry logic, caching, and throttling into unified client
  - Implement connection pooling optimization
  - Add comprehensive error handling
  - Ensure backwards compatibility with existing scraper
- **Validation**: All HTTP operations use single client implementation

**TASK-019**: **Legacy Wrapper Elimination** ⚡ HIGH IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P0 - Critical  
- **Estimated LOC Reduction**: 300+ lines
- **Performance Impact**: 30-50% processing overhead elimination
- **Files**:
  - `markdown_lab/core/scraper.py` (1138 lines) - Major reduction
  - `markdown_lab/core/converter.py` - Direct usage pattern
  - Update CLI and TUI to use Converter directly
- **Requirements**:
  - Create migration path from MarkdownScraper to Converter
  - Remove duplicate session management and performance monitoring
  - Preserve backwards compatibility for existing integrations
  - Document breaking changes and migration guide
- **Validation**: Direct Converter usage throughout application

**TASK-020**: **Configuration Parameter Consolidation** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P1 - High
- **Estimated LOC Reduction**: 150+ lines  
- **Performance Impact**: Reduced initialization overhead
- **Files**:
  - `markdown_lab/core/scraper.py:45-74` - Parameter definitions
  - `markdown_lab/utils/sitemap_utils.py:35-61` - Parameter definitions
  - Multiple test files with similar setup
- **Requirements**:
  - Create single ParameterSet class for shared configurations
  - Implement parameter inheritance and overrides
  - Remove duplicate validation logic
  - Standardize default values across all implementations
- **Validation**: Single source of truth for all configuration parameters

### Priority 2: Async Operations (Target: 300-500% performance improvement)

**TASK-021**: **Async HTTP Operations Implementation** ⚡ HIGH IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P0 - Critical
- **Estimated LOC Change**: +100 lines (net gain in functionality)
- **Performance Impact**: 300-500% improvement for multi-URL operations
- **Files**:
  - `markdown_lab/network/client.py` - Add async methods
  - `markdown_lab/core/converter.py` - Async conversion methods
  - `markdown_lab/core/scraper.py:680-698` - Replace synchronous batch processing
- **Requirements**:
  - Implement async versions of all HTTP operations
  - Add concurrent processing with configurable limits
  - Maintain synchronous API for backwards compatibility
  - Add proper async context management
- **Validation**: Batch operations show 3-5x speed improvement

**TASK-022**: **Stream Processing Architecture** ⚡ HIGH IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P1 - High
- **Estimated LOC Change**: +150 lines (major functionality enhancement)
- **Performance Impact**: 60-70% memory usage reduction
- **Files**:
  - `markdown_lab/core/converter.py` - Stream-based conversion
  - `markdown_lab/utils/chunk_utils.py` - Stream-based chunking
  - `src/markdown_converter.rs` - Streaming Rust implementation
- **Requirements**:
  - Replace in-memory processing with streaming where possible
  - Implement chunked reading and writing for large content
  - Add memory usage monitoring and limits
  - Preserve existing API for small content
- **Validation**: Memory usage reduced by 60-70% for large documents

### Priority 3: Backend Optimization (Target: 100-200% processing improvement)

**TASK-023**: **Rust Backend Prioritization** ⚡ HIGH IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P1 - High
- **Estimated LOC Reduction**: 100+ lines
- **Performance Impact**: 100-200% processing speed improvement
- **Files**:
  - `markdown_lab/utils/chunk_utils.py:166-217` - Replace with Rust calls
  - `markdown_lab/core/converter.py` - Prefer Rust implementations
  - `src/lib.rs` - Expose more Rust functions to Python
- **Requirements**:
  - Replace Python chunking with consistent Rust backend usage
  - Add fallback detection and automatic backend selection
  - Eliminate duplicate processing between Python and Rust
  - Add performance monitoring for backend selection
- **Validation**: Rust backend used for >90% of processing operations

**TASK-024**: **DOM-Based HTML Cleaning** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P2 - Medium
- **Estimated LOC Change**: +50 lines (better algorithm)
- **Performance Impact**: 50-100% improvement for large HTML documents
- **Files**:
  - `src/html_parser.rs:126-131` - Replace string-based cleaning
- **Requirements**:
  - Implement DOM-based element removal instead of string replacement
  - Optimize for O(n) complexity instead of O(n²)
  - Add caching for element removal patterns
  - Maintain exact compatibility with existing behavior
- **Validation**: HTML cleaning shows linear performance scaling

---

## Phase 3: Advanced Optimization (Weeks 4-6)

### Priority 1: Memory & Resource Optimization

**TASK-025**: **Advanced Caching System** ⚡ HIGH IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P1 - High
- **Estimated LOC Change**: +200 lines, -50 lines duplicate logic
- **Performance Impact**: 80% cache hit rate, 40% overall speed improvement
- **Files**:
  - `markdown_lab/core/cache.py:26-28` - Add LRU eviction and size limits
  - `markdown_lab/network/client.py` - Enhanced cache integration
  - New: `markdown_lab/core/cache_manager.py` - Multi-level caching
- **Requirements**:
  - Implement LRU eviction with configurable memory limits
  - Add compression for stored HTML content
  - Implement predictive pre-caching for batch operations
  - Add cache performance metrics and monitoring
- **Validation**: Memory usage bounded, >80% cache hit rate for repeated operations

**TASK-026**: **Regex Pattern Caching** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P2 - Medium
- **Estimated LOC Reduction**: 20+ lines
- **Performance Impact**: 30-50% improvement in sitemap filtering
- **Files**:
  - `markdown_lab/utils/sitemap_utils.py:383-384, 392-393` - Cache compiled patterns
- **Requirements**:
  - Cache compiled regex patterns at class level
  - Implement pattern cache with size limits
  - Add pattern compilation metrics
  - Ensure thread-safety for cached patterns
- **Validation**: Regex compilation overhead eliminated for repeated operations

### Priority 2: Architecture Improvements

**TASK-027**: **Service Layer Architecture** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P1 - High
- **Estimated LOC Change**: +300 lines (major architectural improvement)
- **Performance Impact**: Better resource management, improved testability
- **Files**:
  - New: `markdown_lab/services/` - Service layer implementation
  - `markdown_lab/cli.py` - Use services instead of direct class instantiation
  - `markdown_lab/tui.py` - Service-based architecture
- **Requirements**:
  - Create service layer for business logic separation
  - Implement dependency injection for better testability
  - Add service lifecycle management
  - Create clean interfaces between layers
- **Validation**: Clear separation of concerns, improved test isolation

**TASK-028**: **Format Strategy Pattern** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P2 - Medium
- **Estimated LOC Reduction**: 80+ lines
- **Performance Impact**: Reduced object creation overhead
- **Files**:
  - `markdown_lab/formats/` - Replace inheritance with composition
  - `markdown_lab/core/converter.py` - Use strategy pattern for format selection
- **Requirements**:
  - Replace inheritance with composition for formatters
  - Implement strategy pattern for format selection
  - Add dynamic format registration
  - Reduce object creation overhead
- **Validation**: Format selection shows improved performance and flexibility

---

## Phase 4: Consolidation & Cleanup (Weeks 6-8)

### Priority 1: Duplicate Code Elimination

**TASK-029**: **Unified Utility Functions** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P2 - Medium
- **Estimated LOC Reduction**: 200+ lines
- **Performance Impact**: Reduced maintenance overhead
- **Files**:
  - `markdown_lab/core/scraper.py:452-476` - Filename from URL
  - `markdown_lab/core/converter.py:191-224` - Duplicate filename logic
  - Multiple files with duplicate directory creation logic
- **Requirements**:
  - Create shared utility module for common functions
  - Consolidate URL parsing and filename generation
  - Unify directory creation and file management
  - Add comprehensive utility function tests
- **Validation**: No duplicate utility functions remain in codebase

**TASK-030**: **Test Code Optimization** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P3 - Low
- **Estimated LOC Reduction**: 100+ lines
- **Performance Impact**: Faster test execution
- **Files**:
  - `tests/` - Consolidate shared fixtures and mocks
  - Multiple test files with duplicate setup patterns
- **Requirements**:
  - Move shared fixtures to conftest.py
  - Consolidate HTTP response mocking patterns
  - Remove duplicate test utility functions
  - Optimize test data generation
- **Validation**: Test execution time reduced by 30-50%

### Priority 2: Advanced Features

**TASK-031**: **Plugin Architecture** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P3 - Low
- **Estimated LOC Change**: +250 lines (major feature addition)
- **Performance Impact**: Extensible architecture without core changes
- **Files**:
  - New: `markdown_lab/plugins/` - Plugin system implementation
  - `markdown_lab/core/converter.py` - Plugin integration
- **Requirements**:
  - Design and implement plugin discovery system
  - Add format plugin registration
  - Create plugin API documentation
  - Implement plugin validation and sandboxing
- **Validation**: Third-party formats can be added without core changes

**TASK-032**: **Performance Monitoring** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P2 - Medium
- **Estimated LOC Change**: +100 lines (monitoring infrastructure)
- **Performance Impact**: Performance regression detection
- **Files**:
  - New: `markdown_lab/monitoring/` - Performance monitoring
  - `markdown_lab/core/converter.py` - Add performance instrumentation
- **Requirements**:
  - Add built-in performance profiling
  - Implement resource usage tracking
  - Create performance regression detection
  - Add benchmarking automation
- **Validation**: Automated performance regression detection in CI

---

## Phase 5: Validation & Documentation (Week 8)

### Critical Validation Tasks

**TASK-033**: **Performance Benchmark Validation** ⚡ HIGH IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P0 - Critical
- **Estimated LOC Change**: +50 lines (benchmark automation)
- **Performance Impact**: Validation of all performance targets
- **Files**:
  - `benches/` - Comprehensive benchmark suite
  - New: `scripts/performance_validation.py` - Automated validation
- **Requirements**:
  - Validate all performance targets achieved
  - Automated performance regression testing
  - Memory usage validation
  - Network operation speed validation
- **Validation**: All performance targets documented and achieved

**TASK-034**: **Code Quality Validation** 🎯 MEDIUM IMPACT

- **Status**: 🔄 Ready to Start
- **Priority**: P1 - High
- **Estimated LOC Change**: Documentation and tooling
- **Performance Impact**: Maintainability improvement validation
- **Files**:
  - All source files - Final code quality review
  - New: `scripts/quality_metrics.py` - Quality measurement
- **Requirements**:
  - Validate 40-50% LOC reduction achieved
  - Confirm 95% type annotation coverage
  - Validate test coverage >90%
  - Ensure all quality metrics met
- **Validation**: All code quality targets documented and achieved

---

## Summary Statistics

### Current Progress (Phase 1 Complete)

- **Tasks Completed**: 7/7 (100%)
- **LOC Reduction**: ~350 lines (10% of target)
- **Performance Improvement**: 40-50% HTML parsing
- **Current Codebase**: ~9,369 total LOC (Python + Rust)

### Remaining Work (Phases 2-5)

- **Total Tasks**: 28 tasks
- **High Impact Tasks**: 8 tasks (⚡ symbols)
- **Medium Impact Tasks**: 12 tasks (🎯 symbols)
- **Expected LOC Reduction**: 1,600-1,750 lines (additional 40-45%)
- **Expected Performance Improvement**: 2-5x overall performance

### Performance Targets

- **Network I/O**: 300-500% improvement (async operations)
- **Memory Usage**: 60-70% reduction (streaming + caching)
- **Processing Speed**: 100-200% improvement (Rust backend priority)
- **System Resources**: 80% efficiency improvement

### Code Quality Targets

- **Total LOC Reduction**: 40-50% (1,950-2,100 lines eliminated)
- **Code Duplication**: 80% elimination
- **Type Coverage**: 95% annotation coverage
- **Test Coverage**: Maintain >90% during refactoring

This comprehensive task list provides a clear roadmap for transforming the markdown_lab codebase into a high-performance, maintainable system while achieving massive code consolidation and performance improvements.
