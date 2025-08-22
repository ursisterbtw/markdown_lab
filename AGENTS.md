# Repository Guidelines

## Project Structure & Modules
- `markdown_lab/`: Python package (CLI, TUI, core, utils). Key entry points: `__main__.py`, `cli.py`, `tui.py`.
- `src/`: Rust crate exposing Python bindings via PyO3 (`lib.rs`, converters, chunking, parsers).
- `tests/`: `unit/`, `integration/`, and `rust/` (binding + Rust tests).
- `benches/`: Criterion benchmarks. `examples/` and `docs/` contain demos and assets.

## Build, Test, and Dev Commands
- Setup: `just setup` (creates venv, installs deps, builds Rust via maturin).
- Build: `just build-dev` (debug), `just build-release` (optimized), `just build-js` (enable `real_rendering`).
- Test: `just test` (all), `just test-python`, `just test-rust`, `just test-integration`, `just test-coverage` (>=80%).
- Lint/Type: `just lint` (ruff+black+isort+clippy+fmt), `just typecheck` (mypy).
- Bench: `just bench`, `just bench-html`, `just bench-chunk`.
- Raw equivalents: `uv sync && source .venv/bin/activate && maturin develop`, `pytest`, `cargo test`.

## Coding Style & Naming
- Indentation: 4 spaces (`.editorconfig`), UTF-8, final newline.
- Python: Python 3.12, `black` (88 cols), `isort` (profile=black), `ruff` (E,F,I,N,W,B,…), `mypy` strict; PEP8 names (modules/files `snake_case.py`; classes `CamelCase`; funcs/vars `snake_case`).
- Rust: `cargo fmt` and `clippy -D warnings`; types `CamelCase`, funcs/vars/modules `snake_case`, constants `SCREAMING_SNAKE_CASE`.
- Keep public APIs typed and documented; prefer small modules and cohesive functions.

## Testing Guidelines
- Python: `pytest` with markers: `unit`, `integration`, `slow`, `benchmark`. Place tests under `tests/unit/` and `tests/integration/`; name files `test_*.py`.
- Rust: `cargo test`; unit tests co-located with modules or in `tests/` if added.
- Coverage: run `just test-coverage`; keep threshold ≥ 80%. Add focused tests for new logic and bug regressions.

## Commit & Pull Request Guidelines
- Commits: follow Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, optional scopes (e.g., `feat(cli): ...`). Use imperative, concise subjects.
- PRs: include summary, rationale, linked issues (`Fixes #123`), test coverage notes, and relevant screenshots/CLI output for UX changes (CLI/TUI). Keep PRs small and focused.

## Security & Configuration Tips
- Use `uv sync` and `.venv` from repo root; Python ≥ 3.12 required.
- For JS rendering, build with `--features real_rendering` and ensure headless Chrome availability.
- Never commit secrets; config/state belongs outside VCS. Run `just security-audit` before release work.
