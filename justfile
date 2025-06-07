# Justfile for Markdown Lab
# A comprehensive task runner for development, testing, and deployment

# Default recipe - show available commands
default:
    @just --list

# === SETUP & INSTALLATION ===

# Install all dependencies and set up development environment
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🚀 Setting up Markdown Lab development environment..."
    if ! command -v uv &> /dev/null; then
        echo "Installing UV package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    echo "📦 Installing Python dependencies..."
    uv sync
    echo "🦀 Building Rust components..."
    source .venv/bin/activate && maturin develop
    echo "✅ Setup complete! Run 'just test' to verify installation."

# Clean all build artifacts
clean:
    #!/usr/bin/env bash
    echo "🧹 Cleaning build artifacts..."
    cargo clean
    rm -rf target/
    rm -rf .pytest_cache/
    rm -rf **/__pycache__/
    rm -rf **/*.pyc
    rm -rf *.egg-info/
    rm -rf build/
    rm -rf dist/
    rm -rf .coverage
    rm -rf htmlcov/
    rm -rf .request_cache/
    rm -rf examples/demo_output/
    echo "✅ Clean complete!"

# === DEVELOPMENT ===

# Build Rust components for development
build-dev:
    @echo "🔨 Building Rust components for development..."
    source .venv/bin/activate && maturin develop

# Build Rust components with optimizations
build-release:
    @echo "🚀 Building Rust components with optimizations..."
    source .venv/bin/activate && maturin develop --release

# Build with JavaScript rendering support
build-js:
    @echo "🌐 Building with JavaScript rendering support..."
    cargo build --release --features real_rendering
    source .venv/bin/activate && maturin develop --release --features real_rendering

# Hot reload development mode
dev:
    #!/usr/bin/env bash
    echo "🔄 Starting development mode with hot reload..."
    source .venv/bin/activate
    
    # Build initial version
    maturin develop
    
    echo "Development build complete. Run 'just build-dev' after Rust changes."
    echo "Python changes are automatically picked up."

# === TESTING ===

# Run all tests
test:
    @just test-rust
    @just test-python
    @just test-integration

# Run Rust tests
test-rust:
    @echo "🦀 Running Rust tests..."
    cargo test

# Run Rust tests with output
test-rust-verbose:
    @echo "🦀 Running Rust tests with output..."
    RUST_LOG=debug cargo test -- --nocapture

# Run Python tests
test-python:
    @echo "🐍 Running Python tests..."
    source .venv/bin/activate && pytest tests/ -v

# Run Python binding tests specifically
test-bindings:
    @echo "🔗 Running Python binding tests..."
    source .venv/bin/activate && pytest tests/rust/test_python_bindings.py -v

# Run integration tests
test-integration:
    @echo "🔧 Running integration tests..."
    source .venv/bin/activate && pytest tests/integration/ -v

# Run tests with coverage
test-coverage:
    @echo "📊 Running tests with coverage..."
    source .venv/bin/activate && pytest --cov=markdown_lab --cov-report=html --cov-report=term

# === BENCHMARKING ===

# Run all benchmarks
bench:
    @echo "⚡ Running all benchmarks..."
    cargo bench

# Run specific benchmark
bench-html:
    @echo "📄 Running HTML parsing benchmark..."
    cargo bench html_to_markdown

# Run chunking benchmark
bench-chunk:
    @echo "📝 Running chunking benchmark..."
    cargo bench chunk_markdown

# Visualize benchmark results
bench-viz:
    @echo "📊 Generating benchmark visualization..."
    source .venv/bin/activate && python scripts/visualize_benchmarks.py

# === CODE QUALITY ===

# Run all linting and formatting
lint: lint-python lint-rust

# Lint Python code
lint-python:
    @echo "🔍 Linting Python code..."
    source .venv/bin/activate && ruff check . --fix
    source .venv/bin/activate && black .
    source .venv/bin/activate && isort .

# Lint Python with unsafe fixes
lint-python-unsafe:
    @echo "🔍 Linting Python code with unsafe fixes..."
    source .venv/bin/activate && ruff check . --fix --unsafe-fixes

# Lint Rust code
lint-rust:
    @echo "🦀 Linting Rust code..."
    cargo fmt
    cargo clippy -- -D warnings

# Type checking
typecheck:
    @echo "🔍 Running type checks..."
    source .venv/bin/activate && mypy markdown_lab/

# Full code quality check
quality: lint typecheck test

# === DEMOS & EXAMPLES ===

# Run format conversion demo
demo:
    @echo "🎭 Running format conversion demo..."
    source .venv/bin/activate && python examples/demo_formats.py

# Run simple hello world example
hello:
    @echo "👋 Running hello world example..."
    source .venv/bin/activate && python examples/hello.py

# Test CLI with example URL
cli-test:
    @echo "🖥️  Testing CLI with example URL..."
    source .venv/bin/activate && python -m markdown_lab https://httpbin.org/html -o test_output.md

# Test all output formats
test-formats:
    #!/usr/bin/env bash
    echo "📄 Testing all output formats..."
    source .venv/bin/activate
    
    # Test Markdown output
    python -m markdown_lab https://httpbin.org/html -o test_output.md -f markdown
    
    # Test JSON output
    python -m markdown_lab https://httpbin.org/html -o test_output.json -f json
    
    # Test XML output
    python -m markdown_lab https://httpbin.org/html -o test_output.xml -f xml
    
    echo "✅ All formats tested successfully!"
    echo "Generated files: test_output.md, test_output.json, test_output.xml"

# === DOCUMENTATION ===

# Generate project documentation
docs:
    @echo "📚 Generating project documentation..."
    source .venv/bin/activate && python scripts/generate_flowchart.py

# Show help for CLI
help:
    @echo "❓ Showing CLI help..."
    source .venv/bin/activate && python -m markdown_lab --help

# === PROFILING & DEBUGGING ===

# Profile memory usage
profile-memory:
    @echo "🧠 Profiling memory usage..."
    source .venv/bin/activate && python -m memory_profiler examples/demo_formats.py

# Debug mode build
debug:
    @echo "🐛 Building in debug mode..."
    source .venv/bin/activate && RUST_LOG=debug maturin develop

# === RELEASE & DEPLOYMENT ===

# Prepare for release
release-prep: clean quality bench
    @echo "🎯 Preparing for release..."
    @echo "✅ All checks passed! Ready for release."

# Build wheel for distribution
build-wheel:
    @echo "📦 Building wheel for distribution..."
    source .venv/bin/activate && maturin build --release

# Build wheel with JavaScript support
build-wheel-js:
    @echo "📦 Building wheel with JavaScript support..."
    source .venv/bin/activate && maturin build --release --features real_rendering

# Create release build
release: clean
    #!/usr/bin/env bash
    echo "🚀 Creating release build..."
    
    # Run full test suite
    just test
    
    # Run benchmarks to ensure performance
    just bench
    
    # Build optimized wheel
    just build-wheel
    
    echo "✅ Release build complete!"

# === UTILITIES ===

# Show project status
status:
    #!/usr/bin/env bash
    echo "📊 Markdown Lab Project Status"
    echo "=============================="
    
    # Git status
    echo "🔀 Git Status:"
    git status --short
    echo ""
    
    # Python environment
    echo "🐍 Python Environment:"
    source .venv/bin/activate && python --version
    echo ""
    
    # Rust version
    echo "🦀 Rust Version:"
    rustc --version
    echo ""
    
    # Dependencies
    echo "📦 Key Dependencies:"
    source .venv/bin/activate && pip list | grep -E "(pytest|requests|beautifulsoup4|pyo3)"
    echo ""
    
    # Test status
    echo "🧪 Quick Test:"
    source .venv/bin/activate && python -c "import markdown_lab.markdown_lab_rs; print('✅ Rust bindings working')"

# Update dependencies
update:
    @echo "📦 Updating dependencies..."
    uv sync --upgrade
    cargo update

# Install pre-commit hooks
hooks:
    @echo "🪝 Installing pre-commit hooks..."
    source .venv/bin/activate && pre-commit install

# === DEVELOPMENT SHORTCUTS ===

# Quick development cycle: build + test
dev-cycle: build-dev test-bindings

# Full development cycle: build + lint + test
full-cycle: build-dev lint test

# CI simulation: full pipeline
ci: clean setup quality test bench
    @echo "✅ CI pipeline simulation complete!"

# Performance check: build optimized + benchmark
perf: build-release bench

# === TROUBLESHOOTING ===

# Fix common issues
fix:
    #!/usr/bin/env bash
    echo "🔧 Fixing common issues..."
    
    # Clear Python cache
    find . -type d -name __pycache__ -exec rm -rf {} +
    
    # Rebuild Rust components
    cargo clean
    source .venv/bin/activate && maturin develop
    
    # Clear request cache
    rm -rf .request_cache/
    
    echo "✅ Common issues fixed!"

# Check environment
check-env:
    #!/usr/bin/env bash
    echo "🔍 Checking environment..."
    
    # Check if in virtual environment
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo "✅ Virtual environment active: $VIRTUAL_ENV"
    else
        echo "⚠️  No virtual environment detected"
    fi
    
    # Check UV
    if command -v uv &> /dev/null; then
        echo "✅ UV available: $(uv --version)"
    else
        echo "❌ UV not found"
    fi
    
    # Check Rust
    if command -v rustc &> /dev/null; then
        echo "✅ Rust available: $(rustc --version)"
    else
        echo "❌ Rust not found"
    fi
    
    # Check Python
    if command -v python &> /dev/null; then
        echo "✅ Python available: $(python --version)"
    else
        echo "❌ Python not found"
    fi

# === ADVANCED WORKFLOWS ===

# End-to-end test with real website
e2e url="https://httpbin.org/html":
    #!/usr/bin/env bash
    echo "🌐 Running end-to-end test with {{url}}"
    source .venv/bin/activate
    
    # Test all formats
    python -m markdown_lab "{{url}}" -o e2e_test.md -f markdown
    python -m markdown_lab "{{url}}" -o e2e_test.json -f json
    python -m markdown_lab "{{url}}" -o e2e_test.xml -f xml
    
    # Test with chunking
    python -m markdown_lab "{{url}}" -o e2e_test_chunked.md --save-chunks --chunk-dir e2e_chunks
    
    echo "✅ End-to-end test complete!"
    echo "Generated files: e2e_test.{md,json,xml} and e2e_chunks/"

# Load test with multiple URLs
load-test:
    #!/usr/bin/env bash
    echo "⚡ Running load test..."
    source .venv/bin/activate
    
    # Create test URLs file
    cat > test_urls.txt << EOF
https://httpbin.org/html
https://httpbin.org/json
https://httpbin.org/xml
EOF
    
    # Run parallel processing test
    python -m markdown_lab --links-file test_urls.txt -o load_test_output --parallel --max-workers 3
    
    echo "✅ Load test complete! Check load_test_output/"
    rm test_urls.txt

# === MAINTENANCE ===

# Clean up test files
clean-tests:
    @echo "🧹 Cleaning up test files..."
    rm -f test_output.*
    rm -f e2e_test.*
    rm -rf e2e_chunks/
    rm -rf load_test_output/
    rm -f test_urls.txt

# Archive project (for backup)
archive:
    #!/usr/bin/env bash
    timestamp=$(date +%Y%m%d_%H%M%S)
    echo "📦 Creating project archive: markdown_lab_${timestamp}.tar.gz"
    
    # Create archive excluding common ignored files
    tar -czf "markdown_lab_${timestamp}.tar.gz" \
        --exclude='target' \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='.pytest_cache' \
        --exclude='.request_cache' \
        --exclude='*.pyc' \
        --exclude='.git' \
        .
    
    echo "✅ Archive created: markdown_lab_${timestamp}.tar.gz"