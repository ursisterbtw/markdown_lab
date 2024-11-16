import argparse
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarkdownScraper:
    def __init__(self):
        self.session = requests.Session()

    def scrape_website(self, url):
        logging.info(f"Attempting to scrape the website: {url}")
        try:
            response = self.session.get(url)
            response.raise_for_status()
            logging.info("Successfully retrieved the website content.")
            return response.text
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logging.error(f"An error occurred: {err}")
            raise

    def convert_to_markdown(self, html_content):
        logging.info("Converting HTML content to Markdown.")
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.title.string if soup.title else 'No Title'
        headers = [f"## {header.get_text()}" for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        paragraphs = [p.get_text() for p in soup.find_all('p')]
        links = [f"[{a.get_text()}]({a['href']})" for a in soup.find_all('a', href=True)]
        images = [f"![{img.get('alt', 'image')}]({img['src']})" for img in soup.find_all('img', src=True)]
        lists = []
        for ul in soup.find_all('ul'):
            lists.append("\n".join([f"- {li.get_text()}" for li in ul.find_all('li')]))
        markdown_content = f"# {title}\n\n" + "\n\n".join(headers + paragraphs + links + images + lists)
        logging.info("Conversion to Markdown completed.")
        return markdown_content

    def save_markdown(self, markdown_content, output_file):
        with open(output_file, 'w') as f:
            f.write(markdown_content)
        logging.info(f"Markdown file '{output_file}' has been created successfully.")

def main(url, output_file):
    scraper = MarkdownScraper()
    try:
        html_content = scraper.scrape_website(url)
        markdown_content = scraper.convert_to_markdown(html_content)
        scraper.save_markdown(markdown_content, output_file)
    except Exception as e:
        logging.error(f"An error occurred during the process: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape a website and convert it to Markdown.')
    parser.add_argument('url', type=str, help='The URL of the website to scrape')
    parser.add_argument('-o', '--output', type=str, default='output.md', help='The output Markdown file name')
    args = parser.parse_args()
    main(args.url, args.output)

# ---------------- PYTEST INTEGRATION ----------------

import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def scraper():
    return MarkdownScraper()

@patch('main.requests.Session.get')
def test_scrape_website_success(mock_get, scraper):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '<html><head><title>Test</title></head><body></body></html>'
    mock_get.return_value = mock_response

    result = scraper.scrape_website("http://example.com")
    assert result == '<html><head><title>Test</title></head><body></body></html>'

@patch('main.requests.Session.get')
def test_scrape_website_http_error(mock_get, scraper):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mock_get.return_value = mock_response

    with pytest.raises(requests.exceptions.HTTPError):
        scraper.scrape_website("http://example.com")

@patch('main.requests.Session.get')
def test_scrape_website_general_error(mock_get, scraper):
    mock_get.side_effect = Exception("Connection error")

    with pytest.raises(Exception) as exc_info:
        scraper.scrape_website("http://example.com")
    assert str(exc_info.value) == "Connection error"

def test_convert_to_markdown(scraper):
    html_content = """<html><head><title>Test</title></head>
    <body>
    <h1>Header 1</h1>
    <p>Paragraph 1</p>
    <a href='http://example.com'>Link</a>
    <img src='image.jpg' alt='Test Image'>
    <ul><li>Item 1</li><li>Item 2</li></ul>
    </body></html>"""

    expected_markdown = """# Test

## Header 1

Paragraph 1

[Link](http://example.com)

![Test Image](image.jpg)

- Item 1
- Item 2"""

    result = scraper.convert_to_markdown(html_content)
    assert result.strip() == expected_markdown.strip()

@patch('builtins.open', new_callable=MagicMock)
def test_save_markdown(mock_open, scraper):
    markdown_content = "# Test Markdown"
    output_file = "test_output.md"

    scraper.save_markdown(markdown_content, output_file)

    mock_open.assert_called_once_with(output_file, 'w')
    mock_open.return_value.write.assert_called_once_with(markdown_content)
