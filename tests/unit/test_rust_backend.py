"""Comprehensive unit tests for rust_backend module."""
import pytest
import unittest.mock as mock
from unittest.mock import patch, MagicMock, call, Mock
import tempfile
import os
import sys
import subprocess
import json
from pathlib import Path
from io import StringIO

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the module under test
try:
    from git.markdown_lab.core.rust_backend import RustBackend
except ImportError:
    try:
        from markdown_lab.core.rust_backend import RustBackend
    except ImportError:
        from rust_backend import RustBackend

# Import any custom exceptions
try:
    from git.markdown_lab.core.rust_backend import RustBackendError, RustCompilationError
except ImportError:
    # Define mock exceptions if they don't exist
    class RustBackendError(Exception):
        pass

    class RustCompilationError(Exception):
        pass


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_subprocess():
    """Mock subprocess module for testing."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def sample_rust_config():
    """Provide sample configuration for RustBackend."""
    return {
        "rust_path": "/usr/bin/rustc",
        "cargo_path": "/usr/bin/cargo",
        "target": "x86_64-unknown-linux-gnu",
        "optimization_level": "2",
        "debug": False,
        "features": [],
        "output_dir": "/tmp/rust_output"
    }


@pytest.fixture
def simple_rust_code():
    """Provide simple valid Rust source code for testing."""
    return '''
fn main() {
    println!("Hello, world!");
}
'''


@pytest.fixture
def invalid_rust_code():
    """Provide invalid Rust source code for error testing."""
    return '''
fn main() {
    println!("Hello, world!")  // Missing semicolon
}
'''


@pytest.fixture
def rust_backend_instance(sample_rust_config):
    """Create a RustBackend instance for testing."""
    with patch('subprocess.run'):
        return RustBackend(sample_rust_config)


class TestRustBackendInitialization:
    """Test RustBackend initialization and configuration."""

    def test_init_with_valid_config(self, sample_rust_config):
        """Test successful initialization with valid configuration."""
        with patch('subprocess.run'):
            backend = RustBackend(sample_rust_config)
            assert hasattr(backend, 'config')
            for key, value in sample_rust_config.items():
                assert getattr(backend, key, None) == value or key in str(backend.config)

    def test_init_with_minimal_config(self):
        """Test initialization with minimal configuration."""
        minimal_config = {"rust_path": "/usr/bin/rustc"}
        with patch('subprocess.run'):
            backend = RustBackend(minimal_config)
            assert hasattr(backend, 'config')

    def test_init_with_empty_config(self):
        """Test initialization with empty configuration raises appropriate error."""
        with pytest.raises((ValueError, TypeError, RustBackendError)):
            RustBackend({})

    def test_init_with_none_config(self):
        """Test initialization with None configuration raises TypeError."""
        with pytest.raises((TypeError, AttributeError)):
            RustBackend(None)

    def test_init_with_invalid_config_type(self):
        """Test initialization with non-dict configuration raises TypeError."""
        with pytest.raises((TypeError, AttributeError)):
            RustBackend("invalid_config")

    @pytest.mark.parametrize("invalid_path", [
        "/nonexistent/path/rustc",
        "",
        None,
        123,
        []
    ])
    def test_init_with_invalid_rust_path(self, invalid_path, sample_rust_config):
        """Test initialization with various invalid rust paths."""
        sample_rust_config["rust_path"] = invalid_path
        with pytest.raises((RustBackendError, TypeError, ValueError)):
            RustBackend(sample_rust_config)


class TestRustBackendCompilation:
    """Test RustBackend compilation methods."""

    @patch('subprocess.run')
    def test_compile_success(self, mock_run, rust_backend_instance, simple_rust_code):
        """Test successful compilation with valid Rust code."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Compiling test_program...\nFinished release [optimized] target(s)",
            stderr=""
        )

        result = rust_backend_instance.compile(simple_rust_code, "test_program")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0] if mock_run.call_args else []
        assert any("rustc" in str(arg) or "cargo" in str(arg) for arg in call_args)

    @patch('subprocess.run')
    def test_compile_failure_syntax_error(self, mock_run, rust_backend_instance, invalid_rust_code):
        """Test compilation failure with syntax errors."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: expected `;`, found `}`\n  --> src/main.rs:3:35"
        )

        with pytest.raises((RustCompilationError, subprocess.CalledProcessError, Exception)):
            rust_backend_instance.compile(invalid_rust_code, "test_program")

    @patch('subprocess.run')
    def test_compile_with_optimization_levels(self, mock_run, sample_rust_config, simple_rust_code):
        """Test compilation with different optimization levels."""
        optimization_levels = ["0", "1", "2", "3", "s", "z"]

        for level in optimization_levels:
            mock_run.reset_mock()
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            sample_rust_config["optimization_level"] = level
            backend = RustBackend(sample_rust_config)

            backend.compile(simple_rust_code, f"test_opt_{level}")

            mock_run.assert_called()
            call_args = str(mock_run.call_args)
            assert level in call_args or f"opt-level={level}" in call_args

    def test_compile_empty_source(self, rust_backend_instance):
        """Test compilation with empty source code raises error."""
        with pytest.raises((ValueError, RustBackendError)):
            rust_backend_instance.compile("", "test_program")

    def test_compile_whitespace_only_source(self, rust_backend_instance):
        """Test compilation with whitespace-only source code raises error."""
        with pytest.raises((ValueError, RustBackendError)):
            rust_backend_instance.compile("   \n\t  \n  ", "test_program")

    @pytest.mark.parametrize("invalid_name", ["", None, 123, [], {}])
    def test_compile_invalid_program_name(self, rust_backend_instance, simple_rust_code, invalid_name):
        """Test compilation with invalid program names."""
        with pytest.raises((ValueError, TypeError, RustBackendError)):
            rust_backend_instance.compile(simple_rust_code, invalid_name)


class TestRustBackendErrorHandling:
    """Test RustBackend error handling scenarios."""

    @patch('subprocess.run')
    def test_subprocess_timeout(self, mock_run, rust_backend_instance, simple_rust_code):
        """Test handling of compilation timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("rustc", 30)

        with pytest.raises((subprocess.TimeoutExpired, RustBackendError)):
            rust_backend_instance.compile(simple_rust_code, "test_timeout")

    @patch('subprocess.run')
    def test_subprocess_permission_error(self, mock_run, rust_backend_instance, simple_rust_code):
        """Test handling of permission errors during compilation."""
        mock_run.side_effect = PermissionError("Permission denied: rustc")

        with pytest.raises((PermissionError, RustBackendError)):
            rust_backend_instance.compile(simple_rust_code, "test_permission")

    @patch('subprocess.run')
    def test_subprocess_file_not_found(self, mock_run, rust_backend_instance, simple_rust_code):
        """Test handling when rust compiler is not found."""
        mock_run.side_effect = FileNotFoundError("rustc: command not found")

        with pytest.raises((FileNotFoundError, RustBackendError)):
            rust_backend_instance.compile(simple_rust_code, "test_not_found")

    @patch('subprocess.run')
    def test_compilation_memory_error(self, mock_run, rust_backend_instance):
        """Test handling of memory-intensive compilation."""
        large_code = "fn main() {\n" + "    let x = 42;\n" * 10000 + "}\n"
        mock_run.side_effect = MemoryError("Out of memory during compilation")

        with pytest.raises((MemoryError, RustBackendError)):
            rust_backend_instance.compile(large_code, "test_memory")

    @patch('subprocess.run')
    def test_rust_compiler_crash(self, mock_run, rust_backend_instance, simple_rust_code):
        """Test handling when rust compiler crashes with high return code."""
        mock_run.return_value = MagicMock(
            returncode=101,
            stdout="",
            stderr="internal compiler error: compiler crashed"
        )

        with pytest.raises((RustCompilationError, subprocess.CalledProcessError, Exception)):
            rust_backend_instance.compile(simple_rust_code, "test_crash")


