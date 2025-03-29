#!/usr/bin/env python
"""
Simple "Hello World" example for the markdown_lab library.
"""

from markdown_lab.main import MarkdownScraper


def main():
    """Demonstrate basic usage of the markdown_lab library."""
    print("Hello from markdown-lab!")

    # Create a scraper instance
    scraper = MarkdownScraper()

    # Convert a simple HTML string to markdown
    html = "<h1>Hello World</h1><p>This is a simple example.</p>"
    markdown = scraper.convert_to_markdown(html)

    print("\nConverted Markdown:")
    print("-------------------")
    print(markdown)


if __name__ == "__main__":
    main()
