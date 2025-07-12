"""
Structured logging and telemetry system for markdown_lab.

This module provides modern structured logging with JSON output, correlation IDs,
performance metrics, and OpenTelemetry integration for distributed tracing.
"""

import asyncio
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from typing import Optional

import structlog
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config_v2 import MarkdownLabSettings, get_settings

# Global state
_is_configured = False
_logger_context = {}
_tracer = None
_meter = None


class CorrelationIDProcessor:
    """Add correlation IDs to all log entries."""

    def __call__(self, logger, method_name, event_dict):
        # Add correlation ID if not present
        if "correlation_id" not in event_dict:
            event_dict["correlation_id"] = _logger_context.get(
                "correlation_id", "unknown"
            )

        # Add request ID if available
        if "request_id" in _logger_context:
            event_dict["request_id"] = _logger_context["request_id"]

        return event_dict


class PerformanceProcessor:
    """Add performance metrics to log entries."""

    def __call__(self, logger, method_name, event_dict):
        # Add timestamp
        event_dict["timestamp"] = time.time()

        # Add performance context if available
        if "operation_start_time" in _logger_context:
            duration = time.time() - _logger_context["operation_start_time"]
            event_dict["operation_duration_ms"] = round(duration * 1000, 2)

        return event_dict


class ComponentProcessor:
    """Add component and module information."""

    def __call__(self, logger, method_name, event_dict):
        # Add component info
        event_dict["component"] = "markdown_lab"

        # Add logger name if not present
        if "logger" not in event_dict:
            event_dict["logger"] = logger.name

        # Add method/function context
        if "function" not in event_dict and hasattr(logger, "_context"):
            event_dict["function"] = logger._context.get("function", "unknown")

        return event_dict


def configure_structured_logging(
    settings: Optional[MarkdownLabSettings] = None,
) -> None:
    """
    Configure structured logging with JSON output and correlation IDs.

    Args:
        settings: Configuration settings (uses global settings if None)
    """
    global _is_configured

    if _is_configured:
        return

    if settings is None:
        settings = get_settings()

    # Configure processors based on settings
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        CorrelationIDProcessor(),
        PerformanceProcessor(),
        ComponentProcessor(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add JSON renderer for structured logging
    if settings.structured_logging:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(
            logging,
            (
                settings.log_level
                if isinstance(settings.log_level, str)
                else settings.log_level.value
            ),
        ),
    )

    # Set log file if specified
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(file_handler)

    _is_configured = True


def configure_telemetry(settings: Optional[MarkdownLabSettings] = None) -> None:
    """
    Configure OpenTelemetry tracing and metrics.

    Args:
        settings: Configuration settings (uses global settings if None)
    """
    global _tracer, _meter

    if settings is None:
        settings = get_settings()

    if not settings.telemetry_enabled or not settings.telemetry_endpoint:
        return

    # Configure resource
    resource = Resource.create(
        {
            "service.name": "markdown_lab",
            "service.version": "1.0.0",
            "deployment.environment": "development" if settings.debug else "production",
        }
    )

    # Configure tracing
    trace_exporter = OTLPSpanExporter(endpoint=settings.telemetry_endpoint)
    span_processor = BatchSpanProcessor(trace_exporter)
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(trace_provider)

    # Configure metrics
    metric_exporter = OTLPMetricExporter(endpoint=settings.telemetry_endpoint)
    metric_reader = PeriodicExportingMetricReader(
        exporter=metric_exporter,
        export_interval_millis=10000,  # 10 seconds
    )
    metric_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(metric_provider)

    # Create global tracer and meter
    _tracer = trace.get_tracer("markdown_lab")
    _meter = metrics.get_meter("markdown_lab")


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger with the specified name.

    Args:
        name: Logger name (defaults to calling module)

    Returns:
        Configured structlog logger
    """
    if not _is_configured:
        configure_structured_logging()

    if name is None:
        import inspect

        frame = inspect.currentframe().f_back
        name = frame.f_globals.get("__name__", "unknown")

    return structlog.get_logger(name)


def set_correlation_id(correlation_id: str = None) -> str:
    """
    Set correlation ID for request tracking.

    Args:
        correlation_id: Custom correlation ID (generates UUID if None)

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    _logger_context["correlation_id"] = correlation_id
    return correlation_id


