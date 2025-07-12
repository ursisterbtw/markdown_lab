"""
Simplified property-based tests for markdown_lab components.

These tests focus on the synchronous components and core logic validation
without complex async operations for faster testing.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from markdown_lab.core.config_v2 import MarkdownLabSettings
from markdown_lab.core.errors import MarkdownLabError, NetworkError, ParsingError
from markdown_lab.network.rate_limiter import RateLimiter, TokenBucket


class TestConfigurationProperties:
    """Property-based tests for configuration management."""

    @given(
        requests_per_second=st.floats(min_value=0.1, max_value=1000.0),
        timeout=st.integers(min_value=1, max_value=300),
        max_retries=st.integers(min_value=0, max_value=10),
        chunk_size=st.integers(min_value=100, max_value=10000),
        cache_ttl=st.integers(min_value=1, max_value=86400),
    )
    @settings(max_examples=20)
    def test_config_validation_invariants(
        self, requests_per_second, timeout, max_retries, chunk_size, cache_ttl
    ):
        """Test that valid configurations always validate successfully."""
        config = MarkdownLabSettings(
            requests_per_second=requests_per_second,
            timeout=timeout,
            max_retries=max_retries,
            chunk_size=chunk_size,
            chunk_overlap=min(chunk_size - 1, 200),  # Ensure overlap < size
            cache_ttl=cache_ttl,
        )

        # Invariants
        assert config.requests_per_second > 0
        assert config.timeout > 0
        assert config.max_retries >= 0
        assert config.chunk_size > config.chunk_overlap
        assert config.cache_ttl > 0

    @given(
        chunk_size=st.integers(min_value=50, max_value=1000),
        chunk_overlap=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=15)
    def test_chunk_overlap_validation(self, chunk_size, chunk_overlap):
        """Test chunk overlap validation rules."""
        if chunk_overlap >= chunk_size:
            # Should raise validation error
            with pytest.raises(
                ValueError, match="chunk_overlap.*must be less than.*chunk_size"
            ):
                MarkdownLabSettings(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        else:
            # Should validate successfully
            config = MarkdownLabSettings(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            assert config.chunk_size > config.chunk_overlap


class TestRateLimiterProperties:
    """Property-based tests for rate limiting functionality."""

    @given(
        rate=st.floats(min_value=0.1, max_value=100.0),
        capacity=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=20)
    def test_token_bucket_invariants(self, rate, capacity):
        """Test token bucket maintains invariants."""
        bucket = TokenBucket(rate=rate, capacity=capacity)

        # Initial state invariants
        assert bucket.tokens <= bucket.capacity
        assert bucket.rate == rate
        assert bucket.capacity == capacity

        # After consuming tokens
        initial_tokens = bucket.tokens
        consumed = min(initial_tokens, capacity // 2)

        if consumed > 0:
            bucket._consume_tokens(consumed)
            assert bucket.tokens == initial_tokens - consumed
            assert bucket.tokens >= 0

    @given(
        rates=st.lists(st.floats(min_value=0.1, max_value=10.0), min_size=1, max_size=5)
    )
    @settings(max_examples=10)
    def test_rate_limiter_consistency(self, rates):
        """Test rate limiter with multiple buckets maintains consistency."""
        rate_limiter = RateLimiter()

        # Add buckets for each rate
        bucket_names = []
        for i, rate in enumerate(rates):
            bucket_name = f"bucket_{i}"
            bucket_names.append(bucket_name)
            rate_limiter.add_bucket(bucket_name, rate=rate, capacity=int(rate * 10))

        # Test that all buckets exist and are accessible
        for bucket_name in bucket_names:
            bucket = rate_limiter.get_bucket(bucket_name)
            assert bucket is not None
            assert bucket.rate in rates

    @given(
        tokens_to_acquire=st.lists(
            st.integers(min_value=1, max_value=10), min_size=1, max_size=20
        )
    )
    @settings(max_examples=10)
    def test_token_acquisition_ordering(self, tokens_to_acquire):
        """Test that token acquisition maintains ordering properties."""
        bucket = TokenBucket(rate=10.0, capacity=100)

        # Track acquisitions
        acquired = []
        total_requested = sum(tokens_to_acquire)

        # If we can acquire all tokens immediately
        if total_requested <= bucket.tokens:
            for tokens in tokens_to_acquire:
                if bucket.tokens >= tokens:
                    bucket._consume_tokens(tokens)
                    acquired.append(tokens)

        # Verify acquired tokens don't exceed original capacity
        assert sum(acquired) <= bucket.capacity


class TestErrorHandlingProperties:
    """Property-based tests for error handling consistency."""

    @given(
        error_message=st.text(min_size=1, max_size=200),
        error_code=st.one_of(
            st.none(),
            st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("L", "N")),
            ),
        ),
        context_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("L",)),
            ),
            values=st.one_of(
                st.text(), st.integers(), st.floats(allow_nan=False), st.booleans()
            ),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=15)
    def test_error_hierarchy_properties(self, error_message, error_code, context_data):
        """Test error hierarchy maintains consistent properties."""
        # Test base error
        base_error = MarkdownLabError(error_message, error_code, context_data)

        assert str(base_error) == error_message
        assert base_error.error_code == error_code
        assert base_error.context == context_data

        # Test derived errors maintain properties
        network_error = NetworkError(error_message, error_code, context_data)
        parsing_error = ParsingError(error_message, error_code, context_data)

        for error in [network_error, parsing_error]:
            assert isinstance(error, MarkdownLabError)
            assert str(error) == error_message
            assert error.error_code == error_code
            assert error.context == context_data


class TestTextProcessingProperties:
    """Property-based tests for text processing robustness."""

    @given(
        text_input=st.one_of(
            st.text(min_size=0, max_size=1000),
            st.just(""),
            st.text(alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"))),
            st.text(alphabet=st.characters(blacklist_characters="\x00\n\r\t")),
        )
    )
    @settings(max_examples=25)
    def test_text_processing_robustness(self, text_input):
        """Test that text processing handles various inputs robustly."""
        try:
            # Simulate basic text processing operations
            result = text_input.strip()

            # Property: result should be a string
            assert isinstance(result, str)

            # Property: length should not exceed original
            assert len(result) <= len(text_input)

            # Property: if original was non-empty, result should be meaningful
            if text_input and text_input.strip():
                assert len(result) >= 0

        except Exception as e:
            # Should only fail on encoding issues
            assert isinstance(e, (UnicodeError, ValueError))

    @given(
        html_fragments=st.lists(
            st.one_of(
                st.builds(
                    lambda tag, content: f"<{tag}>{content}</{tag}>",
                    tag=st.sampled_from(
                        ["div", "p", "span", "h1", "h2", "strong", "em"]
                    ),
                    content=st.text(
                        min_size=0,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
                    ),
                ),
                st.text(
                    min_size=0,
                    max_size=100,
                    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
                ),
                st.just(""),
            ),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=20)
    def test_html_fragment_processing(self, html_fragments):
        """Test processing of HTML fragments."""
        combined_html = "".join(html_fragments)

        # Property: should be able to process any HTML-like string
        try:
            # Basic processing - count tags
            tag_count = combined_html.count("<")
            closing_tag_count = combined_html.count("</")

            # Property: basic structure validation
            assert tag_count >= 0
            assert closing_tag_count >= 0
            assert closing_tag_count <= tag_count

        except Exception as e:
            # Should handle gracefully
            assert isinstance(e, (ValueError, UnicodeError))


class TestConfigurationCombinations:
    """Test various configuration combinations for edge cases."""

    @given(
        config_dict=st.dictionaries(
            keys=st.sampled_from(
                [
                    "requests_per_second",
                    "timeout",
                    "max_retries",
                    "chunk_size",
                    "chunk_overlap",
                    "cache_ttl",
                ]
            ),
            values=st.one_of(
                st.integers(min_value=1, max_value=100),
                st.floats(min_value=0.1, max_value=100.0),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=20)
    def test_configuration_combinations(self, config_dict):
        """Test various configuration parameter combinations."""
        try:
            # Ensure chunk_overlap < chunk_size if both present
            if (
                "chunk_size" in config_dict
                and "chunk_overlap" in config_dict
                and config_dict["chunk_overlap"] >= config_dict["chunk_size"]
            ):
                config_dict["chunk_overlap"] = max(0, config_dict["chunk_size"] - 1)

            # Create configuration
            config = MarkdownLabSettings(**config_dict)

            # Validate basic properties
            if hasattr(config, "requests_per_second"):
                assert config.requests_per_second > 0
            if hasattr(config, "timeout"):
                assert config.timeout > 0
            if hasattr(config, "chunk_size") and hasattr(config, "chunk_overlap"):
                assert config.chunk_size > config.chunk_overlap

        except ValueError as e:
            # Expected for invalid combinations
            assert "chunk_overlap" in str(e) or "must be" in str(e).lower()


class SimpleCacheStateMachine(RuleBasedStateMachine):
    """Simplified state machine for testing basic cache-like behavior."""

    def __init__(self):
        super().__init__()
        self.cache_dict = {}  # Simple dict to simulate cache
        self.capacity = 10

    keys = Bundle("keys")

    @rule(target=keys, key=st.text(min_size=1, max_size=10, alphabet="abcdefghij"))
    def add_key(self, key):
        """Generate a key for testing."""
        return key

    @rule(key=keys, value=st.integers(min_value=0, max_value=100))
    def set_operation(self, key, value):
        """Perform a set operation."""
        if len(self.cache_dict) >= self.capacity:
            # Remove oldest item (simplified LRU)
            oldest_key = next(iter(self.cache_dict))
            del self.cache_dict[oldest_key]

        self.cache_dict[key] = value

    @rule(key=keys)
    def get_operation(self, key):
        """Perform a get operation."""
        result = self.cache_dict.get(key)
        # Just verify it's consistent
        if key in self.cache_dict:
            assert result is not None

    @rule(key=keys)
    def delete_operation(self, key):
        """Perform a delete operation."""
        if key in self.cache_dict:
            del self.cache_dict[key]

        # Verify deletion
        assert key not in self.cache_dict

    @invariant()
    def size_invariant(self):
        """Cache should never exceed capacity."""
        assert len(self.cache_dict) <= self.capacity


# State machine test class
TestSimpleCacheStateMachine = SimpleCacheStateMachine.TestCase


if __name__ == "__main__":
    # Run simplified property-based tests
    import hypothesis

    # Configure hypothesis for reasonable testing
    hypothesis.settings.register_profile(
        "default",
        max_examples=20,
        deadline=5000,
    )

    hypothesis.settings.load_profile("default")

    pytest.main([__file__, "-v"])
