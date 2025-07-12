"""
Tests for structured logging system.
"""

import json
import logging
import tempfile
import time
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from markdown_lab.core.config_v2 import LogLevel, MarkdownLabSettings
from markdown_lab.core.logging import (
    ComponentProcessor,
    CorrelationIDProcessor,
    MetricsCollector,
    PerformanceProcessor,
    async_log_context,
    clear_context,
    configure_structured_logging,
    get_logger,
    log_cache_operation,
    log_context,
    log_conversion,
    log_http_request,
    performance_context,
    set_correlation_id,
    set_request_id,
    setup_logging_and_telemetry,
    traced,
)


@pytest.fixture
def temp_log_file():
    """Create temporary log file for tests."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        yield Path(f.name)
    # Cleanup handled by tempfile


@pytest.fixture
def settings_with_logging(temp_log_file):
    """Create settings with logging configuration."""
    return MarkdownLabSettings(
        structured_logging=True,
        log_level=LogLevel.DEBUG,
        log_file=temp_log_file,
        telemetry_enabled=False,
    )


@pytest.fixture
def capture_logs():
    """Capture log output for testing."""
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = root_logger.handlers[:]

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    yield log_capture

    # Cleanup
    root_logger.handlers.clear()
    root_logger.handlers.extend(original_handlers)
    root_logger.setLevel(original_level)


class TestStructuredLoggingConfiguration:
    """Test structured logging configuration."""

    def test_configure_structured_logging_json(
        self, settings_with_logging, capture_logs
    ):
        """Test JSON structured logging configuration."""
        configure_structured_logging(settings_with_logging)

        logger = get_logger("test.module")
        logger.info("Test message", key="value", number=42)

        log_output = capture_logs.getvalue()
        assert log_output.strip()  # Should have output

        # Should be valid JSON
        try:
            log_data = json.loads(log_output.strip())
            assert log_data["event"] == "Test message"
            assert log_data["key"] == "value"
            assert log_data["number"] == 42
            assert "timestamp" in log_data
            assert "level" in log_data
            assert "logger" in log_data
        except json.JSONDecodeError:
            pytest.fail("Log output is not valid JSON")

    def test_configure_structured_logging_console(self, capture_logs):
        """Test console structured logging configuration."""
        settings = MarkdownLabSettings(
            structured_logging=False, log_level=LogLevel.INFO
        )

        configure_structured_logging(settings)

        logger = get_logger("test.console")
        logger.info("Console test message", data="test")

        log_output = capture_logs.getvalue()
        assert "Console test message" in log_output
        assert "data=test" in log_output


class TestCorrelationAndContext:
    """Test correlation IDs and logging context."""

    def test_correlation_id_setting(self, settings_with_logging, capture_logs):
        """Test setting and using correlation IDs."""
        configure_structured_logging(settings_with_logging)

        correlation_id = set_correlation_id("test-correlation-123")
        assert correlation_id == "test-correlation-123"

        logger = get_logger("test.correlation")
        logger.info("Test with correlation ID")

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())
        assert log_data["correlation_id"] == "test-correlation-123"

        # Test auto-generated correlation ID
        clear_context()
        generated_id = set_correlation_id()
        assert len(generated_id) == 36  # UUID format

    def test_request_id_setting(self, settings_with_logging, capture_logs):
        """Test setting request IDs."""
        configure_structured_logging(settings_with_logging)

        set_request_id("req-456")
        set_correlation_id("corr-789")

        logger = get_logger("test.request")
        logger.info("Test with request ID")

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())
        assert log_data["request_id"] == "req-456"
        assert log_data["correlation_id"] == "corr-789"

    def test_log_context_manager(self, settings_with_logging, capture_logs):
        """Test log context manager."""
        configure_structured_logging(settings_with_logging)

        logger = get_logger("test.context")

        with log_context(user_id="user123", operation="test_op"):
            logger.info("Message with context")

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())
        assert log_data["user_id"] == "user123"
        assert log_data["operation"] == "test_op"

    @pytest.mark.asyncio
    async def test_async_log_context_manager(self, settings_with_logging, capture_logs):
        """Test async log context manager."""
        configure_structured_logging(settings_with_logging)

        logger = get_logger("test.async_context")

        async with async_log_context(session_id="session456", task="async_task"):
            logger.info("Async message with context")

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())
        assert log_data["session_id"] == "session456"
        assert log_data["task"] == "async_task"

    def test_clear_context(self, settings_with_logging, capture_logs):
        """Test clearing context."""
        configure_structured_logging(settings_with_logging)

        set_correlation_id("test-123")
        set_request_id("req-456")

        clear_context()

        logger = get_logger("test.clear")
        logger.info("Message after clear")

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())
        assert log_data["correlation_id"] == "unknown"
        assert "request_id" not in log_data


class TestPerformanceLogging:
    """Test performance logging and tracing."""

    def test_performance_context_success(self, settings_with_logging, capture_logs):
        """Test performance context for successful operations."""
        configure_structured_logging(settings_with_logging)

        with performance_context("test_operation"):
            time.sleep(0.1)  # Simulate work

        log_output = capture_logs.getvalue()
        log_lines = [
            line.strip() for line in log_output.strip().split("\n") if line.strip()
        ]

        # Should have start and completion messages
        assert len(log_lines) >= 2

        start_log = json.loads(log_lines[0])
        assert start_log["event"] == "Operation started"
        assert start_log["operation"] == "test_operation"

        completion_log = json.loads(log_lines[1])
        assert completion_log["event"] == "Operation completed"
        assert completion_log["operation"] == "test_operation"
        assert completion_log["status"] == "success"
        assert completion_log["duration_ms"] >= 100  # At least 100ms

    def test_performance_context_error(self, settings_with_logging, capture_logs):
        """Test performance context for failed operations."""
        configure_structured_logging(settings_with_logging)

        with pytest.raises(ValueError):
            with performance_context("failing_operation"):
                raise ValueError("Test error")

        log_output = capture_logs.getvalue()
        log_lines = [
            line.strip() for line in log_output.strip().split("\n") if line.strip()
        ]

        # Should have start and failure messages
        assert len(log_lines) >= 2

        start_log = json.loads(log_lines[0])
        assert start_log["event"] == "Operation started"

        error_log = json.loads(log_lines[1])
        assert error_log["event"] == "Operation failed"
        assert error_log["status"] == "error"
        assert error_log["error"] == "Test error"
        assert error_log["error_type"] == "ValueError"

    def test_traced_decorator_sync(self, settings_with_logging, capture_logs):
        """Test traced decorator for synchronous functions."""
        configure_structured_logging(settings_with_logging)

        @traced("sync_function")
        def test_function(x, y):
            time.sleep(0.05)
            return x + y

        result = test_function(3, 4)
        assert result == 7

        log_output = capture_logs.getvalue()
        log_lines = [
            line.strip() for line in log_output.strip().split("\n") if line.strip()
        ]

        # Should have performance logging
        assert len(log_lines) >= 2

        start_log = json.loads(log_lines[0])
        assert start_log["operation"] == "sync_function"

    @pytest.mark.asyncio
    async def test_traced_decorator_async(self, settings_with_logging, capture_logs):
        """Test traced decorator for async functions."""
        configure_structured_logging(settings_with_logging)

        @traced("async_function")
        async def async_test_function(x, y):
            await asyncio.sleep(0.05)
            return x * y

        result = await async_test_function(3, 4)
        assert result == 12

        log_output = capture_logs.getvalue()
        log_lines = [
            line.strip() for line in log_output.strip().split("\n") if line.strip()
        ]

        # Should have performance logging
        assert len(log_lines) >= 2


class TestLoggingProcessors:
    """Test custom logging processors."""

    def test_correlation_id_processor(self):
        """Test CorrelationIDProcessor."""
        processor = CorrelationIDProcessor()

        # Test with no correlation ID in context
        event_dict = {"event": "test"}
        result = processor(None, None, event_dict)
        assert result["correlation_id"] == "unknown"

        # Test with correlation ID in context
        from markdown_lab.core.logging import _logger_context

        _logger_context["correlation_id"] = "test-id"

        event_dict = {"event": "test"}
        result = processor(None, None, event_dict)
        assert result["correlation_id"] == "test-id"

    def test_performance_processor(self):
        """Test PerformanceProcessor."""
        processor = PerformanceProcessor()

        event_dict = {"event": "test"}
        result = processor(None, None, event_dict)

        assert "timestamp" in result
        assert isinstance(result["timestamp"], float)

        # Test with operation start time
        from markdown_lab.core.logging import _logger_context

        start_time = time.time() - 0.5  # 500ms ago
        _logger_context["operation_start_time"] = start_time

        event_dict = {"event": "test"}
        result = processor(None, None, event_dict)

        assert "operation_duration_ms" in result
        assert result["operation_duration_ms"] >= 400  # Should be around 500ms

    def test_component_processor(self):
        """Test ComponentProcessor."""
        processor = ComponentProcessor()

        mock_logger = MagicMock()
        mock_logger.name = "test.logger"

        event_dict = {"event": "test"}
        result = processor(mock_logger, None, event_dict)

        assert result["component"] == "markdown_lab"
        assert result["logger"] == "test.logger"


class TestConvenienceLoggingFunctions:
    """Test convenience logging functions."""

    def test_log_http_request_success(self, settings_with_logging, capture_logs):
        """Test HTTP request logging for successful requests."""
        configure_structured_logging(settings_with_logging)

        log_http_request(
            url="https://example.com", method="GET", status_code=200, duration=0.5
        )

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["event"] == "HTTP request completed"
        assert log_data["url"] == "https://example.com"
        assert log_data["method"] == "GET"
        assert log_data["status_code"] == 200
        assert log_data["duration_ms"] == 500.0
        assert log_data["event_type"] == "http_request"

    def test_log_http_request_error(self, settings_with_logging, capture_logs):
        """Test HTTP request logging for failed requests."""
        configure_structured_logging(settings_with_logging)

        log_http_request(
            url="https://example.com",
            method="POST",
            status_code=500,
            duration=1.2,
            error=ValueError("Connection failed"),
        )

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["event"] == "HTTP request failed"
        assert log_data["status_code"] == 500
        assert log_data["error"] == "Connection failed"
        assert log_data["error_type"] == "ValueError"

    def test_log_conversion_success(self, settings_with_logging, capture_logs):
        """Test conversion logging for successful conversions."""
        configure_structured_logging(settings_with_logging)

        log_conversion(
            input_format="html",
            output_format="markdown",
            success=True,
            document_size=1024,
            duration=0.25,
        )

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["event"] == "Conversion completed"
        assert log_data["input_format"] == "html"
        assert log_data["output_format"] == "markdown"
        assert log_data["document_size"] == 1024
        assert log_data["duration_ms"] == 250.0

    def test_log_conversion_error(self, settings_with_logging, capture_logs):
        """Test conversion logging for failed conversions."""
        configure_structured_logging(settings_with_logging)

        log_conversion(
            input_format="html",
            output_format="json",
            success=False,
            error=RuntimeError("Parse error"),
        )

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["event"] == "Conversion failed"
        assert log_data["error"] == "Parse error"
        assert log_data["error_type"] == "RuntimeError"

    def test_log_cache_operation(self, settings_with_logging, capture_logs):
        """Test cache operation logging."""
        configure_structured_logging(settings_with_logging)

        log_cache_operation(
            operation="get", cache_type="memory", key="test_key_123", hit=True
        )

        log_output = capture_logs.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["event"] == "Cache operation"
        assert log_data["operation"] == "get"
        assert log_data["cache_type"] == "memory"
        assert log_data["cache_key"] == "test_key_123"
        assert log_data["cache_hit"] is True
        assert log_data["event_type"] == "cache_operation"


class TestMetricsCollector:
    """Test metrics collection."""

    def test_metrics_collector_without_telemetry(self):
        """Test metrics collector when telemetry is disabled."""
        collector = MetricsCollector()

        # Should not raise errors even without telemetry
        collector.record_request("GET", 200, 0.5)
        collector.record_conversion("markdown", True)
        collector.record_cache_hit("memory")
        collector.record_cache_miss("disk")

    @patch("markdown_lab.core.logging._meter")
    def test_metrics_collector_with_telemetry(self, mock_meter):
        """Test metrics collector with telemetry enabled."""
        # Mock meter and counters
        mock_counter = MagicMock()
        mock_histogram = MagicMock()
        mock_meter.create_counter.return_value = mock_counter
        mock_meter.create_histogram.return_value = mock_histogram

        collector = MetricsCollector()

        # Test request recording
        collector.record_request("GET", 200, 0.5)
        mock_counter.add.assert_called()
        mock_histogram.record.assert_called()

        # Test conversion recording
        collector.record_conversion("markdown", True)
        mock_counter.add.assert_called()


class TestFileLogging:
    """Test file-based logging."""

    def test_log_to_file(self, temp_log_file):
        """Test logging to file."""
        settings = MarkdownLabSettings(
            structured_logging=True, log_file=temp_log_file, log_level=LogLevel.INFO
        )

        configure_structured_logging(settings)

        logger = get_logger("test.file")
        logger.info("Test file message", data="test")

        # Check file contents
        with open(temp_log_file, "r") as f:
            content = f.read()

        assert "Test file message" in content

        # Should be valid JSON
        log_data = json.loads(content.strip())
        assert log_data["event"] == "Test file message"
        assert log_data["data"] == "test"


class TestSetupIntegration:
    """Test complete setup integration."""

    def test_setup_logging_and_telemetry(self, capture_logs):
        """Test complete logging and telemetry setup."""
        settings = MarkdownLabSettings(
            structured_logging=True,
            log_level=LogLevel.DEBUG,
            telemetry_enabled=False,  # Disable for testing
        )

        setup_logging_and_telemetry(settings)

        log_output = capture_logs.getvalue()

        # Should log setup completion
        assert "Logging and telemetry configured" in log_output

    def test_setup_with_telemetry_endpoint(self, capture_logs):
        """Test setup with telemetry endpoint."""
        settings = MarkdownLabSettings(
            structured_logging=True,
            telemetry_enabled=True,
            telemetry_endpoint="http://localhost:4317",
        )

        # Mock telemetry setup to avoid actual connections
        with patch("markdown_lab.core.logging.configure_telemetry"):
            setup_logging_and_telemetry(settings)

        log_output = capture_logs.getvalue()
        assert "telemetry_enabled" in log_output


@pytest.mark.asyncio
async def test_real_world_logging_scenario(settings_with_logging, capture_logs):
    """Test a realistic logging scenario."""
    configure_structured_logging(settings_with_logging)

    # Set up context
    correlation_id = set_correlation_id("scenario-123")
    set_request_id("req-456")

    # Simulate application flow
    with log_context(user_id="user789", operation="full_conversion"):
        logger = get_logger("app.main")
        logger.info("Starting document processing")

        # HTTP request
        log_http_request("https://example.com", status_code=200, duration=0.3)

        # Conversion
        with performance_context("html_to_markdown"):
            await asyncio.sleep(0.1)  # Simulate work

        log_conversion("html", "markdown", success=True, document_size=2048)

        # Cache operations
        log_cache_operation("get", "memory", "cached_doc", hit=False)
        log_cache_operation("set", "memory", "cached_doc", hit=None)

        logger.info("Processing completed", documents_processed=1)

    log_output = capture_logs.getvalue()
    log_lines = [
        line.strip() for line in log_output.strip().split("\n") if line.strip()
    ]

    # Verify we have multiple log entries
    assert len(log_lines) >= 5

    # Check that all logs have correlation context
    for line in log_lines:
        log_data = json.loads(line)
        assert log_data["correlation_id"] == correlation_id
        assert log_data.get("user_id") == "user789" or "HTTP request" in log_data.get(
            "event", ""
        )
        assert log_data["component"] == "markdown_lab"
