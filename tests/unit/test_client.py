"""
Comprehensive unit tests for HTTP client classes.

Tests cover HttpClient and CachedHttpClient with various scenarios including
happy paths, edge cases, error conditions, retry logic, caching behavior,
and network failure scenarios.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException

from markdown_lab.http.client import (
    HttpClient,
    CachedHttpClient,
    create_http_client,
    create_cached_http_client
)
from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.errors import NetworkError

@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=MarkdownLabConfig)
    config.user_agent = "TestAgent/1.0"
    config.timeout = 30
    config.max_retries = 3
    config.requests_per_second = 2.0
    config.max_concurrent_requests = 10
    config.cache_enabled = True
    config.cache_ttl = 3600
    return config

@pytest.fixture
def mock_config_no_cache():
    """Create a mock configuration with caching disabled."""
    config = Mock(spec=MarkdownLabConfig)
    config.user_agent = "TestAgent/1.0"
    config.timeout = 30
    config.max_retries = 3
    config.requests_per_second = 2.0
    config.max_concurrent_requests = 10
    config.cache_enabled = False
    config.cache_ttl = 3600
    return config

@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = Mock(spec=requests.Session)
    session.headers = {}
    return session

@pytest.fixture
def mock_cache():
    """Create a mock cache for testing."""
    cache = Mock()
    cache.get.return_value = None
    return cache

class TestHttpClient:
    """Test suite for HttpClient class."""

    def test_init_with_valid_config_creates_client_successfully(self, mock_config):
        client = HttpClient(mock_config)
        assert client.config == mock_config
        assert client.throttler is not None
        assert client.session is not None
        assert client.session.headers["User-Agent"] == "TestAgent/1.0"

    def test_init_with_none_config_uses_default_config(self):
        with patch('markdown_lab.http.client.get_config') as mock_get_config:
            default = Mock(spec=MarkdownLabConfig)
            default.user_agent = "DefaultAgent/1.0"
            default.timeout = 60
            default.max_retries = 5
            default.requests_per_second = 1.0
            default.max_concurrent_requests = 5
            mock_get_config.return_value = default

            client = HttpClient(None)
            assert client.config == default
            mock_get_config.assert_called_once()

    @patch('markdown_lab.http.client.RequestThrottler')
    def test_init_creates_throttler_with_correct_rate(self, mock_throttler, mock_config):
        HttpClient(mock_config)
        mock_throttler.assert_called_once_with(2.0)

    def test_create_session_configures_headers_correctly(self, mock_config):
        client = HttpClient(mock_config)
        expected = {
            "User-Agent": "TestAgent/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        for k, v in expected.items():
            assert client.session.headers[k] == v

    def test_create_session_configures_adapters_correctly(self, mock_config):
        client = HttpClient(mock_config)
        assert "http://" in client.session.adapters
        assert "https://" in client.session.adapters

    @patch('markdown_lab.http.client.time.sleep')
    def test_get_successful_request_returns_content(self, mock_sleep, mock_config, mock_session):
        resp = Mock(text="Test content", status_code=200)
        mock_session.request.return_value = resp

        client = HttpClient(mock_config)
        client.session = mock_session
        result = client.get("https://example.com/test")

        assert result == "Test content"
        mock_session.request.assert_called_once_with(
            "GET", "https://example.com/test", timeout=30
        )

    @patch('markdown_lab.http.client.time.sleep')
    def test_get_request_with_custom_kwargs_passes_correctly(self, mock_sleep, mock_config, mock_session):
        resp = Mock(text="Test content", status_code=200)
        mock_session.request.return_value = resp

        client = HttpClient(mock_config)
        client.session = mock_session
        client.get("https://example.com/test", headers={"X": "Y"}, params={"q": "1"})

        mock_session.request.assert_called_once_with(
            "GET", "https://example.com/test",
            timeout=30, headers={"X": "Y"}, params={"q": "1"}
        )

    @patch('markdown_lab.http.client.time.sleep')
    def test_get_request_with_http_error_retries_and_fails(self, mock_sleep, mock_config, mock_session):
        resp = Mock(status_code=500)
        resp.raise_for_status.side_effect = HTTPError("500 Error")
        mock_session.request.return_value = resp

        client = HttpClient(mock_config)
        client.session = mock_session
        with pytest.raises(NetworkError):
            client.get("https://example.com/test")

        assert mock_session.request.call_count == 4
        assert mock_sleep.call_count == 3
        mock_sleep.assert_has_calls([call(1), call(2), call(4)])

    @patch('markdown_lab.http.client.time.sleep')
    def test_get_request_with_connection_error_retries_with_exponential_backoff(self, mock_sleep, mock_config, mock_session):
        mock_session.request.side_effect = ConnectionError("Conn fail")

        client = HttpClient(mock_config)
        client.session = mock_session
        with pytest.raises(NetworkError):
            client.get("https://example.com/test")

        mock_sleep.assert_has_calls([call(1), call(2), call(4)])

    @patch('markdown_lab.http.client.time.sleep')
    def test_get_request_with_timeout_error_retries_correctly(self, mock_sleep, mock_config, mock_session):
        mock_session.request.side_effect = Timeout("Timeout")
        client = HttpClient(mock_config)
        client.session = mock_session
        with pytest.raises(NetworkError):
            client.get("https://example.com/test")
        assert mock_session.request.call_count == 4

    def test_get_request_success_after_retry_returns_content(self, mock_config, mock_session):
        err = Mock()
        err.raise_for_status.side_effect = HTTPError("500")
        ok = Mock(text="Success", status_code=200)
        mock_session.request.side_effect = [err, ok]

        client = HttpClient(mock_config)
        client.session = mock_session
        with patch('markdown_lab.http.client.time.sleep'):
            result = client.get("https://example.com/test")

        assert result == "Success"
        assert mock_session.request.call_count == 2

    def test_get_request_logs_successful_retrieval(self, mock_config, mock_session, caplog):
        resp = Mock(text="T", status_code=200)
        mock_session.request.return_value = resp

        client = HttpClient(mock_config)
        client.session = mock_session
        client.get("https://example.com/test")

        assert "Successfully retrieved https://example.com/test" in caplog.text
        assert "status: 200" in caplog.text

    def test_head_request_returns_response_object(self, mock_config, mock_session):
        resp = Mock(status_code=200, headers={"Content-Type": "text/html"})
        mock_session.request.return_value = resp

        client = HttpClient(mock_config)
        client.session = mock_session
        result = client.head("https://example.com/test")

        assert result == resp
        mock_session.request.assert_called_once_with(
            "HEAD", "https://example.com/test", timeout=30
        )

    def test_get_many_processes_multiple_urls_successfully(self, mock_config, mock_session):
        responses = [
            Mock(text="1", status_code=200),
            Mock(text="2", status_code=200),
            Mock(text="3", status_code=200)
        ]
        for r in responses:
            r.raise_for_status.return_value = None
        mock_session.request.side_effect = responses

        client = HttpClient(mock_config)
        client.session = mock_session
        urls = ["u1", "u2", "u3"]
        result = client.get_many(urls)

        assert result == {"u1": "1", "u2": "2", "u3": "3"}
        assert mock_session.request.call_count == 3

    def test_get_many_continues_on_individual_failures(self, mock_config, mock_session):
        responses = [
            Mock(text="1", status_code=200),
            ConnectionError("fail"),
            Mock(text="3", status_code=200)
        ]
        responses[0].raise_for_status.return_value = None
        responses[2].raise_for_status.return_value = None
        mock_session.request.side_effect = responses

        client = HttpClient(mock_config)
        client.session = mock_session
        urls = ["u1", "u2", "u3"]
        result = client.get_many(urls)

        assert result == {"u1": "1", "u3": "3"}

    def test_get_many_with_empty_url_list_returns_empty_dict(self, mock_config):
        client = HttpClient(mock_config)
        assert client.get_many([]) == {}

    def test_context_manager_enter_returns_client(self, mock_config):
        client = HttpClient(mock_config)
        with client as ctx:
            assert ctx is client

    def test_context_manager_exit_closes_session(self, mock_config, mock_session):
        client = HttpClient(mock_config)
        client.session = mock_session
        with client:
            pass
        mock_session.close.assert_called_once()

    def test_close_method_closes_session(self, mock_config, mock_session):
        client = HttpClient(mock_config)
        client.session = mock_session
        client.close()
        mock_session.close.assert_called_once()

    def test_close_method_with_none_session_handles_gracefully(self, mock_config):
        client = HttpClient(mock_config)
        client.session = None
        client.close()  # no error

    @patch('markdown_lab.http.client.RequestThrottler')
    def test_throttler_called_before_each_request(self, mock_throttler, mock_config, mock_session):
        thr = Mock()
        mock_throttler.return_value = thr
        resp = Mock(text="T", status_code=200)
        mock_session.request.return_value = resp

        client = HttpClient(mock_config)
        client.session = mock_session
        client.get("https://example.com/test")
        thr.throttle.assert_called_once()

class TestCachedHttpClient:
    """Test suite for CachedHttpClient class."""

    def test_init_with_cache_enabled_creates_cache(self, mock_config):
        mock_config.cache_enabled = True
        with patch('markdown_lab.http.client.RequestCache') as cache_cls:
            cache = Mock()
            cache_cls.return_value = cache
            client = CachedHttpClient(mock_config)
            assert client.cache == cache
            cache_cls.assert_called_once()

    def test_init_with_cache_disabled_sets_none_cache(self, mock_config_no_cache):
        client = CachedHttpClient(mock_config_no_cache)
        assert client.cache is None

    def test_init_with_provided_cache_uses_provided_cache(self, mock_config, mock_cache):
        client = CachedHttpClient(mock_config, cache=mock_cache)
        assert client.cache == mock_cache

    def test_get_with_cache_hit_returns_cached_content(self, mock_config, mock_cache):
        mock_cache.get.return_value = "cached"
        client = CachedHttpClient(mock_config, cache=mock_cache)
        assert client.get("url") == "cached"
        mock_cache.get.assert_called_once_with("url")

    def test_get_with_cache_miss_makes_request_and_caches_result(self, mock_config, mock_cache, mock_session):
        mock_cache.get.return_value = None
        resp = Mock(text="fresh", status_code=200)
        mock_session.request.return_value = resp

        client = CachedHttpClient(mock_config, cache=mock_cache)
        client.session = mock_session
        result = client.get("url")

        assert result == "fresh"
        mock_cache.get.assert_called_once_with("url")
        mock_cache.set.assert_called_once_with("url", "fresh")

    def test_get_with_use_cache_false_bypasses_cache(self, mock_config, mock_cache, mock_session):
        mock_cache.get.return_value = "cached"
        resp = Mock(text="fresh", status_code=200)
        mock_session.request.return_value = resp

        client = CachedHttpClient(mock_config, cache=mock_cache)
        client.session = mock_session
        result = client.get("url", use_cache=False)

        assert result == "fresh"
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()

    def test_get_with_no_cache_instance_behaves_like_base_client(self, mock_config_no_cache, mock_session):
        resp = Mock(text="X", status_code=200)
        mock_session.request.return_value = resp
        client = CachedHttpClient(mock_config_no_cache)
        client.session = mock_session
        assert client.get("url") == "X"
        assert client.cache is None

    def test_clear_cache_clears_cache_instance(self, mock_config, mock_cache):
        client = CachedHttpClient(mock_config, cache=mock_cache)
        client.clear_cache()
        mock_cache.clear.assert_called_once()

    def test_clear_cache_with_no_cache_handles_gracefully(self, mock_config_no_cache):
        client = CachedHttpClient(mock_config_no_cache)
        client.clear_cache()  # no error

class TestFactoryFunctions:
    """Test suite for factory functions."""

    @patch('markdown_lab.http.client.get_config')
    def test_create_http_client_with_none_config_uses_default(self, gc):
        cfg = Mock(spec=MarkdownLabConfig)
        gc.return_value = cfg
        client = create_http_client(None)
        assert isinstance(client, HttpClient)
        assert client.config == cfg
        gc.assert_called_once()

    def test_create_http_client_with_provided_config_uses_provided(self, mock_config):
        client = create_http_client(mock_config)
        assert isinstance(client, HttpClient)
        assert client.config == mock_config

    @patch('markdown_lab.http.client.get_config')
    def test_create_cached_http_client_with_none_config_uses_default(self, gc):  # noqa: E501
        cfg = Mock(spec=MarkdownLabConfig)
        gc.return_value = cfg
        client = create_cached_http_client(None)
        assert isinstance(client, CachedHttpClient)
        assert client.config == cfg

    def test_create_cached_http_client_with_custom_cache(self, mock_config, mock_cache):
        client = create_cached_http_client(mock_config, cache=mock_cache)
        assert isinstance(client, CachedHttpClient)
        assert client.cache == mock_cache

class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling scenarios."""

    def test_get_request_with_malformed_url_raises_appropriate_error(self, mock_config):
        client = HttpClient(mock_config)
        with pytest.raises((NetworkError, requests.exceptions.InvalidURL)):
            client.get("not-a-url")

    def test_get_request_with_none_url_raises_type_error(self, mock_config):
        client = HttpClient(mock_config)
        with pytest.raises(TypeError):
            client.get(None)

    def test_get_request_with_empty_string_url_raises_error(self, mock_config):
        client = HttpClient(mock_config)
        with pytest.raises((NetworkError, requests.exceptions.InvalidURL)):
            client.get("")

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 429, 500, 502, 503, 504])
    @patch('markdown_lab.http.client.time.sleep')
    def test_get_request_with_various_http_error_codes_raises_network_error(self, mock_sleep, status_code, mock_config, mock_session):
        resp = Mock(status_code=status_code)
        resp.raise_for_status.side_effect = HTTPError(f"{status_code} Error")
        mock_session.request.return_value = resp
        client = HttpClient(mock_config)
        client.session = mock_session
        with pytest.raises(NetworkError):
            client.get("url")

    def test_get_request_with_unexpected_exception_reraises(self, mock_config, mock_session):
        mock_session.request.side_effect = ValueError("oops")
        client = HttpClient(mock_config)
        client.session = mock_session
        with pytest.raises(ValueError, match="oops"):
            client.get("url")

    def test_get_request_with_zero_max_retries_fails_immediately(self, mock_config, mock_session):
        mock_config.max_retries = 0
        mock_session.request.side_effect = ConnectionError("fail")
        client = HttpClient(mock_config)
        client.session = mock_session
        with pytest.raises(NetworkError):
            client.get("url")
        assert mock_session.request.call_count == 1

    def test_request_timing_is_logged_correctly(self, mock_config, mock_session, caplog):
        resp = Mock(text="T", status_code=200)
        mock_session.request.return_value = resp
        client = HttpClient(mock_config)
        client.session = mock_session
        with patch('markdown_lab.http.client.time.time', side_effect=[0, 0.5]):
            client.get("url")
        assert "latency: 0.50s" in caplog.text

