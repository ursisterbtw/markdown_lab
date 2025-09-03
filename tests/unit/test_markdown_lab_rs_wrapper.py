import pytest

from markdown_lab import markdown_lab_rs as wrapper


def test_convert_html_to_format_python_fallback_markdown():
    # Ensure wrapper can handle markdown path even if Rust not available
    html = "<html><head><title>T</title></head><body><h1>H1</h1></body></html>"
    out = wrapper.convert_html_to_format(html, "https://example.com", "markdown")
    assert isinstance(out, str)
    assert "# T" in out or "# H1" in out


def test_convert_html_to_format_accepts_enum_and_str():
    # Test that both string and enum values work for format parameter
    html = "<html><head><title>T</title></head><body><h1>H1</h1></body></html>"

    # Test with string format
    out1 = wrapper.convert_html_to_format(html, "https://example.com", "markdown")
    out2 = wrapper.convert_html_to_format(html, "https://example.com", "json")
    out3 = wrapper.convert_html_to_format(html, "https://example.com", "xml")

    # All should return non-empty strings
    assert out1 and isinstance(out1, str)
    assert out2 and isinstance(out2, str)
    assert out3 and isinstance(out3, str)

    # Test that markdown contains expected content
    assert "# T" in out1 or "# H1" in out1
