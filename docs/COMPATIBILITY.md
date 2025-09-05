Compatibility Matrix

Overview
- This project uses a Rust backend (PyO3) packaged as a Python extension. Compatibility depends on Python version, OS toolchain, and Rust toolchain.

Supported (CI)
- Python: 3.12, 3.13
- OS: Ubuntu latest, macOS latest, Windows latest
- Rust: stable (clippy + rustfmt)

Notes
- Wheels are not currently built in CI; development uses `maturin develop` to build an in-place extension. If distribution is intended, add `maturin build --release` across platforms and upload artifacts.
- JS rendering requires headless Chromium availability and the `real_rendering` feature.

Local Setup
- Ensure Python ≥ 3.12 and Rust toolchain installed.
- Use `just setup` or `uv sync && maturin develop` to build the extension.

Future Work
- Add wheel builds (manylinux, macOS universal2, Windows) in CI for releases.
