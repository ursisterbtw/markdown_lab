"""
Tests for async HTTP client implementation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.errors import NetworkError
from markdown_lab.network.async_client import (
    AsyncHttpClient,
    CachedAsyncHttpClient,
    sync_get,
    sync_get_many,
)


@pytest.fixture
def config():
    """Test configuration."""
    return MarkdownLabConfig(
        timeout=30,
        max_retries=2,
        requests_per_second=10,
        max_concurrent_requests=5,
        user_agent="test-agent",
        cache_enabled=True,
    )


@pytest_asyncio.fixture
async def async_client(config):
    """Create async client for testing."""
    client = AsyncHttpClient(config)
    yield client
    await client.close()


@pytest_asyncio.fixture
async def cached_client(config):
    """Create cached async client for testing."""
    client = CachedAsyncHttpClient(config)
    yield client
    await client.close()


class TestAsyncHttpClient:
    """Tests for AsyncHttpClient."""

    @pytest.mark.asyncio
    async def test_initialization(self, config):
        """Test client initialization."""
        client = AsyncHttpClient(config)
        assert client.config == config
        assert client._client is None
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test async context manager."""
        async with AsyncHttpClient(config) as client:
            assert client is not None
            assert isinstance(client, AsyncHttpClient)

    @pytest.mark.asyncio
    async def test_get_request_success(self, async_client):
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Test content"
        mock_response.http_version = "HTTP/2"

        with patch.object(async_client, "_ensure_client") as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure.return_value = mock_client

            result = await async_client.get("https://example.com")
            assert result == "Test content"
            mock_client.request.assert_called_once_with("GET", "https://example.com")

    @pytest.mark.asyncio
    async def test_get_request_retry(self, async_client):
        """Test GET request with retry logic."""
        # First attempt fails, second succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=MagicMock(status_code=500)
            )
        )

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.text = "Success"
        mock_response_success.http_version = "HTTP/2"

        with patch.object(async_client, "_ensure_client") as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=[mock_response_fail, mock_response_success]
            )
            mock_ensure.return_value = mock_client

            result = await async_client.get("https://example.com")
            assert result == "Success"
            assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_get_request_max_retries_exceeded(self, async_client):
        """Test GET request failing after max retries."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=MagicMock(status_code=500)
            )
        )

        with patch.object(async_client, "_ensure_client") as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure.return_value = mock_client

            with pytest.raises(NetworkError) as exc_info:
                await async_client.get("https://example.com")

            assert "500" in str(exc_info.value)
            assert mock_client.request.call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_head_request(self, async_client):
        """Test HEAD request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.http_version = "HTTP/2"

        with patch.object(async_client, "_ensure_client") as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_ensure.return_value = mock_client

            result = await async_client.head("https://example.com")
            assert result == mock_response
            mock_client.request.assert_called_once_with("HEAD", "https://example.com")

    @pytest.mark.asyncio
    async def test_get_many(self, async_client):
        """Test concurrent GET requests."""
        urls = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com",
        ]

        with patch.object(async_client, "get") as mock_get:
            mock_get.side_effect = [
                "Content 1",
                NetworkError("Failed", url=urls[1]),
                "Content 3",
            ]

            results = await async_client.get_many(urls)

            assert len(results) == 2
            assert results["https://example1.com"] == "Content 1"
            assert results["https://example3.com"] == "Content 3"
            assert "https://example2.com" not in results

    @pytest.mark.asyncio
    async def test_http2_support(self, async_client):
        """Test HTTP/2 configuration."""
        client = await async_client._ensure_client()
        assert client._transport._pool._http2 is True


class TestCachedAsyncHttpClient:
    """Tests for CachedAsyncHttpClient."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, cached_client):
        """Test cache hit scenario."""
        url = "https://example.com"
        content = "Cached content"

        # Pre-populate cache
        await cached_client.cache.set(url, content)

        with patch.object(cached_client, "_request_with_retries") as mock_request:
            result = await cached_client.get(url)

            assert result == content
            mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss(self, cached_client):
        """Test cache miss scenario."""
        url = "https://example.com"
        content = "Fresh content"

        with patch.object(
            cached_client, "_request_with_retries", return_value=content
        ) as mock_request:
            result = await cached_client.get(url)

            assert result == content
            mock_request.assert_called_once()

            # Verify content was cached
            cached_content = await cached_client.cache.get(url)
            assert cached_content == content

    @pytest.mark.asyncio
    async def test_get_many_with_cache(self, cached_client):
        """Test get_many with partial cache hits."""
        urls = ["https://example1.com", "https://example2.com", "https://example3.com"]

        # Pre-cache one URL
        await cached_client.cache.set(urls[0], "Cached 1")

        with patch.object(cached_client, "_request_with_retries") as mock_request:
            mock_request.side_effect = ["Fresh 2", "Fresh 3"]

            results = await cached_client.get_many(urls)

            assert len(results) == 3
            assert results[urls[0]] == "Cached 1"
            assert results[urls[1]] == "Fresh 2"
            assert results[urls[2]] == "Fresh 3"

            # Only 2 requests should have been made
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_cache(self, cached_client):
        """Test cache clearing."""
        url = "https://example.com"
        await cached_client.cache.set(url, "Content")

        assert await cached_client.cache.get(url) == "Content"

        await cached_client.clear_cache()

        assert await cached_client.cache.get(url) is None


class TestSyncWrappers:
    """Tests for synchronous wrapper functions."""

    def test_sync_get(self, config):
        """Test synchronous GET wrapper."""
        with patch("markdown_lab.network.async_client.AsyncHttpClient.get") as mock_get:
            mock_get.return_value = asyncio.Future()
            mock_get.return_value.set_result("Test content")

            result = sync_get("https://example.com", config)
            assert result == "Test content"

    def test_sync_get_many(self, config):
        """Test synchronous get_many wrapper."""
        urls = ["https://example1.com", "https://example2.com"]
        expected = {urls[0]: "Content 1", urls[1]: "Content 2"}

        with patch(
            "markdown_lab.network.async_client.AsyncHttpClient.get_many"
        ) as mock_get_many:
            mock_get_many.return_value = asyncio.Future()
            mock_get_many.return_value.set_result(expected)

            result = sync_get_many(urls, config)
            assert result == expected


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiting(self, config):
        """Test that rate limiting is applied."""
        config.requests_per_second = 2  # 2 requests per second
        client = AsyncHttpClient(config)

        with patch.object(client.throttler, "throttle") as mock_throttle:
            mock_throttle.return_value = asyncio.Future()
            mock_throttle.return_value.set_result(None)

            with patch.object(client, "_ensure_client") as mock_ensure:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = "Content"
                mock_response.http_version = "HTTP/1.1"
                mock_client.request = AsyncMock(return_value=mock_response)
                mock_ensure.return_value = mock_client

                # Make multiple requests
                await asyncio.gather(
                    client.get("https://example.com"),
                    client.get("https://example.com"),
                    client.get("https://example.com"),
                )

                # Verify throttle was called for each request
                assert mock_throttle.call_count == 3

        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
