# Markdown Lab 🔄📝

A powerful and modular web scraper that converts web content into well-structured Markdown files with RAG-ready chunking capabilities.

[![Python CI](https://github.com/ursisterbtw/markdown_lab/actions/workflows/CI.yml/badge.svg)](https://github.com/ursisterbtw/markdown_lab/actions/workflows/CI.yml)

## Features

- 🌐 Scrapes any accessible website with robust error handling and rate limiting
- 📝 Converts HTML to clean Markdown format
- 🧩 Implements intelligent chunking for RAG (Retrieval-Augmented Generation) systems
- 🔄 Handles various HTML elements:
  - Headers (h1-h6)
  - Paragraphs
  - Links with resolved relative URLs
  - Images with resolved relative URLs
  - Ordered and unordered lists
  - Blockquotes
  - Code blocks
- 📋 Preserves document structure
- 🪵 Comprehensive logging
- ✅ Robust error handling with exponential backoff
- 🏎️ Performance optimizations and best practices

## Installation

```bash
git clone https://github.com/ursisterbtw/markdown_lab.git
cd markdown_lab
pip install -r requirements.txt
```

## Usage

### Basic Markdown Conversion

```bash
python main.py https://www.example.com -o output.md
```

### With RAG Chunking

```bash
python main.py https://www.example.com -o output.md --save-chunks --chunk-dir my_chunks
```

### Advanced Options

```bash
python main.py https://www.example.com -o output.md \
    --save-chunks \
    --chunk-dir my_chunks \
    --chunk-format jsonl \
    --chunk-size 1500 \
    --chunk-overlap 300 \
    --requests-per-second 2.0
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `url` | The URL to scrape | (required) |
| `-o, --output` | Output markdown file | `output.md` |
| `--save-chunks` | Save content chunks for RAG | False |
| `--chunk-dir` | Directory to save chunks | `chunks` |
| `--chunk-format` | Format for chunks (`json`, `jsonl`) | `jsonl` |
| `--chunk-size` | Maximum chunk size (chars) | 1000 |
| `--chunk-overlap` | Overlap between chunks (chars) | 200 |
| `--requests-per-second` | Rate limit for requests | 1.0 |

### As a Module

#### Basic Scraping and Conversion

```python
from main import MarkdownScraper

scraper = MarkdownScraper()
html_content = scraper.scrape_website("https://example.com")
markdown_content = scraper.convert_to_markdown(html_content, "https://example.com")
scraper.save_markdown(markdown_content, "output.md")
```

#### With RAG Chunking

```python
from main import MarkdownScraper

scraper = MarkdownScraper(chunk_size=1500, chunk_overlap=300)
html_content = scraper.scrape_website("https://example.com")
markdown_content = scraper.convert_to_markdown(html_content, "https://example.com")
scraper.save_markdown(markdown_content, "output.md")

# Create and save chunks for RAG
chunks = scraper.create_chunks(markdown_content, "https://example.com")
scraper.save_chunks(chunks, "my_chunks", "jsonl")
```

#### Using the Chunking Utils Directly

```python
from chunk_utils import create_semantic_chunks, ContentChunker

# Create chunks from any text content
chunks = create_semantic_chunks(
    content="# My Document\n\nThis is some content.",
    source_url="https://example.com",
    chunk_size=1000,
    chunk_overlap=200
)

# Save chunks to disk
chunker = ContentChunker()
chunker.save_chunks(chunks, "my_chunks", "jsonl")
```

## RAG Chunking Capabilities

The library implements intelligent chunking designed specifically for RAG (Retrieval-Augmented Generation) systems:

- **Semantic Chunking**: Preserves the semantic structure of documents by chunking based on headers
- **Content-Aware**: Large sections are split into overlapping chunks for better context preservation
- **Metadata-Rich**: Each chunk contains detailed metadata for better retrieval
- **Multiple Formats**: Save chunks as individual JSON files or as a single JSONL file
- **Customizable**: Control chunk size and overlap to balance between precision and context

## Testing

The project includes comprehensive unit tests. To run them:

```bash
pytest
```

## Dependencies

- requests: Web scraping and HTTP requests
- beautifulsoup4: HTML parsing
- pytest: Testing framework
- typing-extensions: Additional type checking support
- pathlib: Object-oriented filesystem paths
- python-dateutil: Powerful extensions to the standard datetime module

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE file](LICENSE) for details.

## Project Structure

- `main.py`: The main scraper implementation
- `chunk_utils.py`: Utilities for chunking text for RAG
- `throttle.py`: Rate limiting for web requests
- `test_*.py`: Unit tests

## Roadmap

- [x] Add support for more HTML elements
- [x] Implement chunking for RAG
- [ ] Add support for JavaScript-rendered pages
- [ ] Implement custom markdown templates
- [ ] Add concurrent scraping for multiple URLs
- [ ] Include CSS selector support
- [ ] Add configuration file support

## Author

🐍🦀 ursister

---
