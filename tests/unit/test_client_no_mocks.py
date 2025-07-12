"""Test HTTP clients without mocking - using real test server."""

import pytest
import requests

from markdown_lab.core.client import HttpClient as CoreHttpClient
from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.network.client import (
    CachedHttpClient,
)
from markdown_lab.network.client import HttpClient as NetworkHttpClient
from tests.integration.test_http_server import TestHTTPServer


@pytest.fixture
def test_server():
    """Provide a real HTTP test server."""
    server = TestHTTPServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def core_client():
    """Fixture for CoreHttpClient instance."""
    return CoreHttpClient()


@pytest.fixture
def network_client():
    """Fixture for NetworkHttpClient instance."""
    config = MarkdownLabConfig()
    return NetworkHttpClient(config)


@pytest.fixture
def cached_client():
    """Fixture for CachedHttpClient instance."""
    config = MarkdownLabConfig()
    return CachedHttpClient(config)


class TestCoreClientWithRealServer:
    """Test CoreHttpClient with real HTTP server."""

    def test_get_homepage(self, core_client, test_server):
        """Test GET request to homepage."""
        result = core_client.get(f"{test_server.url}/")
        assert result is not None
        assert isinstance(result, str)
        assert "markdown_lab" in result
        assert "Fast Markdown Conversion Library" in result

        # Verify request was received
        requests = test_server.get_requests()
        assert len(requests) == 1
        assert requests[0]["method"] == "GET"
        assert requests[0]["path"] == "/"

    def test_get_documentation_page(self, core_client, test_server):
        """Test GET request to documentation page."""
        result = core_client.get(f"{test_server.url}/docs")
        assert "HttpClient Class" in result
        assert "API Reference" in result
        assert "config: MarkdownLabConfig" in result

    def test_get_with_skip_cache(self, core_client, test_server):
        """Test GET request with cache skipping."""
        # First request
        result1 = core_client.get(f"{test_server.url}/blog")
        assert "Building Fast Web Scrapers" in result1

        # Second request with skip_cache
        test_server.clear_requests()
        result2 = core_client.get(f"{test_server.url}/blog", skip_cache=True)
        assert result1 == result2

        # Verify request was made despite potential caching
        requests = test_server.get_requests()
        assert len(requests) == 1

    def test_error_handling(self, core_client, test_server):
        """Test handling of HTTP errors."""
        with pytest.raises(requests.exceptions.HTTPError):
            core_client.get(f"{test_server.url}/error?code=404")

        with pytest.raises(requests.exceptions.HTTPError):
            core_client.get(f"{test_server.url}/error?code=500")


class TestNetworkClientWithRealServer:
    """Test NetworkHttpClient with real HTTP server."""

    def test_get_json_api(self, network_client, test_server):
        """Test GET request to JSON API endpoint."""
        result = network_client.get(f"{test_server.url}/api/data")
        assert result is not None
        # Result should be JSON string
        assert '"status": "success"' in result
        assert '"items"' in result

    def test_head_request(self, network_client, test_server):
        """Test HEAD request."""
        response = network_client.head(f"{test_server.url}/")
        assert response is not None
        assert hasattr(response, "headers")
        assert "Content-Type" in response.headers

        # Verify only HEAD request was made
        requests = test_server.get_requests()
        assert requests[-1]["method"] == "HEAD"

    def test_get_many_urls(self, network_client, test_server):
        """Test fetching multiple URLs."""
        urls = [
            f"{test_server.url}/",
            f"{test_server.url}/docs",
            f"{test_server.url}/blog",
            f"{test_server.url}/news",
        ]

        results = network_client.get_many(urls)
        assert isinstance(results, dict)
        assert len(results) == len(urls)

        # Verify all URLs were fetched
        for url in urls:
            assert url in results
            assert results[url] is not None
            if "error" not in results[url]:
                assert len(results[url]) > 0

    def test_slow_response_handling(self, network_client, test_server):
        """Test handling of slow responses."""
        # Should complete within timeout
        result = network_client.get(f"{test_server.url}/slow?delay=0.5")
        assert "Slow Response" in result

    def test_large_content_handling(self, network_client, test_server):
        """Test handling of large content."""
        result = network_client.get(f"{test_server.url}/large")
        assert result is not None
        assert "Large Document" in result
        assert "Paragraph 999" in result  # Verify we got all content

    def test_redirect_handling(self, network_client, test_server):
        """Test handling of redirects."""
        result = network_client.get(f"{test_server.url}/redirect")
        # Should follow redirect to /docs
        assert "HttpClient Class" in result

    def test_context_manager_usage(self, test_server):
        """Test NetworkHttpClient as context manager."""
        config = MarkdownLabConfig()
        with NetworkHttpClient(config) as client:
            result = client.get(f"{test_server.url}/product")
            assert "Professional Web Scraping Toolkit" in result
            assert "$299.99" in result