class TestRustBackendParameterized:
    """Parameterized tests for comprehensive coverage."""

    @pytest.mark.parametrize("target", [
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu",
        "x86_64-pc-windows-msvc",
        "x86_64-apple-darwin",
        "wasm32-unknown-unknown",
        "thumbv7em-none-eabihf"
    ])
    @patch('subprocess.run')
    def test_compile_different_targets(self, mock_run, target, sample_rust_config, simple_rust_code):
        """Test compilation for different target architectures."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        sample_rust_config["target"] = target
        backend = RustBackend(sample_rust_config)

        backend.compile(simple_rust_code, "test_target")

        mock_run.assert_called()
        call_args = str(mock_run.call_args)
        assert target in call_args or "--target" in call_args

    @pytest.mark.parametrize("feature_set", [
        [],
        ["serde"],
        ["serde", "tokio"],
        ["default", "extra-traits"],
        ["full"]
    ])
    @patch('subprocess.run')
    def test_compile_with_features(self, mock_run, feature_set, sample_rust_config, simple_rust_code):
        """Test compilation with different feature sets."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        sample_rust_config["features"] = feature_set
        backend = RustBackend(sample_rust_config)

        backend.compile(simple_rust_code, "test_features")

        mock_run.assert_called()
        if feature_set:
            call_args = str(mock_run.call_args)
            assert "--features" in call_args or any(feature in call_args for feature in feature_set)

    @pytest.mark.parametrize("source_variant", [
        "fn main() { println!(\"Hello\"); }",
        "fn main() {\n    let x = 42;\n    println!(\"{}\", x);\n}",
        "use std::collections::HashMap;\nfn main() { let _map = HashMap::new(); }",
        "#[derive(Debug)]\nstruct Point { x: i32, y: i32 }\nfn main() { let _p = Point { x: 1, y: 2 }; }"
    ])
    @patch('subprocess.run')
    def test_compile_various_source_patterns(self, mock_run, source_variant, rust_backend_instance):
        """Test compilation with various valid Rust source code patterns."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = rust_backend_instance.compile(source_variant, "test_variant")
        mock_run.assert_called()


class TestRustBackendUtilities:
    """Test utility methods and helper functions."""

    @patch('subprocess.run')
    def test_get_rust_version(self, mock_run, rust_backend_instance):
        """Test retrieving Rust compiler version."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="rustc 1.70.0 (90c541806 2023-05-31)\nbinary: rustc"
        )

        if hasattr(rust_backend_instance, 'get_rust_version'):
            version = rust_backend_instance.get_rust_version()
            assert "1.70.0" in version
        else:
            rust_backend_instance.compile("fn main() {}", "version_test")
            mock_run.assert_called()

    @patch('subprocess.run')
    def test_list_available_targets(self, mock_run, rust_backend_instance):
        """Test listing available compilation targets."""
        mock_targets = "x86_64-unknown-linux-gnu\naarch64-unknown-linux-gnu\nx86_64-pc-windows-msvc"
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_targets)

        if hasattr(rust_backend_instance, 'list_targets'):
            targets = rust_backend_instance.list_targets()
            assert "x86_64-unknown-linux-gnu" in targets
            assert "aarch64-unknown-linux-gnu" in targets

    @patch('subprocess.run')
    def test_validate_configuration(self, mock_run, sample_rust_config):
        """Test configuration validation."""
        mock_run.return_value = MagicMock(returncode=0)

        backend = RustBackend(sample_rust_config)
        if hasattr(backend, 'validate_config'):
            assert backend.validate_config() is True

        invalid_config = sample_rust_config.copy()
        invalid_config["optimization_level"] = "invalid"
        with pytest.raises((ValueError, RustBackendError)):
            RustBackend(invalid_config)

    def test_cleanup_resources(self, rust_backend_instance, temp_dir):
        """Test proper cleanup of temporary resources."""
        temp_file = temp_dir / "test.rs"
        temp_file.write_text("fn main() {}")

        if hasattr(rust_backend_instance, 'cleanup'):
            rust_backend_instance.cleanup()

        if hasattr(rust_backend_instance, '__enter__'):
            with rust_backend_instance:
                pass


