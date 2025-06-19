from unittest.mock import MagicMock, patch

import pytest

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.converter import Converter


@pytest.fixture
def converter():
    config = MarkdownLabConfig(cache_enabled=False)
    return Converter(config)


@pytest.mark.benchmark(group="convert_url")
@patch("markdown_lab.network.client.requests.Session.request")
def test_convert_url_benchmark(benchmark, mock_request, converter):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    url = "http://example.com"
    benchmark(converter.convert_url, url)


@pytest.mark.benchmark(group="convert_html")
def test_convert_html_benchmark(benchmark, converter):
    html_content = "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"
    benchmark(
        converter.convert_html,
        html_content,
        "http://example.com",
        output_format="markdown",
    )


@pytest.mark.benchmark(group="convert_html_to_json")
def test_convert_html_to_json_benchmark(benchmark, converter):
    html_content = "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"
    benchmark(
        converter.convert_html, html_content, "http://example.com", output_format="json"
    )


@pytest.mark.benchmark(group="convert_html_to_xml")
def test_convert_html_to_xml_benchmark(benchmark, converter):
    html_content = "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"
    benchmark(
        converter.convert_html, html_content, "http://example.com", output_format="xml"
    )


@pytest.mark.benchmark(group="convert_url_list")
@patch("markdown_lab.network.client.requests.Session.request")
def test_convert_url_list_benchmark(benchmark, mock_request, converter, tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    urls = ["http://example1.com", "http://example2.com", "http://example3.com"]

    def convert_multiple_urls():
        return converter.convert_url_list(
            urls=urls,
            output_dir=str(tmp_path),
            output_format="markdown",
            save_chunks=False,
        )

    benchmark(convert_multiple_urls)


@pytest.mark.benchmark(group="large_html_conversion")
def test_large_html_conversion_benchmark(benchmark, converter):
    # Generate large HTML content for performance testing
    large_html = "<html><head><title>Large Document</title></head><body>"
    for i in range(1000):
        large_html += f"<div><h2>Section {i}</h2><p>This is paragraph {i} with some content to test performance.</p></div>"
    large_html += "</body></html>"

    benchmark(
        converter.convert_html,
        large_html,
        "http://example.com",
        output_format="markdown",
    )


@pytest.mark.benchmark(group="cache_performance")
def test_cache_performance_benchmark(benchmark, tmp_path):
    config = MarkdownLabConfig(cache_enabled=True, cache_ttl=3600)
    converter = Converter(config)

    html_content = "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"

    with patch("markdown_lab.network.client.requests.Session.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        url = "http://example.com"

        def convert_with_cache():
            # First call - cache miss
            converter.convert_url(url)
            # Second call - cache hit
            return converter.convert_url(url)

        benchmark(convert_with_cache)
