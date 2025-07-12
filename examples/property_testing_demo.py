#!/usr/bin/env python3
"""
Demonstration of property-based testing with hypothesis.

This example shows how to use hypothesis for generating test data and
discovering edge cases in the markdown_lab codebase.
"""

import asyncio

from hypothesis import example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from markdown_lab.core.config_v2 import MarkdownLabSettings
from markdown_lab.network.advanced_cache import LRUMemoryCache
from markdown_lab.network.rate_limiter import RateLimiter, TokenBucket


def demo_basic_property_testing():
    """Demonstrate basic property-based testing concepts."""

    @given(
        rate=st.floats(min_value=0.1, max_value=100.0),
        capacity=st.integers(min_value=1, max_value=1000),
    )
    @example(rate=1.0, capacity=10)  # Always test this specific example
    def test_token_bucket_properties(rate, capacity):
        """Token bucket should maintain basic invariants."""
        bucket = TokenBucket(rate=rate, capacity=capacity)

        # Property: tokens should never exceed capacity
        assert bucket.tokens <= bucket.capacity

        # Property: initial tokens should equal capacity
        assert bucket.tokens == bucket.capacity

        # Property: rate and capacity should be preserved
        assert bucket.rate == rate
        assert bucket.capacity == capacity

    # Run the property test
    test_token_bucket_properties()


def demo_configuration_validation():
    """Demonstrate property testing for configuration validation."""

    @given(
        chunk_size=st.integers(min_value=100, max_value=5000),
        chunk_overlap=st.integers(min_value=0, max_value=500),
    )
    def test_chunk_configuration_properties(chunk_size, chunk_overlap):
        """Test chunk configuration validation properties."""
        if chunk_overlap >= chunk_size:
            # Property: Invalid configs should raise ValueError
            try:
                MarkdownLabSettings(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                raise AssertionError("Should have raised ValueError")
            except ValueError as e:
                assert "chunk_overlap" in str(e)
        else:
            # Property: Valid configs should validate successfully
            config = MarkdownLabSettings(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            assert config.chunk_size > config.chunk_overlap

    test_chunk_configuration_properties()


def demo_cache_properties():
    """Demonstrate property testing for cache behavior."""

    @given(
        capacity=st.integers(min_value=1, max_value=20),
        items=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
                st.integers(min_value=0, max_value=1000),
            ),
            min_size=0,
            max_size=50,
            unique_by=lambda x: x[0],  # Unique keys
        ),
    )
    def test_cache_size_property(capacity, items):
        """Test that cache never exceeds its capacity."""
        cache = LRUMemoryCache(max_size=capacity)

        for key, value in items:
            cache.set(key, value)

            # Property: cache size should never exceed capacity
            assert len(cache._cache) <= capacity
            assert len(cache._order) <= capacity

            # Property: internal consistency
            assert len(cache._cache) == len(cache._order)

    test_cache_size_property()


def demo_rate_limiter_consistency():
    """Demonstrate consistency properties of rate limiter."""

    @given(
        bucket_configs=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
                st.floats(min_value=0.1, max_value=10.0),
                st.integers(min_value=1, max_value=100),
            ),
            min_size=1,
            max_size=5,
            unique_by=lambda x: x[0],  # Unique bucket names
        )
    )
    def test_rate_limiter_bucket_management(bucket_configs):
        """Test rate limiter bucket management properties."""
        rate_limiter = RateLimiter()

        # Add all buckets
        for bucket_name, rate, capacity in bucket_configs:
            rate_limiter.add_bucket(bucket_name, rate=rate, capacity=capacity)

        # Property: all buckets should be accessible
        for bucket_name, rate, capacity in bucket_configs:
            bucket = rate_limiter.get_bucket(bucket_name)
            assert bucket is not None
            assert bucket.rate == rate
            assert bucket.capacity == capacity

    test_rate_limiter_bucket_management()


class CacheStateMachineDemo(RuleBasedStateMachine):
    """State machine for comprehensive cache testing."""

    def __init__(self):
        super().__init__()
        self.cache = LRUMemoryCache(max_size=5)
        self.expected_items = {}
        self.operation_count = 0

    keys = Bundle("keys")

    @rule(target=keys, key=st.text(min_size=1, max_size=8, alphabet="abcdefghij"))
    def add_key(self, key):
        """Generate a key for testing."""
        return key

    @rule(key=keys, value=st.integers(min_value=0, max_value=100))
    def set_operation(self, key, value):
        """Perform a set operation."""
        self.cache.set(key, value)
        self.expected_items[key] = value
        self.operation_count += 1

        # Clean up expected items if we exceed capacity
        if len(self.expected_items) > 5:
            # Remove oldest items (simplified for demo)
            keys_to_remove = list(self.expected_items.keys())[:-5]
            for k in keys_to_remove:
                self.expected_items.pop(k, None)

    @rule(key=keys)
    def get_operation(self, key):
        """Perform a get operation."""
        result = self.cache.get(key)
        expected = self.expected_items.get(key)

        if expected is not None and result is not None:
            assert result == expected

        self.operation_count += 1

    @rule(key=keys)
    def delete_operation(self, key):
        """Perform a delete operation."""
        self.cache.delete(key)
        self.expected_items.pop(key, None)
        self.operation_count += 1

        # Verify deletion
        assert self.cache.get(key) is None

    @invariant()
    def size_invariant(self):
        """Cache should never exceed capacity."""
        assert len(self.cache._cache) <= 5
        assert len(self.cache._order) <= 5
        assert len(self.cache._cache) == len(self.cache._order)


