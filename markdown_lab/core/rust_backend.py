"""
Simplified Rust backend interface for markdown_lab.

This module provides a clean boundary between Python and Rust code,
eliminating complex fallback logic and simplifying integration.
"""

import logging
from typing import List, Optional

from markdown_lab.core.errors import RustIntegrationError

logger = logging.getLogger(__name__)


class RustBackend:
    """Simplified interface to Rust functions."""

    def __init__(self, fallback_enabled: bool = False):
        """
        Initialize Rust backend.

        Args:
            fallback_enabled: Whether to allow fallback to Python implementations
        """
        self.fallback_enabled = fallback_enabled
        self._rust_module = None
        self._initialize_rust()

    def _initialize_rust(self) -> None:
        """Initialize the Rust module."""
        try:
            from markdown_lab import markdown_lab_rs

            self._rust_module = markdown_lab_rs
            logger.debug("Rust backend initialized successfully")
        except ImportError as e:
            if not self.fallback_enabled:
                raise RustIntegrationError(
                    "Rust backend required but not available",
                    rust_function="module_import",
                    fallback_available=False,
                    cause=e,
                ) from e
            logger.warning("Rust backend not available, fallback enabled")

    def convert_html_to_format(
        self, html: str, base_url: str, output_format: str = "markdown"
    ) -> str:
        """
        Converts HTML content to the specified output format using the Rust backend.

        Parameters:
            html (str): The HTML content to convert.
            base_url (str): The base URL used to resolve relative links in the HTML.
            output_format (str, optional): The desired output format ("markdown", "json", or "xml"). Defaults to "markdown".

        Returns:
            str: The converted content in the specified format.

        Raises:
            RustIntegrationError: If the Rust backend is unavailable or the conversion fails.
        """
        if not self._rust_module:
            raise RustIntegrationError(
                "Rust backend not available",
                rust_function="convert_html_to_format",
                fallback_available=self.fallback_enabled,
            )

        try:
            # Always pass a normalized string to the underlying module
            normalized = (output_format or "markdown").lower()
            # Use the convert_html_to_format entrypoint
            return self._rust_module.convert_html_to_format(html, base_url, normalized)
        except Exception as e:
            raise RustIntegrationError(
                f"Rust conversion failed: {str(e)}",
                rust_function="convert_html_to_format",
                fallback_available=self.fallback_enabled,
                cause=e,
            ) from e

    def convert_html_to_markdown(self, html: str, base_url: str) -> str:
        """
        Convert HTML to markdown (legacy method).

        Args:
            html: HTML content to convert
            base_url: Base URL for resolving relative links

        Returns:
            Markdown content
        """
        return self.convert_html_to_format(html, base_url, "markdown")

    def chunk_markdown(
        self, markdown: str, chunk_size: int = 1000, chunk_overlap: int = 200
    ) -> List[str]:
        """
        Create semantic chunks from markdown content.

        Args:
            markdown: Markdown content to chunk
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks in characters

        Returns:
            List of chunk strings

        Raises:
            RustIntegrationError: If chunking fails
        """
        if not self._rust_module:
            raise RustIntegrationError(
                "Rust backend not available",
                rust_function="chunk_markdown",
                fallback_available=self.fallback_enabled,
            )

        try:
            return self._rust_module.chunk_markdown(markdown, chunk_size, chunk_overlap)
        except Exception as e:
            raise RustIntegrationError(
                f"Rust chunking failed: {str(e)}",
                rust_function="chunk_markdown",
                fallback_available=self.fallback_enabled,
                cause=e,
            ) from e

    def render_js_page(self, url: str, wait_time: Optional[int] = None) -> str:
        """
        Render a JavaScript-enabled page.

        Args:
            url: URL to render
            wait_time: Time to wait for JavaScript execution (ms)

        Returns:
            Rendered HTML content

        Raises:
            RustIntegrationError: If rendering fails
        """
        if not self._rust_module:
            raise RustIntegrationError(
                "Rust backend not available",
                rust_function="render_js_page",
                fallback_available=False,  # No Python fallback for JS rendering
            )

        try:
            return self._rust_module.render_js_page(url, wait_time)
        except Exception as e:
            raise RustIntegrationError(
                f"Rust JS rendering failed: {str(e)}",
                rust_function="render_js_page",
                fallback_available=False,
                cause=e,
            ) from e

    def is_available(self) -> bool:
        """Check if Rust backend is available."""
        return self._rust_module is not None

    def get_version_info(self) -> dict:
        """Get version information about the Rust backend."""
        if not self._rust_module:
            return {"available": False, "version": None}

        # Try to get version info if available
        try:
            # This would need to be implemented in the Rust side
            version = getattr(self._rust_module, "__version__", "unknown")
            return {"available": True, "version": version}
        except Exception:
            return {"available": True, "version": "unknown"}


# Global instance for convenience
_rust_backend: Optional[RustBackend] = None


def get_rust_backend(fallback_enabled: bool = False) -> RustBackend:
    """
    Get the global Rust backend instance.

    Args:
        fallback_enabled: Whether to enable Python fallbacks

    Returns:
        RustBackend instance
    """
    global _rust_backend
    if _rust_backend is None:
        _rust_backend = RustBackend(fallback_enabled=fallback_enabled)
    # _rust_backend is guaranteed to be non-None after initialization
    return _rust_backend  # type: ignore


def reset_rust_backend() -> None:
    """Reset the global Rust backend instance."""
    global _rust_backend
    _rust_backend = None
