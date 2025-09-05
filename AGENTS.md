# Repository Guidelines

## Project Structure & Module Organization
- `markdown_lab/`: Python package (CLI, TUI, core, utils). Entry points: `__main__.py`, `cli.py`, `tui.py`.
- `src/`: Rust crate exposing Python bindings with PyO3 (`lib.rs`, converters, chunking, parsers).
- `tests/`: Python `unit/`, `integration/`, and `rust/` (bindings + Rust tests).
- `benches/`: Criterion benchmarks. `examples/` and `docs/` contain demos and assets.
- Keep modules small, cohesive, and public APIs typed and documented.

## Build, Test, and Development Commands
- Setup: `just setup` — create `.venv`, install deps, build Rust via maturin.
- Build: `just build-dev` (debug), `just build-release` (optimized), `just build-js` (enable `real_rendering`).
- Tests: `just test` (all), `just test-python`, `just test-rust`, `just test-integration`, `just test-coverage` (≥80%).
- Lint/Type: `just lint` (ruff, black, isort, clippy, fmt), `just typecheck` (mypy).
- Bench: `just bench`, `just bench-html`, `just bench-chunk`.
- Raw dev equivalents: `uv sync && source .venv/bin/activate && maturin develop`, `pytest`, `cargo test`.

## Coding Style & Naming Conventions
- Indentation: 4 spaces; UTF‑8; final newline. Python 3.12 required.
- Python: `black` (88 cols), `isort` (profile=black), `ruff` (E,F,I,N,W,B,…), `mypy --strict`.
- Rust: `cargo fmt` and `clippy -D warnings`.
- Naming: modules/files `snake_case.py`; classes `CamelCase`; funcs/vars `snake_case`; consts `SCREAMING_SNAKE_CASE`.

## Testing Guidelines
- Python: `pytest` with markers `unit`, `integration`, `slow`, `benchmark`.
- Layout: `tests/unit/test_*.py`, `tests/integration/test_*.py`. Prefer focused tests.
- Run subsets, e.g., `pytest -m unit` or `pytest -k name`.
- Rust: `cargo test` for crate and binding tests under `tests/`.
- Coverage: enforce ≥80% via `just test-coverage` for PRs.

## Commit & Pull Request Guidelines
- Commits: Conventional Commits, e.g., `feat(cli): add render flag`, `fix(rust): guard null ptr`.
- PRs: clear summary, rationale, and linked issues (e.g., `Fixes #123`).
- Include test notes, coverage impact, and screenshots/CLI output for UX changes (CLI/TUI).
- Keep PRs small and focused; update docs when behavior changes.

## Security & Configuration Tips
- Use `uv sync` from repo root and the local `.venv`.
- For JS rendering, build with `--features real_rendering` and ensure headless Chrome.
- Never commit secrets; keep config/state out of VCS. Run `just security-audit` before releases.

