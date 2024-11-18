from main import MarkdownScraper
import pytest
import requests
from unittest.mock import patch, MagicMock


@pytest.fixture
def scraper():
    return MarkdownScraper()


@patch("main.requests.Session.get")
def test_scrape_website_success(mock_get, scraper):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Test</title></head><body></body></html>"
    mock_get.return_value = mock_response

    result = scraper.scrape_website("http://example.com")
    assert result == "<html><head><title>Test</title></head><body></body></html>"


@patch("main.requests.Session.get")
def test_scrape_website_http_error(mock_get, scraper):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mock_get.return_value = mock_response

    with pytest.raises(requests.exceptions.HTTPError):
        scraper.scrape_website("http://example.com")


@patch("main.requests.Session.get")
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


@patch("builtins.open")
def test_save_markdown(mock_open):
    # setup the mock file object
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    scraper = MarkdownScraper()
    markdown_content = "# Test Markdown"
    output_file = "test_output.md"

    # call the method under test
    scraper.save_markdown(markdown_content, output_file)

    # assert that open was called with the correct file name and mode
    mock_open.assert_called_once_with(output_file, "w")

    # assert write was called with the content
    mock_file.write.assert_called_once_with(markdown_content)