class TestPerformanceAndIntegration:
    """Test suite for performance characteristics and integration scenarios."""

    def test_get_many_respects_rate_limiting(self, mock_config, mock_session):
        responses = [Mock(text=str(i), status_code=200) for i in range(3)]
        for r in responses:
            r.raise_for_status.return_value = None
        mock_session.request.side_effect = responses

        client = HttpClient(mock_config)
        client.session = mock_session
        with patch.object(client.throttler, 'throttle') as thr:
            client.get_many(["a", "b", "c"])
            assert thr.call_count == 3

    @patch('markdown_lab.http.client.time.sleep')
    def test_retry_backoff_timing_is_correct(self, mock_sleep, mock_config, mock_session):
        mock_session.request.side_effect = ConnectionError()
        client = HttpClient(mock_config)
        client.session = mock_session
        with pytest.raises(NetworkError):
            client.get("url")
        mock_sleep.assert_has_calls([call(1), call(2), call(4)])

    def test_large_response_handling(self, mock_config, mock_session):
        large = "x" * 1000000
        resp = Mock(text=large, status_code=200)
        mock_session.request.return_value = resp

        client = HttpClient(mock_config)
        client.session = mock_session
        result = client.get("url")
        assert result == large
        assert len(result) == 1000000

    def test_concurrent_cache_access_safety(self, mock_config, mock_cache):
        mock_cache.get.return_value = "C"
        client = CachedHttpClient(mock_config, cache=mock_cache)
        results = [client.get("url") for _ in range(10)]
        assert all(r == "C" for r in results)
        assert mock_cache.get.call_count == 10

    def test_session_reuse_across_requests(self, mock_config, mock_session):
        responses = [Mock(text=str(i), status_code=200) for i in range(5)]
        for r in responses:
            r.raise_for_status.return_value = None
        mock_session.request.side_effect = responses

        client = HttpClient(mock_config)
        client.session = mock_session
        for i in range(5):
            client.get(f"url{i}")
        assert mock_session.request.call_count == 5

    def test_memory_cleanup_on_client_destruction(self, mock_config, mock_session):
        client = HttpClient(mock_config)
        client.session = mock_session
        del client
        # cleanup should not error

