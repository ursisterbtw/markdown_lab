"""
URL utilities for markdown_lab.

Provides centralized URL processing functionality including validation,
filename generation, resolution, and normalization.
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse, ParseResult


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format and structure.
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_url("https://example.com")
        (True, None)
        >>> validate_url("not-a-url")
        (False, "URL must start with http:// or https://")
    """
    if not url:
        return False, "URL cannot be empty"

    if not url.startswith(("http://", "https://")):
        return False, "URL must start with http:// or https://"

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, "Invalid URL format"
    except Exception:
        return False, "Invalid URL format"

    return True, None


def get_filename_from_url(url: str, output_format: str) -> str:
    """
    Generate a safe filename from a URL with appropriate extension.
    
    Args:
        url: The source URL
        output_format: The output format for extension (markdown, json, xml)
        
    Returns:
        A safe filename with appropriate extension
        
    Examples:
        >>> get_filename_from_url("https://example.com/path/to/page", "markdown")
        'path_to_page.md'
        >>> get_filename_from_url("https://example.com/", "json")
        'index.json'
    """
    # Extract path from URL
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip("/").split("/")

    # Handle empty paths
    if not path_parts or path_parts[0] == "":
        filename = "index"
    else:
        filename = "_".join(path_parts)

    # Remove or replace invalid characters for filesystem safety
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)

    # Ensure correct file extension based on output format
    output_ext = ".md" if output_format == "markdown" else f".{output_format}"
    if not filename.endswith(output_ext):
        # Remove any existing extension and add the correct one
        if "." in filename:
            filename = filename.rsplit(".", 1)[0] + output_ext
        else:
            filename += output_ext

    return filename


def extract_base_url(url: str) -> str:
    """
    Extract the base URL (scheme + netloc) from a full URL.
    
    Args:
        url: Full URL string
        
    Returns:
        Base URL string (scheme://netloc)
        
    Examples:
        >>> extract_base_url("https://example.com/path/page?query=1")
        'https://example.com'
    """
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def normalize_url(url: str) -> str:
    """
    Normalize a URL by removing trailing slashes and fragments.
    
    Args:
        url: URL string to normalize
        
    Returns:
        Normalized URL string
        
    Examples:
        >>> normalize_url("https://example.com/path/")
        'https://example.com/path'
        >>> normalize_url("https://example.com/page#section")
        'https://example.com/page'
    """
    parsed = urlparse(url)
    # Remove fragment and normalize path
    normalized_path = parsed.path.rstrip("/") if parsed.path != "/" else parsed.path
    
    # Reconstruct URL without fragment
    result = f"{parsed.scheme}://{parsed.netloc}{normalized_path}"
    if parsed.query:
        result += f"?{parsed.query}"
    
    return result


def get_domain_from_url(url: str) -> str:
    """
    Extract just the domain (netloc) from a URL.
    
    Args:
        url: URL string
        
    Returns:
        Domain string
        
    Examples:
        >>> get_domain_from_url("https://sub.example.com/path")
        'sub.example.com'
    """
    return urlparse(url).netloc


def is_absolute_url(url: str) -> bool:
    """
    Check if a URL is absolute (has scheme).
    
    Args:
        url: URL string to check
        
    Returns:
        True if URL is absolute, False otherwise
        
    Examples:
        >>> is_absolute_url("https://example.com/path")
        True
        >>> is_absolute_url("/relative/path")
        False
    """
    return url.startswith(("http://", "https://"))


def parse_url_safe(url: str) -> Optional[ParseResult]:
    """
    Safely parse a URL, returning None if parsing fails.
    
    Args:
        url: URL string to parse
        
    Returns:
        ParseResult object or None if parsing fails
    """
    try:
        return urlparse(url)
    except Exception:
        return None


def get_url_path_parts(url: str) -> list[str]:
    """
    Get the path parts of a URL as a list.
    
    Args:
        url: URL string
        
    Returns:
        List of path parts (excluding empty parts)
        
    Examples:
        >>> get_url_path_parts("https://example.com/path/to/page")
        ['path', 'to', 'page']
    """
    parsed = urlparse(url)
    return [part for part in parsed.path.strip("/").split("/") if part]


def sanitize_filename_part(part: str) -> str:
    """
    Sanitize a string to be safe for use in filenames.
    
    Args:
        part: String to sanitize
        
    Returns:
        Sanitized string safe for filenames
        
    Examples:
        >>> sanitize_filename_part('hello/world:test')
        'hello_world_test'
    """
    return re.sub(r'[\\/*?:"<>|]', "_", part)