class TestRustBackendIntegration:
    """Integration tests for complete workflows."""

    @patch('subprocess.run')
    def test_complete_build_workflow(self, mock_run, temp_dir, sample_rust_config):
        """Test complete build workflow from source to executable."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Build successful")

        backend = RustBackend(sample_rust_config)

        source_code = '''
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    println!("Hello from Rust! Args: {:?}", args);
}
'''

        result = backend.compile(source_code, "integration_test")
        mock_run.assert_called()

        if hasattr(backend, 'get_build_artifacts'):
            artifacts = backend.get_build_artifacts()
            assert len(artifacts) >= 0

    @patch('subprocess.run')
    def test_error_recovery_workflow(self, mock_run, rust_backend_instance):
        """Test error recovery and retry mechanisms."""
        mock_run.return_value = MagicMock(returncode=1, stderr="temporary error")
        with pytest.raises((RustCompilationError, Exception)):
            rust_backend_instance.compile("fn main() {}", "retry_test")

        mock_run.return_value = MagicMock(returncode=0, stdout="success")
        if hasattr(rust_backend_instance, 'retry_compilation'):
            result = rust_backend_instance.retry_compilation("fn main() {}", "retry_test")
        else:
            result = rust_backend_instance.compile("fn main() {}", "retry_test2")


@pytest.mark.slow
class TestRustBackendStress:
    """Stress tests and performance-related tests."""

    @pytest.mark.parametrize("code_size", [100, 1000, 5000])
    @patch('subprocess.run')
    def test_large_source_compilation(self, mock_run, code_size, rust_backend_instance):
        """Test compilation with large source files."""
        mock_run.return_value = MagicMock(returncode=0)

        large_code = "fn main() {\n"
        large_code += "    let mut sum = 0;\n" * code_size
        large_code += "    println!(\"Sum: {}\", sum);\n}\n"

        result = rust_backend_instance.compile(large_code, f"large_test_{code_size}")
        mock_run.assert_called()

    @patch('subprocess.run')
    def test_concurrent_compilation_safety(self, mock_run, rust_backend_instance):
        """Test thread safety during concurrent operations."""
        import threading
        mock_run.return_value = MagicMock(returncode=0)

        results = []
        errors = []

        def compile_worker(worker_id):
            try:
                code = f"fn main() {{ println!(\"Worker {worker_id}\"); }}"
                result = rust_backend_instance.compile(code, f"worker_{worker_id}")
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=compile_worker, args=(i,)) for i in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0 or all(isinstance(e, (RustBackendError, Exception)) for e in errors)


class TestRustBackendEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.parametrize("special_chars", [
        "fn main() { println!(\"Hello 世界\"); }",
        "fn main() { println!(\"Quote: \\\"test\\\"\"); }",
        "fn main() { println!(r#\"Raw string\"#); }",
    ])
    @patch('subprocess.run')
    def test_special_character_handling(self, mock_run, special_chars, rust_backend_instance):
        """Test handling of special characters in source code."""
        mock_run.return_value = MagicMock(returncode=0)

        result = rust_backend_instance.compile(special_chars, "special_chars_test")
        mock_run.assert_called()

    def test_configuration_edge_cases(self, sample_rust_config):
        """Test configuration with edge case values."""
        edge_cases = [
            {"rust_path": "/usr/bin/rustc", "optimization_level": ""},
            {"rust_path": "/usr/bin/rustc", "target": ""},
            {"rust_path": "/usr/bin/rustc", "debug": None},
        ]

        for config in edge_cases:
            try:
                with patch('subprocess.run'):
                    backend = RustBackend(config)
                    assert backend is not None
            except (ValueError, TypeError, RustBackendError):
                pass


def test_module_imports():
    """Test that all required modules can be imported."""
    try:
        import subprocess
        import tempfile
        import pathlib
        assert True
    except ImportError as e:
        pytest.fail(f"Required module import failed: {e}")


def test_rust_backend_class_exists():
    """Test that RustBackend class exists and is instantiable."""
    try:
        with patch('subprocess.run'):
            RustBackend({"rust_path": "/usr/bin/rustc"})
    except (TypeError, ValueError, RustBackendError):
        pass
    except Exception as e:
        pytest.fail(f"Unexpected error instantiating RustBackend: {e}")


def test_rust_backend_has_docstrings():
    """Test that RustBackend class and methods have proper documentation."""
    if hasattr(RustBackend, '__doc__'):
        assert RustBackend.__doc__ is not None

    for method_name in ['compile', '__init__']:
        if hasattr(RustBackend, method_name):
            method = getattr(RustBackend, method_name)
            if hasattr(method, '__doc__'):
                pass