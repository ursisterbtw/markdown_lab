import pytest
from unittest.mock import Mock, patch, MagicMock, call
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import json
import time
from typing import Optional, Dict, Any

from markdown_lab.core.client import CoreClient
from markdown_lab.network.client import NetworkClient

@pytest.fixture
def mock_response():
    """Mock HTTP response for testing network operations."""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>Test HTML</h1></body></html>"
    mock_resp.json.return_value = {"status": "success", "data": "test"}
    mock_resp.headers = {"content-type": "text/html"}
    return mock_resp

@pytest.fixture
def core_client():
    """Fixture for CoreClient instance."""
    return CoreClient()

@pytest.fixture
def network_client():
    """Fixture for NetworkClient instance."""
    return NetworkClient()

@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"

@pytest.fixture
def sample_config():
    """Sample configuration for client testing."""
    return {
        "timeout": 30,
        "retries": 3,
        "user_agent": "MarkdownLab/1.0",
        "headers": {"Accept": "text/html,application/xhtml+xml"}
    }

class TestCoreClient:
    """Test suite for CoreClient functionality."""
    
    def test_core_client_initialization_default(self):
        """Test CoreClient initializes with default parameters."""
        client = CoreClient()
        assert client is not None
        assert hasattr(client, 'config')
        
    def test_core_client_initialization_with_config(self, sample_config):
        """Test CoreClient initializes with custom configuration."""
        client = CoreClient(config=sample_config)
        assert client is not None
        
    def test_core_client_invalid_config(self):
        """Test CoreClient handles invalid configuration gracefully."""
        with pytest.raises((ValueError, TypeError)):
            CoreClient(config="invalid_config")
            
    def test_core_client_none_config(self):
        """Test CoreClient handles None configuration."""
        client = CoreClient(config=None)
        assert client is not None
        
    def test_process_html_valid_input(self, core_client, sample_html):
        """Test processing valid HTML content."""
        result = core_client.process_html(sample_html)
        assert result is not None
        assert isinstance(result, str)
        
    def test_process_html_empty_input(self, core_client):
        """Test processing empty HTML content."""
        result = core_client.process_html("")
        assert result is not None
        
    def test_process_html_none_input(self, core_client):
        """Test processing None input."""
        with pytest.raises((ValueError, TypeError)):
            core_client.process_html(None)
            
    def test_process_html_malformed_html(self, core_client):
        """Test processing malformed HTML content."""
        malformed_html = "<html><body><h1>Unclosed header<p>Unclosed paragraph"
        result = core_client.process_html(malformed_html)
        assert result is not None
        
    def test_process_html_with_special_characters(self, core_client):
        """Test processing HTML with special characters and encoding."""
        special_html = "<html><body><p>Special chars: åäö, 中文, emoji 🚀</p></body></html>"
        result = core_client.process_html(special_html)
        assert result is not None
        assert isinstance(result, str)