class TestCachedHttpClientWithRealServer:
    """Test CachedHttpClient with real HTTP server."""

    def test_cache_behavior(self, cached_client, test_server):
        """Test that caching works correctly."""
        url = f"{test_server.url}/news"

        # First request
        test_server.clear_requests()
        result1 = cached_client.get(url)
        assert "Tech Giants Invest Billions" in result1
        first_requests = len(test_server.get_requests())
        assert first_requests == 1

        # Second request - should come from cache
        test_server.clear_requests()
        result2 = cached_client.get(url)
        assert result1 == result2
        second_requests = len(test_server.get_requests())
        assert second_requests == 0  # No new request made

    def test_cache_bypass(self, cached_client, test_server):
        """Test bypassing cache."""
        url = f"{test_server.url}/"

        # Prime the cache
        result1 = cached_client.get(url)

        # Clear cache and fetch again
        cached_client.clear_cache()
        test_server.clear_requests()
        result2 = cached_client.get(url)

        assert result1 == result2
        assert len(test_server.get_requests()) == 1  # New request was made

    def test_cache_with_different_urls(self, cached_client, test_server):
        """Test that different URLs are cached separately."""
        url1 = f"{test_server.url}/"
        url2 = f"{test_server.url}/docs"

        # Fetch both URLs
        result1 = cached_client.get(url1)
        result2 = cached_client.get(url2)

        assert "markdown_lab" in result1
        assert "HttpClient Class" in result2
        assert result1 != result2

        # Fetch again - should be from cache
        test_server.clear_requests()
        cached_result1 = cached_client.get(url1)
        cached_result2 = cached_client.get(url2)

        assert cached_result1 == result1
        assert cached_result2 == result2
        assert len(test_server.get_requests()) == 0


class TestClientErrorScenarios:
    """Test error scenarios with real conditions."""

    def test_connection_refused(self, network_client):
        """Test handling when server is not running."""
        # Use a port that's unlikely to have a server
        with pytest.raises(requests.exceptions.ConnectionError):
            network_client.get("http://localhost:59999/")

    def test_invalid_url(self, network_client):
        """Test handling of invalid URLs."""
        with pytest.raises(requests.exceptions.RequestException):
            network_client.get("not-a-valid-url")

    def test_timeout_handling(self, network_client, test_server):
        """Test request timeout handling."""
        # Create client with very short timeout
        config = MarkdownLabConfig(timeout=0.1)
        client = NetworkHttpClient(config)

        with pytest.raises(requests.exceptions.Timeout):
            client.get(f"{test_server.url}/slow?delay=5")


@pytest.mark.parametrize(
    "path,expected_content",
    [
        ("/", "markdown_lab"),
        ("/docs", "HttpClient Class"),
        ("/blog", "Building Fast Web Scrapers"),
        ("/product", "Professional Web Scraping Toolkit"),
        ("/news", "Tech Giants Invest Billions"),
    ],
)
def test_various_content_types(network_client, test_server, path, expected_content):
    """Test fetching various types of content."""
    result = network_client.get(f"{test_server.url}{path}")
    assert expected_content in result
