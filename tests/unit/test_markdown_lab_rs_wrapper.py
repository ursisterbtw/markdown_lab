import pytest

from markdown_lab import markdown_lab_rs as wrapper


def test_convert_html_to_format_python_fallback_markdown():
    # Ensure wrapper can handle markdown path even if Rust not available
    html = "<html><head><title>T</title></head><body><h1>H1</h1></body></html>"
    out = wrapper.convert_html_to_format(html, "https://example.com", "markdown")
    assert isinstance(out, str)
    assert "# T" in out or "# H1" in out


def test_convert_html_to_format_accepts_enum_and_str():
    from markdown_lab.markdown_lab_rs import OutputFormat as LocalFmt

    html = "<html><head><title>T</title></head><body><h1>H1</h1></body></html>"
    out1 = wrapper.convert_html_to_format(
        html, "https://example.com", LocalFmt.MARKDOWN
    )
    out2 = wrapper.convert_html_to_format(html, "https://example.com", "markdown")
    assert out1 and out2
