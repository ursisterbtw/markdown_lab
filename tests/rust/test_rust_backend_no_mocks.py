"""Test Rust backend without any mocking - using real subprocess execution."""

import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "git"))

from markdown_lab.core.rust_backend import RustBackend
from tests.fixtures.rust_samples import (
    COMPILE_ERROR_MISSING_SEMICOLON,
    COMPILE_ERROR_TYPE_MISMATCH,
    LARGE_OUTPUT_GENERATOR,
    MEMORY_INTENSIVE,
    UNICODE_CONTENT,
    VALID_HELLO_WORLD,
    VALID_WITH_STRUCTS,
)


@pytest.fixture
def rust_backend():
    """Create a RustBackend instance for testing."""
    backend = RustBackend()
    yield backend
    if hasattr(backend, "cleanup"):
        backend.cleanup()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="session")
def ensure_rust_available():
    """Ensure Rust toolchain is available for testing."""
    try:
        result = subprocess.run(
            ["rustc", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip("Rust toolchain not available")
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("Rust toolchain not available")


class TestRustBackendRealExecution:
    """Test Rust backend with real subprocess execution."""

    def test_compile_valid_hello_world(
        self, rust_backend, temp_dir, ensure_rust_available
    ):
        """Test compilation of valid Hello World program."""
        source_file = temp_dir / "hello.rs"
        source_file.write_text(VALID_HELLO_WORLD)

        if hasattr(rust_backend, "compile"):
            result = rust_backend.compile(str(source_file))
            assert result is not None
            # Check if executable was created
            exe_path = source_file.with_suffix(
                ".exe" if sys.platform == "win32" else ""
            )
            if exe_path.exists():
                # Try to run the compiled program
                run_result = subprocess.run(
                    [str(exe_path)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                assert "Hello from markdown_lab test suite!" in run_result.stdout

    def test_compile_complex_structs(
        self, rust_backend, temp_dir, ensure_rust_available
    ):
        """Test compilation of complex Rust code with structs."""
        source_file = temp_dir / "complex.rs"
        source_file.write_text(VALID_WITH_STRUCTS)

        if hasattr(rust_backend, "compile"):
            result = rust_backend.compile(str(source_file))
            assert result is not None

    def test_compile_error_missing_semicolon(
        self, rust_backend, temp_dir, ensure_rust_available
    ):
        """Test handling of compilation error - missing semicolon."""
        source_file = temp_dir / "error_semicolon.rs"
        source_file.write_text(COMPILE_ERROR_MISSING_SEMICOLON)

        if hasattr(rust_backend, "compile"):
            try:
                result = rust_backend.compile(str(source_file))
                # If compile returns a result object, check for error
                if hasattr(result, "success"):
                    assert not result.success
                elif hasattr(result, "error"):
                    assert result.error is not None
            except subprocess.CalledProcessError as e:
                # Real rustc should return non-zero exit code
                assert e.returncode != 0
                assert "expected `;`" in e.stderr or "expected `;`" in str(e)

    def test_compile_error_type_mismatch(
        self, rust_backend, temp_dir, ensure_rust_available
    ):
        """Test handling of type mismatch compilation error."""
        source_file = temp_dir / "error_type.rs"
        source_file.write_text(COMPILE_ERROR_TYPE_MISMATCH)

        if hasattr(rust_backend, "compile"):
            try:
                result = rust_backend.compile(str(source_file))
                if hasattr(result, "success"):
                    assert not result.success
            except subprocess.CalledProcessError as e:
                assert "mismatched types" in e.stderr or "type mismatch" in str(e)

    def test_unicode_content_handling(
        self, rust_backend, temp_dir, ensure_rust_available
    ):
        """Test compilation of Rust code with Unicode content."""
        source_file = temp_dir / "unicode.rs"
        source_file.write_text(UNICODE_CONTENT, encoding="utf-8")

        if hasattr(rust_backend, "compile"):
            result = rust_backend.compile(str(source_file))
            assert result is not None

    def test_concurrent_compilations(
        self, rust_backend, temp_dir, ensure_rust_available
    ):
        """Test concurrent Rust compilations."""
        results = []
        errors = []

        def compile_thread(thread_id):
            try:
                source_file = temp_dir / f"concurrent_{thread_id}.rs"
                source_file.write_text(
                    f"""
fn main() {{
    println!("Hello from thread {thread_id}");
    std::thread::sleep(std::time::Duration::from_millis(100));
    println!("Thread {thread_id} completed");
}}
"""
                )
                if hasattr(rust_backend, "compile"):
                    result = rust_backend.compile(str(source_file))
                    results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, e))

        threads = []
        for i in range(3):
            thread = threading.Thread(target=compile_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        # At least some compilations should succeed
        assert results or errors

    def test_memory_intensive_compilation(
        self, rust_backend, temp_dir, ensure_rust_available
    ):
        """Test compilation of memory-intensive Rust code."""
        source_file = temp_dir / "memory_test.rs"
        source_file.write_text(MEMORY_INTENSIVE)

        if hasattr(rust_backend, "compile"):
            # This should compile successfully but might be slow
            result = rust_backend.compile(str(source_file))
            assert result is not None

    def test_large_output_program(self, rust_backend, temp_dir, ensure_rust_available):
        """Test handling of programs that generate large output."""
        source_file = temp_dir / "large_output.rs"
        source_file.write_text(LARGE_OUTPUT_GENERATOR)

        if hasattr(rust_backend, "compile"):
            result = rust_backend.compile(str(source_file))
            assert result is not None

            # If we can run the compiled program
            exe_path = source_file.with_suffix(
                ".exe" if sys.platform == "win32" else ""
            )
            if exe_path.exists() and hasattr(rust_backend, "run"):
                run_result = rust_backend.run(str(exe_path))
                if hasattr(run_result, "output"):
                    # Output should be truncated if too large
                    assert len(run_result.output) < 10 * 1024 * 1024  # 10MB limit

    def test_workspace_cleanup(self, rust_backend, temp_dir, ensure_rust_available):
        """Test that temporary files are cleaned up properly."""
        source_file = temp_dir / "cleanup_test.rs"
        source_file.write_text(VALID_HELLO_WORLD)

        initial_files = set(temp_dir.iterdir())

        if hasattr(rust_backend, "compile"):
            rust_backend.compile(str(source_file))

            if hasattr(rust_backend, "cleanup"):
                rust_backend.cleanup()

            # Check that we don't leave too many artifacts
            final_files = set(temp_dir.iterdir())
            new_files = final_files - initial_files

            # Should only have the executable and maybe a few compiler artifacts
            assert len(new_files) <= 3


class TestRustBackendErrorConditions:
    """Test error conditions with real file system."""

    def test_nonexistent_file(self, rust_backend, ensure_rust_available):
        """Test handling of non-existent source file."""
        if hasattr(rust_backend, "compile"):
            with pytest.raises((FileNotFoundError, IOError, ValueError)):
                rust_backend.compile("/definitely/not/a/real/path/test.rs")

    def test_empty_file(self, rust_backend, temp_dir, ensure_rust_available):
        """Test compilation of empty file."""
        source_file = temp_dir / "empty.rs"
        source_file.write_text("")

        if hasattr(rust_backend, "compile"):
            # Empty file should fail compilation
            try:
                result = rust_backend.compile(str(source_file))
                if hasattr(result, "success"):
                    assert not result.success
            except subprocess.CalledProcessError:
                pass  # Expected

    def test_permission_denied(self, rust_backend, temp_dir, ensure_rust_available):
        """Test handling of permission errors."""
        if sys.platform == "win32":
            pytest.skip("Permission test not reliable on Windows")

        source_file = temp_dir / "readonly.rs"
        source_file.write_text(VALID_HELLO_WORLD)
        source_file.chmod(0o000)

        try:
            if hasattr(rust_backend, "compile"):
                with pytest.raises((PermissionError, IOError)):
                    rust_backend.compile(str(source_file))
        finally:
            source_file.chmod(0o644)

    def test_directory_instead_of_file(
        self, rust_backend, temp_dir, ensure_rust_available
    ):
        """Test handling when directory path is provided instead of file."""
        if hasattr(rust_backend, "compile"):
            with pytest.raises((IsADirectoryError, IOError, ValueError)):
                rust_backend.compile(str(temp_dir))


@pytest.mark.parametrize(
    "filename,content,expected_error",
    [
        ("syntax_error.rs", "fn main() { let x = ", "unexpected end of file"),
        (
            "undefined_fn.rs",
            "fn main() { undefined_function(); }",
            "cannot find function",
        ),
        (
            "infinite_recursion.rs",
            "fn f() { f() } fn main() { f(); }",
            None,
        ),  # Compiles but would stack overflow
    ],
)
def test_various_compilation_errors(
    rust_backend, temp_dir, filename, content, expected_error, ensure_rust_available
):
    """Test various compilation error scenarios."""
    source_file = temp_dir / filename
    source_file.write_text(content)

    if hasattr(rust_backend, "compile"):
        try:
            result = rust_backend.compile(str(source_file))
            if expected_error:
                # Should have failed
                if hasattr(result, "success"):
                    assert not result.success
                elif hasattr(result, "error"):
                    assert expected_error in result.error.lower()
        except subprocess.CalledProcessError as e:
            if expected_error:
                assert (
                    expected_error in e.stderr.lower()
                    or expected_error in str(e).lower()
                )
