# Markdown Lab 🔄📝

A (soon to be) powerful and modular web scraper that converts web content into well-structured Markdown files.
[![Python CI](https://github.com/ursisterbtw/markdown_lab/actions/workflows/CI.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/CI.yml)
## Features

- 🌐 Scrapes any accessible website
- 📝 Converts HTML to clean Markdown format
- 🔄 Handles various HTML elements:
  - Headers (h1-h6)
  - Paragraphs
  - Links
  - Images
  - Lists
- 📋 Preserves document structure
- 🪵 Comprehensive logging
- ✅ Robust error handling

## Installation

```bash
git clone https://github.com/ursisterbtw/markdown_lab.git
cd markdown_lab
pip install -r requirements.txt
```

## Usage

### From The Command Line

```python
python main.py <url> -o <output_file>
```

Example:

```python
python main.py https://www.example.com -o output.md
```

### As a Module

```python
from main import MarkdownScraper
scraper = MarkdownScraper()
html_content = scraper.scrape_website("https://example.com")
markdown_content = scraper.convert_to_markdown(html_content)
scraper.save_markdown(markdown_content, "output.md")
```

## Testing

The project includes comprehensive unit tests. To run them:

```bash
pytest
```

## Dependencies

- requests: Web scraping
- beautifulsoup4: HTML parsing
- pytest: Testing framework
- argparse: CLI argument parsing

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE file](LICENSE) for details.

## Acknowledgments

- BeautifulSoup4 for excellent HTML parsing capabilities
- Requests library for simplified HTTP handling
- Python community for continuous inspiration 🐍

## Roadmap

- [ ] Add support for more HTML elements
- [ ] Implement custom markdown templates
- [ ] Add concurrent scraping for multiple URLs
- [ ] Include CSS selector support
- [ ] Add configuration file support

## Author

🐍🦀 ursister

---
