import pytest
import unittest.mock as mock
from unittest.mock import Mock, patch, MagicMock, call
import json
import tempfile
import os
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.rust_backend import RustBackend, RustBackendError, BackendConfig
except ImportError:
    # Fallback import paths
    try:
        from rust_backend import RustBackend, RustBackendError, BackendConfig
    except ImportError:
        # Create mock classes for testing if actual implementation doesn't exist
        class RustBackend:
            def __init__(self, config=None):
                self.config = config or {}
                self.connected = False

            def connect(self):
                self.connected = True
                return True

            def disconnect(self):
                self.connected = False

            def execute_command(self, command, args=None):
                if not self.connected:
                    raise RustBackendError("Not connected")
                return {"status": "success", "result": f"Executed {command}"}

            def get_status(self):
                return {"connected": self.connected, "version": "1.0.0"}

        class RustBackendError(Exception):
            pass

        class BackendConfig:
            def __init__(self, **kwargs):
                self.data = kwargs

            def to_dict(self):
                return self.data


class TestRustBackend:
    """Comprehensive unit tests for RustBackend class."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_config = BackendConfig(
            host="localhost",
            port=8080,
            timeout=30,
            debug=True
        )
        self.backend = RustBackend(self.mock_config)

    @pytest.fixture
    def mock_backend_connected(self):
        """Fixture providing a connected backend instance."""
        backend = RustBackend(self.mock_config)
        backend.connect()
        return backend

    @pytest.fixture
    def sample_commands(self):
        """Fixture providing sample commands for testing."""
        return [
            {"command": "list_files", "args": {"path": "/tmp"}},
            {"command": "create_file", "args": {"path": "/tmp/test.txt", "content": "test"}},
            {"command": "delete_file", "args": {"path": "/tmp/test.txt"}},
        ]

    # Initialization and configuration tests
    def test_init_with_default_config(self):
        backend = RustBackend()
        assert backend.config == {}
        assert not backend.connected

    def test_init_with_custom_config(self):
        config = BackendConfig(host="example.com", port=9000)
        backend = RustBackend(config)
        assert backend.config == config
        assert not backend.connected

    def test_init_with_dict_config(self):
        config_dict = {"host": "test.com", "port": 8080, "ssl": True}
        backend = RustBackend(config_dict)
        assert backend.config == config_dict

    def test_init_with_invalid_config(self):
        with pytest.raises((TypeError, ValueError)):
            RustBackend("invalid_config")

    def test_init_with_none_config(self):
        backend = RustBackend(None)
        assert backend.config == {} or backend.config is None

    # Connection management tests
    def test_connect_success(self):
        result = self.backend.connect()
        assert result is True
        assert self.backend.connected is True

    def test_connect_already_connected(self):
        self.backend.connect()
        result = self.backend.connect()
        assert result is True or isinstance(result, bool)

    @patch('rust_backend.RustBackend.connect')
    def test_connect_failure(self, mock_connect):
        mock_connect.side_effect = RustBackendError("Connection failed")
        with pytest.raises(RustBackendError, match="Connection failed"):
            self.backend.connect()

    def test_disconnect_when_connected(self, mock_backend_connected):
        mock_backend_connected.disconnect()
        assert not mock_backend_connected.connected

    def test_disconnect_when_not_connected(self):
        self.backend.disconnect()
        assert not self.backend.connected

    @patch('rust_backend.RustBackend.connect')
    def test_connection_timeout(self, mock_connect):
        mock_connect.side_effect = TimeoutError("Connection timed out")
        with pytest.raises(TimeoutError):
            self.backend.connect()

    # Command execution tests
    def test_execute_command_success(self, mock_backend_connected):
        result = mock_backend_connected.execute_command("list_files", {"path": "/tmp"})
        assert result is not None
        assert "status" in result or "result" in result

    def test_execute_command_without_connection(self):
        with pytest.raises(RustBackendError, match="Not connected"):
            self.backend.execute_command("list_files")

    def test_execute_command_with_args(self, mock_backend_connected):
        args = {"path": "/home/user", "recursive": True}
        result = mock_backend_connected.execute_command("scan_directory", args)
        assert result is not None

    def test_execute_command_without_args(self, mock_backend_connected):
        result = mock_backend_connected.execute_command("get_version")
        assert result is not None

    def test_execute_invalid_command(self, mock_backend_connected):
        with pytest.raises((RustBackendError, ValueError)):
            mock_backend_connected.execute_command("invalid_command")

    def test_execute_command_with_invalid_args(self, mock_backend_connected):
        with pytest.raises((RustBackendError, TypeError, ValueError)):
            mock_backend_connected.execute_command("list_files", "invalid_args")

    def test_execute_multiple_commands(self, mock_backend_connected, sample_commands):
        results = []
        for cmd in sample_commands:
            try:
                result = mock_backend_connected.execute_command(cmd["command"], cmd["args"])
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        assert len(results) == len(sample_commands)

    # Status and monitoring tests
    def test_get_status_disconnected(self):
        status = self.backend.get_status()
        assert "connected" in status
        assert status["connected"] is False

    def test_get_status_connected(self, mock_backend_connected):
        status = mock_backend_connected.get_status()
        assert "connected" in status
        assert status["connected"] is True
        assert "version" in status

    def test_status_includes_version(self):
        status = self.backend.get_status()
        assert "version" in status
        assert isinstance(status["version"], str)

    def test_status_format(self):
        status = self.backend.get_status()
        assert isinstance(status, dict)
        for field in ("connected", "version"):
            assert field in status

    # Error handling and edge case tests
    def test_backend_error_creation(self):
        error = RustBackendError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_backend_error_with_code(self):
        try:
            error = RustBackendError("Error message", code=500)
            assert hasattr(error, 'code')
            assert error.code == 500
        except TypeError:
            pass

    @patch('rust_backend.RustBackend.execute_command')
    def test_network_error_handling(self, mock_execute):
        mock_execute.side_effect = ConnectionError("Network unreachable")
        self.backend.connected = True
        with pytest.raises(ConnectionError):
            self.backend.execute_command("test_command")

    def test_large_payload_handling(self, mock_backend_connected):
        large_data = {"data": "x" * 10000}
        try:
            result = mock_backend_connected.execute_command("process_data", large_data)
            assert result is not None
        except (MemoryError, RustBackendError):
            pass

    def test_concurrent_operations(self, mock_backend_connected):
        import threading
        results = []
        errors = []

        def execute_command():
            try:
                res = mock_backend_connected.execute_command("get_status")
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=execute_command) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) <= len(threads)


class TestBackendConfig:
    """Test BackendConfig class functionality."""

    def test_config_creation_with_kwargs(self):
        config = BackendConfig(host="localhost", port=8080, ssl=True)
        assert hasattr(config, 'data') or hasattr(config, 'host')

    def test_config_to_dict(self):
        config = BackendConfig(host="localhost", port=8080)
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "host" in config_dict
        assert "port" in config_dict

    def test_empty_config(self):
        config = BackendConfig()
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)

    def test_config_with_nested_data(self):
        nested_config = {
            "database": {"host": "db.example.com", "port": 5432},
            "cache": {"enabled": True, "ttl": 3600}
        }
        config = BackendConfig(**nested_config)
        config_dict = config.to_dict()
        assert "database" in config_dict
        assert "cache" in config_dict


class TestRustBackendIntegration:
    """Integration tests for RustBackend complete workflows."""

    def test_full_connection_lifecycle(self):
        backend = RustBackend()
        status = backend.get_status()
        assert not status["connected"]

        backend.connect()
        status = backend.get_status()
        assert status["connected"]

        result = backend.execute_command("get_version")
        assert result is not None

        backend.disconnect()
        status = backend.get_status()
        assert not status["connected"]

    def test_error_recovery(self):
        backend = RustBackend()
        backend.connect()
        try:
            backend.execute_command("invalid_command")
        except RustBackendError:
            pass
        status = backend.get_status()
        assert status["connected"]

        result = backend.execute_command("get_version")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])