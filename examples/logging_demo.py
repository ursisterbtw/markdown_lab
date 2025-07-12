#!/usr/bin/env python3
"""
Demonstration of structured logging and telemetry features.

This example shows how to use the modern logging system with JSON output,
correlation IDs, performance tracking, and metrics collection.
"""

import asyncio
import time

from markdown_lab.core.config_v2 import LogLevel, MarkdownLabSettings
from markdown_lab.core.logging import (
    async_log_context,
    get_logger,
    log_cache_operation,
    log_context,
    log_conversion,
    log_http_request,
    metrics_collector,
    performance_context,
    set_correlation_id,
    set_request_id,
    setup_logging_and_telemetry,
    traced,
)


def demo_basic_structured_logging():
    """Demonstrate basic structured logging."""

    # Configure logging
    settings = MarkdownLabSettings(
        structured_logging=True, log_level=LogLevel.INFO, telemetry_enabled=False
    )
    setup_logging_and_telemetry(settings)

    # Get logger
    logger = get_logger("demo.basic")

    # Basic structured logging
    logger.info("Application started", version="1.0.0", environment="demo")
    logger.warning("This is a warning", issue_type="demo", severity="low")
    logger.error("Simulated error", error_code="DEMO_001", recoverable=True)


def demo_correlation_and_context():
    """Demonstrate correlation IDs and context management."""

    logger = get_logger("demo.correlation")

    # Set correlation ID for request tracking
    set_correlation_id("demo-session-123")
    set_request_id("req-456")

    logger.info("Request started", endpoint="/api/convert")

    # Use context manager for additional context
    with log_context(user_id="user789", organization="demo_org"):
        logger.info("Processing user request", action="document_conversion")

        # Nested context
        with log_context(document_id="doc_abc123", format="html"):
            logger.info("Document loaded", size_bytes=1024)
            logger.info("Conversion started", target_format="markdown")

    logger.info("Request completed", status="success", duration_ms=250)


def demo_performance_tracking():
    """Demonstrate performance tracking and timing."""

    logger = get_logger("demo.performance")

    # Performance context for automatic timing
    with performance_context("document_processing"):
        time.sleep(0.1)  # Simulate processing
        logger.info("Processing step 1 completed")

        with performance_context("html_parsing"):
            time.sleep(0.05)  # Simulate parsing
            logger.info("HTML parsed successfully", elements_found=42)

        with performance_context("markdown_conversion"):
            time.sleep(0.08)  # Simulate conversion
            logger.info("Conversion completed", output_lines=25)


def demo_traced_functions():
    """Demonstrate function tracing with decorators."""

    @traced("sync_calculation")
    def calculate_complexity(text: str) -> int:
        """Calculate text complexity score."""
        time.sleep(0.02)  # Simulate calculation
        return len(text) * 2

    @traced("async_validation")
    async def validate_document(content: str) -> bool:
        """Validate document content."""
        await asyncio.sleep(0.03)  # Simulate async validation
        return content != ""

    # Test synchronous traced function
    calculate_complexity("Hello world!")

    # Test asynchronous traced function
    async def run_async_demo():
        await validate_document("Sample content")

    asyncio.run(run_async_demo())


def demo_convenience_logging():
    """Demonstrate convenience logging functions."""

    # HTTP request logging
    log_http_request(
        url="https://api.example.com/content",
        method="GET",
        status_code=200,
        duration=0.45,
    )

    log_http_request(
        url="https://api.example.com/upload",
        method="POST",
        status_code=500,
        duration=2.3,
        error=ConnectionError("Timeout occurred"),
    )

    # Conversion logging
    log_conversion(
        input_format="html",
        output_format="markdown",
        success=True,
        document_size=2048,
        duration=0.15,
    )

    log_conversion(
        input_format="html",
        output_format="json",
        success=False,
        error=ValueError("Invalid HTML structure"),
    )

    # Cache operation logging
    log_cache_operation("get", "memory", "doc_cache_key_123", hit=True)
    log_cache_operation("set", "disk", "doc_cache_key_456", hit=None)
    log_cache_operation("get", "redis", "doc_cache_key_789", hit=False)


async def demo_async_contexts():
    """Demonstrate async context management."""

    logger = get_logger("demo.async")

    # Async context for request processing
    async with async_log_context(session_id="async_session_456", worker_id="worker_01"):
        logger.info("Async processing started")

        # Simulate async work with nested contexts
        async with async_log_context(task_type="fetch", source="external_api"):
            await asyncio.sleep(0.1)
            logger.info("Data fetched from external source", records=15)

        async with async_log_context(task_type="transform", algorithm="html2md"):
            await asyncio.sleep(0.08)
            logger.info("Data transformation completed", output_format="markdown")

        logger.info("Async processing completed", total_duration_ms=180)


