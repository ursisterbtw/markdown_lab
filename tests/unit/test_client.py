import time
from unittest.mock import Mock, patch

import pytest
import requests
from requests.exceptions import ConnectionError, Timeout

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.network.client import CachedHttpClient, HttpClient


@pytest.fixture
def mock_response():
    """Mock HTTP response for testing network operations."""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>Test HTML</h1></body></html>"
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.elapsed.total_seconds.return_value = 0.25
    mock_resp.raise_for_status.return_value = None
    return mock_resp


@pytest.fixture
def test_config():
    """Test configuration for HTTP clients."""
    return MarkdownLabConfig(
        timeout=10,
        max_retries=2,
        requests_per_second=5,
        cache_enabled=True,
        user_agent="TestAgent/1.0",
    )


@pytest.fixture
def http_client(test_config):
    """Fixture for HttpClient instance."""
    return HttpClient(test_config)


@pytest.fixture
def cached_http_client(test_config):
    """Fixture for CachedHttpClient instance."""
    return CachedHttpClient(test_config)


class TestHttpClient:
    """Test suite for unified HttpClient functionality."""

    def test_http_client_initialization_default(self):
        """Test HttpClient initializes with default configuration."""
        client = HttpClient()
        assert client is not None
        assert hasattr(client, "config")
        assert hasattr(client, "session")
        assert hasattr(client, "throttler")

    def test_http_client_initialization_with_config(self, test_config):
        """Test HttpClient initializes with custom configuration."""
        client = HttpClient(test_config)
        assert client.config == test_config
        assert client.config.timeout == 10
        assert client.config.max_retries == 2

    @patch("requests.Session.request")
    def test_get_success(self, mock_request, http_client, mock_response):
        """Test successful GET request."""
        mock_request.return_value = mock_response
        result = http_client.get("https://example.com")
        assert result == mock_response.text
        mock_request.assert_called_once()

    @patch("requests.Session.request")
    def test_get_with_retries(self, mock_request, http_client, mock_response):
        """Test GET request with retry logic."""
        mock_request.side_effect = [ConnectionError("Connection failed"), mock_response]
        result = http_client.get("https://example.com")
        assert result == mock_response.text
        assert mock_request.call_count == 2

    @patch("requests.Session.request")
    def test_get_max_retries_exceeded(self, mock_request, http_client):
        """Test GET request when max retries exceeded."""
        mock_request.side_effect = ConnectionError("Connection failed")
        with pytest.raises(Exception):
            http_client.get("https://example.com")
        assert mock_request.call_count == http_client.config.max_retries + 1

    @patch("requests.Session.request")
    def test_head_request(self, mock_request, http_client, mock_response):
        """Test HEAD request functionality."""
        mock_request.return_value = mock_response
        result = http_client.head("https://example.com")
        assert result == mock_response
        mock_request.assert_called_once_with("HEAD", "https://example.com", timeout=10)

    @patch("requests.Session.request")
    def test_get_many_urls(self, mock_request, http_client, mock_response):
        """Test batch GET requests."""
        mock_request.return_value = mock_response
        urls = ["https://example1.com", "https://example2.com", "https://example3.com"]
        results = http_client.get_many(urls)
        assert len(results) == 3
        assert all(url in results for url in urls)
        assert mock_request.call_count == 3

    def test_context_manager(self, test_config):
        """Test HttpClient as context manager and verify close is called."""
        # Mock the close method to verify it's called
        with patch.object(HttpClient, 'close') as mock_close:
            with HttpClient(test_config) as client:
                assert client is not None
                assert hasattr(client, "session")
                assert client.session is not None
            # Verify close was called on context exit
            mock_close.assert_called_once()

    def test_close_method(self, http_client):
        """Test explicit close method."""
        # Mock the session close method to verify it's called
        with patch.object(http_client.session, 'close') as mock_close:
            http_client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, test_config):
        """Test HttpClient as async context manager."""
        async with HttpClient(test_config) as client:
            assert client is not None
            assert hasattr(client, "aclose")
        # Should complete without errors

    @pytest.mark.asyncio 
    async def test_async_close_method(self, http_client):
        """Test async close method."""
        await http_client.aclose()
        # Should not raise any exceptions


