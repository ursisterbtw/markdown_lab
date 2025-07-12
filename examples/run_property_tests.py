#!/usr/bin/env python3
"""
Script to run property-based tests and show results.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from markdown_lab.core.config_v2 import MarkdownLabSettings
from markdown_lab.core.errors import MarkdownLabError, NetworkError
from markdown_lab.network.rate_limiter import TokenBucket


def run_config_property_tests():
    """Run configuration property tests."""

    @given(
        requests_per_second=st.floats(min_value=0.1, max_value=10.0),
        timeout=st.integers(min_value=1, max_value=30),
        chunk_size=st.integers(min_value=100, max_value=2000),
    )
    @settings(max_examples=10)
    def test_config_invariants(requests_per_second, timeout, chunk_size):
        config = MarkdownLabSettings(
            requests_per_second=requests_per_second,
            timeout=timeout,
            chunk_size=chunk_size,
            chunk_overlap=min(chunk_size - 1, 200),
        )
        assert config.requests_per_second > 0
        assert config.timeout > 0
        assert config.chunk_size > config.chunk_overlap

    test_config_invariants()


def run_token_bucket_tests():
    """Run token bucket property tests."""

    @given(
        rate=st.floats(min_value=0.1, max_value=50.0),
        capacity=st.integers(min_value=1, max_value=200),
    )
    @settings(max_examples=8)
    def test_bucket_invariants(rate, capacity):
        bucket = TokenBucket(rate=rate, capacity=capacity)

        # Test initial state
        assert bucket.tokens <= bucket.capacity
        assert bucket.tokens == bucket.capacity  # Should start full
        assert bucket.rate == rate

        # Test token consumption
        if capacity > 5:
            initial_tokens = bucket.available_tokens
            success = bucket.try_acquire(3)  # Try to acquire 3 tokens
            if success:
                current_tokens = bucket.available_tokens
                assert current_tokens <= initial_tokens

    test_bucket_invariants()


def run_error_property_tests():
    """Run error handling property tests."""

    @given(
        message=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        )
    )
    @settings(max_examples=5)
    def test_error_basic_properties(message):
        # Test base error with default code
        base_error = MarkdownLabError(message)
        assert isinstance(base_error, Exception)
        assert message in str(base_error)
        assert hasattr(base_error, "error_code")
        assert hasattr(base_error, "context")

        # Test inheritance
        network_error = NetworkError(message)
        assert isinstance(network_error, MarkdownLabError)
        assert isinstance(network_error, Exception)
        assert message in str(network_error)

    test_error_basic_properties()


def run_edge_case_tests():
    """Run edge case discovery tests."""

    @given(
        chunk_size=st.integers(min_value=100, max_value=500),  # Matches validation min
        overlap=st.integers(min_value=0, max_value=500),
    )
    @settings(max_examples=8)
    def test_chunk_validation_edge_cases(chunk_size, overlap):
        if overlap >= chunk_size:
            try:
                MarkdownLabSettings(chunk_size=chunk_size, chunk_overlap=overlap)
                raise AssertionError("Should have failed validation")
            except ValueError:
                pass
        else:
            config = MarkdownLabSettings(chunk_size=chunk_size, chunk_overlap=overlap)
            assert config.chunk_size > config.chunk_overlap

    test_chunk_validation_edge_cases()


def main():
    """Run all property test demonstrations."""

    run_config_property_tests()
    run_token_bucket_tests()
    run_error_property_tests()
    run_edge_case_tests()


if __name__ == "__main__":
    main()
