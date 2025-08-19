# Markdown Lab Project-Specific Agents

This directory contains specialized Claude Code sub-agents optimized for the markdown_lab project's unique hybrid Rust-Python architecture and development workflow.

## Repository Analysis Summary

### Project Type
**markdown_lab** is a high-performance HTML to Markdown converter with a hybrid architecture:
- **Core Engine**: Rust with PyO3 bindings for performance-critical operations (HTML parsing, conversion, chunking)
- **Orchestration Layer**: Python for CLI, web scraping, caching, and user interface
- **Output Formats**: Markdown, JSON, and XML with semantic chunking for RAG applications

### Technology Stack
- **Languages**: Rust (2024 edition), Python 3.12+
- **Key Libraries**: PyO3, Tokio, scraper, Typer, Rich, pytest, criterion
- **Build System**: maturin, uv, justfile
- **Testing**: pytest, cargo test, pytest-benchmark, criterion

### Architecture Patterns
- Strict Rust-Python separation with PyO3 FFI boundary
- Centralized configuration (MarkdownLabConfig)
- Unified error hierarchy with structured exceptions
- Shared resource pools (Tokio runtime, thread pools)
- Async/sync boundary management

### Development Workflow
- PLANNING.md for design and execution tracking
- TASKS.md with Kanban-style task management
- Structured commit conventions
- Quality gates and acceptance criteria
- Performance benchmarking requirements

## Generated Agents

### 1. markdown-lab-developer
**Location**: `development/markdown-lab-developer.md`
**Purpose**: Comprehensive development support for daily coding tasks
**Key Focus Areas**:
- Hybrid Rust-Python development patterns
- Build system management (maturin, justfile, uv)
- Feature implementation guidance
- CLI development (Typer and legacy)
- Testing and debugging workflows

**When to Use**:
- Adding new features or fixing bugs
- Build system issues or setup
- Understanding project conventions
- Running development workflows
- Debugging PyO3 binding issues

### 2. rust-python-optimizer
**Location**: `optimization/rust-python-optimizer.md`
**Purpose**: Optimizes the PyO3 bindings and hybrid architecture performance
**Key Focus Areas**:
- FFI boundary optimization
- Memory passing between Rust and Python
- Async/sync boundary management
- Dual implementation elimination
- Resource pool optimization

**When to Use**: 
- Performance bottlenecks at language boundaries
- Memory usage concerns in FFI operations
- Async runtime optimization needs
- PyO3 binding improvements

### 2. markdown-lab-architect
**Location**: `architecture/markdown-lab-architect.md`
**Purpose**: Maintains architectural integrity and enforces established patterns
**Key Focus Areas**:
- Rust-Python boundary enforcement
- Pattern consistency (config, errors, base classes)
- Code duplication prevention
- Architectural drift detection
- Module organization

**When to Use**:
- Adding new features or modules
- Architectural decision making
- Code review for pattern violations
- Refactoring guidance

### 3. chunking-semantic-expert
**Location**: `optimization/chunking-semantic-expert.md`
**Purpose**: Optimizes text chunking and semantic density calculations
**Key Focus Areas**:
- Regex pattern optimization
- Sentence/paragraph boundary detection
- Semantic density scoring
- Chunk size/overlap optimization
- RAG application performance

**When to Use**:
- Improving chunking algorithms
- Optimizing text processing pipelines
- RAG quality improvements
- Regex performance issues

### 4. planning-task-coordinator
**Location**: `workflow/planning-task-coordinator.md`
**Purpose**: Manages PLANNING.md and TASKS.md workflow
**Key Focus Areas**:
- Execution report updates
- Task state transitions
- Dependency tracking
- Quality gate validation
- Acceptance criteria monitoring

**When to Use**:
- Updating project status
- Task prioritization
- Workflow optimization
- Sprint planning

### 5. http-cache-network-specialist
**Location**: `optimization/http-cache-network-specialist.md`
**Purpose**: Optimizes networking and caching layers
**Key Focus Areas**:
- HTTP client optimization
- Cache strategy improvements
- Rate limiting algorithms
- Batch processing efficiency
- Connection pooling

**When to Use**:
- Network performance issues
- Cache optimization needs
- Rate limiting improvements
- Batch URL processing

### 6. test-coverage-guardian
**Location**: `testing/test-coverage-guardian.md`
**Purpose**: Ensures comprehensive testing coverage
**Key Focus Areas**:
- Rust and Python test coverage
- PyO3 binding testing
- Integration test development
- Performance benchmark validation
- Regression prevention

**When to Use**:
- Writing new tests
- Coverage gap analysis
- Performance regression detection
- Test strategy planning

## Agent Integration Strategy

### Complementary Usage
The agents work together to cover the full development lifecycle:

1. **Planning Phase**: `planning-task-coordinator` sets up tasks and tracks progress
2. **Architecture Phase**: `markdown-lab-architect` ensures proper design
3. **Development Phase**: `markdown-lab-developer` implements features and fixes
4. **Optimization Phase**: `rust-python-optimizer` and specialists optimize code
5. **Testing Phase**: `test-coverage-guardian` validates changes
6. **Delivery Phase**: `planning-task-coordinator` updates execution reports

### Workflow Integration

#### For New Features
1. Use `planning-task-coordinator` to create tasks
2. Consult `markdown-lab-architect` for design decisions
3. Apply `rust-python-optimizer` for performance
4. Validate with `test-coverage-guardian`

#### For Optimization Work
1. Identify bottlenecks with `rust-python-optimizer`
2. Apply specific optimizations with specialist agents
3. Benchmark with `test-coverage-guardian`
4. Update progress with `planning-task-coordinator`

#### For Refactoring
1. Plan with `planning-task-coordinator`
2. Maintain patterns with `markdown-lab-architect`
3. Optimize during refactoring with specialists
4. Ensure coverage with `test-coverage-guardian`

## Usage Examples

### Example 1: Optimizing Batch URL Processing
```
User: "The batch URL processing is too slow"
Action: http-cache-network-specialist analyzes and optimizes
       → Implements connection pooling
       → Adds parallel processing
       → Optimizes cache strategy
```

### Example 2: Adding New Output Format
```
User: "Add CSV output format"
Action: markdown-lab-architect designs integration
       → Determines Rust vs Python placement
       → Ensures pattern consistency
       → Maintains architectural boundaries
```

### Example 3: Performance Regression
```
User: "HTML parsing got slower after recent changes"
Action: rust-python-optimizer investigates
       → Profiles FFI boundaries
       → Identifies bottlenecks
       → Suggests optimizations
```

## Best Practices

1. **Let agents work proactively** - They'll auto-invoke based on context
2. **Use multiple agents concurrently** - They complement each other
3. **Trust agent expertise** - They have deep project knowledge
4. **Follow agent guidance** - They enforce established patterns
5. **Update agents as needed** - They evolve with the project

## Maintenance

These agents are project-specific and should be:
- Updated when architecture changes significantly
- Enhanced when new patterns are established
- Reviewed when performance targets change
- Versioned with the project repository

## Getting Started

Simply continue working on markdown_lab - the agents will automatically activate when their expertise is needed. They understand your PLANNING.md/TASKS.md workflow and will help maintain the high standards established in your CLAUDE.md conventions.