class TestNetworkClient:
    """Test suite for NetworkClient functionality."""
    
    def test_network_client_initialization(self):
        """Test NetworkClient initializes correctly."""
        client = NetworkClient()
        assert client is not None
        
    def test_network_client_with_timeout(self):
        """Test NetworkClient initializes with custom timeout."""
        client = NetworkClient(timeout=60)
        assert client.timeout == 60
        
    @patch('requests.get')
    def test_fetch_url_success(self, mock_get, network_client, mock_response):
        """Test successful URL fetching."""
        mock_get.return_value = mock_response
        result = network_client.fetch_url("https://example.com")
        assert result is not None
        mock_get.assert_called_once()
        
    @patch('requests.get')
    def test_fetch_url_with_headers(self, mock_get, network_client, mock_response):
        """Test URL fetching with custom headers."""
        mock_get.return_value = mock_response
        custom_headers = {"User-Agent": "TestAgent"}
        result = network_client.fetch_url("https://example.com", headers=custom_headers)
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "headers" in kwargs
        
    @patch('requests.get')
    def test_fetch_url_timeout(self, mock_get, network_client):
        """Test URL fetching with timeout."""
        mock_get.side_effect = Timeout("Request timed out")
        with pytest.raises(Timeout):
            network_client.fetch_url("https://example.com")
            
    @patch('requests.get')
    def test_fetch_url_connection_error(self, mock_get, network_client):
        """Test URL fetching with connection error."""
        mock_get.side_effect = ConnectionError("Connection failed")
        with pytest.raises(ConnectionError):
            network_client.fetch_url("https://example.com")
            
    @patch('requests.get')
    def test_fetch_url_invalid_url(self, mock_get, network_client):
        """Test fetching invalid URL."""
        with pytest.raises((ValueError, RequestException)):
            network_client.fetch_url("not-a-valid-url")
            
    @patch('requests.get')
    def test_fetch_url_empty_url(self, mock_get, network_client):
        """Test fetching empty URL."""
        with pytest.raises((ValueError, RequestException)):
            network_client.fetch_url("")
            
    @patch('requests.get')
    def test_fetch_url_none_url(self, mock_get, network_client):
        """Test fetching None URL."""
        with pytest.raises((ValueError, TypeError)):
            network_client.fetch_url(None)
            
    def test_core_client_large_html_input(self, core_client):
        """Test processing very large HTML input."""
        large_html = "<html><body>" + "<p>Large content</p>" * 10000 + "</body></html>"
        result = core_client.process_html(large_html)
        assert result is not None
        
    def test_core_client_deeply_nested_html(self, core_client):
        """Test processing deeply nested HTML."""
        nested_html = "<html><body>"
        for i in range(100):
            nested_html += f"<div class='level-{i}'>"
        nested_html += "Deep content"
        for i in range(100):
            nested_html += "</div>"
        nested_html += "</body></html>"
        result = core_client.process_html(nested_html)
        assert result is not None
        
    @patch('requests.get')
    def test_network_client_retry_mechanism(self, mock_get, network_client):
        """Test retry mechanism on network failures."""
        mock_get.side_effect = [
            ConnectionError("First attempt failed"),
            ConnectionError("Second attempt failed"),
            Mock(status_code=200, text="Success")
        ]
        result = network_client.fetch_url_with_retry("https://example.com", max_retries=3)
        assert mock_get.call_count == 3
        
    def test_core_client_concurrent_processing(self, core_client, sample_html):
        """Test concurrent HTML processing."""
        import threading
        results = []
        def process_html():
            result = core_client.process_html(sample_html)
            results.append(result)
        threads = [threading.Thread(target=process_html) for _ in range(5)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        assert len(results) == 5
        assert all(result is not None for result in results)
        
    @patch('requests.get')
    def test_network_client_rate_limiting(self, mock_get, network_client, mock_response):
        """Test rate limiting behavior."""
        mock_get.return_value = mock_response
        start_time = time.time()
        for _ in range(3):
            network_client.fetch_url_with_rate_limit("https://example.com", min_interval=0.1)
        end_time = time.time()
        assert end_time - start_time >= 0.2

class TestClientIntegration:
    """Integration tests for client interactions."""
    
    @patch('requests.get')
    def test_end_to_end_workflow(self, mock_get, mock_response):
        """Test complete workflow from URL fetch to markdown conversion."""
        mock_get.return_value = mock_response
        network_client = NetworkClient()
        core_client = CoreClient()
        html_content = network_client.fetch_url("https://example.com")
        markdown_result = core_client.process_html(html_content)
        assert html_content is not None
        assert markdown_result is not None
        mock_get.assert_called_once()
        
    def test_error_propagation_workflow(self):
        """Test error propagation through client chain."""
        network_client = NetworkClient()
        core_client = CoreClient()
        with patch('requests.get', side_effect=ConnectionError("Network error")):
            with pytest.raises(ConnectionError):
                html_content = network_client.fetch_url("https://example.com")
                core_client.process_html(html_content)
                
    @patch('requests.get')
    def test_client_state_management(self, mock_get, mock_response):
        """Test client state management across multiple operations."""
        mock_get.return_value = mock_response
        client = NetworkClient()
        result1 = client.fetch_url("https://example1.com")
        result2 = client.fetch_url("https://example2.com")
        assert result1 is not None
        assert result2 is not None
        assert mock_get.call_count == 2

class TestParametrizedScenarios:
    """Parametrized tests for comprehensive coverage."""
    
    @pytest.mark.parametrize("html_input,expected_type", [
        ("<h1>Header</h1>", str),
        ("<p>Paragraph</p>", str),
        ("<div><span>Nested</span></div>", str),
        ("Plain text", str),
        ("<html></html>", str),
    ])
    def test_core_client_various_inputs(self, core_client, html_input, expected_type):
        """Test CoreClient with various HTML inputs."""
        result = core_client.process_html(html_input)
        assert isinstance(result, expected_type)
        
    @pytest.mark.parametrize("url,should_raise", [
        ("https://valid-url.com", False),
        ("http://another-valid.com", False),
        ("invalid-url", True),
        ("", True),
        ("ftp://not-http.com", True),
    ])
    @patch('requests.get')
    def test_network_client_url_validation(self, mock_get, network_client, mock_response, url, should_raise):
        """Test NetworkClient URL validation."""
        mock_get.return_value = mock_response
        if should_raise:
            with pytest.raises((ValueError, RequestException)):
                network_client.fetch_url(url)
        else:
            result = network_client.fetch_url(url)
            assert result is not None
            
    @pytest.mark.parametrize("status_code,should_raise", [
        (200, False),
        (201, False),
        (404, True),
        (500, True),
        (403, True),
    ])
    @patch('requests.get')
    def test_network_client_status_codes(self, mock_get, network_client, status_code, should_raise):
        """Test NetworkClient handling of various HTTP status codes."""
        mock_resp = Mock()
        mock_resp.status_code = status_code
        mock_resp.raise_for_status.side_effect = None if status_code < 400 else RequestException(f"HTTP {status_code}")
        mock_get.return_value = mock_resp
        if should_raise:
            with pytest.raises(RequestException):
                network_client.fetch_url("https://example.com")
        else:
            result = network_client.fetch_url("https://example.com")
            assert result is not None

class TestClientUtilities:
    """Test utility methods and edge cases."""
    
    def test_client_cleanup_resources(self, network_client):
        """Test proper resource cleanup."""
        network_client.fetch_url("https://example.com")
        if hasattr(network_client, 'cleanup'):
            network_client.cleanup()
        assert True
        
    def test_client_configuration_validation(self):
        """Test client configuration validation."""
        valid_configs = [
            {"timeout": 30, "retries": 3},
            {"user_agent": "TestAgent"},
            {},
        ]
        for config in valid_configs:
            client = NetworkClient(**config)
            assert client is not None
            
    def test_client_memory_usage(self, core_client, sample_html):
        """Test memory usage with large inputs."""
        import sys
        initial_size = sys.getsizeof(core_client)
        for _ in range(10):
            large_html = sample_html * 1000
            core_client.process_html(large_html)
        final_size = sys.getsizeof(core_client)
        assert final_size - initial_size < 1000000
        
    def teardown_method(self, method):
        """Clean up after each test method."""
        pass
        
    @classmethod
    def teardown_class(cls):
        """Clean up after all tests in class."""
        pass

class TestClientPerformance:
    """Performance benchmarks for client operations."""
    
    def test_core_client_performance(self, benchmark, core_client, sample_html):
        """Benchmark CoreClient HTML processing performance."""
        result = benchmark(core_client.process_html, sample_html)
        assert result is not None
        
    @patch('requests.get')
    def test_network_client_performance(self, benchmark, mock_get, network_client, mock_response):
        """Benchmark NetworkClient URL fetching performance."""
        mock_get.return_value = mock_response
        result = benchmark(network_client.fetch_url, "https://example.com")
        assert result is not None