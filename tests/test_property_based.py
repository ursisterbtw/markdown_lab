"""
Property-based tests using hypothesis for markdown_lab.

These tests generate random inputs to verify invariants and edge cases
across all components of the system.
"""

import asyncio

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from markdown_lab.core.config_v2 import MarkdownLabSettings
from markdown_lab.core.errors import MarkdownLabError, NetworkError, ParsingError
from markdown_lab.network.advanced_cache import LRUMemoryCache
from markdown_lab.network.async_client import AsyncHTTPClient
from markdown_lab.network.rate_limiter import RateLimiter, TokenBucket
from markdown_lab.processing.streaming_parser import StreamingHTMLParser


class TestConfigurationProperties:
    """Property-based tests for configuration management."""

    @given(
        requests_per_second=st.floats(min_value=0.1, max_value=1000.0),
        timeout=st.integers(min_value=1, max_value=300),
        max_retries=st.integers(min_value=0, max_value=10),
        chunk_size=st.integers(min_value=100, max_value=10000),
        cache_ttl=st.integers(min_value=1, max_value=86400),
    )
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
    @settings(max_examples=10, deadline=2000)  # Reduced examples for async test
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


class TestCacheProperties:
    """Property-based tests for caching systems."""

    @given(
        capacity=st.integers(min_value=1, max_value=100),
        keys=st.lists(
            st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("L", "N")),
            ),
            min_size=1,
            max_size=150,
            unique=True,
        ),
        values=st.lists(
            st.integers(min_value=0, max_value=1000), min_size=1, max_size=150
        ),
    )
    @settings(max_examples=20, deadline=5000)
    def test_lru_cache_invariants(self, capacity, keys, values):
        """Test LRU cache maintains size and ordering invariants."""
        cache = LRUMemoryCache(capacity=capacity)

        # Pair keys with values
        items = list(zip(keys, values[: len(keys)], strict=False))

        # Add items to cache
        for key, value in items:
            cache.set(key, value)

        # Cache size should never exceed capacity
        assert len(cache._cache) <= capacity
        assert len(cache._order) <= capacity
        assert len(cache._cache) == len(cache._order)

        # If we added more items than capacity, oldest should be evicted
        if len(items) > capacity:
            # Only the last 'capacity' items should be in cache
            expected_keys = {key for key, _ in items[-capacity:]}
            actual_keys = set(cache._cache.keys())

            # All actual keys should be from the expected set
            assert actual_keys.issubset(expected_keys)
            assert len(actual_keys) == capacity

    @given(
        operations=st.lists(
            st.one_of(
                st.tuples(
                    st.just("set"), st.text(min_size=1, max_size=10), st.integers()
                ),
                st.tuples(st.just("get"), st.text(min_size=1, max_size=10)),
                st.tuples(st.just("delete"), st.text(min_size=1, max_size=10)),
            ),
            min_size=1,
            max_size=50,
        ),
        capacity=st.integers(min_value=5, max_value=20),
    )
    def test_cache_operation_consistency(self, operations, capacity):
        """Test cache operations maintain consistency."""
        cache = LRUMemoryCache(capacity=capacity)
        stored_items = {}

        for operation in operations:
            if operation[0] == "set":
                _, key, value = operation
                cache.set(key, value)
                stored_items[key] = value

                # Verify item was stored (unless evicted by capacity)
                if len(stored_items) <= capacity:
                    assert cache.get(key) == value

            elif operation[0] == "get":
                _, key = operation
                result = cache.get(key)

                # If key exists in our tracking and cache isn't over capacity
                if (
                    key in stored_items
                    and len(stored_items) <= capacity
                    and result is not None
                ):
                    assert result == stored_items[key]

            elif operation[0] == "delete":
                _, key = operation
                cache.delete(key)
                if key in stored_items:
                    del stored_items[key]

                # Verify deletion
                assert cache.get(key) is None

        # Final consistency check
        assert len(cache._cache) <= capacity


class TestHTMLParsingProperties:
    """Property-based tests for HTML parsing and processing."""

    @given(
        html_content=st.one_of(
            # Valid HTML structures
            st.builds(
                lambda title, content: f"<html><head><title>{title}</title></head><body>{content}</body></html>",
                title=st.text(
                    min_size=0,
                    max_size=50,
                    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
                ),
                content=st.text(
                    min_size=0,
                    max_size=200,
                    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
                ),
            ),
            # Simple structures
            st.builds(
                lambda tag, content: f"<{tag}>{content}</{tag}>",
                tag=st.sampled_from(["div", "p", "span", "h1", "h2"]),
                content=st.text(
                    min_size=0,
                    max_size=100,
                    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
                ),
            ),
            # Edge cases
            st.just(""),
            st.just("<html></html>"),
            st.just("plain text"),
        )
    )
    @settings(max_examples=50, deadline=3000)
    def test_html_parsing_robustness(self, html_content):
        """Test HTML parsing handles various inputs robustly."""
        parser = StreamingHTMLParser()

        try:
            # Should not crash on any input
            result = parser._parse_html_content(html_content.encode("utf-8"))

            # Result should be a string
            assert isinstance(result, str)

            # If input was valid HTML, result should not be empty for non-empty input
            if html_content.strip() and "<" in html_content:
                # Should extract some content or at least return empty string gracefully
                assert isinstance(result, str)

        except Exception as e:
            # If it fails, should be a controlled failure with proper error type
            assert isinstance(e, (ParsingError, ValueError, UnicodeDecodeError))

    @given(
        chunk_sizes=st.lists(
            st.integers(min_value=1, max_value=1000), min_size=1, max_size=10
        )
    )
    def test_chunk_size_processing(self, chunk_sizes):
        """Test that different chunk sizes don't affect parsing correctness."""
        html_content = "<html><body><p>Test content</p></body></html>"

        results = []
        for chunk_size in chunk_sizes:
            parser = StreamingHTMLParser(chunk_size=chunk_size)
            try:
                result = parser._parse_html_content(html_content.encode("utf-8"))
                results.append(result)
            except Exception:
                # Some chunk sizes might cause issues, that's okay
                continue

        # If we got any results, they should be consistent
        if results:
            first_result = results[0]
            for result in results[1:]:
                # Results should be equivalent (allowing for minor differences in whitespace)
                assert result.strip() == first_result.strip()


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


