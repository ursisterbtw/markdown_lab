import pytest


def test_rust_backend_calls_convert_html_to_format(monkeypatch):
    from markdown_lab.core.rust_backend import RustBackend

    class DummyModule:
        def convert_html_to_format(self, html, base_url, fmt):
            assert fmt in ("markdown", "json", "xml")
            return "ok"

    backend = RustBackend(fallback_enabled=True)
    backend._rust_module = DummyModule()
    out = backend.convert_html_to_format("<html/>", "https://x", "json")
    assert out == "ok"
