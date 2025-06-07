"""
Unified error hierarchy for markdown_lab.

This module provides a consistent error handling system across all components,
replacing scattered exception handling patterns throughout the codebase.
"""

from typing import Any, Dict, Optional


class MarkdownLabError(Exception):
    """Base exception for all markdown_lab operations.

    This exception provides structured error information including error codes
    and context data for better debugging and error handling.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initializes a MarkdownLabError with a message, error code, context, and optional cause.
        
        Args:
            message: Description of the error.
            error_code: Optional error code; defaults to the uppercase class name if not provided.
            context: Optional dictionary with additional contextual information about the error.
            cause: Optional underlying exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        """
        Returns a string representation of the error, including the error code and context if available.
        """
        base_msg = self.message
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg = f"{base_msg} (Context: {context_str})"
        return base_msg

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the error instance into a dictionary suitable for structured logging.
        
        Returns:
            A dictionary containing the error type, code, message, context, and cause.
        """
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

        super().__init__(message, context=context, **kwargs)


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

        super().__init__(message, context=context, **kwargs)


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

        super().__init__(message, context=context, **kwargs)


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

        super().__init__(message, context=context, **kwargs)


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

        super().__init__(message, context=context, **kwargs)


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

        super().__init__(message, context=context, **kwargs)


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

        super().__init__(message, context=context, **kwargs)


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

        super().__init__(message, context=context, **kwargs)


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
        error_code="NETWORK_TIMEOUT",
        context={"timeout": timeout, "retry_count": retry_count},
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
