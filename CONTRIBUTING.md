# Contributing to Markdown Lab

Thank you for your interest in contributing! This project blends Python (CLI/TUI, orchestration) with Rust (HTML parsing and conversion) via PyO3 bindings.

## Architecture Overview
- Python entrypoints: `markdown_lab/__main__.py` routes to the modern CLI (`markdown_lab/cli.py`) and TUI (`markdown_lab/tui.py`).
- Core services: HTTP client, caching, throttling, sitemap parsing, and chunking live under `markdown_lab/core/*` and `markdown_lab/utils/*`.
- Rust engine: The PyO3 module `markdown_lab_rs` (from `src/lib.rs`) exposes conversion (`convert_html_to_format`, `convert_html_to_markdown`), chunking, simple HTML utilities, and optional JS rendering.
- Bridge layer: `markdown_lab/core/rust_backend.py` wraps the Rust module and centralizes error handling and fallbacks.

## CLI/TUI and Legacy Fallbacks
- Modern CLI: `mlab` with rich output and subcommands (`convert`, `sitemap`, `batch`, `status`, `config`).
- TUI: `mlab-tui` provides an interactive interface using Textual.
- Legacy: Set `MARKDOWN_LAB_LEGACY=1` or use `mlab-legacy` to invoke the older scraper-based interface when needed.

## Development
1. `just setup` (requires Python 3.12+, Rust, and uv). This creates `.venv`, installs deps, and builds the Rust extension via `maturin`.
2. Run linting and typing with `just lint` and `just typecheck`.
3. Run tests with `just test` or `just test-coverage`.

## Testing Guidelines
- Unit tests must be hermetic (no network). Use mocks in Python and avoid external HTTP in Rust tests.
- Network or environment-dependent tests must be marked `@pytest.mark.integration` (Python) or `#[ignore]`/feature-gated (Rust).
- A feature `offline_tests` enables an offline path for `render_js_page` by allowing inline HTML via `inline://` URLs in tests.

## Code Style
- Python: black (88), ruff, isort profile=black, mypy strict on public APIs.
- Rust: `cargo fmt` and `clippy -D warnings`.

## Security & Dependencies
- CI runs `safety` for Python and `cargo audit` for Rust. High/critical issues fail the build.
- Dependabot tracks both `pip` and `cargo` ecosystems.

## Commit Messages
- Follow Conventional Commits (e.g., `feat(cli): ...`, `fix(core): ...`). Keep subjects imperative and concise.

