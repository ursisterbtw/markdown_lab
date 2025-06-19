"""
Comprehensive unit tests for the HTTP client modules.

Tests both HttpClient and CachedHttpClient classes from the core and network
client modules, covering happy paths, edge cases, and failure conditions.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException

# Import the client classes and their dependencies
from markdown_lab.core.client import HttpClient as CoreHttpClient
from markdown_lab.network.client import HttpClient, CachedHttpClient, create_http_client, create_cached_http_client
from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.errors import NetworkError

@pytest.fixture
def mock_config():
    """Create a mock MarkdownLabConfig for testing."""
    config = Mock(spec=MarkdownLabConfig)
    config.user_agent = "TestAgent/1.0"
    config.requests_per_second = 2.0
    config.max_retries = 3
    config.timeout = 30
    config.cache_enabled = True
    config.cache_ttl = 300
    config.max_concurrent_requests = 10
    return config

@pytest.fixture
def mock_success_response():
    """Create a mock successful HTTP response."""
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.text = "Success response content"
    response.elapsed.total_seconds.return_value = 0.5
    response.raise_for_status.return_value = None
    return response

@pytest.fixture
def mock_error_response():
    """Create a mock HTTP error response."""
    response = Mock(spec=requests.Response)
    response.status_code = 404
    response.raise_for_status.side_effect = HTTPError("404 Not Found")
    return response

@pytest.fixture
def http_client(mock_config):
    """Create an HttpClient instance for testing."""
    with patch('markdown_lab.network.client.RequestThrottler'):
        return HttpClient(mock_config)

@pytest.fixture
def cached_http_client(mock_config):
    """Create a CachedHttpClient instance for testing."""
    with patch('markdown_lab.network.client.RequestThrottler'), \
         patch('markdown_lab.network.client.RequestCache'):
        return CachedHttpClient(mock_config)

@pytest.fixture
def core_http_client(mock_config):
    """Create a CoreHttpClient instance for testing."""
    with patch('markdown_lab.core.client.RequestThrottler'), \
         patch('markdown_lab.core.client.RequestCache'), \
         patch('markdown_lab.core.client.get_config', return_value=mock_config):
        return CoreHttpClient(mock_config)

class TestHttpClientInitialization:
    """Test HttpClient initialization and configuration."""
    
    def test_init_with_config(self, mock_config):
        """Test HttpClient initialization with provided config."""
        with patch('markdown_lab.network.client.RequestThrottler') as mock_throttler, \
             patch('requests.Session') as mock_session:
            
            client = HttpClient(mock_config)
            
            assert client.config == mock_config
            mock_throttler.assert_called_once_with(mock_config.requests_per_second)
            mock_session.assert_called_once()
    
    def test_session_configuration(self, mock_config):
        """Test that HTTP session is properly configured."""
        with patch('markdown_lab.network.client.RequestThrottler'), \
             patch('requests.Session') as mock_session:
            
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            
            client = HttpClient(mock_config)
            
            expected_headers = {
                "User-Agent": mock_config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            mock_session_instance.headers.update.assert_called_once_with(expected_headers)
            
            assert mock_session_instance.mount.call_count == 2
            mock_session_instance.mount.assert_any_call("http://", pytest.any)
            mock_session_instance.mount.assert_any_call("https://", pytest.any)
    
    def test_context_manager_support(self, http_client):
        """Test HttpClient context manager functionality."""
        with patch.object(http_client, 'close') as mock_close:
            with http_client as client:
                assert client is http_client
            mock_close.assert_called_once()
    
    def test_close_session(self, http_client):
        """Test that close() properly closes the session."""
        with patch.object(http_client.session, 'close') as mock_close:
            http_client.close()
            mock_close.assert_called_once()

class TestHttpClientGetRequests:
    """Test HttpClient GET request functionality."""
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_get_success(self, mock_handle_exception, http_client, mock_success_response):
        """Test successful GET request."""
        with patch.object(http_client.session, 'request', return_value=mock_success_response), \
             patch.object(http_client.throttler, 'throttle'):
            
            url = "https://example.com/test"
            result = http_client.get(url)
            
            assert result == "Success response content"
            http_client.session.request.assert_called_once_with(
                "GET", url, timeout=http_client.config.timeout
            )
            http_client.throttler.throttle.assert_called_once()
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_get_with_custom_timeout(self, mock_handle_exception, http_client, mock_success_response):
        """Test GET request with custom timeout."""
        with patch.object(http_client.session, 'request', return_value=mock_success_response), \
             patch.object(http_client.throttler, 'throttle'):
            
            url = "https://example.com/test"
            custom_timeout = 60
            result = http_client.get(url, timeout=custom_timeout)
            
            http_client.session.request.assert_called_once_with(
                "GET", url, timeout=custom_timeout
            )
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_get_with_additional_kwargs(self, mock_handle_exception, http_client, mock_success_response):
        """Test GET request with additional keyword arguments."""
        with patch.object(http_client.session, 'request', return_value=mock_success_response), \
             patch.object(http_client.throttler, 'throttle'):
            
            url = "https://example.com/test"
            headers = {"Custom-Header": "value"}
            params = {"param1": "value1"}
            
            result = http_client.get(url, headers=headers, params=params)
            
            http_client.session.request.assert_called_once_with(
                "GET", url, timeout=http_client.config.timeout,
                headers=headers, params=params
            )
    
    @patch('time.sleep')
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_get_retry_on_http_error(self, mock_handle_exception, mock_sleep, http_client):
        """Test GET request retry logic on HTTP errors."""
        network_error = NetworkError("HTTP Error", url="https://example.com/test", error_code="HTTP_ERROR")
        mock_handle_exception.return_value = network_error
        
        http_error = HTTPError("500 Server Error")
        success_response = Mock(spec=requests.Response)
        success_response.status_code = 200
        success_response.text = "Success"
        success_response.raise_for_status.return_value = None
        success_response.elapsed.total_seconds.return_value = 0.3
        
        with patch.object(http_client.session, 'request') as mock_request, \
             patch.object(http_client.throttler, 'throttle'):
            
            mock_request.side_effect = [http_error, http_error, success_response]
            
            url = "https://example.com/test"
            result = http_client.get(url)
            
            assert result == "Success"
            assert mock_request.call_count == 3
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1)
            mock_sleep.assert_any_call(2)
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_get_max_retries_exceeded(self, mock_handle_exception, http_client):
        """Test GET request when max retries are exceeded."""
        network_error = NetworkError("Max retries exceeded", url="https://example.com/test", error_code="MAX_RETRIES")
        mock_handle_exception.return_value = network_error
        
        http_error = HTTPError("500 Server Error")
        
        with patch.object(http_client.session, 'request', side_effect=http_error), \
             patch.object(http_client.throttler, 'throttle'), \
             patch('time.sleep'):
            
            url = "https://example.com/test"
            with pytest.raises(NetworkError):
                http_client.get(url)
            
            expected_calls = http_client.config.max_retries + 1
            assert http_client.session.request.call_count == expected_calls

class TestHttpClientHeadRequests:
    """Test HttpClient HEAD request functionality."""
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_head_success(self, mock_handle_exception, http_client, mock_success_response):
        """Test successful HEAD request."""
        with patch.object(http_client.session, 'request', return_value=mock_success_response), \
             patch.object(http_client.throttler, 'throttle'):
            
            url = "https://example.com/test"
            result = http_client.head(url)
            
            assert result == mock_success_response
            http_client.session.request.assert_called_once_with(
                "HEAD", url, return_response=True, timeout=http_client.config.timeout
            )
    
    def test_get_many_success(self, http_client, mock_success_response):
        """Test successful processing of multiple URLs."""
        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        
        with patch.object(http_client, 'get', return_value="Success content") as mock_get:
            result = http_client.get_many(urls)
            
            assert len(result) == 3
            for url in urls:
                assert result[url] == "Success content"
            assert mock_get.call_count == 3
            for url in urls:
                mock_get.assert_any_call(url)
    
    def test_get_many_with_failures(self, http_client):
        """Test get_many continues on individual URL failures."""
        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        
        def mock_get_side_effect(url):
            if url == "https://example.com/2":
                raise NetworkError("Failed", url=url, error_code="ERROR")
            return f"Success content for {url}"
        
        with patch.object(http_client, 'get', side_effect=mock_get_side_effect):
            result = http_client.get_many(urls)
            
            assert len(result) == 2
            assert "https://example.com/1" in result
            assert "https://example.com/3" in result
            assert "https://example.com/2" not in result

class TestHttpClientErrorHandling:
    """Test HttpClient error handling scenarios."""
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_connection_error_handling(self, mock_handle_exception, http_client):
        """Test handling of connection errors."""
        network_error = NetworkError("Connection failed", url="https://example.com/test", error_code="CONNECTION_ERROR")
        mock_handle_exception.return_value = network_error
        
        connection_error = ConnectionError("Connection refused")
        
        with patch.object(http_client.session, 'request', side_effect=connection_error), \
             patch.object(http_client.throttler, 'throttle'):
            
            with pytest.raises(NetworkError) as exc_info:
                http_client.get("https://example.com/test")
            
            assert exc_info.value.error_code == "CONNECTION_ERROR"
            mock_handle_exception.assert_called()
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_timeout_error_handling(self, mock_handle_exception, http_client):
        """Test handling of timeout errors."""
        network_error = NetworkError("Request timeout", url="https://example.com/test", error_code="TIMEOUT")
        mock_handle_exception.return_value = network_error
        
        timeout_error = Timeout("Request timed out")
        
        with patch.object(http_client.session, 'request', side_effect=timeout_error), \
             patch.object(http_client.throttler, 'throttle'):
            
            with pytest.raises(NetworkError) as exc_info:
                http_client.get("https://example.com/test")
            
            assert exc_info.value.error_code == "TIMEOUT"
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_http_error_status_codes(self, mock_handle_exception, http_client):
        """Test handling of various HTTP error status codes."""
        error_codes = [400, 401, 403, 404, 500, 502, 503]
        
        for code in error_codes:
            network_error = NetworkError(f"HTTP {code}", url="https://example.com/test", error_code=f"HTTP_{code}")
            mock_handle_exception.return_value = network_error
            
            error_response = Mock(spec=requests.Response)
            error_response.status_code = code
            error_response.raise_for_status.side_effect = HTTPError(f"{code} Error")
            
            with patch.object(http_client.session, 'request', return_value=error_response), \
                 patch.object(http_client.throttler, 'throttle'):
                
                with pytest.raises(NetworkError):
                    http_client.get("https://example.com/test")
    
    @patch('markdown_lab.network.client.handle_request_exception')
    def test_unexpected_exception_handling(self, mock_handle_exception, http_client):
        """Test handling of unexpected exceptions."""
        network_error = NetworkError("Unexpected error", url="https://example.com/test", error_code="UNEXPECTED")
        mock_handle_exception.return_value = network_error
        
        unexpected_error = ValueError("Unexpected error occurred")
        
        with patch.object(http_client.session, 'request', side_effect=unexpected_error), \
             patch.object(http_client.throttler, 'throttle'):
            
            with pytest.raises(NetworkError):
                http_client.get("https://example.com/test")

class TestCachedHttpClient:
    """Test CachedHttpClient functionality."""
    
    def test_init_with_cache_enabled(self, mock_config):
        """Test CachedHttpClient initialization with caching enabled."""
        mock_config.cache_enabled = True
        
        with patch('markdown_lab.network.client.RequestThrottler'), \
             patch('markdown_lab.network.client.RequestCache') as mock_cache_class:
            
            mock_cache = Mock()
            mock_cache_class.return_value = mock_cache
            
            client = CachedHttpClient(mock_config)
            
            assert client.cache == mock_cache
            mock_cache_class.assert_called_once()
    
    def test_init_with_cache_disabled(self, mock_config):
        """Test CachedHttpClient initialization with caching disabled."""
        mock_config.cache_enabled = False
        
        with patch('markdown_lab.network.client.RequestThrottler'):
            client = CachedHttpClient(mock_config)
            assert client.cache is None
    
    def test_init_with_provided_cache(self, mock_config):
        """Test CachedHttpClient initialization with provided cache instance."""
        custom_cache = Mock()
        
        with patch('markdown_lab.network.client.RequestThrottler'):
            client = CachedHttpClient(mock_config, cache=custom_cache)
            assert client.cache == custom_cache
    
    def test_get_cache_hit(self, cached_http_client):
        """Test GET request with cache hit."""
        url = "https://example.com/test"
        cached_content = "Cached response content"
        
        cached_http_client.cache = Mock()
        cached_http_client.cache.get.return_value = cached_content
        
        result = cached_http_client.get(url)
        
        assert result == cached_content
        cached_http_client.cache.get.assert_called_once_with(url)
        cached_http_client.cache.set.assert_not_called()
    
    def test_get_cache_miss(self, cached_http_client, mock_success_response):
        """Test GET request with cache miss."""
        url = "https://example.com/test"
        response_content = "Fresh response content"
        
        cached_http_client.cache = Mock()
        cached_http_client.cache.get.return_value = None
        
        with patch.object(cached_http_client.session, 'request', return_value=mock_success_response), \
             patch.object(cached_http_client.throttler, 'throttle'), \
             patch('markdown_lab.network.client.handle_request_exception'):
            
            mock_success_response.text = response_content
            result = cached_http_client.get(url)
            
            assert result == response_content
            cached_http_client.cache.get.assert_called_once_with(url)
            cached_http_client.cache.set.assert_called_once_with(url, response_content)
    
    def test_get_skip_cache(self, cached_http_client, mock_success_response):
        """Test GET request with cache bypassed."""
        url = "https://example.com/test"
        response_content = "Fresh response content"
        
        cached_http_client.cache = Mock()
        cached_http_client.cache.get.return_value = "Cached content"
        
        with patch.object(cached_http_client.session, 'request', return_value=mock_success_response), \
             patch.object(cached_http_client.throttler, 'throttle'), \
             patch('markdown_lab.network.client.handle_request_exception'):
            
            mock_success_response.text = response_content
            result = cached_http_client.get(url, use_cache=False)
            
            assert result == response_content
            cached_http_client.cache.get.assert_not_called()
            cached_http_client.cache.set.assert_not_called()
    
    def test_clear_cache(self, cached_http_client):
        """Test cache clearing functionality."""
        cached_http_client.cache = Mock()
        
        cached_http_client.clear_cache()
        
        cached_http_client.cache.clear.assert_called_once()
    
    def test_clear_cache_when_disabled(self, mock_config):
        """Test clear_cache when caching is disabled."""
        mock_config.cache_enabled = False
        
        with patch('markdown_lab.network.client.RequestThrottler'):
            client = CachedHttpClient(mock_config)
            client.clear_cache()

class TestCoreHttpClient:
    """Test the core HttpClient functionality."""
    
    def test_init_with_config(self, mock_config):
        """Test core HttpClient initialization with config."""
        with patch('markdown_lab.core.client.RequestThrottler') as mock_throttler, \
             patch('markdown_lab.core.client.RequestCache') as mock_cache, \
             patch('requests.Session'):
            
            mock_config.cache_enabled = True
            client = CoreHttpClient(mock_config)
            
            assert client.config == mock_config
            mock_throttler.assert_called_once_with(mock_config.requests_per_second)
            mock_cache.assert_called_once_with(max_age=mock_config.cache_ttl)
    
    def test_init_without_config(self):
        """Test core HttpClient initialization without config."""
        with patch('markdown_lab.core.client.get_config') as mock_get_config, \
             patch('markdown_lab.core.client.RequestThrottler'), \
             patch('markdown_lab.core.client.RequestCache'), \
             patch('requests.Session'):
            
            default_config = Mock()
            default_config.cache_enabled = True
            default_config.cache_ttl = 300
            default_config.requests_per_second = 1.0
            default_config.user_agent = "DefaultAgent"
            mock_get_config.return_value = default_config
            
            client = CoreHttpClient()
            
            assert client.config == default_config
            mock_get_config.assert_called_once()
    
    def test_get_with_cache_enabled(self, core_http_client, mock_success_response):
        """Test GET request with caching enabled."""
        url = "https://example.com/test"
        cached_content = "Cached content"
        
        core_http_client.cache = Mock()
        core_http_client.cache.get.return_value = cached_content
        
        result = core_http_client.get(url)
        
        assert result == cached_content
        core_http_client.cache.get.assert_called_once_with(url)
    
    def test_get_skip_cache_parameter(self, core_http_client, mock_success_response):
        """Test GET request with skip_cache parameter."""
        url = "https://example.com/test"
        response_content = "Fresh content"
        
        core_http_client.cache = Mock()
        core_http_client.cache.get.return_value = "Cached content"
        
        with patch.object(core_http_client, '_fetch_with_retries', return_value=response_content):
            result = core_http_client.get(url, skip_cache=True)
            
            assert result == response_content
            core_http_client.cache.get.assert_not_called()
            core_http_client.cache.set.assert_called_once_with(url, response_content)
    
    def test_fetch_with_retries_success(self, core_http_client, mock_success_response):
        """Test successful fetch with retries."""
        url = "https://example.com/test"
        
        with patch.object(core_http_client.session, 'get', return_value=mock_success_response), \
             patch.object(core_http_client.throttler, 'throttle'):
            
            result = core_http_client._fetch_with_retries(url)
            
            assert result == mock_success_response.text
            core_http_client.throttler.throttle.assert_called_once()
            core_http_client.session.get.assert_called_once_with(
                url, timeout=core_http_client.config.timeout
            )
    
    @patch('time.sleep')
    def test_fetch_with_retries_http_error(self, mock_sleep, core_http_client):
        """Test fetch with retries on HTTP error."""
        url = "https://example.com/test"
        
        error_response = Mock()
        error_response.raise_for_status.side_effect = HTTPError("500 Server Error")
        
        success_response = Mock()
        success_response.raise_for_status.return_value = None
        success_response.text = "Success content"
        success_response.elapsed.total_seconds.return_value = 0.3
        success_response.status_code = 200
        
        with patch.object(core_http_client.session, 'get') as mock_get, \
             patch.object(core_http_client.throttler, 'throttle'):
            
            mock_get.side_effect = [error_response, error_response, success_response]
            
            result = core_http_client._fetch_with_retries(url)
            
            assert result == "Success content"
            assert mock_get.call_count == 3
            assert mock_sleep.call_count == 2

class TestConvenienceFunctions:
    """Test convenience functions for creating client instances."""
    
    @patch('markdown_lab.network.client.get_config')
    def test_create_http_client_without_config(self, mock_get_config):
        """Test creating HttpClient without providing config."""
        default_config = Mock()
        mock_get_config.return_value = default_config
        
        with patch('markdown_lab.network.client.HttpClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            result = create_http_client()
            
            mock_get_config.assert_called_once()
            mock_client_class.assert_called_once_with(default_config)
            assert result == mock_client
    
    def test_create_http_client_with_config(self, mock_config):
        """Test creating HttpClient with provided config."""
        with patch('markdown_lab.network.client.HttpClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            result = create_http_client(mock_config)
            
            mock_client_class.assert_called_once_with(mock_config)
            assert result == mock_client
    
    @patch('markdown_lab.network.client.get_config')
    def test_create_cached_http_client_without_config(self, mock_get_config):
        """Test creating CachedHttpClient without providing config."""
        default_config = Mock()
        mock_get_config.return_value = default_config
        
        with patch('markdown_lab.network.client.CachedHttpClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            result = create_cached_http_client()
            
            mock_get_config.assert_called_once()
            mock_client_class.assert_called_once_with(default_config, None)
            assert result == mock_client
    
    def test_create_cached_http_client_with_cache(self, mock_config):
        """Test creating CachedHttpClient with provided cache."""
        custom_cache = Mock()
        
        with patch('markdown_lab.network.client.CachedHttpClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            result = create_cached_http_client(mock_config, custom_cache)
            
            mock_client_class.assert_called_once_with(mock_config, custom_cache)
            assert result == mock_client

class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions."""
    
    def test_empty_url_handling(self, http_client):
        """Test handling of empty URL."""
        with patch.object(http_client.session, 'request') as mock_request, \
             patch.object(http_client.throttler, 'throttle'):
            
            http_client.get("")
            mock_request.assert_called_once()
    
    def test_very_long_url_handling(self, http_client, mock_success_response):
        """Test handling of very long URLs."""
        long_url = "https://example.com/" + "a" * 2000
        
        with patch.object(http_client.session, 'request', return_value=mock_success_response), \
             patch.object(http_client.throttler, 'throttle'), \
             patch('markdown_lab.network.client.handle_request_exception'):
            
            result = http_client.get(long_url)
            assert result == mock_success_response.text
    
    def test_unicode_url_handling(self, http_client, mock_success_response):
        """Test handling of URLs with Unicode characters."""
        unicode_url = "https://example.com/测试"
        
        with patch.object(http_client.session, 'request', return_value=mock_success_response), \
             patch.object(http_client.throttler, 'throttle'), \
             patch('markdown_lab.network.client.handle_request_exception'):
            
            result = http_client.get(unicode_url)
            assert result == mock_success_response.text
    
    def test_zero_timeout_handling(self, mock_config):
        """Test handling of zero timeout configuration."""
        mock_config.timeout = 0
        
        with patch('markdown_lab.network.client.RequestThrottler'):
            client = HttpClient(mock_config)
            
            with patch.object(client.session, 'request') as mock_request, \
                 patch.object(client.throttler, 'throttle'):
                
                client.get("https://example.com/test")
                call_args = mock_request.call_args
                assert call_args[1]['timeout'] == 0
    
    def test_negative_retry_count(self, mock_config):
        """Test handling of negative retry count."""
        mock_config.max_retries = -1
        
        with patch('markdown_lab.network.client.RequestThrottler'):
            client = HttpClient(mock_config)
            assert hasattr(client, 'config')
    
    def test_concurrent_requests_thread_safety(self, http_client, mock_success_response):
        """Test thread safety with concurrent requests."""
        import concurrent.futures
        
        results = []
        errors = []
        
        def make_request(url_suffix):
            try:
                with patch.object(http_client.session, 'request', return_value=mock_success_response), \
                     patch.object(http_client.throttler, 'throttle'), \
                     patch('markdown_lab.network.client.handle_request_exception'):
                    
                    result = http_client.get(f"https://example.com/{url_suffix}")
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            concurrent.futures.wait(futures)
        
        assert not errors, f"Concurrent requests failed: {errors}"
        assert len(results) == 10