def demo_real_world_scenario():
    """Demonstrate a realistic application scenario."""

    logger = get_logger("app.main")

    # Simulate a web request processing pipeline
    request_id = f"req_{int(time.time())}"
    set_correlation_id(f"session_{int(time.time())}")
    set_request_id(request_id)

    with log_context(
        user_id="user_12345",
        organization="acme_corp",
        plan="premium",
        feature="batch_conversion",
    ):
        logger.info("Request received", endpoint="/api/v1/convert/batch")

        try:
            # Simulate authentication
            with performance_context("authentication"):
                time.sleep(0.02)
                logger.info("User authenticated", method="jwt_token")

            # Simulate rate limiting check
            with performance_context("rate_limit_check"):
                time.sleep(0.01)
                logger.info("Rate limit check passed", remaining_quota=95)

            # Simulate document processing
            documents = ["doc1.html", "doc2.html", "doc3.html"]

            for i, doc in enumerate(documents):
                with log_context(document_id=doc, batch_position=i + 1):
                    logger.info("Processing document", document=doc)

                    # Fetch document
                    log_http_request(
                        f"https://storage.example.com/{doc}",
                        status_code=200,
                        duration=0.12,
                    )

                    # Convert document
                    with performance_context("document_conversion"):
                        time.sleep(0.05)
                        log_conversion(
                            "html",
                            "markdown",
                            success=True,
                            document_size=1024 * (i + 1),
                            duration=0.05,
                        )

                    # Cache result
                    log_cache_operation("set", "redis", f"result_{doc}", hit=None)

            logger.info(
                "Batch conversion completed",
                documents_processed=len(documents),
                total_duration_ms=250,
                status="success",
            )

        except Exception as e:
            logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                status="error",
            )


def demo_metrics_collection():
    """Demonstrate metrics collection."""

    logger = get_logger("demo.metrics")

    # Simulate some operations that generate metrics
    logger.info("Starting metrics collection demo")

    # Simulate various HTTP requests
    for i in range(5):
        method = "GET" if i % 2 == 0 else "POST"
        status = 200 if i < 4 else 500
        duration = 0.1 + (i * 0.05)

        metrics_collector.record_request(method, status, duration)
        log_http_request(
            f"https://api.example.com/endpoint/{i}",
            method=method,
            status_code=status,
            duration=duration,
        )

    # Simulate conversions
    for format_combo in [("html", "markdown"), ("html", "json"), ("xml", "markdown")]:
        success = format_combo[1] != "json"  # Simulate json conversion failure
        metrics_collector.record_conversion(format_combo[1], success)
        log_conversion(format_combo[0], format_combo[1], success=success)

    # Simulate cache operations
    for i in range(10):
        hit = i < 7  # 70% hit rate
        cache_type = "memory" if i < 5 else "disk"

        if hit:
            metrics_collector.record_cache_hit(cache_type)
        else:
            metrics_collector.record_cache_miss(cache_type)

        log_cache_operation("get", cache_type, f"key_{i}", hit=hit)

    logger.info("Metrics collection demo completed", operations_simulated=20)


def demo_console_vs_json_logging():
    """Demonstrate console vs JSON logging formats."""

    # JSON logging (structured)
    settings_json = MarkdownLabSettings(
        structured_logging=True, log_level=LogLevel.INFO
    )
    setup_logging_and_telemetry(settings_json)

    logger = get_logger("demo.json")
    logger.info("This is JSON formatted", format="json", readable=False)

    # Console logging (human-readable)
    settings_console = MarkdownLabSettings(
        structured_logging=False, log_level=LogLevel.INFO
    )
    setup_logging_and_telemetry(settings_console)

    logger = get_logger("demo.console")
    logger.info("This is console formatted", format="console", readable=True)


def main():
    """Run all logging demonstrations."""

    # Run demonstrations
    demo_basic_structured_logging()
    demo_correlation_and_context()
    demo_performance_tracking()
    demo_traced_functions()
    demo_convenience_logging()

    # Async demonstrations
    asyncio.run(demo_async_contexts())

    demo_real_world_scenario()
    demo_metrics_collection()
    demo_console_vs_json_logging()


if __name__ == "__main__":
    main()
