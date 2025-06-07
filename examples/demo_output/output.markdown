# Output Format Demo

# Markdown Lab Output Formats

## Benefits of Multiple Formats

This demo shows the three output formats supported by markdown_lab:

Having multiple output formats provides several advantages:

Format conversion is performed efficiently using Rust implementations.

- Markdown - Human-readable plain text format
- JSON - Structured data format for programmatic usage
- XML - Markup format for document interchange

1. Flexibility for different use cases
2. Integration with various systems
3. Easier data processing and transformation

```
# Sample Python code
from markdown_lab.markdown_lab_rs import convert_html_to_format

result = convert_html_to_format(html_content, url, "json")
```

```
# Sample Python code
from markdown_lab.markdown_lab_rs import convert_html_to_format

result = convert_html_to_format(html_content, url, "json")
```

> Format conversion is performed efficiently using Rust implementations.