"""
Unified error hierarchy for markdown_lab.

This module provides a consistent error handling system across all components,
replacing scattered exception handling patterns throughout the codebase.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class MarkdownLabError(Exception):
    """Base exception for all markdown_lab operations."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        base_msg = self.message
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg = f"{base_msg} (Context: {context_str})"
        return base_msg

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for structured logging."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }


class NetworkError(MarkdownLabError):
    """Network-related errors including timeouts, connection failures, and HTTP errors."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        retry_count: Optional[int] = None,
        **kwargs,
    ):
        """
        Initializes a NetworkError with message and optional network context.

        Args:
            message: Description of the network error.
            url: The URL associated with the network operation, if applicable.
            status_code: HTTP status code returned by the network request, if available.
            retry_count: Number of retry attempts made before the error occurred.
        """
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
        if status_code:
            context["status_code"] = status_code
        if retry_count is not None:
            context["retry_count"] = retry_count

        # Remove context from kwargs to avoid duplicate parameter
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        super().__init__(message, context=context, **filtered_kwargs)


class ParsingError(MarkdownLabError):
    """HTML/XML parsing and content extraction errors."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        parser_type: Optional[str] = None,
        element_selector: Optional[str] = None,
        **kwargs,
    ):
        """
        Initializes a ParsingError with a message and optional parsing context.

        Args:
            message: Description of the parsing error.
            url: The URL of the content being parsed, if applicable.
            parser_type: The type of parser involved (e.g., "html", "xml").
            element_selector: The selector for the element related to the error, if any.

        Additional context can be provided via keyword arguments and will be included in the error's context dictionary.
        """
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
        if parser_type:
            context["parser_type"] = parser_type
        if element_selector:
            context["element_selector"] = element_selector

        # Remove context from kwargs to avoid duplicate parameter
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        super().__init__(message, context=context, **filtered_kwargs)


class ConversionError(MarkdownLabError):
    """Errors during format conversion (HTML to Markdown/JSON/XML)."""

    def __init__(
        self,
        message: str,
        source_format: Optional[str] = None,
        target_format: Optional[str] = None,
        conversion_stage: Optional[str] = None,
        **kwargs,
    ):
        """
        Initializes a ConversionError with details about a format conversion failure.

        Adds source format, target format, and conversion stage to the error context if provided.
        """
        context = kwargs.get("context", {})
        if source_format:
            context["source_format"] = source_format
        if target_format:
            context["target_format"] = target_format
        if conversion_stage:
            context["conversion_stage"] = conversion_stage

        # Remove context from kwargs to avoid duplicate parameter
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        super().__init__(message, context=context, **filtered_kwargs)


class ConfigurationError(MarkdownLabError):
    """Configuration validation and setup errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs,
    ):
        """
        Initializes a ConfigurationError with an error message and optional configuration details.

        Args:
            message: Description of the configuration error.
            config_key: The configuration key related to the error, if applicable.
            config_value: The value associated with the configuration key, if relevant.
        """
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        if config_value is not None:
            context["config_value"] = config_value

        # Remove context from kwargs to avoid duplicate parameter
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        super().__init__(message, context=context, **filtered_kwargs)


class ResourceError(MarkdownLabError):
    """Memory, disk, or other resource constraint errors."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        current_usage: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs,
    ):
        """
        Initializes a ResourceError with details about a resource constraint violation.

        Adds resource type, current usage, and limit to the error context if provided.
        """
        context = kwargs.get("context", {})
        if resource_type:
            context["resource_type"] = resource_type
        if current_usage is not None:
            context["current_usage"] = current_usage
        if limit is not None:
            context["limit"] = limit

        # Remove context from kwargs to avoid duplicate parameter
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        super().__init__(message, context=context, **filtered_kwargs)


class CacheError(MarkdownLabError):
    """Cache-related errors including storage and retrieval failures."""

    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        cache_operation: Optional[str] = None,
        **kwargs,
    ):
        """
        Initializes a CacheError with an optional cache key and operation.

        Adds cache-specific context such as the cache key and operation type to the error details if provided.
        """
        context = kwargs.get("context", {})
        if cache_key:
            context["cache_key"] = cache_key
        if cache_operation:
            context["cache_operation"] = cache_operation

        # Remove context from kwargs to avoid duplicate parameter
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        super().__init__(message, context=context, **filtered_kwargs)