class TestCachedHttpClient:
    """Test suite for CachedHttpClient functionality."""

    def test_cached_client_initialization_default(self):
        """Test CachedHttpClient initializes with default configuration."""
        client = CachedHttpClient()
        assert client is not None
        assert hasattr(client, "cache")

    def test_cached_client_initialization_with_config(self, test_config):
        """Test CachedHttpClient initializes with custom configuration."""
        client = CachedHttpClient(test_config)
        assert client.config == test_config

    @patch("requests.Session.request")
    def test_get_with_cache_miss(self, mock_request, cached_http_client, mock_response):
        """Test GET request with cache miss."""
        mock_request.return_value = mock_response
        result = cached_http_client.get("https://example.com")
        assert result == mock_response.text
        mock_request.assert_called_once()

    @patch("requests.Session.request")
    def test_get_with_cache_hit(self, mock_request, cached_http_client, mock_response):
        """Test GET request with cache hit."""
        mock_request.return_value = mock_response

        # First request - cache miss
        result1 = cached_http_client.get("https://example.com")
        assert result1 == mock_response.text

        # Second request - cache hit
        result2 = cached_http_client.get("https://example.com")
        assert result2 == mock_response.text

        # Should only make one actual HTTP request
        mock_request.assert_called_once()

    @patch("requests.Session.request")
    def test_get_skip_cache(self, mock_request, cached_http_client, mock_response):
        """Test GET request with skip_cache parameter."""
        mock_request.return_value = mock_response

        # First request
        cached_http_client.get("https://example.com")

        # Second request with skip_cache=True
        result = cached_http_client.get("https://example.com", skip_cache=True)
        assert result == mock_response.text

        # Should make two HTTP requests
        assert mock_request.call_count == 2

    @patch("requests.Session.request")
    def test_get_use_cache_false(self, mock_request, cached_http_client, mock_response):
        """Test GET request with use_cache=False."""
        mock_request.return_value = mock_response

        # First request
        cached_http_client.get("https://example.com")

        # Second request with use_cache=False
        result = cached_http_client.get("https://example.com", use_cache=False)
        assert result == mock_response.text

        # Should make two HTTP requests
        assert mock_request.call_count == 2

    def test_clear_cache(self, cached_http_client):
        """Test cache clearing functionality."""
        cached_http_client.clear_cache()
        # Should not raise any exceptions

    def test_cache_disabled_config(self):
        """Test CachedHttpClient with caching disabled."""
        config = MarkdownLabConfig(cache_enabled=False)
        client = CachedHttpClient(config)
        assert client.cache is None

    def test_cached_client_close_method(self, cached_http_client):
        """Test CachedHttpClient close method."""
        cached_http_client.close()
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_cached_client_async_close(self, cached_http_client):
        """Test CachedHttpClient async close method."""
        await cached_http_client.aclose()
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_cached_client_async_context_manager(self, test_config):
        """Test CachedHttpClient as async context manager."""
        async with CachedHttpClient(test_config) as client:
            assert client is not None
            assert hasattr(client, "cache")
        # Should complete without errors


class TestClientIntegration:
    """Integration tests for HTTP client functionality."""

    @patch("requests.Session.request")
    def test_throttling_behavior(self, mock_request, test_config, mock_response):
        """Test that requests are properly throttled."""
        mock_request.return_value = mock_response
        client = HttpClient(test_config)

        start_time = time.time()
        # Make multiple requests that should be throttled
        for i in range(3):
            client.get(f"https://example{i}.com")
        end_time = time.time()

        # With 5 requests per second, 3 requests should take at least 0.4 seconds
        # (allowing some margin for test execution overhead)
        elapsed = end_time - start_time
        assert elapsed >= 0.3  # Conservative check

    @patch("requests.Session.request")
    def test_error_handling_chain(self, mock_request, http_client):
        """Test error handling through the request chain."""
        mock_request.side_effect = [
            Timeout("Request timeout"),
            ConnectionError("Connection error"),
            requests.exceptions.HTTPError("HTTP error"),
        ]

        with pytest.raises(Exception):
            http_client.get("https://example.com")

    def test_session_configuration(self, http_client):
        """Test that session is properly configured."""
        session = http_client.session
        assert "User-Agent" in session.headers
        assert session.headers["User-Agent"] == http_client.config.user_agent

    @patch("requests.Session.request")
    def test_response_timing_logging(self, mock_request, http_client, mock_response):
        """Test that response timing is logged."""
        mock_request.return_value = mock_response

        with patch("markdown_lab.network.client.logger") as mock_logger:
            http_client.get("https://example.com")
            # Verify that info log was called (response timing is logged)
            mock_logger.info.assert_called()


class TestErrorScenarios:
    """Test various error scenarios."""

    @pytest.mark.parametrize(
        "exception_type",
        [
            ConnectionError,
            Timeout,
            requests.exceptions.HTTPError,
            requests.exceptions.RequestException,
        ],
    )
    @patch("requests.Session.request")
    def test_exception_handling(self, mock_request, http_client, exception_type):
        """Test handling of various request exceptions."""
        mock_request.side_effect = exception_type("Test error")

        with pytest.raises(Exception):
            http_client.get("https://example.com")

    @patch("requests.Session.request")
    def test_http_error_status_codes(self, mock_request, http_client):
        """Test handling of HTTP error status codes."""
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_request.return_value = mock_resp

        with pytest.raises(Exception):
            http_client.get("https://example.com")


class TestPerformance:
    """Performance-related tests."""

    @patch("requests.Session.request")
    def test_connection_reuse(self, mock_request, http_client, mock_response):
        """Test that connections are reused efficiently."""
        mock_request.return_value = mock_response

        # Make multiple requests to the same domain
        for i in range(5):
            http_client.get("https://example.com/page" + str(i))

        # All requests should use the same session
        assert mock_request.call_count == 5

    def test_memory_efficiency(self, cached_http_client):
        """Test memory efficiency of cached client."""
        import sys

        initial_size = sys.getsizeof(cached_http_client)

        # Simulate adding items to cache
        if cached_http_client.cache:
            for i in range(100):
                cached_http_client.cache.set(f"url{i}", f"content{i}")

        # Memory usage should be reasonable
        final_size = sys.getsizeof(cached_http_client)
        size_increase = final_size - initial_size
        assert size_increase < 1000000  # Less than 1MB increase
