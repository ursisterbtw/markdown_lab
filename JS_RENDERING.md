# JavaScript Rendering Support

This document outlines how to use the JavaScript rendering capabilities in Markdown Lab to scrape JavaScript-heavy websites.

## Overview

Many modern websites rely heavily on JavaScript to load and render content dynamically. Traditional scraping methods that only fetch the initial HTML won't capture this dynamically generated content. Markdown Lab now includes support for rendering JavaScript-enabled pages before scraping.

## Requirements

To use the JavaScript rendering feature:

1. **Rust Extension**: The JavaScript rendering feature requires the Rust extension to be built and installed.

2. **Building the Rust Extension**:
   ```bash
   # Install maturin (build tool for Rust Python extensions)
   pip install maturin

   # Build and install the extension
   maturin develop
   ```

## Usage

### Command Line

```bash
# Basic usage with JS rendering
python main.py https://www.example.com -o output.md --use-js-rendering

# With custom wait time (in milliseconds)
python main.py https://www.example.com -o output.md --use-js-rendering --js-wait-time 5000

# With sitemap discovery and JS rendering
python main.py https://www.example.com -o output_dir --use-sitemap --use-js-rendering
```

### As a Module

```python
from main import MarkdownScraper

scraper = MarkdownScraper(js_rendering=True, js_wait_time=3000)
html_content = scraper.scrape_website("https://example.com")
markdown_content = scraper.convert_to_markdown(html_content, "https://example.com")
scraper.save_markdown(markdown_content, "output.md")
```

## How It Works

1. The scraper first attempts to fetch the page normally.
2. It analyzes the content to determine if JavaScript rendering is needed.
3. If needed (and enabled), it uses a headless browser approach to:
   - Load the page in a controlled browser environment
   - Wait for the specified time for JavaScript to execute
   - Extract the fully rendered HTML content
   - Process the rendered content through the normal Markdown conversion pipeline

## Performance Considerations

JavaScript rendering is significantly more resource-intensive than standard scraping:

- It requires more CPU and memory resources
- Pages take longer to process (seconds instead of milliseconds)
- There's a higher potential for failures on some websites

Use JS rendering selectively on pages that require it, rather than enabling it globally.

## Limitations

- Some websites employ anti-bot measures that might detect and block automated browsers
- Very complex JavaScript applications may not render completely
- Infinite scrolling pages will only capture content loaded during the wait time

## Troubleshooting

If you encounter issues with JavaScript rendering:

1. **Increase wait time**: Some pages need more time to fully load (try 5000-10000ms)
2. **Check console output**: Look for warnings or errors in the logs
3. **Verify site accessibility**: Ensure the site doesn't block automated browsers
4. **Consider using a proxy**: Some sites might block requests based on IP address

## Advanced Configuration

For more complex scenarios, you can modify the `js_renderer.rs` file in the Rust extension to customize the browser behavior and configuration.
