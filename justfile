# Markdown Lab Justfile

# Variables
set shell := ["bash", "-c"]

# Default: show available commands
default:
    @just --list

# === SETUP ===

# Install everything and build
setup:
    #!/usr/bin/env bash
    echo "🚀 Setting up environment..."
    command -v uv &>/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
    uv sync
    source .venv/bin/activate && python -m maturin develop

# Clean all artifacts
clean:
    @echo "🧹 Cleaning..."
    @cargo clean 2>/dev/null || true
    @find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    @rm -rf target build dist .pytest_cache .coverage htmlcov .request_cache *.egg-info 2>/dev/null || true

# === BUILD ===

# Build Rust (dev/release/js)
build mode="dev":
    @echo "🔨 Building {{mode}}..."
    @if [ "{{mode}}" = "js" ]; then \
        cargo build --release --features real_rendering && source .venv/bin/activate && python -m maturin develop --release --features real_rendering; \
    elif [ "{{mode}}" = "release" ]; then \
        source .venv/bin/activate && python -m maturin develop --release; \
    else \
        source .venv/bin/activate && python -m maturin develop; \
    fi

# === TEST ===

# Run all tests
test: 
    @cargo test
    @source .venv/bin/activate && python -m pytest

# Test specific suite (rust/python/bindings/integration/coverage)
test-only suite="python" *args="":
    @if [ "{{suite}}" = "rust" ]; then cargo test {{args}}; \
    elif [ "{{suite}}" = "python" ]; then source .venv/bin/activate && python -m pytest tests/ {{args}}; \
    elif [ "{{suite}}" = "bindings" ]; then source .venv/bin/activate && python -m pytest tests/rust/test_python_bindings.py {{args}}; \
    elif [ "{{suite}}" = "integration" ]; then source .venv/bin/activate && python -m pytest tests/integration/ {{args}}; \
    elif [ "{{suite}}" = "coverage" ]; then source .venv/bin/activate && python -m pytest --cov=markdown_lab --cov-report=html {{args}}; \
    else echo "❌ Unknown suite: {{suite}}"; fi

# === QUALITY ===

# Lint and format
lint:
    @source .venv/bin/activate && python -m ruff check . --fix
    @source .venv/bin/activate && python -m black .
    @cargo fmt
    @cargo clippy

# Type check
types:
    @source .venv/bin/activate && python -m mypy markdown_lab/

# === BENCH ===

# Run benchmarks
bench target="":
    @if [ -z "{{target}}" ]; then cargo bench; else cargo bench {{target}}; fi

# === DEMO ===

# Run demo
demo url="https://httpbin.org/html":
    @source .venv/bin/activate && python -m markdown_lab "{{url}}" -o demo_output.md
    @source .venv/bin/activate && python -m markdown_lab "{{url}}" -o demo_output.json -f json
    @source .venv/bin/activate && python -m markdown_lab "{{url}}" -o demo_output.xml -f xml

# === UTILS ===

# Quick dev cycle
dev: build
    @just test-only bindings

# Full check
check: lint types test

# Build release wheel
wheel:
    @source .venv/bin/activate && python -m maturin build --release

# Fix common issues
fix:
    @find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    @cargo clean && source .venv/bin/activate && python -m maturin develop

# Show status
status:
    @echo "📊 Status:"
    @git status --short
    @source .venv/bin/activate && python -c "import markdown_lab.markdown_lab_rs; print('✅ Bindings OK')" 2>/dev/null || echo "❌ Bindings failed"

# Help
help:
    @source .venv/bin/activate && python -m markdown_lab --help