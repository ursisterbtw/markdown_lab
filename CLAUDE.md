# Commands & Guidelines for markdown_lab

## Build & Test Commands
- `cargo build` - Build Rust components
- `cargo build --release --features real_rendering` - Build with JS rendering support
- `pip install -r requirements.txt` - Install Python dependencies
- `pytest` - Run all Python tests
- `pytest tests/test_python_bindings.py -v` - Run Python binding tests
- `pytest test_main.py::test_convert_to_markdown -v` - Run specific Python test
- `cargo test` - Run Rust tests
- `RUST_LOG=debug cargo test -- --nocapture` - Run Rust tests with logging
- `cargo bench` - Run all benchmarks
- `cargo bench html_to_markdown` - Run specific benchmark
- `mypy *.py` - Type checking

## Code Style Guidelines
- **Python**: Python 3.12+ with type annotations
- **Imports**: Group imports (stdlib, third-party, local)
- **Formatting**: Follow PEP 8 guidelines
- **Error handling**: Use exception handling with specific exceptions
- **Naming**: snake_case for Python, snake_case for Rust
- **Testing**: Use pytest fixtures and mocks
- **Documentation**: Docstrings for public functions and classes
- **Rust**: Follow Rust 2024 edition idioms and use thiserror for errors
- **Type annotations**: Required for all new code

## Repository Structure
- **src/**: Rust code with PyO3 bindings
- **Python modules**: Main functionality (main.py, chunk_utils.py, etc.)
- **tests/**: Test files for both Python and Rust components
- **benches/**: Performance benchmarks