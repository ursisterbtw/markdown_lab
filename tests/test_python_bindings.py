import pytest
import markdown_lab_rs

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
    html = markdown_lab_rs.render_js_page(url)
    assert isinstance(html, str)
    assert len(html) > 0

def test_error_handling():
    with pytest.raises(RuntimeError):
        markdown_lab_rs.convert_html_to_markdown(None, "https://example.com")

    with pytest.raises(RuntimeError):
        markdown_lab_rs.chunk_markdown(None, 500, 50)

    with pytest.raises(RuntimeError):
        markdown_lab_rs.render_js_page(None)
