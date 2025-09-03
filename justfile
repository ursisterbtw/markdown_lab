# Justfile for Markdown Lab

default:
    @just --list

# Setup development environment
setup:
    command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
    uv sync
    uv run maturin develop

# Clean build artifacts
clean:
    cargo clean
    rm -rf target/ build/ dist/ .pytest_cache/ .coverage/ htmlcov/ .request_cache/ __pycache__/ *.egg-info

# Build (use --release for optimized, --features real_rendering for JS)  
build *args:
    uv run maturin develop {{args}}

# Testing
test:
    cargo test
    uv run pytest tests/

test-coverage:
    uv run pytest --cov=markdown_lab --cov-report=html --cov-report=term --cov-fail-under=85

# Benchmarking
bench *args:
    cargo bench {{args}}

# Code quality
lint:
    uv run ruff check . --fix
    uv run ruff format .
    cargo fmt && cargo clippy -- -D warnings

typecheck:
    uv run mypy markdown_lab/

# Examples and demos
demo:
    uv run python examples/demo_formats.py

# Documentation
docs:
    uv run python scripts/generate_flowchart.py

# Release
release:
    #!/usr/bin/env bash
    [ -n "$(git status --porcelain)" ] && { echo "Uncommitted changes"; exit 1; }
    VERSION=$(grep -m 1 '^version =' Cargo.toml | cut -d '"' -f 2)
    just test && just bench
    uv run maturin build --release
    git tag -a "v$VERSION" -m "Release v$VERSION"

# Update dependencies
update:
    uv sync --upgrade && cargo update