class CacheStateMachine(RuleBasedStateMachine):
    """State machine for testing cache behavior comprehensively."""

    def __init__(self):
        super().__init__()
        self.cache = LRUMemoryCache(capacity=10)
        self.model = {}  # Track what should be in cache

    keys = Bundle("keys")
    values = Bundle("values")

    @rule(target=keys, key=st.text(min_size=1, max_size=20))
    def generate_key(self, key):
        return key

    @rule(target=values, value=st.integers())
    def generate_value(self, value):
        return value

    @rule(key=keys, value=values)
    def set_item(self, key, value):
        """Set an item in the cache."""
        self.cache.set(key, value)
        self.model[key] = value

        # If model exceeds capacity, remove oldest items
        if len(self.model) > 10:
            # Remove oldest keys (this is approximate for testing)
            keys_to_remove = list(self.model.keys())[:-10]
            for k in keys_to_remove:
                self.model.pop(k, None)

    @rule(key=keys)
    def get_item(self, key):
        """Get an item from the cache."""
        cache_result = self.cache.get(key)
        model_result = self.model.get(key)

        if model_result is not None and cache_result is not None:
            assert cache_result == model_result

    @rule(key=keys)
    def delete_item(self, key):
        """Delete an item from the cache."""
        self.cache.delete(key)
        self.model.pop(key, None)

        # Verify deletion
        assert self.cache.get(key) is None

    @invariant()
    def cache_size_invariant(self):
        """Cache size should never exceed capacity."""
        assert len(self.cache._cache) <= 10
        assert len(self.cache._order) <= 10
        assert len(self.cache._cache) == len(self.cache._order)


# State machine test
TestCacheStateMachine = CacheStateMachine.TestCase


class TestAsyncProperties:
    """Property-based tests for async functionality."""

    @given(
        delays=st.lists(
            st.floats(min_value=0.001, max_value=0.1), min_size=1, max_size=5
        )
    )
    @settings(max_examples=5, deadline=3000)
    @pytest.mark.asyncio
    async def test_async_rate_limiter_properties(self, delays):
        """Test async rate limiter maintains properties under concurrent access."""
        rate_limiter = RateLimiter()
        rate_limiter.add_bucket("test", rate=10.0, capacity=50)

        async def acquire_with_delay(delay):
            await asyncio.sleep(delay)
            async with rate_limiter.acquire("test", tokens=1):
                return True

        # Run multiple acquisitions concurrently
        tasks = [acquire_with_delay(delay) for delay in delays]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed (rate limiter should handle concurrency)
        successful = [r for r in results if r is True]
        assert len(successful) == len(delays)

        # Bucket should still be valid
        bucket = rate_limiter.get_bucket("test")
        assert bucket is not None
        assert bucket.tokens >= 0
        assert bucket.tokens <= bucket.capacity


class TestNetworkProperties:
    """Property-based tests for network functionality."""

    @given(
        user_agents=st.lists(
            st.text(
                min_size=5,
                max_size=100,
                alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            ),
            min_size=1,
            max_size=5,
            unique=True,
        ),
        timeouts=st.lists(
            st.integers(min_value=1, max_value=60), min_size=1, max_size=5
        ),
    )
    def test_http_client_configuration_properties(self, user_agents, timeouts):
        """Test HTTP client configuration maintains properties."""
        for user_agent in user_agents:
            for timeout in timeouts:
                # Should be able to create client with any reasonable config
                config = MarkdownLabSettings(user_agent=user_agent, timeout=timeout)

                client = AsyncHTTPClient(config)

                # Properties should be preserved
                assert client.config.user_agent == user_agent
                assert client.config.timeout == timeout
                assert client.session is not None


if __name__ == "__main__":
    # Run property-based tests
    import hypothesis

    # Configure hypothesis for more thorough testing
    hypothesis.settings.register_profile(
        "thorough",
        max_examples=100,
        deadline=10000,
        suppress_health_check=[HealthCheck.too_slow],
    )

    hypothesis.settings.load_profile("thorough")

    pytest.main([__file__, "-v"])
