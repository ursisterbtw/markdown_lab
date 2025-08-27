#!/usr/bin/env python3
"""
Simple demo example of using markdown_lab to convert HTML to markdown.
"""

from markdown_lab.markdown_lab_rs import convert_html_to_markdown

html = """
<html>
<head>
    <title>Hello Markdown Lab</title>
</head>
<body>
    <h1>Hello from Markdown Lab!</h1>
    <p>This is a simple example of converting HTML to Markdown.</p>
    <ul>
        <li>Simple to use</li>
        <li>Fast performance with Rust</li>
        <li>Multiple output formats</li>
    </ul>
</body>
</html>
"""

markdown = convert_html_to_markdown(html)
