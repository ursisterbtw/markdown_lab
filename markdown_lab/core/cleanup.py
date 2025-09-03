"""Resource cleanup utilities for markdown_lab."""

import atexit
import logging

logger = logging.getLogger(__name__)

_cleanup_registered = False


def cleanup_rust_resources() -> None:
    """Clean up Rust-side resources (runtime, thread pools, etc.)."""
    try:
        from markdown_lab.markdown_lab_rs import cleanup_resources

        cleanup_resources()
        logger.debug("Rust resources cleaned up successfully")
    except ImportError:
        logger.debug("Rust module not available, skipping cleanup")
    except Exception as e:
        logger.warning(f"Error cleaning up Rust resources: {e}")


def register_cleanup() -> None:
    """Register cleanup functions to run at program exit."""
    global _cleanup_registered

    if not _cleanup_registered:
        atexit.register(cleanup_rust_resources)
        _cleanup_registered = True
        logger.debug("Resource cleanup registered")


def force_cleanup() -> None:
    """Force immediate cleanup of resources."""
    cleanup_rust_resources()


# Auto-register cleanup on module import
register_cleanup()
