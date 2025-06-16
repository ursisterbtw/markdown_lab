#!/usr/bin/env python
"""
Demo script to showcase markdown_lab's multiple output formats.
"""

from pathlib import Path

from markdown_lab.markdown_lab_rs import convert_html_to_format

# HTML sample for conversion testing
SAMPLE_HTML = """
<html>
<head>
    <title>Output Format Demo</title>
</head>
<body>
    <h1>Markdown Lab Output Formats</h1>
    <p>This demo shows the three output formats supported by markdown_lab:</p>
    <ul>
        <li>Markdown - Human-readable plain text format</li>
        <li>JSON - Structured data format for programmatic usage</li>
        <li>XML - Markup format for document interchange</li>
    </ul>

    <h2>Benefits of Multiple Formats</h2>
    <p>Having multiple output formats provides several advantages:</p>
    <ol>
        <li>Flexibility for different use cases</li>
        <li>Integration with various systems</li>
        <li>Easier data processing and transformation</li>
    </ol>

    <blockquote>
        <p>Format conversion is performed efficiently using Rust implementations.</p>
    </blockquote>

    <pre><code>
# Sample Python code
from markdown_lab.markdown_lab_rs import convert_html_to_format

result = convert_html_to_format(html_content, url, "json")
    </code></pre>
</body>
</html>
"""


def main():
    """
    Converts a sample HTML string to Markdown, JSON, and XML formats and writes each result to a file in the output directory.

    Creates the output directory if it does not exist. For each format, the converted content is saved as `output.<format>` in the directory.
    """
    base_url = "http://example.com"
    output_dir = Path("examples/demo_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert to all three formats
    formats = ["markdown", "json", "xml"]

    for format_name in formats:
        output_file = output_dir / f"output.{format_name}"
        content = convert_html_to_format(SAMPLE_HTML, base_url, format_name)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Show a preview of each format
        content.split("\n")[:5]


if __name__ == "__main__":
    main()
