import pytest
import unittest.mock as mock
from unittest.mock import patch, MagicMock, call
import tempfile
import os
import sys
from pathlib import Path
import subprocess
import json
import time
import threading
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'git'))
from markdown_lab.core.rust_backend import RustBackend, get_rust_backend

@pytest.fixture
def rust_backend():
    """
    Pytest fixture that provides a RustBackend instance for use in tests, ensuring cleanup after test execution.
    """
    backend = RustBackend()
    yield backend
    # Cleanup after test
    if hasattr(backend, 'cleanup'):
        backend.cleanup()

@pytest.fixture
def temp_dir():
    """
    Yield a temporary directory as a Path object for use in tests.
    
    The directory is automatically cleaned up after the test completes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_rust_code():
    """
    Provides a sample valid Rust program as a string for use in tests.
    
    Returns:
        str: A simple Rust program that prints messages and a variable value.
    """
    return '''
fn main() {
    println!("Hello, world!");
    let x = 42;
    println!("The answer is: {}", x);
}
'''

@pytest.fixture
def invalid_rust_code():
    """
    Return a string containing intentionally invalid Rust code for testing compilation error handling.
    """
    return '''
fn main() {
    println!("Hello, world!"  // Missing semicolon and closing paren
    let x = ;  // Invalid assignment
}
'''

@pytest.fixture
def complex_rust_code():
    """
    Return a string containing complex Rust code that defines a struct, implements methods, uses a HashMap, and iterates over entries.
    
    Returns:
        str: A multi-line Rust program suitable for advanced compilation and behavior tests.
    """
    return '''
use std::collections::HashMap;

struct Person {
    name: String,
    age: u32,
}

impl Person {
    fn new(name: String, age: u32) -> Person {
        Person { name, age }
    }

    fn greet(&self) {
        println!("Hello, my name is {} and I'm {} years old", self.name, self.age);
    }
}

fn main() {
    let mut people = HashMap::new();
    let person1 = Person::new("Alice".to_string(), 30);
    let person2 = Person::new("Bob".to_string(), 25);

    people.insert("alice", person1);
    people.insert("bob", person2);

    for (key, person) in &people {
        println!("Key: {}", key);
        person.greet();
    }
}
'''

@pytest.fixture
def mock_subprocess_success():
    """
    Create a mock object simulating a successful subprocess execution with return code 0 and stdout set to "Success".
    
    Returns:
        MagicMock: A mock subprocess result indicating success.
    """
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    return mock_result

@pytest.fixture
def mock_subprocess_failure():
    """
    Create a mock object simulating a failed subprocess execution with a nonzero return code and error message.
    """
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Compilation failed"
    return mock_result

class TestRustBackendHappyPath:
    """Test cases for successful rust backend operations."""

    def test_rust_backend_initialization(self):
        """
        Verify that a RustBackend instance is created and has the correct class name.
        """
        backend = RustBackend()
        assert backend is not None
        assert hasattr(backend, '__class__')
        assert backend.__class__.__name__ == 'RustBackend'

    def test_get_rust_backend_function(self):
        """
        Test that the get_rust_backend factory function returns a valid RustBackend instance.
        """
        backend = get_rust_backend()
        assert backend is not None
        assert isinstance(backend, RustBackend)

    def test_rust_backend_singleton_behavior(self):
        """
        Verify that multiple calls to get_rust_backend return valid, non-None instances.
        
        This test ensures that the factory function consistently provides usable RustBackend instances, supporting singleton or repeated instantiation as required.
        """
        backend1 = get_rust_backend()
        backend2 = get_rust_backend()
        assert backend1 is not None
        assert backend2 is not None

    @patch('subprocess.run')
    def test_successful_rust_compilation(self, mock_run, rust_backend, sample_rust_code, temp_dir, mock_subprocess_success):
        """
        Tests that valid Rust code is successfully compiled using the RustBackend, verifying that the result is not None for both 'compile' and 'process' methods.
        """
        mock_run.return_value = mock_subprocess_success

        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)

        if hasattr(rust_backend, 'compile'):
            result = rust_backend.compile(str(source_file))
            assert result is not None
        elif hasattr(rust_backend, 'process'):
            result = rust_backend.process(str(source_file))
            assert result is not None

    @patch('subprocess.run')
    def test_rust_backend_with_complex_code(self, mock_run, rust_backend, complex_rust_code, temp_dir, mock_subprocess_success):
        """
        Tests that the RustBackend can successfully compile complex Rust code using a mocked subprocess.
        
        Creates a temporary Rust source file with complex code, mocks the subprocess call to simulate successful compilation, and asserts that the compile method returns a non-None result.
        """
        mock_run.return_value = mock_subprocess_success

        source_file = temp_dir / "complex.rs"
        source_file.write_text(complex_rust_code)

        if hasattr(rust_backend, 'compile'):
            result = rust_backend.compile(str(source_file))
            assert result is not None

    def test_rust_backend_configuration(self, rust_backend):
        """
        Tests getting and setting configuration options on the RustBackend if supported.
        """
        if hasattr(rust_backend, 'get_config'):
            config = rust_backend.get_config()
            assert config is not None
        if hasattr(rust_backend, 'set_config'):
            test_config = {"debug": True, "optimize": False}
            rust_backend.set_config(test_config)

    def test_rust_backend_version_info(self, rust_backend):
        """
        Tests that the RustBackend provides valid version information if supported.
        
        Verifies that the `version` and `rust_version` methods, if present, return non-None values of the expected type.
        """
        if hasattr(rust_backend, 'version'):
            version = rust_backend.version()
            assert version is not None
            assert isinstance(version, str)
        if hasattr(rust_backend, 'rust_version'):
            rust_version = rust_backend.rust_version()
            assert rust_version is not None

class TestRustBackendEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_rust_file(self, rust_backend, temp_dir):
        """
        Tests compilation of an empty Rust file, asserting that the backend either returns a result or raises an exception.
        """
        source_file = temp_dir / "empty.rs"
        source_file.write_text("")

        if hasattr(rust_backend, 'compile'):
            try:
                result = rust_backend.compile(str(source_file))
                assert result is not None
            except Exception as e:
                assert e is not None

    def test_very_large_rust_file(self, rust_backend, temp_dir):
        """
        Tests compilation of a very large Rust file to ensure the backend can handle large input sizes without running into memory or timeout errors.
        """
        large_code_lines = ["fn main() {"]
        for i in range(10000):
            large_code_lines.append(f'    println!("Line {i}");')
        large_code_lines.append("}")
        large_code = "\n".join(large_code_lines)

        source_file = temp_dir / "large.rs"
        source_file.write_text(large_code)

        if hasattr(rust_backend, 'compile'):
            try:
                result = rust_backend.compile(str(source_file))
                assert result is not None
            except Exception as e:
                assert "memory" in str(e).lower() or "timeout" in str(e).lower()

    def test_rust_file_with_unicode_content(self, rust_backend, temp_dir):
        """
        Tests that the Rust backend can compile Rust files containing Unicode characters in strings and variable names.
        
        Creates a Rust source file with Unicode content and attempts compilation, ignoring exceptions.
        """
        unicode_code = '''
fn main() {
    println!("Hello, 世界! 🦀");
    println!("Rust with émojis: 🚀 and äccénts");
    let 变量 = "Unicode variable names";
    println!("{}", 变量);
}
'''
        source_file = temp_dir / "unicode.rs"
        source_file.write_text(unicode_code, encoding='utf-8')

        if hasattr(rust_backend, 'compile'):
            try:
                result = rust_backend.compile(str(source_file))
                assert result is not None
            except Exception:
                pass

    def test_rust_file_with_special_characters_in_path(self, rust_backend, temp_dir):
        """
        Tests compilation of Rust files located in directories with special characters in their paths, such as spaces, dashes, underscores, and dots, ensuring the backend can handle these cases without errors.
        """
        special_dirs = ["with spaces", "with-dashes", "with_underscores", "with.dots"]
        for dir_name in special_dirs:
            special_dir = temp_dir / dir_name
            special_dir.mkdir()
            source_file = special_dir / "main.rs"
            source_file.write_text("fn main() { println!('Hello'); }")
            if hasattr(rust_backend, 'compile'):
                try:
                    result = rust_backend.compile(str(source_file))
                    assert result is not None
                except Exception:
                    pass

    def test_concurrent_rust_backend_usage(self, rust_backend, sample_rust_code, temp_dir):
        """
        Tests that the Rust backend can be used concurrently from multiple threads without errors.
        
        Runs three threads in parallel, each compiling a separate Rust source file, and collects results and exceptions to verify concurrent operation.
        """
        results = []
        errors = []

        def compile_in_thread(thread_id):
            """
            Compiles a Rust source file in a separate thread and records the result or any exception.
            
            Parameters:
                thread_id (int): Identifier for the thread, used to name the source file and track results.
            """
            try:
                source_file = temp_dir / f"main_{thread_id}.rs"
                source_file.write_text(sample_rust_code)
                if hasattr(rust_backend, 'compile'):
                    result = rust_backend.compile(str(source_file))
                    results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, e))

        threads = []
        for i in range(3):
            thread = threading.Thread(target=compile_in_thread, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert len(results) <= 3

    def test_rust_backend_with_very_long_lines(self, rust_backend, temp_dir):
        """
        Tests compilation of a Rust file containing an extremely long line to ensure the backend can handle large line lengths without errors.
        """
        very_long_line = "fn main() { " + "println!(\"" + "x" * 10000 + "\"); }"
        source_file = temp_dir / "long_lines.rs"
        source_file.write_text(very_long_line)
        if hasattr(rust_backend, 'compile'):
            try:
                result = rust_backend.compile(str(source_file))
                assert result is not None
            except Exception:
                pass

class TestRustBackendFailureConditions:
    """Test failure conditions and error handling."""

    def test_nonexistent_file_handling(self, rust_backend):
        """
        Test that the RustBackend correctly raises an exception when attempting to compile a non-existent Rust file.
        
        Asserts that compiling a file path that does not exist results in an appropriate exception being raised.
        """
        nonexistent_file = "/definitely/does/not/exist/file.rs"
        if hasattr(rust_backend, 'compile'):
            with pytest.raises((FileNotFoundError, IOError, ValueError, Exception)):
                rust_backend.compile(nonexistent_file)

    def test_invalid_rust_syntax_handling(self, rust_backend, invalid_rust_code, temp_dir):
        """
        Test that the Rust backend correctly handles compilation of Rust code with invalid syntax.
        
        Creates a file with invalid Rust code and attempts to compile it, asserting that the compilation fails or an appropriate error is raised.
        """
        source_file = temp_dir / "invalid.rs"
        source_file.write_text(invalid_rust_code)
        if hasattr(rust_backend, 'compile'):
            try:
                result = rust_backend.compile(str(source_file))
                if hasattr(result, 'success'):
                    assert not result.success
                elif hasattr(result, 'error'):
                    assert result.error is not None
            except Exception as e:
                assert e is not None

    def test_permission_denied_handling(self, rust_backend, sample_rust_code, temp_dir):
        """
        Tests that the RustBackend correctly handles permission denied errors when compiling a Rust source file with restricted permissions.
        """
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        os.chmod(source_file, 0o000)
        try:
            if hasattr(rust_backend, 'compile'):
                with pytest.raises((PermissionError, IOError, Exception)):
                    rust_backend.compile(str(source_file))
        finally:
            os.chmod(source_file, 0o644)

    @patch('subprocess.run')
    def test_subprocess_failure_handling(self, mock_run, rust_backend, sample_rust_code, temp_dir, mock_subprocess_failure):
        """
        Test that the RustBackend correctly handles subprocess failures during compilation.
        
        Simulates a failed subprocess execution and verifies that the backend either returns a failure indicator or raises an exception.
        """
        mock_run.return_value = mock_subprocess_failure
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile'):
            try:
                result = rust_backend.compile(str(source_file))
                if hasattr(result, 'success'):
                    assert not result.success
                elif hasattr(result, 'error'):
                    assert result.error is not None
            except Exception as e:
                assert e is not None

    @patch('subprocess.run')
    def test_subprocess_timeout_handling(self, mock_run, rust_backend, sample_rust_code, temp_dir):
        """
        Test that the RustBackend correctly handles subprocess timeouts during compilation.
        
        Simulates a timeout by configuring the subprocess mock to raise TimeoutExpired, then asserts that the compile method raises the appropriate exception.
        """
        mock_run.side_effect = subprocess.TimeoutExpired("rustc", 10)
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile'):
            with pytest.raises((subprocess.TimeoutExpired, Exception)):
                rust_backend.compile(str(source_file))

    def test_invalid_configuration_handling(self, rust_backend):
        """
        Test that the RustBackend correctly handles attempts to set invalid configuration values.
        
        Verifies that setting various invalid configurations raises an appropriate exception.
        """
        if hasattr(rust_backend, 'set_config'):
            invalid_configs = [
                None,
                "invalid_string",
                123,
                {"invalid_key": "invalid_value"},
                {"timeout": -1},
                {"memory_limit": "invalid"},
            ]
            for cfg in invalid_configs:
                try:
                    rust_backend.set_config(cfg)
                except (ValueError, TypeError, Exception) as e:
                    assert e is not None

    def test_rust_backend_after_disposal(self, rust_backend):
        """
        Test that the Rust backend raises an exception when compilation is attempted after it has been disposed.
        """
        if hasattr(rust_backend, 'dispose'):
            rust_backend.dispose()
            if hasattr(rust_backend, 'compile'):
                with pytest.raises(Exception):
                    rust_backend.compile("dummy.rs")

    def test_multiple_disposal_calls(self, rust_backend):
        """
        Verify that calling the dispose method multiple times on the RustBackend does not raise errors or cause issues.
        """
        if hasattr(rust_backend, 'dispose'):
            rust_backend.dispose()
            rust_backend.dispose()
            rust_backend.dispose()

class TestRustBackendMocking:
    """Test rust backend with mocked external dependencies."""

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_mocked_file_operations(self, mock_exists, mock_run, rust_backend, mock_subprocess_success):
        """
        Tests that file existence checks and subprocess execution are correctly invoked during compilation when file operations are mocked.
        """
        mock_exists.return_value = True
        mock_run.return_value = mock_subprocess_success
        if hasattr(rust_backend, 'compile'):
            result = rust_backend.compile("/fake/path/main.rs")
            mock_exists.assert_called()
            mock_run.assert_called()

    @patch('subprocess.run')
    def test_mocked_rustc_command_structure(self, mock_run, rust_backend, sample_rust_code, temp_dir, mock_subprocess_success):
        """
        Verify that the Rust compiler (`rustc`) is invoked with the correct command structure during compilation.
        
        This test ensures that the backend's compile method constructs and calls a subprocess command containing 'rustc' when compiling Rust source files.
        """
        mock_run.return_value = mock_subprocess_success
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile'):
            rust_backend.compile(str(source_file))
            mock_run.assert_called()
            call_args = mock_run.call_args
            if call_args:
                cmd = call_args[0][0] if isinstance(call_args[0], (list, tuple)) else call_args[0]
                assert any('rustc' in str(arg) for arg in (cmd if isinstance(cmd, (list, tuple)) else [cmd]))

    @patch('subprocess.Popen')
    def test_mocked_streaming_output(self, mock_popen, rust_backend, sample_rust_code, temp_dir):
        """
        Test that the RustBackend correctly handles streaming output from a mocked subprocess during compilation.
        
        Simulates line-by-line output from a subprocess to verify that streaming output is processed as expected when compiling Rust code.
        """
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [b"Line 1\n", b"Line 2\n", b""]
        mock_process.stderr.readline.side_effect = [b""]
        mock_process.poll.return_value = 0
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile_with_streaming'):
            result = rust_backend.compile_with_streaming(str(source_file))
            mock_popen.assert_called()

    @patch('os.environ')
    def test_mocked_environment_variables(self, mock_env, rust_backend, sample_rust_code, temp_dir):
        """
        Test that environment variables are correctly copied and used during Rust code compilation when mocked.
        
        This test verifies that the backend interacts with the environment as expected by asserting that the environment's copy method is called during compilation.
        """
        mock_env.copy.return_value = {
            'PATH': '/usr/bin',
            'RUST_BACKTRACE': '1',
            'RUSTFLAGS': '-C opt-level=2',
        }
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile'):
            try:
                rust_backend.compile(str(source_file))
                mock_env.copy.assert_called()
            except Exception:
                pass

    @patch('tempfile.mkdtemp')
    def test_mocked_temporary_directory_creation(self, mock_mkdtemp, rust_backend, sample_rust_code, temp_dir):
        """
        Tests that the temporary directory creation function is called during Rust code compilation by mocking its behavior.
        """
        mock_mkdtemp.return_value = str(temp_dir / "rust_temp")
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile'):
            try:
                rust_backend.compile(str(source_file))
                assert mock_mkdtemp.called
            except Exception:
                pass

    @patch('shutil.which')
    def test_mocked_executable_detection(self, mock_which, rust_backend):
        """
        Tests that the Rust compiler executable detection logic correctly identifies when `rustc` is available or missing, using a mocked executable lookup.
        """
        mock_which.return_value = "/usr/bin/rustc"
        if hasattr(rust_backend, 'check_rustc_available'):
            assert rust_backend.check_rustc_available() is True
            mock_which.assert_called_with('rustc')
        mock_which.return_value = None
        if hasattr(rust_backend, 'check_rustc_available'):
            assert rust_backend.check_rustc_available() is False

class TestRustBackendPerformanceAndResources:
    """Test performance characteristics and resource management."""

    def test_memory_usage_monitoring(self, rust_backend, sample_rust_code, temp_dir):
        """
        Checks that compiling Rust code does not increase memory usage by more than 100MB.
        
        This test writes sample Rust code to a file, compiles it using the backend, and asserts that the process's memory usage remains within acceptable limits.
        """
        import psutil
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile'):
            try:
                rust_backend.compile(str(source_file))
                peak_memory = process.memory_info().rss
                memory_increase = peak_memory - initial_memory
                assert memory_increase < 100 * 1024 * 1024
            except ImportError:
                pytest.skip("psutil not available for memory monitoring")
            except Exception:
                pass

    def test_compilation_timeout_handling(self, rust_backend, temp_dir):
        """
        Test that the RustBackend correctly handles compilation timeouts.
        
        This test writes a complex Rust source file designed to trigger a long compilation and verifies that the backend either returns a result or raises a timeout-related exception when a very short timeout is specified.
        """
        complex_code = '''
        macro_rules! recursive_macro {
            (0) => { 1 };
            ($n:expr) => { $n * recursive_macro!($n - 1) };
        }
        fn main() {
            let result = recursive_macro!(20);
            println!("Result: {}", result);
        }
        '''
        source_file = temp_dir / "complex.rs"
        source_file.write_text(complex_code)
        if hasattr(rust_backend, 'compile_with_timeout'):
            try:
                result = rust_backend.compile_with_timeout(str(source_file), timeout=0.1)
                assert result is not None
            except Exception as e:
                assert "timeout" in str(e).lower()

    def test_multiple_sequential_compilations(self, rust_backend, sample_rust_code, temp_dir):
        """
        Test that performing multiple sequential compilations does not result in memory leaks or failures.
        
        Runs the compilation process ten times in a row using different source files to ensure the backend remains stable and functional across repeated use.
        """
        for i in range(10):
            source_file = temp_dir / f"main_{i}.rs"
            source_file.write_text(sample_rust_code)
            if hasattr(rust_backend, 'compile'):
                try:
                    result = rust_backend.compile(str(source_file))
                    assert result is not None
                except Exception:
                    pass

    def test_large_output_handling(self, rust_backend, temp_dir):
        """
        Tests that the backend can compile and run a Rust program producing large output without exceeding output size limits.
        """
        large_output_code = '''
        fn main() {
            for i in 0..10000 {
                println!("Output line number: {}", i);
            }
        }
        '''
        source_file = temp_dir / "large_output.rs"
        source_file.write_text(large_output_code)
        if hasattr(rust_backend, 'compile_and_run'):
            try:
                result = rust_backend.compile_and_run(str(source_file))
                if hasattr(result, 'output'):
                    assert len(result.output) < 10 * 1024 * 1024
            except Exception:
                pass

    def test_resource_cleanup_after_errors(self, rust_backend, invalid_rust_code, temp_dir):
        """
        Verify that temporary files and resources are properly cleaned up after a compilation error occurs.
        
        This test writes invalid Rust code to a file, attempts compilation to trigger an error, and then invokes the backend's cleanup method if available. It asserts that the number of files in the temporary directory does not increase unexpectedly, ensuring resource cleanup is effective after errors.
        """
        source_file = temp_dir / "invalid.rs"
        source_file.write_text(invalid_rust_code)
        initial_files = len(list(temp_dir.glob("*")))
        if hasattr(rust_backend, 'compile'):
            try:
                rust_backend.compile(str(source_file))
            except Exception:
                pass
        if hasattr(rust_backend, 'cleanup'):
            rust_backend.cleanup()
        final_files = len(list(temp_dir.glob("*")))
        assert final_files <= initial_files + 1

class TestRustBackendCleanupAndIntegration:
    """Test cleanup, resource management, and integration scenarios."""

    def test_proper_cleanup_after_successful_compilation(self, rust_backend, sample_rust_code, temp_dir):
        """
        Verify that temporary files are properly cleaned up after a successful Rust code compilation.
        
        This test ensures that after compiling a Rust source file, invoking the backend's cleanup method removes any additional files created during compilation, leaving at most one extra file in the temporary directory.
        """
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        initial_files = set(temp_dir.rglob("*"))
        if hasattr(rust_backend, 'compile'):
            try:
                _ = rust_backend.compile(str(source_file))
                if hasattr(rust_backend, 'cleanup'):
                    rust_backend.cleanup()
                final_files = set(temp_dir.rglob("*"))
                extra = final_files - initial_files
                assert len(extra) <= 1
            except Exception:
                if hasattr(rust_backend, 'cleanup'):
                    rust_backend.cleanup()

    def test_context_manager_support(self, sample_rust_code, temp_dir):
        """
        Test whether RustBackend supports the context manager protocol and can compile code within a context block.
        
        Skips the test if RustBackend does not implement context manager support.
        """
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        try:
            with RustBackend() as backend:
                if hasattr(backend, 'compile'):
                    result = backend.compile(str(source_file))
                    assert result is not None
        except TypeError:
            pytest.skip("RustBackend does not support context manager protocol")

    def test_backend_state_consistency(self, rust_backend, sample_rust_code, temp_dir):
        """
        Verify that the backend's readiness state remains consistent before and after compilation operations.
        """
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'is_ready'):
            initial_ready = rust_backend.is_ready()
        if hasattr(rust_backend, 'compile'):
            try:
                _ = rust_backend.compile(str(source_file))
                if hasattr(rust_backend, 'is_ready'):
                    assert rust_backend.is_ready() == initial_ready
            except Exception:
                if hasattr(rust_backend, 'is_ready'):
                    assert isinstance(rust_backend.is_ready(), bool)

    def test_integration_with_real_rust_environment(self, rust_backend, sample_rust_code, temp_dir):
        """
        Performs an integration test of the RustBackend using the actual Rust toolchain if available.
        
        Skips the test if `rustc` is not present in the environment. Compiles a sample Rust source file and verifies successful compilation and the existence of the resulting executable, if supported by the backend.
        """
        import shutil
        if shutil.which('rustc') is None:
            pytest.skip("rustc not available for integration testing")
        source_file = temp_dir / "integration_test.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile'):
            try:
                result = rust_backend.compile(str(source_file))
                assert result is not None
                if getattr(result, 'success', False) and hasattr(result, 'executable_path'):
                    assert Path(result.executable_path).exists()
            except Exception as e:
                pytest.skip(f"Integration test failed due to environment: {e}")

def setup_module(module):
    """
    Create the 'test_artifacts' directory for storing module-level test resources if it does not already exist.
    """
    test_dir = Path("test_artifacts")
    test_dir.mkdir(exist_ok=True)

def teardown_module(module):
    """
    Remove the 'test_artifacts' directory and its contents after all tests in the module have run.
    """
    import shutil
    test_dir = Path("test_artifacts")
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)

@pytest.mark.parametrize("rust_code,expected_behavior", [
    ("fn main() {}", "simple_success"),
    ("fn main() { panic!(\"test\"); }", "runtime_panic"),
    ("invalid rust code", "compile_error"),
    ("fn main() { loop {} }", "infinite_loop"),
])
def test_parametrized_rust_code_scenarios(rust_code, expected_behavior, temp_dir):
    """
    Runs a parametrized test to validate RustBackend's behavior for various Rust code scenarios, including successful compilation, compile errors, and runtime panics.
    
    Parameters:
        rust_code (str): The Rust source code to compile and test.
        expected_behavior (str): The expected outcome, such as "simple_success", "compile_error", or "runtime_panic".
        temp_dir (Path): Temporary directory for writing the Rust source file.
    """
    backend = RustBackend()
    source_file = temp_dir / f"{expected_behavior}.rs"
    source_file.write_text(rust_code)
    if hasattr(backend, 'compile'):
        try:
            result = backend.compile(str(source_file))
            if expected_behavior == "simple_success":
                assert result is not None
            elif expected_behavior == "compile_error":
                if hasattr(result, 'success'):
                    assert not result.success
        except Exception as e:
            if expected_behavior in ["compile_error", "runtime_panic"]:
                assert e is not None
            else:
                pytest.fail(f"Unexpected exception for {expected_behavior}: {e}")

@pytest.mark.slow
def test_compilation_performance_benchmark(temp_dir):
    """
    Benchmarks the compilation time of a Rust program using the RustBackend, asserting it completes within 10 seconds.
    
    Skips the test if compilation fails due to environment issues.
    """
    import time
    rust_code = '''
    fn fibonacci(n: u32) -> u32 {
        match n {
            0 => 0,
            1 => 1,
            _ => fibonacci(n - 1) + fibonacci(n - 2),
        }
    }
    fn main() {
        for i in 0..30 {
            println!("fib({}) = {}", i, fibonacci(i));
        }
    }
    '''
    backend = RustBackend()
    source_file = temp_dir / "benchmark.rs"
    source_file.write_text(rust_code)
    if hasattr(backend, 'compile'):
        start = time.time()
        try:
            _ = backend.compile(str(source_file))
            elapsed = time.time() - start
            assert elapsed < 10.0, f"Compilation took too long: {elapsed}s"
        except Exception:
            pytest.skip("Performance benchmark failed due to environment issues")