class ChunkingError(MarkdownLabError):
    """Content chunking and semantic processing errors."""

    def __init__(
        self,
        message: str,
        content_length: Optional[int] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        **kwargs,
    ):
        """
        Initializes a ChunkingError with details about content chunking parameters.

        Args:
            message: Description of the chunking error.
            content_length: Total length of the content being chunked, if available.
            chunk_size: Size of each chunk, if specified.
            chunk_overlap: Overlap between chunks, if specified.

        Additional context can be provided via keyword arguments and will be included in the error's context.
        """
        context = kwargs.get("context", {})
        if content_length is not None:
            context["content_length"] = content_length
        if chunk_size is not None:
            context["chunk_size"] = chunk_size
        if chunk_overlap is not None:
            context["chunk_overlap"] = chunk_overlap

        # Remove context from kwargs to avoid duplicate parameter
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        super().__init__(message, context=context, **filtered_kwargs)


class RustIntegrationError(MarkdownLabError):
    """Errors related to Rust backend integration and fallback mechanisms."""

    def __init__(
        self,
        message: str,
        rust_function: Optional[str] = None,
        fallback_available: bool = True,
        **kwargs,
    ):
        """
        Initializes a RustIntegrationError with details about a Rust backend integration failure.

        Args:
            message: Description of the integration error.
            rust_function: Name of the Rust function involved, if applicable.
            fallback_available: Indicates if a Python fallback is available for the failed operation.
        """
        context = kwargs.get("context", {})
        if rust_function:
            context["rust_function"] = rust_function
        context["fallback_available"] = fallback_available

        # Remove context from kwargs to avoid duplicate parameter
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        super().__init__(message, context=context, **filtered_kwargs)


# Convenience functions for common error scenarios
def network_timeout_error(url: str, timeout: int, retry_count: int = 0) -> NetworkError:
    """
    Creates a NetworkError representing a request timeout with contextual details.

    Args:
        url: The URL where the timeout occurred.
        timeout: The timeout duration in seconds.
        retry_count: The number of retry attempts made before the timeout.

    Returns:
        A NetworkError instance with a standardized message and context.
    """
    return NetworkError(
        f"Request to {url} timed out after {timeout} seconds",
        url=url,
        retry_count=retry_count,
        error_code="NETWORK_TIMEOUT",
        context={"timeout": timeout},
    )


def parsing_element_not_found_error(
    url: str, selector: str, parser_type: str = "html"
) -> ParsingError:
    """
    Creates a ParsingError for a missing element identified by a selector in the specified parser type.

    Args:
        url: The URL of the content being parsed.
        selector: The selector used to locate the element.
        parser_type: The type of parser used (default is "html").

    Returns:
        A ParsingError indicating that the specified element was not found.
    """
    return ParsingError(
        f"Element with selector '{selector}' not found in {parser_type}",
        url=url,
        parser_type=parser_type,
        element_selector=selector,
        error_code="ELEMENT_NOT_FOUND",
    )


def conversion_format_error(
    source_format: str, target_format: str, stage: str
) -> ConversionError:
    """
    Creates a ConversionError for failures during format conversion.

    Args:
        source_format: The original format being converted from.
        target_format: The target format being converted to.
        stage: The stage at which the conversion failed.

    Returns:
        A ConversionError instance with detailed context about the conversion failure.
    """
    return ConversionError(
        f"Failed to convert from {source_format} to {target_format} at stage: {stage}",
        source_format=source_format,
        target_format=target_format,
        conversion_stage=stage,
        error_code="CONVERSION_FAILED",
    )


def config_validation_error(key: str, value: Any, reason: str) -> ConfigurationError:
    """
    Creates a ConfigurationError for an invalid configuration entry.

    Args:
        key: The configuration key that failed validation.
        value: The invalid value associated with the key.
        reason: Description of why the configuration is invalid.

    Returns:
        A ConfigurationError instance with details about the invalid configuration.
    """
    return ConfigurationError(
        f"Invalid configuration for '{key}': {reason}",
        config_key=key,
        config_value=value,
        error_code="CONFIG_INVALID",
    )