def demo_stateful_testing():
    """Demonstrate stateful testing with state machines."""

    # Create and run a state machine test

    # This would normally be run by hypothesis, but we'll simulate it
    state_machine = CacheStateMachineDemo()

    # Simulate some operations
    key1 = state_machine.add_key("key1")
    key2 = state_machine.add_key("key2")

    state_machine.set_operation(key1, 100)
    state_machine.set_operation(key2, 200)
    state_machine.get_operation(key1)
    state_machine.get_operation(key2)
    state_machine.delete_operation(key1)
    state_machine.get_operation(key1)  # Should be None


def demo_edge_case_discovery():
    """Demonstrate how property testing discovers edge cases."""

    @given(
        text_input=st.one_of(
            st.text(),  # Any text
            st.just(""),  # Empty string
            st.text(max_size=0),  # Another way to get empty
            st.text(min_size=1000, max_size=2000),  # Very long text
            st.text(
                alphabet=st.characters(blacklist_characters="\x00\n\r\t")
            ),  # No control chars
            st.binary(),  # Binary data
        )
    )
    @settings(max_examples=20)  # Limited for demo
    def test_text_processing_robustness(text_input):
        """Test that our processing handles various text inputs."""
        try:
            # Simulate text processing
            if isinstance(text_input, bytes):
                text_input = text_input.decode("utf-8", errors="ignore")

            # Property: processing should not crash
            result = str(text_input).strip()

            # Property: result should be a string
            assert isinstance(result, str)

        except UnicodeDecodeError:
            # This is an acceptable failure mode
            pass

    test_text_processing_robustness()


async def demo_async_properties():
    """Demonstrate property testing with async code."""

    @given(
        delays=st.lists(
            st.floats(min_value=0.001, max_value=0.05), min_size=1, max_size=3
        )
    )
    @settings(max_examples=5, deadline=2000)
    async def test_async_rate_limiter(delays):
        """Test async rate limiter properties."""
        rate_limiter = RateLimiter()
        rate_limiter.add_bucket("test", rate=20.0, capacity=100)

        async def make_request(delay):
            await asyncio.sleep(delay)
            async with rate_limiter.acquire("test", tokens=1):
                return True

        # Run requests concurrently
        tasks = [make_request(delay) for delay in delays]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Property: all should succeed
        successful = [r for r in results if r is True]
        assert len(successful) == len(delays)

    await test_async_rate_limiter()


def demo_test_statistics():
    """Demonstrate hypothesis test statistics and reporting."""

    # Example of collecting statistics during testing
    statistics = {
        "config_tests": 0,
        "cache_tests": 0,
        "rate_limiter_tests": 0,
        "edge_cases_found": 0,
    }

    @given(
        config_type=st.sampled_from(["basic", "advanced", "minimal"]),
        parameters=st.dictionaries(
            keys=st.sampled_from(["timeout", "retries", "chunk_size"]),
            values=st.integers(min_value=1, max_value=100),
            min_size=1,
            max_size=3,
        ),
    )
    @settings(max_examples=15)
    def test_configuration_coverage(config_type, parameters):
        """Test configuration with various parameter combinations."""
        statistics["config_tests"] += 1

        try:
            # Create config based on type
            if config_type == "minimal":
                config = MarkdownLabSettings(
                    **{k: v for k, v in parameters.items() if k in ["timeout"]}
                )
            else:
                config = MarkdownLabSettings(**parameters)

            # Property: valid configs should have reasonable defaults
            assert config.timeout > 0
            assert config.max_retries >= 0

        except Exception:
            statistics["edge_cases_found"] += 1

    test_configuration_coverage()


def main():
    """Run all property-based testing demonstrations."""

    # Run demonstrations
    demo_basic_property_testing()
    demo_configuration_validation()
    demo_cache_properties()
    demo_rate_limiter_consistency()
    demo_stateful_testing()
    demo_edge_case_discovery()

    # Run async demo
    asyncio.run(demo_async_properties())

    demo_test_statistics()


if __name__ == "__main__":
    main()
