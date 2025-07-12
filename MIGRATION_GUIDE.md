# Mock Removal Migration Guide

This guide explains how to migrate from mock-based tests to real implementation tests in the markdown_lab codebase.

## Overview

We've eliminated all mock usage in favor of:

1. Real HTTP test servers for network testing
2. Actual subprocess execution for Rust compilation tests
3. Realistic fixture data instead of placeholders

## Migration Steps

### 1. Replace Mock-Based Tests

**Old approach (with mocks):**

```python
from unittest.mock import Mock, patch

@patch("requests.Session.get")
def test_something(mock_get):
    mock_response = Mock()
    mock_response.text = "<html><body><h1>Test</h1></body></html>"
    mock_get.return_value = mock_response
    # ... test code
```

**New approach (with real server):**

```python
from tests.integration.test_http_server import test_server

def test_something(test_server):
    result = client.get(f"{test_server.url}/")
    # ... test with real HTTP response
```

### 2. Use Real Fixtures

We've created comprehensive fixture modules:

- `tests/fixtures/html_samples.py` - Real-world HTML samples
- `tests/fixtures/rust_samples.py` - Valid and invalid Rust code samples

### 3. New Test Files

- `tests/unit/test_client_no_mocks.py` - HTTP client tests with real server
- `tests/unit/test_main_no_mocks.py` - Main functionality tests
- `tests/rust/test_rust_backend_no_mocks.py` - Rust backend tests
- `tests/integration/test_http_server.py` - Test HTTP server implementation

### 4. Running Tests

```bash
# Run all tests including mock validation
just test

# Or manually:
python scripts/validate-no-mocks.py
pytest tests/
```

## CI Integration

Add to your GitHub Actions workflow:

```yaml
- name: Check for mocks
  run: python scripts/validate-no-mocks.py
```

## Benefits

1. **More realistic testing** - Tests behave like production code
2. **Better error discovery** - Real implementations expose edge cases
3. **Improved confidence** - No false positives from mock behavior
4. **Easier debugging** - Real stack traces and error messages

## FAQ

**Q: What if I need to test network failures?**
A: The test server supports error simulation via `/error?code=500` endpoints.

**Q: How do I test timeouts?**
A: Use the `/slow?delay=5` endpoint or `/timeout` endpoint.

**Q: What about testing without Rust installed?**
A: Tests will skip with `pytest.skip()` if Rust toolchain is unavailable.

## Enforcement

The `scripts/validate-no-mocks.py` script will fail CI if any mock usage is detected. This includes:

- `unittest.mock` imports
- `pytest-mock` usage
- `monkeypatch` fixtures
- Mock objects like `MagicMock`, `Mock`, `patch`

Keep tests real, keep them valuable!