def set_request_id(request_id: str) -> None:
    """Set request ID for HTTP request tracking."""
    _logger_context["request_id"] = request_id


def clear_context() -> None:
    """Clear logging context."""
    _logger_context.clear()


@contextmanager
def log_context(**kwargs):
    """
    Context manager for adding context to logs.

    Example:
        with log_context(user_id="123", operation="convert"):
            logger.info("Processing document")
    """
    old_context = _logger_context.copy()
    _logger_context.update(kwargs)
    try:
        yield
    finally:
        _logger_context.clear()
        _logger_context.update(old_context)


@asynccontextmanager
async def async_log_context(**kwargs):
    """
    Async context manager for adding context to logs.

    Example:
        async with async_log_context(url="https://example.com"):
            await scrape_website(url)
    """
    old_context = _logger_context.copy()
    _logger_context.update(kwargs)
    try:
        yield
    finally:
        _logger_context.clear()
        _logger_context.update(old_context)


@contextmanager
def performance_context(operation_name: str):
    """
    Context manager for performance tracking.

    Example:
        with performance_context("html_parsing"):
            parse_html(content)
    """
    logger = get_logger()
    start_time = time.time()

    with log_context(operation=operation_name, operation_start_time=start_time):
        logger.info("Operation started", operation=operation_name)
        try:
            yield
            duration = time.time() - start_time
            logger.info(
                "Operation completed",
                operation=operation_name,
                duration_ms=round(duration * 1000, 2),
                status="success",
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Operation failed",
                operation=operation_name,
                duration_ms=round(duration * 1000, 2),
                status="error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


def traced(operation_name: str = None):
    """
    Decorator for adding tracing to functions.

    Args:
        operation_name: Name of the operation (uses function name if None)

    Example:
        @traced("convert_html")
        def convert_to_markdown(html: str) -> str:
            return convert(html)
    """

    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            get_logger()

            with performance_context(operation_name):
                if _tracer:
                    with _tracer.start_as_current_span(operation_name) as span:
                        span.set_attribute("function.name", func.__name__)
                        span.set_attribute("function.module", func.__module__)

                        try:
                            result = func(*args, **kwargs)
                            span.set_attribute("operation.status", "success")
                            return result
                        except Exception as e:
                            span.set_attribute("operation.status", "error")
                            span.set_attribute("error.type", type(e).__name__)
                            span.set_attribute("error.message", str(e))
                            raise
                else:
                    return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            get_logger()

            async with async_log_context(operation=operation_name):
                if _tracer:
                    with _tracer.start_as_current_span(operation_name) as span:
                        span.set_attribute("function.name", func.__name__)
                        span.set_attribute("function.module", func.__module__)

                        try:
                            result = await func(*args, **kwargs)
                            span.set_attribute("operation.status", "success")
                            return result
                        except Exception as e:
                            span.set_attribute("operation.status", "error")
                            span.set_attribute("error.type", type(e).__name__)
                            span.set_attribute("error.message", str(e))
                            raise
                else:
                    return await func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


class MetricsCollector:
    """Collector for application metrics."""

    def __init__(self):
        if _meter:
            self.request_counter = _meter.create_counter(
                "markdown_lab_requests_total",
                description="Total number of HTTP requests",
            )
            self.request_duration = _meter.create_histogram(
                "markdown_lab_request_duration_seconds",
                description="HTTP request duration in seconds",
            )
            self.conversion_counter = _meter.create_counter(
                "markdown_lab_conversions_total",
                description="Total number of HTML conversions",
            )
            self.cache_hits = _meter.create_counter(
                "markdown_lab_cache_hits_total", description="Total cache hits"
            )
            self.cache_misses = _meter.create_counter(
                "markdown_lab_cache_misses_total", description="Total cache misses"
            )
        else:
            # Stub implementations if telemetry not enabled
            self.request_counter = None
            self.request_duration = None
            self.conversion_counter = None
            self.cache_hits = None
            self.cache_misses = None

    def record_request(self, method: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        if self.request_counter:
            self.request_counter.add(
                1, {"method": method, "status_code": str(status_code)}
            )

        if self.request_duration:
            self.request_duration.record(
                duration, {"method": method, "status_code": str(status_code)}
            )

    def record_conversion(self, format_type: str, success: bool):
        """Record conversion metrics."""
        if self.conversion_counter:
            self.conversion_counter.add(
                1, {"format": format_type, "status": "success" if success else "error"}
            )

    def record_cache_hit(self, cache_type: str = "unknown"):
        """Record cache hit."""
        if self.cache_hits:
            self.cache_hits.add(1, {"cache_type": cache_type})

    def record_cache_miss(self, cache_type: str = "unknown"):
        """Record cache miss."""
        if self.cache_misses:
            self.cache_misses.add(1, {"cache_type": cache_type})


# Global metrics collector
metrics_collector = MetricsCollector()


def setup_logging_and_telemetry(settings: Optional[MarkdownLabSettings] = None) -> None:
    """
    Complete setup of logging and telemetry systems.

    Args:
        settings: Configuration settings (uses global settings if None)
    """
    if settings is None:
        settings = get_settings()

    # Configure structured logging
    configure_structured_logging(settings)

    # Configure telemetry if enabled
    if settings.telemetry_enabled:
        configure_telemetry(settings)

    # Log setup completion
    logger = get_logger(__name__)
    logger.info(
        "Logging and telemetry configured",
        structured_logging=settings.structured_logging,
        telemetry_enabled=settings.telemetry_enabled,
        log_level=(
            settings.log_level
            if isinstance(settings.log_level, str)
            else settings.log_level.value
        ),
    )


# Convenience functions for common logging patterns
def log_http_request(
    url: str,
    method: str = "GET",
    status_code: int = None,
    duration: float = None,
    error: Exception = None,
):
    """Log HTTP request with standard fields."""
    logger = get_logger("http")

    log_data = {"url": url, "method": method, "event_type": "http_request"}

    if status_code:
        log_data["status_code"] = status_code

    if duration:
        log_data["duration_ms"] = round(duration * 1000, 2)
        # Record metrics
        metrics_collector.record_request(method, status_code or 0, duration)

    if error:
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        logger.error("HTTP request failed", **log_data)
    else:
        logger.info("HTTP request completed", **log_data)


def log_conversion(
    input_format: str,
    output_format: str,
    success: bool = True,
    document_size: int = None,
    duration: float = None,
    error: Exception = None,
):
    """Log document conversion with standard fields."""
    logger = get_logger("conversion")

    log_data = {
        "input_format": input_format,
        "output_format": output_format,
        "event_type": "conversion",
    }

    if document_size:
        log_data["document_size"] = document_size

    if duration:
        log_data["duration_ms"] = round(duration * 1000, 2)

    # Record metrics
    metrics_collector.record_conversion(output_format, success)

    if error:
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        logger.error("Conversion failed", **log_data)
    else:
        logger.info("Conversion completed", **log_data)


def log_cache_operation(operation: str, cache_type: str, key: str, hit: bool = None):
    """Log cache operations with standard fields."""
    logger = get_logger("cache")

    log_data = {
        "operation": operation,
        "cache_type": cache_type,
        "cache_key": key,
        "event_type": "cache_operation",
    }

    if hit is not None:
        log_data["cache_hit"] = hit
        if hit:
            metrics_collector.record_cache_hit(cache_type)
        else:
            metrics_collector.record_cache_miss(cache_type)

    logger.info("Cache operation", **log_data)


if __name__ == "__main__":
    # Demo structured logging
    from .config_v2 import create_development_config

    settings = create_development_config()
    setup_logging_and_telemetry(settings)

    logger = get_logger(__name__)

    # Demo various logging patterns
    with log_context(user_id="demo_user", session_id="session_123"):
        logger.info("Demo started", demo_type="structured_logging")

        with performance_context("demo_operation"):
            import time

            time.sleep(0.1)  # Simulate work

        # Demo HTTP request logging
        log_http_request("https://example.com", status_code=200, duration=0.5)

        # Demo conversion logging
        log_conversion(
            "html", "markdown", success=True, document_size=1024, duration=0.25
        )

        # Demo cache logging
        log_cache_operation("get", "memory", "key_123", hit=True)

        logger.info("Demo completed", status="success")