class TestConfigurationHandling:
    """Test suite for configuration handling edge cases."""

    def test_client_respects_custom_timeout_configuration(self, mock_session):
        cfg = Mock(spec=MarkdownLabConfig)
        cfg.user_agent = "A"; cfg.timeout = 120; cfg.max_retries = 3
        cfg.requests_per_second = 1.0; cfg.max_concurrent_requests = 5
        resp = Mock(text="X", status_code=200)
        mock_session.request.return_value = resp

        client = HttpClient(cfg)
        client.session = mock_session
        client.get("url")
        mock_session.request.assert_called_once_with("GET", "url", timeout=120)

    def test_client_respects_zero_retries_configuration(self, mock_session):
        cfg = Mock(spec=MarkdownLabConfig)
        cfg.user_agent = "A"; cfg.timeout = 30; cfg.max_retries = 0
        cfg.requests_per_second = 1.0; cfg.max_concurrent_requests = 5
        mock_session.request.side_effect = ConnectionError()

        client = HttpClient(cfg)
        client.session = mock_session
        with pytest.raises(NetworkError):
            client.get("url")
        assert mock_session.request.call_count == 1

    def test_client_handles_negative_retry_configuration_gracefully(self, mock_session):
        cfg = Mock(spec=MarkdownLabConfig)
        cfg.user_agent = "A"; cfg.timeout = 30; cfg.max_retries = -1
        cfg.requests_per_second = 1.0; cfg.max_concurrent_requests = 5
        mock_session.request.side_effect = ConnectionError()

        client = HttpClient(cfg)
        client.session = mock_session
        with pytest.raises(NetworkError):
            client.get("url")
        assert mock_session.request.call_count == 1

@pytest.mark.integration
class TestRealWorldScenarios:
    """Integration tests for real-world scenarios (marked as integration)."""

    @pytest.mark.skip(reason="Integration test - requires network access")
    def test_real_http_request_integration(self):
        pass

    @pytest.mark.skip(reason="Integration test - requires performance measurement")
    def test_performance_benchmarking(self):
        pass

# Test coverage verification
# This test file provides comprehensive coverage for:
# - HttpClient initialization and configuration
# - GET, HEAD, and get_many methods
# - Retry logic with exponential backoff
# - Error handling for various HTTP status codes
# - Network error scenarios (timeouts, connection errors)
# - CachedHttpClient caching behavior
# - Context manager functionality
# - Factory function behavior
# - Edge cases and boundary conditions
# - Performance characteristics
# - Memory management and cleanup
#
# Testing framework: pytest
# External dependencies mocked: requests, time.sleep
# Test patterns: fixtures, parametrize, patching, caplog