def memory_limit_error(current: int, limit: int) -> ResourceError:
    """
    Creates a ResourceError indicating that memory usage has exceeded the specified limit.

    Args:
        current: The current memory usage in bytes.
        limit: The memory usage limit in bytes.

    Returns:
        A ResourceError instance with details about the exceeded memory limit.
    """
    return ResourceError(
        f"Memory usage ({current:,} bytes) exceeds limit ({limit:,} bytes)",
        resource_type="memory",
        current_usage=current,
        limit=limit,
        error_code="MEMORY_LIMIT_EXCEEDED",
    )


# Error handling utilities
def handle_request_exception(
    exception: Exception, url: str, retry_count: int = 0
) -> NetworkError:
    """
    Converts a requests library exception into a standardized NetworkError.

    Maps Timeout, ConnectionError, HTTPError, and other RequestException types to NetworkError
    with appropriate error codes and context, preserving the original exception as the cause.
    """
    import requests

    if isinstance(exception, requests.exceptions.Timeout):
        return NetworkError(
            f"Request to {url} timed out",
            url=url,
            retry_count=retry_count,
            error_code="REQUEST_TIMEOUT",
            cause=exception,
        )
    if isinstance(exception, requests.exceptions.ConnectionError):
        return NetworkError(
            f"Failed to connect to {url}",
            url=url,
            retry_count=retry_count,
            error_code="CONNECTION_FAILED",
            cause=exception,
        )
    if isinstance(exception, requests.exceptions.HTTPError):
        status_code = getattr(exception.response, "status_code", None)
        return NetworkError(
            f"HTTP error {status_code} for {url}",
            url=url,
            status_code=status_code,
            retry_count=retry_count,
            error_code="HTTP_ERROR",
            cause=exception,
        )
    if isinstance(exception, requests.exceptions.RequestException):
        return NetworkError(
            f"Request error for {url}: {str(exception)}",
            url=url,
            retry_count=retry_count,
            error_code="REQUEST_ERROR",
            cause=exception,
        )
    return NetworkError(
        f"Unexpected error for {url}: {str(exception)}",
        url=url,
        retry_count=retry_count,
        error_code="UNEXPECTED_ERROR",
        cause=exception,
    )


def handle_parsing_exception(
    exception: Exception, url: str, parser_type: str = "html"
) -> ParsingError:
    """
    Converts a generic parsing exception into a standardized ParsingError.

    Args:
        exception: The original exception raised during parsing.
        url: The URL of the content being parsed.
        parser_type: The type of parser used (e.g., "html", "xml"). Defaults to "html".

    Returns:
        A ParsingError instance encapsulating the original exception and relevant context.
    """
    return ParsingError(
        f"Failed to parse {parser_type} content from {url}: {str(exception)}",
        url=url,
        parser_type=parser_type,
        error_code="PARSING_FAILED",
        cause=exception,
    )


