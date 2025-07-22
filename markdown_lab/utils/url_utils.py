"""
URL utilities for markdown_lab.

Provides centralized URL processing functionality including validation,
filename generation, resolution, and normalization.
"""

import hashlib
import re
from typing import Optional, Tuple
from urllib.parse import ParseResult, urlparse


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
    Truncates or hashes long filenames to prevent issues with filesystem limits.
    
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
    # Map output_format to file extension
    ext_map = {
        "markdown": ".md",
        "json": ".json",
        "xml": ".xml"
    }
    ext = ext_map.get(output_format.lower(), f".{output_format}")

    # Parse the URL and build a filename
    parsed = urlparse(url)
    # Use netloc and path, replace unsafe chars
    safe_path = (parsed.netloc + parsed.path).replace("/", "_").replace("\\", "_")
    if not safe_path:
        safe_path = "file"

    # Remove query and fragment
    safe_path = safe_path.split("?", 1)[0].split("#", 1)[0]

    # Remove or replace invalid characters for filesystem safety
    safe_path = re.sub(r'[\\/*?:"<>|]', "_", safe_path)

    # Limit filename length (255 is a common max, but leave room for extension and hash)
    max_filename_length = 200
    filename = safe_path
    if len(filename) > max_filename_length:
        # Hash the full path for uniqueness
        hash_suffix = hashlib.sha1(safe_path.encode("utf-8")).hexdigest()[:10]
        filename = f"{safe_path[:max_filename_length]}_{hash_suffix}"

    # Ensure total length with extension does not exceed 255
    max_total_length = 255 - len(ext)
    if len(filename) > max_total_length:
        filename = filename[:max_total_length]

    return f"{filename}{ext}"


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

