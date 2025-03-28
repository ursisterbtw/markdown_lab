#!/usr/bin/env python
"""
Demo script to showcase markdown_lab's multiple output formats.
"""

from pathlib import Path

from markdown_lab_rs import OutputFormat, convert_html

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
from markdown_lab_rs import convert_html, OutputFormat

result = convert_html(html_content, url, OutputFormat.JSON)
    </code></pre>
</body>
</html>
"""


def main():
    """Demo all three output formats."""
    base_url = "http://example.com"
    output_dir = Path("demo_output")
    output_dir.mkdir(exist_ok=True)

    # Convert to all three formats
    formats = {
        "markdown": OutputFormat.MARKDOWN,
        "json": OutputFormat.JSON,
        "xml": OutputFormat.XML,
    }

    for name, format_enum in formats.items():
        output_file = output_dir / f"demo.{name}"
        content = convert_html(SAMPLE_HTML, base_url, format_enum)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Generated {name} output in {output_file}")

        # Show a preview of each format
        preview = content.split("\n")[:5]
        print(f"\n{name.upper()} PREVIEW:")
        print("-" * 40)
        print("\n".join(preview))
        print("-" * 40)


if __name__ == "__main__":
    main()
