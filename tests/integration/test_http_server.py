"""HTTP test server for integration testing without mocks."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from tests.fixtures.html_samples import (
    BLOG_POST_WITH_IMAGES,
    DOCUMENTATION_PAGE,
    ECOMMERCE_PRODUCT_PAGE,
    GITHUB_README_STYLE,
    NEWS_ARTICLE,
)


class TestHTTPHandler(BaseHTTPRequestHandler):
    """Test HTTP server handler that serves real content."""

    # Class variable to track requests for assertions
    requests_received = []

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests with realistic responses."""
        self.requests_received.append(
            {"method": "GET", "path": self.path, "headers": dict(self.headers)}
        )

        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Route to different content based on path
        if path == "/":
            self._serve_html(GITHUB_README_STYLE)
        elif path == "/api/data":
            self._serve_json(
                {
                    "status": "success",
                    "data": {
                        "items": [
                            {"id": 1, "name": "Item One", "value": 42.5},
                            {"id": 2, "name": "Item Two", "value": 87.3},
                        ],
                        "total": 129.8,
                        "timestamp": "2024-01-20T10:30:00Z",
                    },
                }
            )
        elif path == "/blog":
            self._serve_html(BLOG_POST_WITH_IMAGES)
        elif path == "/docs":
            self._serve_html(DOCUMENTATION_PAGE)
        elif path == "/error":
            # Simulate various HTTP errors
            error_code = int(query_params.get("code", ["500"])[0])
            self.send_error(error_code)
        elif path == "/large":
            content = "<html><body>" + "<h1>Large Document</h1>"
            for i in range(1000):
                content += f"<p>Paragraph {i}: Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                content += "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>"
            content += "</body></html>"
            self._serve_html(content)
        elif path == "/news":
            self._serve_html(NEWS_ARTICLE)
        elif path == "/product":
            self._serve_html(ECOMMERCE_PRODUCT_PAGE)
        elif path == "/redirect":
            # Simulate redirect
            self.send_response(302)
            self.send_header("Location", "/docs")
            self.end_headers()
        elif path == "/slow":
            # Simulate slow response
            delay = float(query_params.get("delay", ["1"])[0])
            time.sleep(min(delay, 5))  # Cap at 5 seconds
            self._serve_html("<html><body><h1>Slow Response</h1></body></html>")
        elif path == "/timeout":
            # Simulate timeout by sleeping longer than typical timeout
            time.sleep(35)
            self._serve_html("<html><body><h1>Should timeout</h1></body></html>")
        else:
            self.send_error(404, "Page not found")

    def do_HEAD(self):
        """Handle HEAD requests."""
        self.requests_received.append(
            {"method": "HEAD", "path": self.path, "headers": dict(self.headers)}
        )

        # HEAD should return same headers as GET but no body
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(GITHUB_README_STYLE)))
            self.end_headers()
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")

        self.requests_received.append(
            {
                "method": "POST",
                "path": self.path,
                "headers": dict(self.headers),
                "body": post_data,
            }
        )

        if self.path == "/api/submit":
            try:
                data = json.loads(post_data)
                response = {
                    "status": "success",
                    "message": f"Received {len(data)} fields",
                    "echo": data,
                }
                self._serve_json(response)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
        else:
            self.send_error(405, "Method not allowed")

    def _serve_html(self, content):
        """Serve HTML content with proper headers."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Test-Server", "markdown-lab/1.0")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _serve_json(self, data):
        """Serve JSON content with proper headers."""
        content = json.dumps(data, indent=2)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))


class TestHTTPServer:
    """Test HTTP server for integration testing."""

    def __init__(self, port=0):
        """Initialize test server on specified or random port."""
        self.server = HTTPServer(("localhost", port), TestHTTPHandler)
        self.port = self.server.server_port
        self.url = f"http://localhost:{self.port}"
        self.thread = None
        self._running = False

    def start(self):
        """Start the server in a background thread."""
        if self._running:
            return

        def run_server():
            self._running = True
            self.server.serve_forever()

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

        # Wait for server to be ready
        time.sleep(0.1)

    def stop(self):
        """Stop the server."""
        if self._running:
            self.server.shutdown()
            self._running = False
            if self.thread:
                self.thread.join(timeout=5)

    def clear_requests(self):
        """Clear the request log."""
        TestHTTPHandler.requests_received.clear()

    def get_requests(self):
        """Get list of requests received."""
        return TestHTTPHandler.requests_received.copy()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Pytest fixtures for easy use in tests
import pytest


@pytest.fixture
def test_server():
    """Provide a test HTTP server for integration tests."""
    server = TestHTTPServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def test_server_url(test_server):
    """Provide the base URL of the test server."""
    return test_server.url
