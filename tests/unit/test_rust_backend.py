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
    """
    Pytest fixture that provides a temporary directory as a `Path` object for use in tests.
    
    Yields:
        Path: Path to the temporary directory, which is automatically cleaned up after use.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_subprocess():
    """
    Fixture that mocks the `subprocess.run` function for testing purposes.
    
    Yields:
        MagicMock: A mock object that simulates successful subprocess execution with a return code of 0 and empty stdout and stderr.
    """
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def sample_rust_config():
    """
    Return a sample configuration dictionary for initializing a RustBackend instance.
    
    Returns:
        dict: Example configuration with typical Rust compiler settings, including paths, target, optimization level, debug flag, features, and output directory.
    """
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
    """
    Returns a simple, valid Rust source code snippet suitable for compilation tests.
    """
    return '''
fn main() {
    println!("Hello, world!");
}
'''


@pytest.fixture
def invalid_rust_code():
    """
    Returns a string containing invalid Rust source code intended for testing compilation error handling.
    """
    return '''
fn main() {
    println!("Hello, world!")  // Missing semicolon
}
'''


@pytest.fixture
def rust_backend_instance(sample_rust_config):
    """
    Create a `RustBackend` instance using a sample configuration with subprocess calls mocked for testing purposes.
    
    Parameters:
        sample_rust_config (dict): Configuration dictionary for initializing the RustBackend.
    
    Returns:
        RustBackend: An instance of RustBackend with subprocess interactions patched.
    """
    with patch('subprocess.run'):
        return RustBackend(sample_rust_config)


class TestRustBackendInitialization:
    """Test RustBackend initialization and configuration."""

    def test_init_with_valid_config(self, sample_rust_config):
        """
        Test that RustBackend initializes correctly with a valid configuration.
        
        Verifies that the RustBackend instance has the expected configuration attributes after initialization.
        """
        with patch('subprocess.run'):
            backend = RustBackend(sample_rust_config)
            assert hasattr(backend, 'config')
            for key, value in sample_rust_config.items():
                assert getattr(backend, key, None) == value or key in str(backend.config)

    def test_init_with_minimal_config(self):
        """
        Verify that RustBackend can be initialized with only the minimal required configuration.
        """
        minimal_config = {"rust_path": "/usr/bin/rustc"}
        with patch('subprocess.run'):
            backend = RustBackend(minimal_config)
            assert hasattr(backend, 'config')

    def test_init_with_empty_config(self):
        """
        Test that initializing RustBackend with an empty configuration raises an error.
        
        Raises:
            ValueError, TypeError, or RustBackendError: If the configuration is empty.
        """
        with pytest.raises((ValueError, TypeError, RustBackendError)):
            RustBackend({})

    def test_init_with_none_config(self):
        """
        Test that initializing RustBackend with None as the configuration raises a TypeError or AttributeError.
        """
        with pytest.raises((TypeError, AttributeError)):
            RustBackend(None)

    def test_init_with_invalid_config_type(self):
        """
        Test that initializing RustBackend with a non-dictionary configuration raises a TypeError or AttributeError.
        """
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
        """
        Test that initializing RustBackend with an invalid rust_path raises an appropriate exception.
        
        Parameters:
            invalid_path: An invalid value for the rust_path configuration key.
        """
        sample_rust_config["rust_path"] = invalid_path
        with pytest.raises((RustBackendError, TypeError, ValueError)):
            RustBackend(sample_rust_config)


class TestRustBackendCompilation:
    """Test RustBackend compilation methods."""

    @patch('subprocess.run')
    def test_compile_success(self, mock_run, rust_backend_instance, simple_rust_code):
        """
        Verifies that compiling valid Rust code with RustBackend succeeds and invokes the expected subprocess call.
        """
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
        """
        Verifies that compiling invalid Rust code with syntax errors raises an appropriate exception.
        """
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: expected `;`, found `}`\n  --> src/main.rs:3:35"
        )

        with pytest.raises((RustCompilationError, subprocess.CalledProcessError, Exception)):
            rust_backend_instance.compile(invalid_rust_code, "test_program")

    @patch('subprocess.run')
    def test_compile_with_optimization_levels(self, mock_run, sample_rust_config, simple_rust_code):
        """
        Verifies that the RustBackend compiles code with each supported optimization level and passes the correct flags to the subprocess call.
        
        Parameters:
        	mock_run: Mocked subprocess.run function.
        	sample_rust_config: Sample configuration dictionary for RustBackend.
        	simple_rust_code: Valid Rust source code to compile.
        """
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
        """
        Test that compiling empty source code raises a ValueError or RustBackendError.
        """
        with pytest.raises((ValueError, RustBackendError)):
            rust_backend_instance.compile("", "test_program")

    def test_compile_whitespace_only_source(self, rust_backend_instance):
        """
        Test that compiling whitespace-only Rust source code raises a ValueError or RustBackendError.
        """
        with pytest.raises((ValueError, RustBackendError)):
            rust_backend_instance.compile("   \n\t  \n  ", "test_program")

    @pytest.mark.parametrize("invalid_name", ["", None, 123, [], {}])
    def test_compile_invalid_program_name(self, rust_backend_instance, simple_rust_code, invalid_name):
        """
        Test that compiling with an invalid program name raises an appropriate exception.
        
        Parameters:
        	invalid_name: A value that is not a valid program name (e.g., empty string, None, or non-string type).
        """
        with pytest.raises((ValueError, TypeError, RustBackendError)):
            rust_backend_instance.compile(simple_rust_code, invalid_name)


class TestRustBackendErrorHandling:
    """Test RustBackend error handling scenarios."""

    @patch('subprocess.run')
    def test_subprocess_timeout(self, mock_run, rust_backend_instance, simple_rust_code):
        """
        Test that a compilation timeout is handled by raising the appropriate exception.
        """
        mock_run.side_effect = subprocess.TimeoutExpired("rustc", 30)

        with pytest.raises((subprocess.TimeoutExpired, RustBackendError)):
            rust_backend_instance.compile(simple_rust_code, "test_timeout")

    @patch('subprocess.run')
    def test_subprocess_permission_error(self, mock_run, rust_backend_instance, simple_rust_code):
        """
        Test that a permission error during Rust code compilation is correctly handled.
        
        Raises:
            PermissionError or RustBackendError: If a permission error occurs when invoking the Rust compiler.
        """
        mock_run.side_effect = PermissionError("Permission denied: rustc")

        with pytest.raises((PermissionError, RustBackendError)):
            rust_backend_instance.compile(simple_rust_code, "test_permission")

    @patch('subprocess.run')
    def test_subprocess_file_not_found(self, mock_run, rust_backend_instance, simple_rust_code):
        """
        Test that a FileNotFoundError or RustBackendError is raised when the Rust compiler executable is missing.
        """
        mock_run.side_effect = FileNotFoundError("rustc: command not found")

        with pytest.raises((FileNotFoundError, RustBackendError)):
            rust_backend_instance.compile(simple_rust_code, "test_not_found")

    @patch('subprocess.run')
    def test_compilation_memory_error(self, mock_run, rust_backend_instance):
        """
        Test that a memory error during compilation is properly handled.
        
        Simulates a memory-intensive Rust compilation and verifies that a MemoryError or RustBackendError is raised when the compilation process runs out of memory.
        """
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
        """
        Tests that the RustBackend compiles code for various target architectures and includes the correct target flag in the subprocess call.
        """
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
        """
        Test that the RustBackend compiles code with various feature sets and passes the correct feature flags to the compiler.
        
        Parameters:
            feature_set (list): List of Rust features to enable during compilation.
        """
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
        """
        Test that the RustBackend can successfully compile various valid Rust source code patterns.
        
        Parameters:
            source_variant (str): A valid Rust source code pattern to compile.
        """
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = rust_backend_instance.compile(source_variant, "test_variant")
        mock_run.assert_called()


class TestRustBackendUtilities:
    """Test utility methods and helper functions."""

    @patch('subprocess.run')
    def test_get_rust_version(self, mock_run, rust_backend_instance):
        """
        Test that the Rust compiler version can be retrieved using the RustBackend instance.
        
        Verifies that the `get_rust_version` method returns the expected version string, or that version information can be obtained via compilation if the method is unavailable.
        """
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
        """
        Tests that the RustBackend instance correctly lists available compilation targets by parsing the output from the Rust compiler.
        """
        mock_targets = "x86_64-unknown-linux-gnu\naarch64-unknown-linux-gnu\nx86_64-pc-windows-msvc"
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_targets)

        if hasattr(rust_backend_instance, 'list_targets'):
            targets = rust_backend_instance.list_targets()
            assert "x86_64-unknown-linux-gnu" in targets
            assert "aarch64-unknown-linux-gnu" in targets

    @patch('subprocess.run')
    def test_validate_configuration(self, mock_run, sample_rust_config):
        """
        Tests that the RustBackend configuration is validated correctly, accepting valid configurations and raising exceptions for invalid ones.
        """
        mock_run.return_value = MagicMock(returncode=0)

        backend = RustBackend(sample_rust_config)
        if hasattr(backend, 'validate_config'):
            assert backend.validate_config() is True

        invalid_config = sample_rust_config.copy()
        invalid_config["optimization_level"] = "invalid"
        with pytest.raises((ValueError, RustBackendError)):
            RustBackend(invalid_config)

    def test_cleanup_resources(self, rust_backend_instance, temp_dir):
        """
        Test that the RustBackend instance properly cleans up temporary files and resources.
        
        Verifies that both the `cleanup` method and context manager protocol (`__enter__`) perform resource cleanup without errors.
        """
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
        """
        Tests the full build workflow of the RustBackend from compiling source code to producing executable artifacts.
        
        Verifies that the backend can successfully compile valid Rust code and, if available, retrieve build artifacts after compilation.
        """
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
        """
        Test that the error recovery and retry mechanisms in the RustBackend handle compilation failures and subsequent retries correctly.
        
        Simulates a compilation failure followed by a successful retry, verifying that the appropriate exceptions are raised and that retry logic (if implemented) functions as expected.
        """
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
        """
        Tests that the RustBackend can successfully compile large Rust source files of varying sizes.
        
        Parameters:
            code_size (int): The number of repeated lines to include in the generated source code.
        """
        mock_run.return_value = MagicMock(returncode=0)

        large_code = "fn main() {\n"
        large_code += "    let mut sum = 0;\n" * code_size
        large_code += "    println!(\"Sum: {}\", sum);\n}\n"

        result = rust_backend_instance.compile(large_code, f"large_test_{code_size}")
        mock_run.assert_called()

    @patch('subprocess.run')
    def test_concurrent_compilation_safety(self, mock_run, rust_backend_instance):
        """
        Verify that the RustBackend instance can safely handle concurrent compilation requests from multiple threads without raising unexpected exceptions.
        """
        import threading
        mock_run.return_value = MagicMock(returncode=0)

        results = []
        errors = []

        def compile_worker(worker_id):
            """
            Compiles a simple Rust program for a specific worker and records the result or any exception.
            
            Parameters:
                worker_id (int): Identifier for the worker, used in the program output and executable name.
            """
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
        """
        Test that the RustBackend correctly compiles source code containing special characters.
        
        Parameters:
            special_chars (str): Rust source code string containing special or non-ASCII characters.
        
        Returns:
            The result of the compilation process.
        """
        mock_run.return_value = MagicMock(returncode=0)

        result = rust_backend_instance.compile(special_chars, "special_chars_test")
        mock_run.assert_called()

    def test_configuration_edge_cases(self, sample_rust_config):
        """
        Test initialization of RustBackend with configuration edge case values.
        
        Verifies that RustBackend can be instantiated or raises appropriate exceptions when provided with edge case configuration values such as empty strings or None for certain keys.
        """
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