def retry_with_backoff(
    func: Callable, max_retries: int, url: str, backoff_base: int = 2, *args, **kwargs
):
    """
    Executes a function with exponential backoff retry logic.

    This unified retry mechanism eliminates duplicate retry patterns across the codebase.

    Args:
        func: The function to execute
        max_retries: Maximum number of retry attempts
        url: URL for error context (used in logging)
        backoff_base: Base for exponential backoff calculation
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the successful function call

    Raises:
        NetworkError: If all retry attempts fail
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            network_error = handle_request_exception(e, url, attempt)

            # Log the attempt
            if attempt < max_retries - 1:
                wait_time = backoff_base**attempt  # Exponential backoff
                logger.warning(
                    f"Request failed for {url} on attempt {attempt + 1}/{max_retries}: "
                    f"{network_error.message}. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"Request failed for {url} after {max_retries} attempts: "
                    f"{network_error.message}"
                )
                raise network_error from e

    # This should never be reached, but included for completeness
    raise NetworkError(
        f"Failed to retrieve {url} after {max_retries} attempts",
        url=url,
        error_code="MAX_RETRIES_EXCEEDED",
    )


# Enhanced Error Catalog with Troubleshooting Guidance
ERROR_CATALOG = {
    # Network Errors
    "NETWORK_TIMEOUT": {
        "title": "Request Timeout",
        "description": "The request timed out waiting for a response from the server",
        "troubleshooting": [
            "• Increase timeout with --timeout parameter (current: {timeout}s)",
            "• Check your internet connection",
            "• Try using --profile conservative for slower, more reliable requests",
            "• The server might be overloaded - try again later",
        ],
        "examples": [
            "mlab convert url --timeout 60",
            "mlab convert url --profile conservative",
        ],
        "severity": "medium",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#troubleshooting-network-timeouts",
    },
    "CONNECTION_FAILED": {
        "title": "Connection Failed",
        "description": "Failed to establish a connection to the target server",
        "troubleshooting": [
            "• Check the URL is correct and accessible: {url}",
            "• Verify your internet connection",
            "• Check if the website is down using a service like downforeveryoneorjustme.com",
            "• Try using --profile conservative for better reliability",
            "• Check if you need to be behind a VPN or proxy",
        ],
        "examples": [
            "mlab convert https://example.com --profile conservative",
            "curl -I {url}  # Test URL accessibility",
        ],
        "severity": "high",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#troubleshooting-connection-issues",
    },
    "HTTP_ERROR": {
        "title": "HTTP Error Response",
        "description": "The server returned an HTTP error status code",
        "troubleshooting": [
            "• Status {status_code}: {status_message}",
            "• Check if the URL requires authentication",
            "• Verify the URL is correct: {url}",
            "• Try accessing the URL in a browser first",
            "• For 429 errors, use --profile conservative to reduce request rate",
            "• For 403/401 errors, the content might be protected",
        ],
        "examples": [
            "mlab convert url --profile conservative  # For rate limiting",
            "curl -I {url}  # Check status in terminal",
        ],
        "severity": "medium",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#http-status-codes",
    },
    "ELEMENT_NOT_FOUND": {
        "title": "HTML Element Not Found",
        "description": "Could not find the expected HTML element using the provided selector",
        "troubleshooting": [
            "• The website structure might have changed",
            "• Element '{element_selector}' not found in the HTML",
            "• Try converting anyway - other content might still be extracted",
            "• Check if the site requires JavaScript (try --js-rendering if available)",
            "• Inspect the page source to verify the element exists",
        ],
        "examples": [
            "mlab convert url --format json  # See full document structure",
            "curl {url} | grep '{element_selector}'  # Check if element exists",
        ],
        "severity": "low",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#html-parsing-issues",
    },
    "CONVERSION_FAILED": {
        "title": "Format Conversion Failed",
        "description": "Failed to convert content from one format to another",
        "troubleshooting": [
            "• Conversion from {source_format} to {target_format} failed at: {conversion_stage}",
            "• Try using a different output format (markdown/json/xml)",
            "• The content might contain unsupported elements",
            "• Use --verbose for more detailed error information",
            "• Try the legacy converter: mlab legacy",
        ],
        "examples": [
            "mlab convert url --format json  # Try JSON output",
            "mlab convert url --verbose      # Get more details",
        ],
        "severity": "medium",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#conversion-troubleshooting",
    },
    "CONFIG_INVALID": {
        "title": "Invalid Configuration",
        "description": "A configuration parameter has an invalid value",
        "troubleshooting": [
            "• Parameter '{config_key}' has invalid value: {config_value}",
            "• Check the allowed values in the help: mlab convert --help",
            "• Use a configuration profile: mlab profiles",
            "• Reset to defaults: mlab config --reset",
            "• Check environment variables (MARKDOWN_LAB_*)",
        ],
        "examples": [
            "mlab profiles                    # See available profiles",
            "mlab convert url --profile dev   # Use development profile",
        ],
        "severity": "high",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#configuration-guide",
    },
    "MEMORY_LIMIT_EXCEEDED": {
        "title": "Memory Limit Exceeded",
        "description": "The operation exceeded the configured memory limit",
        "troubleshooting": [
            "• Current usage: {current_usage:,} bytes, Limit: {limit:,} bytes",
            "• Try processing smaller content or increase memory limit",
            "• Use --profile fast for more aggressive memory settings",
            "• Split large batch operations into smaller chunks",
            "• Close other applications to free memory",
        ],
        "examples": [
            "mlab convert url --profile fast  # Higher memory limits",
            "mlab batch links.txt --max-workers 2  # Reduce parallel processing",
        ],
        "severity": "high",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#memory-management",
    },
    "CACHE_ERROR": {
        "title": "Cache Operation Failed",
        "description": "An error occurred during cache read/write operations",
        "troubleshooting": [
            "• Cache operation '{cache_operation}' failed for key: {cache_key}",
            "• Clear cache directory: rm -rf .request_cache",
            "• Disable cache temporarily: --no-cache",
            "• Check disk space and permissions",
            "• Use --skip-cache to bypass cache for this request",
        ],
        "examples": [
            "mlab convert url --no-cache      # Disable cache",
            "mlab convert url --skip-cache    # Skip cache once",
            "rm -rf .request_cache            # Clear cache",
        ],
        "severity": "low",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#cache-management",
    },
    "PARSING_FAILED": {
        "title": "Content Parsing Failed",
        "description": "Failed to parse the content using the specified parser",
        "troubleshooting": [
            "• Parser '{parser_type}' failed for URL: {url}",
            "• The content might be malformed or use unsupported encoding",
            "• Try a different output format",
            "• Check if the content requires JavaScript rendering",
            "• Verify the URL returns valid HTML",
        ],
        "examples": [
            "mlab convert url --format json   # Try structured output",
            "curl {url} | head -50           # Inspect raw content",
        ],
        "severity": "medium",
        "docs_url": "https://github.com/ursisterbtw/markdown_lab#parsing-errors",
    },
}


def get_status_message(status_code: int) -> str:
    """Get human-readable HTTP status message."""
    status_messages = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }
    return status_messages.get(status_code, f"HTTP {status_code}")


def get_troubleshooting_guide(error: MarkdownLabError) -> Dict[str, Any]:
    """
    Get comprehensive troubleshooting guide for an error.

    Args:
        error: The MarkdownLabError instance

    Returns:
        Dictionary with troubleshooting information
    """
    error_code = error.error_code
    if error_code not in ERROR_CATALOG:
        return {
            "title": "Unknown Error",
            "description": f"Error code {error_code} not found in catalog",
            "troubleshooting": [
                "• This is an unexpected error",
                "• Please report this issue on GitHub",
                "• Include the full error message and context",
            ],
            "examples": ["mlab legacy  # Try legacy interface"],
            "severity": "unknown",
        }

    guide = ERROR_CATALOG[error_code].copy()
    context = error.context or {}

    # Format troubleshooting messages with context
    if "troubleshooting" in guide:
        guide["troubleshooting"] = [
            msg.format(**context, **_get_format_extras(error))
            for msg in guide["troubleshooting"]
        ]

    # Format examples with context
    if "examples" in guide:
        guide["examples"] = [
            example.format(**context, **_get_format_extras(error))
            for example in guide["examples"]
        ]

    return guide


def _get_format_extras(error: MarkdownLabError) -> Dict[str, str]:
    """Get additional format values for error messages."""
    extras = {}

    # Add HTTP status message for HTTP errors
    if isinstance(error, NetworkError) and "status_code" in error.context:
        status_code = error.context["status_code"]
        extras["status_message"] = get_status_message(status_code)

    return extras


def format_error_for_cli(
    error: MarkdownLabError, show_troubleshooting: bool = True
) -> str:
    """
    Format an error for CLI display with rich troubleshooting information.

    Args:
        error: The MarkdownLabError instance
        show_troubleshooting: Whether to include troubleshooting guide

    Returns:
        Formatted error message for CLI display
    """
    guide = get_troubleshooting_guide(error)

    # Basic error info
    output = [
        f"❌ {guide['title']}",
        f"   {error.message}",
    ]

    # Add context if available
    if error.context:
        context_items = [f"{k}={v}" for k, v in error.context.items()]
        output.append(f"   Context: {', '.join(context_items)}")

    if show_troubleshooting:
        output.extend(("", "🔧 Troubleshooting:"))
        output.extend(f"   {step}" for step in guide["troubleshooting"])

        if guide.get("examples"):
            output.extend(("", "💡 Examples:"))
            output.extend(f"   {example}" for example in guide["examples"])

        if guide.get("docs_url"):
            output.extend(("", f"📖 Documentation: {guide['docs_url']}"))
    return "\n".join(output)
