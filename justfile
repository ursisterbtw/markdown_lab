# Justfile for Markdown Lab

# Default recipe - show available commands
default:
    @just --list

# === SETUP ===

# Install dependencies and set up development environment
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🚀 Setting up development environment..."
    
    # Install UV if not present
    if ! command -v uv &> /dev/null; then
        echo "📦 Installing UV package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    
    uv sync
    source .venv/bin/activate && maturin develop
    echo "✅ Setup complete! Run 'just test' to verify."

# Clean all build artifacts
clean:
    #!/usr/bin/env bash
    cargo clean 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.py[co]" -delete 2>/dev/null || true
    rm -rf target build dist .pytest_cache .coverage .request_cache *.egg-info 2>/dev/null || true

# === DEVELOPMENT ===

# Build Rust components for development
build:
    source .venv/bin/activate && maturin develop

# Build with optimizations
build-release:
    source .venv/bin/activate && maturin develop --release

# === TESTING ===

# Run all tests
test:
    cargo test --color=always
    source .venv/bin/activate && python -m pytest tests/ -v --color=yes

# Run Python tests only
test-python:
    source .venv/bin/activate && python -m pytest tests/ -v --color=yes

# Run Rust tests only
test-rust:
    cargo test --color=always

# Run tests with coverage
test-coverage:
    source .venv/bin/activate && python -m pytest --cov=markdown_lab --cov-report=html --cov-report=term --color=yes

# === CODE QUALITY ===

# Run all linting and formatting
lint:
    source .venv/bin/activate && ruff check . --fix
    source .venv/bin/activate && black .
    source .venv/bin/activate && isort .
    cargo fmt
    cargo clippy -- -D warnings

# Type checking
typecheck:
    source .venv/bin/activate && mypy markdown_lab/

# === BENCHMARKS ===

# Run benchmarks
bench:
    cargo bench

# === UTILITIES ===

# Show project status
status:
    #!/usr/bin/env bash
    echo "📊 Markdown Lab Status"
    echo "====================="
    git status --short
    echo ""
    if [ -d ".venv" ] && source .venv/bin/activate && python -c "import markdown_lab.markdown_lab_rs" 2>/dev/null; then
        echo "✅ Environment ready"
    else
        echo "❌ Run 'just setup' first"
    fi

# Update dependencies
update:
    uv sync --upgrade
    cargo update

# Run format conversion demo
demo:
    source .venv/bin/activate && python examples/demo_formats.py

# Fix common issues
fix:
    #!/usr/bin/env bash
    echo "🔧 Fixing common issues..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    cargo clean 2>/dev/null || true
    rm -rf .pytest_cache .mypy_cache .request_cache 2>/dev/null || true
    if [ -d ".venv" ]; then
        source .venv/bin/activate && maturin develop
    fi