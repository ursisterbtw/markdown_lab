# Makefile for Markdown Lab
# Alternative task runner (backup for justfile)

.PHONY: help setup clean build-dev build-release test test-rust test-python lint demo

# Default target
help:
	@echo "Markdown Lab - Available Commands:"
	@echo "=================================="
	@echo "  setup        - Install dependencies and set up development environment"
	@echo "  clean        - Clean all build artifacts"
	@echo "  build-dev    - Build Rust components for development"
	@echo "  build-release - Build Rust components with optimizations"
	@echo "  test         - Run all tests"
	@echo "  test-rust    - Run Rust tests only"
	@echo "  test-python  - Run Python tests only"
	@echo "  lint         - Run linting and formatting"
	@echo "  demo         - Run format conversion demo"
	@echo "  status       - Show project status"
	@echo "  e2e          - Run end-to-end test"

# Setup development environment
setup:
	@echo "🚀 Setting up Markdown Lab development environment..."
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "Installing UV package manager..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	@echo "📦 Installing Python dependencies..."
	uv sync
	@echo "🦀 Building Rust components..."
	bash -c "source .venv/bin/activate && maturin develop"
	@echo "✅ Setup complete! Run 'make test' to verify installation."

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	cargo clean
	rm -rf target/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf *.egg-info/ build/ dist/ .coverage htmlcov/ .request_cache/
	rm -rf examples/demo_output/
	@echo "✅ Clean complete!"

# Build for development
build-dev:
	@echo "🔨 Building Rust components for development..."
	bash -c "source .venv/bin/activate && maturin develop"

# Build for release
build-release:
	@echo "🚀 Building Rust components with optimizations..."
	bash -c "source .venv/bin/activate && maturin develop --release"

# Run all tests
test: test-rust test-python

# Run Rust tests
test-rust:
	@echo "🦀 Running Rust tests..."
	cargo test

# Run Python tests
test-python:
	@echo "🐍 Running Python tests..."
	bash -c "source .venv/bin/activate && pytest tests/ -v"

# Run Python binding tests specifically
test-bindings:
	@echo "🔗 Running Python binding tests..."
	bash -c "source .venv/bin/activate && pytest tests/rust/test_python_bindings.py -v"

# Linting and formatting
lint:
	@echo "🔍 Linting and formatting code..."
	bash -c "source .venv/bin/activate && ruff check . --fix"
	bash -c "source .venv/bin/activate && black ."
	bash -c "source .venv/bin/activate && isort ."
	cargo fmt
	cargo clippy -- -D warnings

# Run type checking
typecheck:
	@echo "🔍 Running type checks..."
	bash -c "source .venv/bin/activate && mypy markdown_lab/"

# Run format conversion demo
demo:
	@echo "🎭 Running format conversion demo..."
	bash -c "source .venv/bin/activate && python examples/demo_formats.py"

# Test CLI functionality
cli-test:
	@echo "🖥️  Testing CLI with example URL..."
	bash -c "source .venv/bin/activate && python -m markdown_lab https://httpbin.org/html -o test_output.md"

# Test all output formats
test-formats:
	@echo "📄 Testing all output formats..."
	bash -c "source .venv/bin/activate && \
		python -m markdown_lab https://httpbin.org/html -o test_output.md -f markdown && \
		python -m markdown_lab https://httpbin.org/html -o test_output.json -f json && \
		python -m markdown_lab https://httpbin.org/html -o test_output.xml -f xml"
	@echo "✅ All formats tested successfully!"

# Show project status
status:
	@echo "📊 Markdown Lab Project Status"
	@echo "=============================="
	@echo "🔀 Git Status:"
	@git status --short || true
	@echo ""
	@echo "🐍 Python Environment:"
	@bash -c "source .venv/bin/activate && python --version" || echo "Python environment not ready"
	@echo ""
	@echo "🦀 Rust Version:"
	@rustc --version || echo "Rust not available"
	@echo ""
	@echo "🧪 Quick Test:"
	@bash -c "source .venv/bin/activate && python -c 'import markdown_lab.markdown_lab_rs; print(\"✅ Rust bindings working\")'" || echo "❌ Rust bindings not working"

# Run benchmarks
bench:
	@echo "⚡ Running all benchmarks..."
	cargo bench

# Development cycle (build + test)
dev-cycle: build-dev test-bindings

# Full development cycle
full-cycle: build-dev lint test

# End-to-end test
e2e:
	@echo "🌐 Running end-to-end test..."
	bash -c "source .venv/bin/activate && \
		python -m markdown_lab https://httpbin.org/html -o e2e_test.md -f markdown && \
		python -m markdown_lab https://httpbin.org/html -o e2e_test.json -f json && \
		python -m markdown_lab https://httpbin.org/html -o e2e_test.xml -f xml && \
		python -m markdown_lab https://httpbin.org/html -o e2e_test_chunked.md --save-chunks --chunk-dir e2e_chunks"
	@echo "✅ End-to-end test complete!"

# Clean test files
clean-tests:
	@echo "🧹 Cleaning up test files..."
	rm -f test_output.* e2e_test.*
	rm -rf e2e_chunks/

# Show help by default
.DEFAULT_GOAL := help