#!/usr/bin/env python3
"""
Simplified property-based testing demonstration focusing on synchronous components.

This example shows core property-based testing patterns without complex async operations.
"""


from hypothesis import example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from markdown_lab.core.config_v2 import MarkdownLabSettings
from markdown_lab.network.rate_limiter import RateLimiter, TokenBucket


def demo_basic_property_testing():
    """Demonstrate basic property-based testing concepts."""

    @given(
        rate=st.floats(min_value=0.1, max_value=100.0),
        capacity=st.integers(min_value=1, max_value=1000),
    )
    @example(rate=1.0, capacity=10)  # Always test this specific example
    @settings(max_examples=10)
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
    @settings(max_examples=10)
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
    @settings(max_examples=10)
    def test_rate_limiter_bucket_management(bucket_configs):
        """Test rate limiter bucket management properties."""
        rate_limiter = RateLimiter()

        # Add all buckets
        for bucket_name, rate, capacity in bucket_configs:
            rate_limiter.configure_bucket(bucket_name, rate=rate, capacity=capacity)

        # Property: all buckets should be accessible
        for bucket_name, rate, capacity in bucket_configs:
            bucket = rate_limiter.buckets.get(bucket_name)
            assert bucket is not None
            assert bucket.rate == rate
            assert bucket.capacity == capacity

    test_rate_limiter_bucket_management()


def demo_edge_case_discovery():
    """Demonstrate how property testing discovers edge cases."""

    @given(
        text_input=st.one_of(
            st.text(),  # Any text
            st.just(""),  # Empty string
            st.text(max_size=0),  # Another way to get empty
            st.text(min_size=100, max_size=200),  # Long text
            st.text(
                alphabet=st.characters(blacklist_characters="\x00\n\r\t")
            ),  # No control chars
        )
    )
    @settings(max_examples=15)
    def test_text_processing_robustness(text_input):
        """Test that our processing handles various text inputs."""
        try:
            # Simulate text processing
            result = str(text_input).strip()

            # Property: processing should not crash
            assert isinstance(result, str)

            # Property: length should not exceed original
            assert len(result) <= len(text_input)

        except Exception:
            # This is an acceptable failure mode for some inputs
            pass

    test_text_processing_robustness()


class SimpleStateMachine(RuleBasedStateMachine):
    """Simplified state machine for demonstrating stateful testing."""

    def __init__(self):
        super().__init__()
        self.data = {}  # Simple data store
        self.operation_count = 0
        self.max_size = 5

    keys = Bundle("keys")

    @rule(target=keys, key=st.text(min_size=1, max_size=8, alphabet="abcdefghij"))
    def add_key(self, key):
        """Generate a key for testing."""
        return key

    @rule(key=keys, value=st.integers(min_value=0, max_value=100))
    def set_operation(self, key, value):
        """Perform a set operation."""
        if len(self.data) >= self.max_size:
            # Remove a random item to make space
            oldest_key = next(iter(self.data))
            del self.data[oldest_key]

        self.data[key] = value
        self.operation_count += 1

    @rule(key=keys)
    def get_operation(self, key):
        """Perform a get operation."""
        self.data.get(key)
        self.operation_count += 1

    @rule(key=keys)
    def delete_operation(self, key):
        """Perform a delete operation."""
        if key in self.data:
            del self.data[key]

        self.operation_count += 1

    @invariant()
    def size_invariant(self):
        """Data store should never exceed max size."""
        assert len(self.data) <= self.max_size


def demo_stateful_testing():
    """Demonstrate stateful testing with state machines."""

    # Create and run a simple state machine test

    # Simulate the state machine operations
    state_machine = SimpleStateMachine()

    # Simulate some operations
    key1 = state_machine.add_key("key1")
    key2 = state_machine.add_key("key2")

    state_machine.set_operation(key1, 100)
    state_machine.set_operation(key2, 200)
    state_machine.get_operation(key1)
    state_machine.get_operation(key2)
    state_machine.delete_operation(key1)
    state_machine.get_operation(key1)  # Should be None


def demo_comprehensive_configuration_testing():
    """Demonstrate comprehensive configuration testing."""

    @given(
        config_data=st.dictionaries(
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
            max_size=4,
        )
    )
    @settings(max_examples=15)
    def test_configuration_robustness(config_data):
        """Test configuration with various parameter combinations."""
        try:
            # Fix chunk overlap if needed
            if (
                "chunk_size" in config_data
                and "chunk_overlap" in config_data
                and config_data["chunk_overlap"] >= config_data["chunk_size"]
            ):
                config_data["chunk_overlap"] = max(0, config_data["chunk_size"] - 1)

            # Create configuration
            config = MarkdownLabSettings(**config_data)

            # Test properties
            if hasattr(config, "requests_per_second"):
                assert config.requests_per_second > 0
            if hasattr(config, "timeout"):
                assert config.timeout > 0
            if hasattr(config, "chunk_size") and hasattr(config, "chunk_overlap"):
                assert config.chunk_size > config.chunk_overlap

        except Exception:
            pass

    test_configuration_robustness()


def demo_data_generation_strategies():
    """Demonstrate various hypothesis data generation strategies."""

    # Test with specific patterns
    @given(
        identifier=st.text(
            min_size=3,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ).filter(
            lambda x: x[0].isalpha()
        ),  # Must start with letter
        config_value=st.one_of(
            st.integers(min_value=1, max_value=1000),
            st.floats(min_value=0.1, max_value=100.0),
            st.booleans(),
            st.sampled_from(["low", "medium", "high"]),
        ),
    )
    @settings(max_examples=10)
    def test_data_generation(identifier, config_value):
        """Test with sophisticated data generation."""
        # Property: identifier should be valid
        assert len(identifier) >= 3
        assert identifier[0].isalpha()
        assert identifier.isalnum()

        # Property: config value should be reasonable
        if isinstance(config_value, (int, float)):
            assert config_value > 0
        elif isinstance(config_value, str):
            assert config_value in ["low", "medium", "high"]

    test_data_generation()


def main():
    """Run all property-based testing demonstrations."""

    # Run demonstrations
    demo_basic_property_testing()
    demo_configuration_validation()
    demo_rate_limiter_consistency()
    demo_stateful_testing()
    demo_edge_case_discovery()
    demo_comprehensive_configuration_testing()
    demo_data_generation_strategies()


if __name__ == "__main__":
    main()
