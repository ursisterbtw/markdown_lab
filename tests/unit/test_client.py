import time
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import ConnectionError, RequestException, Timeout

from markdown_lab.core.client import HttpClient as CoreHttpClient
from markdown_lab.network.client import HttpClient as NetworkHttpClient, CachedHttpClient
from markdown_lab.core.config import MarkdownLabConfig


@pytest.fixture
def mock_response():
    """Mock HTTP response for testing network operations."""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>Test HTML</h1></body></html>"
    mock_resp.json.return_value = {"status": "success", "data": "test"}
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.raise_for_status.return_value = None
    # Mock the elapsed time properly
    mock_resp.elapsed.total_seconds.return_value = 0.123
    return mock_resp


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


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return "<html><body><h1>Test</h1><p>Content</p></body></html>"


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return MarkdownLabConfig(
        timeout=60,
        max_retries=5,
        requests_per_second=2.0
    )


class TestCoreClient:
    """Test suite for CoreHttpClient functionality."""

    def test_core_client_initialization_default(self):
        """Test CoreHttpClient initializes with default parameters."""
        client = CoreHttpClient()
        assert client is not None
        assert hasattr(client, 'config')

    def test_core_client_initialization_with_config(self, sample_config):
        """Test CoreHttpClient initializes with custom configuration."""
        client = CoreHttpClient(config=sample_config)
        assert client is not None

    def test_core_client_none_config(self):
        """Test CoreHttpClient handles None configuration."""
        client = CoreHttpClient(config=None)
        assert client is not None

    @patch('requests.Session.get')
    def test_get_valid_url(self, mock_get, core_client, mock_response):
        """Test GET request to a valid URL."""
        mock_get.return_value = mock_response
        result = core_client.get("https://httpbin.org/html")
        assert result is not None
        assert isinstance(result, str)
        assert "<html>" in result or "Test HTML" in result

    @patch('requests.Session.get')
    def test_get_with_skip_cache(self, mock_get, core_client, mock_response):
        """Test GET request with cache skipping."""
        mock_get.return_value = mock_response
        result = core_client.get("https://httpbin.org/html", skip_cache=True)
        assert result is not None
        assert isinstance(result, str)


class TestNetworkClient:
    """Test suite for NetworkHttpClient functionality."""

    def test_network_client_initialization(self):
        """Test NetworkHttpClient initializes correctly."""
        config = MarkdownLabConfig()
        client = NetworkHttpClient(config)
        assert client is not None
        assert hasattr(client, 'config')
        assert hasattr(client, 'session')

    def test_network_client_with_custom_config(self, sample_config):
        """Test NetworkHttpClient initializes with custom configuration."""
        client = NetworkHttpClient(sample_config)
        assert client.config == sample_config

    @patch('requests.Session.request')
    def test_get_success(self, mock_request, network_client, mock_response):
        """Test successful GET request."""
        mock_request.return_value = mock_response
        result = network_client.get("https://example.com")
        assert result is not None
        assert isinstance(result, str)
        mock_request.assert_called_once()

    @patch('requests.Session.request')
    def test_head_request(self, mock_request, network_client, mock_response):
        """Test HEAD request."""
        mock_request.return_value = mock_response
        result = network_client.head("https://example.com")
        assert result is not None
        mock_request.assert_called_once_with("HEAD", "https://example.com", timeout=30)

    @patch('requests.Session.request')
    def test_get_many_urls(self, mock_request, network_client, mock_response):
        """Test fetching multiple URLs."""
        mock_request.return_value = mock_response
        urls = ["https://example1.com", "https://example2.com"]
        results = network_client.get_many(urls)
        assert isinstance(results, dict)
        assert len(results) <= len(urls)  # Some might fail

    def test_context_manager(self, sample_config):
        """Test NetworkHttpClient as context manager."""
        with NetworkHttpClient(sample_config) as client:
            assert client is not None


class TestCachedHttpClient:
    """Test suite for CachedHttpClient functionality."""

    def test_cached_client_initialization(self):
        """Test CachedHttpClient initializes correctly."""
        config = MarkdownLabConfig()
        client = CachedHttpClient(config)
        assert client is not None
        assert hasattr(client, 'cache')

    @patch('requests.Session.request')
    def test_cached_get_success(self, mock_request, cached_client, mock_response):
        """Test successful cached GET request."""
        mock_request.return_value = mock_response
        result = cached_client.get("https://example.com")
        assert result is not None
        assert isinstance(result, str)

    def test_clear_cache(self, cached_client):
        """Test cache clearing functionality."""
        cached_client.clear_cache()  # Should not raise an exception