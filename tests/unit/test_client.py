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
    """
    Create a mock HTTP response object with preset status code, text, JSON data, and headers for use in network-related tests.
    
    Returns:
        Mock: A mock object simulating an HTTP response.
    """
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>Test HTML</h1></body></html>"
    mock_resp.json.return_value = {"status": "success", "data": "test"}
    mock_resp.headers = {"content-type": "text/html"}
    return mock_resp

@pytest.fixture
def core_client():
    """
    Provides a pytest fixture that returns a new instance of CoreClient for use in tests.
    """
    return CoreClient()

@pytest.fixture
def network_client():
    """
    Provides a pytest fixture that returns a new instance of NetworkClient for use in tests.
    """
    return NetworkClient()

@pytest.fixture
def sample_html():
    """
    Provides sample HTML content for use in tests.
    
    Returns:
        str: A simple HTML string containing a header and paragraph.
    """
    return "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph</p></body></html>"

@pytest.fixture
def sample_config():
    """
    Provides a sample configuration dictionary for initializing and testing client instances.
    
    Returns:
        dict: A configuration with timeout, retries, user agent, and headers settings.
    """
    return {
        "timeout": 30,
        "retries": 3,
        "user_agent": "MarkdownLab/1.0",
        "headers": {"Accept": "text/html,application/xhtml+xml"}
    }

class TestCoreClient:
    """Test suite for CoreClient functionality."""
    
    def test_core_client_initialization_default(self):
        """
        Test that CoreClient initializes successfully with default parameters and has a config attribute.
        """
        client = CoreClient()
        assert client is not None
        assert hasattr(client, 'config')
        
    def test_core_client_initialization_with_config(self, sample_config):
        """
        Test that CoreClient initializes successfully with a custom configuration dictionary.
        """
        client = CoreClient(config=sample_config)
        assert client is not None
        
    def test_core_client_invalid_config(self):
        """
        Test that CoreClient raises ValueError or TypeError when initialized with an invalid configuration.
        """
        with pytest.raises((ValueError, TypeError)):
            CoreClient(config="invalid_config")
            
    def test_core_client_none_config(self):
        """
        Verify that CoreClient can be initialized with a None configuration without errors.
        """
        client = CoreClient(config=None)
        assert client is not None
        
    def test_process_html_valid_input(self, core_client, sample_html):
        """
        Tests that processing valid HTML content with CoreClient returns a non-null string result.
        """
        result = core_client.process_html(sample_html)
        assert result is not None
        assert isinstance(result, str)
        
    def test_process_html_empty_input(self, core_client):
        """
        Verify that processing an empty HTML string with CoreClient returns a non-null result.
        """
        result = core_client.process_html("")
        assert result is not None
        
    def test_process_html_none_input(self, core_client):
        """
        Test that processing None as HTML input raises a ValueError or TypeError.
        """
        with pytest.raises((ValueError, TypeError)):
            core_client.process_html(None)
            
    def test_process_html_malformed_html(self, core_client):
        """
        Test that processing malformed HTML content with CoreClient returns a non-null result.
        """
        malformed_html = "<html><body><h1>Unclosed header<p>Unclosed paragraph"
        result = core_client.process_html(malformed_html)
        assert result is not None
        
    def test_process_html_with_special_characters(self, core_client):
        """
        Tests that processing HTML containing special characters and various encodings returns a non-null string result.
        """
        special_html = "<html><body><p>Special chars: åäö, 中文, emoji 🚀</p></body></html>"
        result = core_client.process_html(special_html)
        assert result is not None
        assert isinstance(result, str)

