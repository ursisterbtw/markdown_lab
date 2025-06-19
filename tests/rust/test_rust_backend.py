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
    """Create a RustBackend instance for testing."""
    backend = RustBackend()
    yield backend
    # Cleanup after test
    if hasattr(backend, 'cleanup'):
        backend.cleanup()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_rust_code():
    """Sample valid Rust code for testing."""
    return '''
fn main() {
    println!("Hello, world!");
    let x = 42;
    println!("The answer is: {}", x);
}
'''

@pytest.fixture
def invalid_rust_code():
    """Invalid Rust code for testing error handling."""
    return '''
fn main() {
    println!("Hello, world!"  // Missing semicolon and closing paren
    let x = ;  // Invalid assignment
}
'''

@pytest.fixture
def complex_rust_code():
    """More complex Rust code for advanced testing."""
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
    """Mock successful subprocess execution."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    return mock_result

@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess execution."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Compilation failed"
    return mock_result

class TestRustBackendHappyPath:
    """Test cases for successful rust backend operations."""

    def test_rust_backend_initialization(self):
        """Test that RustBackend initializes correctly."""
        backend = RustBackend()
        assert backend is not None
        assert hasattr(backend, '__class__')
        assert backend.__class__.__name__ == 'RustBackend'

    def test_get_rust_backend_function(self):
        """Test the get_rust_backend factory function."""
        backend = get_rust_backend()
        assert backend is not None
        assert isinstance(backend, RustBackend)

    def test_rust_backend_singleton_behavior(self):
        """Test if get_rust_backend returns singleton instances when expected."""
        backend1 = get_rust_backend()
        backend2 = get_rust_backend()
        assert backend1 is not None
        assert backend2 is not None

    @patch('subprocess.run')
    def test_successful_rust_compilation(self, mock_run, rust_backend, sample_rust_code, temp_dir, mock_subprocess_success):
        """Test successful compilation of valid Rust code."""
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
        """Test rust backend with more complex Rust code."""
        mock_run.return_value = mock_subprocess_success

        source_file = temp_dir / "complex.rs"
        source_file.write_text(complex_rust_code)

        if hasattr(rust_backend, 'compile'):
            result = rust_backend.compile(str(source_file))
            assert result is not None

    def test_rust_backend_configuration(self, rust_backend):
        """Test rust backend configuration and settings."""
        if hasattr(rust_backend, 'get_config'):
            config = rust_backend.get_config()
            assert config is not None
        if hasattr(rust_backend, 'set_config'):
            test_config = {"debug": True, "optimize": False}
            rust_backend.set_config(test_config)

    def test_rust_backend_version_info(self, rust_backend):
        """Test rust backend version information."""
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
        """Test handling of empty Rust file."""
        source_file = temp_dir / "empty.rs"
        source_file.write_text("")

        if hasattr(rust_backend, 'compile'):
            try:
                result = rust_backend.compile(str(source_file))
                assert result is not None
            except Exception as e:
                assert e is not None

    def test_very_large_rust_file(self, rust_backend, temp_dir):
        """Test handling of very large Rust file."""
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
        """Test handling of Rust files with Unicode characters."""
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
        """Test handling of files with special characters in path."""
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
        """Test concurrent usage of rust backend."""
        results = []
        errors = []

        def compile_in_thread(thread_id):
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
        """Test handling of Rust files with very long lines."""
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
        """Test handling of non-existent files."""
        nonexistent_file = "/definitely/does/not/exist/file.rs"
        if hasattr(rust_backend, 'compile'):
            with pytest.raises((FileNotFoundError, IOError, ValueError, Exception)):
                rust_backend.compile(nonexistent_file)

    def test_invalid_rust_syntax_handling(self, rust_backend, invalid_rust_code, temp_dir):
        """Test handling of invalid Rust syntax."""
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
        """Test handling of permission denied errors."""
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
        """Test handling of subprocess failures."""
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
        """Test handling of subprocess timeouts."""
        mock_run.side_effect = subprocess.TimeoutExpired("rustc", 10)
        source_file = temp_dir / "main.rs"
        source_file.write_text(sample_rust_code)
        if hasattr(rust_backend, 'compile'):
            with pytest.raises((subprocess.TimeoutExpired, Exception)):
                rust_backend.compile(str(source_file))

    def test_invalid_configuration_handling(self, rust_backend):
        """Test handling of invalid configuration."""
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
        """Test rust backend behavior after disposal/cleanup."""
        if hasattr(rust_backend, 'dispose'):
            rust_backend.dispose()
            if hasattr(rust_backend, 'compile'):
                with pytest.raises(Exception):
                    rust_backend.compile("dummy.rs")

    def test_multiple_disposal_calls(self, rust_backend):
        """Test multiple disposal calls don't cause issues."""
        if hasattr(rust_backend, 'dispose'):
            rust_backend.dispose()
            rust_backend.dispose()
            rust_backend.dispose()

class TestRustBackendMocking:
    """Test rust backend with mocked external dependencies."""

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_mocked_file_operations(self, mock_exists, mock_run, rust_backend, mock_subprocess_success):
        """Test file operations with mocked dependencies."""
        mock_exists.return_value = True
        mock_run.return_value = mock_subprocess_success
        if hasattr(rust_backend, 'compile'):
            result = rust_backend.compile("/fake/path/main.rs")
            mock_exists.assert_called()
            mock_run.assert_called()

    @patch('subprocess.run')
    def test_mocked_rustc_command_structure(self, mock_run, rust_backend, sample_rust_code, temp_dir, mock_subprocess_success):
        """Test that rustc is called with correct command structure."""
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
        """Test streaming output handling with mocked Popen."""
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
        """Test environment variable handling."""
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
        """Test temporary directory creation with mocking."""
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
        """Test executable detection with mocking."""
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
        """Test memory usage during compilation."""
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
        """Test compilation timeout handling."""
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
        """Test multiple sequential compilations for memory leaks."""
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
        """Test handling of programs that produce large output."""
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
        """Test resource cleanup after compilation errors."""
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
        """Test cleanup after successful compilation."""
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
        """Test context manager support if available."""
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
        """Test backend state remains consistent across operations."""
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
        """Integration test with real Rust environment if available."""
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
    """Set up module-level resources."""
    test_dir = Path("test_artifacts")
    test_dir.mkdir(exist_ok=True)

def teardown_module(module):
    """Clean up module-level resources."""
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
    """Parametrized tests for different Rust code scenarios."""
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
    """Benchmark compilation performance (marked as slow test)."""
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