class TestPerformanceAndResourceManagement:
    """Test performance-related functionality and resource management."""
    
    def test_session_reuse(self, http_client, mock_success_response):
        """Test that HTTP session is reused across requests."""
        with patch.object(http_client.session, 'request', return_value=mock_success_response), \
             patch.object(http_client.throttler, 'throttle'), \
             patch('markdown_lab.network.client.handle_request_exception'):
            
            urls = [f"https://example.com/{i}" for i in range(5)]
            for url in urls:
                http_client.get(url)
            assert http_client.session.request.call_count == 5
    
    def test_throttling_applied(self, http_client, mock_success_response):
        """Test that throttling is properly applied."""
        with patch.object(http_client.session, 'request', return_value=mock_success_response), \
             patch.object(http_client.throttler, 'throttle') as mock_throttle, \
             patch('markdown_lab.network.client.handle_request_exception'):
            
            http_client.get("https://example.com/test")
            mock_throttle.assert_called_once()
    
    def test_large_response_handling(self, http_client):
        """Test handling of large responses."""
        large_response = Mock(spec=requests.Response)
        large_response.status_code = 200
        large_response.text = "x" * 1000000
        large_response.raise_for_status.return_value = None
        large_response.elapsed.total_seconds.return_value = 2.0
        
        with patch.object(http_client.session, 'request', return_value=large_response), \
             patch.object(http_client.throttler, 'throttle'), \
             patch('markdown_lab.network.client.handle_request_exception'):
            
            result = http_client.get("https://example.com/large")
            assert len(result) == 1000000
            assert result == "x" * 1000000

def test_module_imports():
    """Test that all required modules can be imported."""
    from markdown_lab.core.client import HttpClient as CoreHttpClient
    from markdown_lab.network.client import HttpClient, CachedHttpClient
    assert CoreHttpClient is not None
    assert HttpClient is not None
    assert CachedHttpClient is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])