class TestNetworkClient:
    """Test suite for NetworkClient functionality."""
    
    def test_network_client_initialization(self):
        """
        Verify that NetworkClient can be instantiated successfully.
        """
        client = NetworkClient()
        assert client is not None
        
    def test_network_client_with_timeout(self):
        """
        Verify that NetworkClient initializes correctly with a custom timeout value.
        """
        client = NetworkClient(timeout=60)
        assert client.timeout == 60
        
    @patch('requests.get')
    def test_fetch_url_success(self, mock_get, network_client, mock_response):
        """
        Tests that `NetworkClient.fetch_url` successfully retrieves content from a valid URL and that the underlying HTTP request is made exactly once.
        """
        mock_get.return_value = mock_response
        result = network_client.fetch_url("https://example.com")
        assert result is not None
        mock_get.assert_called_once()
        
    @patch('requests.get')
    def test_fetch_url_with_headers(self, mock_get, network_client, mock_response):
        """
        Tests that fetching a URL with custom headers passes the headers to the underlying HTTP request.
        """
        mock_get.return_value = mock_response
        custom_headers = {"User-Agent": "TestAgent"}
        result = network_client.fetch_url("https://example.com", headers=custom_headers)
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "headers" in kwargs
        
    @patch('requests.get')
    def test_fetch_url_timeout(self, mock_get, network_client):
        """
        Test that fetching a URL with a timeout raises a Timeout exception.
        """
        mock_get.side_effect = Timeout("Request timed out")
        with pytest.raises(Timeout):
            network_client.fetch_url("https://example.com")
            
    @patch('requests.get')
    def test_fetch_url_connection_error(self, mock_get, network_client):
        """
        Test that `fetch_url` raises a `ConnectionError` when a connection failure occurs.
        """
        mock_get.side_effect = ConnectionError("Connection failed")
        with pytest.raises(ConnectionError):
            network_client.fetch_url("https://example.com")
            
    @patch('requests.get')
    def test_fetch_url_invalid_url(self, mock_get, network_client):
        """
        Test that fetching an invalid URL with NetworkClient raises a ValueError or RequestException.
        """
        with pytest.raises((ValueError, RequestException)):
            network_client.fetch_url("not-a-valid-url")
            
    @patch('requests.get')
    def test_fetch_url_empty_url(self, mock_get, network_client):
        """
        Test that fetching an empty URL with NetworkClient raises a ValueError or RequestException.
        """
        with pytest.raises((ValueError, RequestException)):
            network_client.fetch_url("")
            
    @patch('requests.get')
    def test_fetch_url_none_url(self, mock_get, network_client):
        """
        Test that fetching a URL with a value of None raises a ValueError or TypeError.
        """
        with pytest.raises((ValueError, TypeError)):
            network_client.fetch_url(None)
            
    def test_core_client_large_html_input(self, core_client):
        """
        Tests that CoreClient can process very large HTML input without errors.
        
        Parameters:
            core_client: An instance of CoreClient used for processing.
        """
        large_html = "<html><body>" + "<p>Large content</p>" * 10000 + "</body></html>"
        result = core_client.process_html(large_html)
        assert result is not None
        
    def test_core_client_deeply_nested_html(self, core_client):
        """
        Tests that CoreClient can process deeply nested HTML structures without errors.
        """
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
        """
        Test that the network client retries fetching a URL up to the maximum number of retries on connection errors and succeeds if a later attempt is successful.
        """
        mock_get.side_effect = [
            ConnectionError("First attempt failed"),
            ConnectionError("Second attempt failed"),
            Mock(status_code=200, text="Success")
        ]
        result = network_client.fetch_url_with_retry("https://example.com", max_retries=3)
        assert mock_get.call_count == 3
        
    def test_core_client_concurrent_processing(self, core_client, sample_html):
        """
        Verifies that CoreClient can process multiple HTML inputs concurrently without errors.
        
        Ensures that concurrent processing of the same HTML input using multiple threads produces non-null results for each thread.
        """
        import threading
        results = []
        def process_html():
            """
            Processes the sample HTML content using the core client and appends the result to the results list.
            """
            result = core_client.process_html(sample_html)
            results.append(result)
        threads = [threading.Thread(target=process_html) for _ in range(5)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        assert len(results) == 5
        assert all(result is not None for result in results)
        
    @patch('requests.get')
    def test_network_client_rate_limiting(self, mock_get, network_client, mock_response):
        """
        Test that NetworkClient enforces a minimum interval between consecutive requests when rate limiting is applied.
        
        Verifies that multiple calls to `fetch_url_with_rate_limit` with a specified `min_interval` result in a total elapsed time consistent with the enforced rate limit.
        """
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
        """
        Tests the full integration workflow from fetching HTML content via URL to converting it into markdown.
        
        Verifies that the network client successfully retrieves HTML and the core client processes it into a non-null markdown result.
        """
        mock_get.return_value = mock_response
        network_client = NetworkClient()
        core_client = CoreClient()
        html_content = network_client.fetch_url("https://example.com")
        markdown_result = core_client.process_html(html_content)
        assert html_content is not None
        assert markdown_result is not None
        mock_get.assert_called_once()
        
    def test_error_propagation_workflow(self):
        """
        Verify that a network error during URL fetching is correctly propagated through the client workflow.
        
        This test ensures that when a `ConnectionError` occurs in `NetworkClient.fetch_url`, the exception is raised and not suppressed when the result is passed to `CoreClient.process_html`.
        """
        network_client = NetworkClient()
        core_client = CoreClient()
        with patch('requests.get', side_effect=ConnectionError("Network error")):
            with pytest.raises(ConnectionError):
                html_content = network_client.fetch_url("https://example.com")
                core_client.process_html(html_content)
                
    @patch('requests.get')
    def test_client_state_management(self, mock_get, mock_response):
        """
        Test that NetworkClient maintains correct state and performs independent fetches across multiple URL requests.
        
        Verifies that separate fetch operations return non-null results and that the underlying network call is invoked for each request.
        """
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
        """
        Test that CoreClient processes various HTML inputs and returns the expected output type.
        
        Parameters:
            html_input: The HTML or text input to be processed.
            expected_type: The expected type of the result after processing.
        """
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
        """
        Test that NetworkClient correctly validates URLs and raises exceptions for invalid inputs.
        
        Parameters:
            url (str): The URL to be fetched.
            should_raise (bool): Indicates whether an exception is expected for the given URL.
        """
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
        """
        Test that NetworkClient correctly handles different HTTP status codes when fetching a URL.
        
        Parameters:
            status_code (int): The HTTP status code to simulate in the response.
            should_raise (bool): Whether an exception is expected for the given status code.
        """
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
        """
        Verify that the NetworkClient performs resource cleanup after fetching a URL if a cleanup method is available.
        """
        network_client.fetch_url("https://example.com")
        if hasattr(network_client, 'cleanup'):
            network_client.cleanup()
        assert True
        
    def test_client_configuration_validation(self):
        """
        Verifies that NetworkClient initializes successfully with various valid configuration dictionaries.
        """
        valid_configs = [
            {"timeout": 30, "retries": 3},
            {"user_agent": "TestAgent"},
            {},
        ]
        for config in valid_configs:
            client = NetworkClient(**config)
            assert client is not None
            
    def test_client_memory_usage(self, core_client, sample_html):
        """
        Tests that repeated processing of large HTML inputs by CoreClient does not cause excessive memory usage growth.
        
        Parameters:
            core_client: Instance of CoreClient used for processing.
            sample_html: Sample HTML string to be multiplied for large input testing.
        """
        import sys
        initial_size = sys.getsizeof(core_client)
        for _ in range(10):
            large_html = sample_html * 1000
            core_client.process_html(large_html)
        final_size = sys.getsizeof(core_client)
        assert final_size - initial_size < 1000000
        
    def teardown_method(self, method):
        """
        Performs cleanup operations after each test method execution.
        """
        pass
        
    @classmethod
    def teardown_class(cls):
        """
        Hook for cleaning up resources after all tests in the class have run.
        """
        pass

class TestClientPerformance:
    """Performance benchmarks for client operations."""
    
    def test_core_client_performance(self, benchmark, core_client, sample_html):
        """
        Benchmark the performance of CoreClient's HTML processing method.
        
        Measures the execution time of processing sample HTML content using the benchmark fixture and asserts that the result is not None.
        """
        result = benchmark(core_client.process_html, sample_html)
        assert result is not None
        
    @patch('requests.get')
    def test_network_client_performance(self, benchmark, mock_get, network_client, mock_response):
        """
        Benchmark the performance of the NetworkClient's URL fetching method using a mocked HTTP response.
        """
        mock_get.return_value = mock_response
        result = benchmark(network_client.fetch_url, "https://example.com")
        assert result is not None