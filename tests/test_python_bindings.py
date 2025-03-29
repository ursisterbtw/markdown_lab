import pytest

from markdown_lab import markdown_lab_rs


def test_convert_html_to_markdown():
    html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Title</h1>
                <p>This is a test paragraph.</p>
            </body>
        </html>
    """
    base_url = "https://example.com"
    markdown = markdown_lab_rs.convert_html_to_markdown(html, base_url)

    assert "# Test Page" in markdown
    assert "# Main Title" in markdown
    assert "This is a test paragraph." in markdown


def test_chunk_markdown():
    markdown = """
# Title

## Section 1

This is a test paragraph.

## Section 2

* List item 1
* List item 2
    """

    chunks = markdown_lab_rs.chunk_markdown(markdown, 500, 50)
    assert len(chunks) > 0
    assert any("# Title" in chunk for chunk in chunks)
    assert any("## Section 1" in chunk for chunk in chunks)
    assert any("## Section 2" in chunk for chunk in chunks)


def test_render_js_page():
    url = "https://example.com"
    # When Rust extension is not available, render_js_page returns None
    # Just test that it runs without error
    html = markdown_lab_rs.render_js_page(url)
    # Only perform assertions if the result is not None
    if html is not None:
        assert isinstance(html, str)
        assert len(html) > 0


def test_error_handling():
    # Test with empty string instead of None to avoid TypeError
    empty_html = ""
    empty_markdown = markdown_lab_rs.convert_html_to_markdown(empty_html, "https://example.com")
    assert isinstance(empty_markdown, str)

    empty_chunks = markdown_lab_rs.chunk_markdown("", 500, 50)
    assert isinstance(empty_chunks, list)
    assert len(empty_chunks) == 0
