import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.converter import Converter


@pytest.fixture
def converter():
    config = MarkdownLabConfig(cache_enabled=False)
    return Converter(config)


@pytest.fixture
def test_html():
    return "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"


@patch("markdown_lab.network.client.requests.Session.request")
def test_convert_url_success(mock_request, converter, test_html):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = test_html
    mock_response.elapsed.total_seconds.return_value = 0.1
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    result = converter.convert_url("http://example.com")
    assert "# Header" in result
    assert "Paragraph" in result


@patch("markdown_lab.network.client.requests.Session.request")
def test_convert_url_http_error(mock_request, converter):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )
    mock_request.return_value = mock_response

    with pytest.raises(Exception):
        converter.convert_url("http://example.com")


def test_convert_html_to_markdown(converter, test_html):
    converted_content, markdown_content = converter.convert_html(
        test_html, "http://example.com", output_format="markdown"
    )
    assert "# Header" in converted_content
    assert "Paragraph" in converted_content


def test_convert_html_to_json(converter, test_html):
    converted_content, markdown_content = converter.convert_html(
        test_html, "http://example.com", output_format="json"
    )
    assert '"title": "Test"' in converted_content
    assert '"content"' in converted_content


def test_convert_html_to_xml(converter, test_html):
    converted_content, markdown_content = converter.convert_html(
        test_html, "http://example.com", output_format="xml"
    )
    assert "<title>Test</title>" in converted_content
    assert "<content>" in converted_content


def test_convert_url_list(converter):
    """Test URL list conversion functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        urls = ["http://example1.com", "http://example2.com"]

        with patch(
            "markdown_lab.network.client.requests.Session.request"
        ) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body><h1>Test</h1></body></html>"
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response

            results = converter.convert_url_list(
                urls=urls,
                output_dir=temp_dir,
                output_format="markdown",
                save_chunks=False,
            )

            assert len(results) == 2
            assert results == urls

            # Check that files were created
            output_path = Path(temp_dir)
            files = list(output_path.glob("*.md"))
            assert len(files) == 2


def test_convert_format_validation(converter, test_html):
    """Test that invalid formats raise appropriate errors."""
    with pytest.raises(ValueError):
        converter.convert_html(
            test_html, "http://example.com", output_format="invalid_format"
        )


def test_converter_with_cache_enabled():
    """Test converter with caching enabled."""
    config = MarkdownLabConfig(cache_enabled=True, cache_ttl=3600)
    converter = Converter(config)

    assert converter.client.cache is not None


def test_converter_with_cache_disabled():
    """Test converter with caching disabled."""
    config = MarkdownLabConfig(cache_enabled=False)
    converter = Converter(config)

    # The CachedHttpClient should have cache=None when disabled
    assert converter.client.cache is None


@patch("markdown_lab.network.client.requests.Session.request")
def test_convert_sitemap_functionality(mock_request, converter):
    """Test sitemap conversion functionality."""
    # Mock sitemap XML response
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>http://example.com/page1</loc>
            <priority>0.8</priority>
        </url>
        <url>
            <loc>http://example.com/page2</loc>
            <priority>0.6</priority>
        </url>
    </urlset>"""

    # Mock HTML response
    html_response = "<html><body><h1>Test Page</h1></body></html>"

    def mock_response_side_effect(method, url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None

        if "sitemap" in url:
            mock_resp.text = sitemap_xml
        else:
            mock_resp.text = html_response

        return mock_resp

    mock_request.side_effect = mock_response_side_effect

    with tempfile.TemporaryDirectory() as temp_dir:
        results = converter.convert_sitemap(
            base_url="http://example.com",
            output_dir=temp_dir,
            output_format="markdown",
            min_priority=0.5,
            limit=2,
        )

        assert len(results) == 2

        # Check that files were created
        output_path = Path(temp_dir)
        files = list(output_path.glob("*.md"))
        assert len(files) == 2


def test_error_handling_with_invalid_url(converter):
    """Test error handling with invalid URLs."""
    with pytest.raises(Exception):
        converter.convert_url("not-a-valid-url")


def test_chunking_functionality(converter, test_html):
    """Test content chunking functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        chunk_dir = Path(temp_dir) / "chunks"

        with patch(
            "markdown_lab.network.client.requests.Session.request"
        ) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = test_html
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response

            results = converter.convert_url_list(
                urls=["http://example.com"],
                output_dir=temp_dir,
                output_format="markdown",
                save_chunks=True,
                chunk_dir=str(chunk_dir),
                chunk_format="json",
            )

            assert len(results) == 1
            assert chunk_dir.exists()

            # Check that chunk files were created
            chunk_files = list(chunk_dir.glob("*.json"))
            assert len(chunk_files) >= 1
