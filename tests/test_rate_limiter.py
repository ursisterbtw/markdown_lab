"""
Tests for token bucket rate limiter.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from markdown_lab.network.rate_limiter import (
    RateLimiter,
    TokenBucket,
    get_rate_limiter,
    rate_limit,
)


class TestTokenBucket:
    """Test cases for TokenBucket implementation."""

    def test_initialization(self):
        """Test bucket initializes with full capacity."""
        bucket = TokenBucket(rate=10.0, capacity=100)
        assert bucket.available_tokens == 100
        assert bucket.rate == 10.0
        assert bucket.capacity == 100

    def test_try_acquire_success(self):
        """Test successful token acquisition."""
        bucket = TokenBucket(rate=10.0, capacity=100)
        assert bucket.try_acquire(10) is True
        assert 89.9 <= bucket.available_tokens <= 90.1  # Allow small timing variance

    def test_try_acquire_failure(self):
        """Test failed token acquisition when insufficient tokens."""
        bucket = TokenBucket(rate=10.0, capacity=100)
        assert bucket.try_acquire(101) is False
        assert bucket.available_tokens == 100  # No tokens consumed

    def test_refill_over_time(self):
        """Test tokens refill at the specified rate."""
        bucket = TokenBucket(rate=10.0, capacity=100)

        # Consume all tokens
        bucket.try_acquire(100)
        assert bucket.available_tokens <= 0.1  # Allow tiny timing variance

        # Wait for refill
        time.sleep(0.5)  # Should add 5 tokens
        assert 4 <= bucket.available_tokens <= 6  # Allow for timing variance

    def test_capacity_limit(self):
        """Test tokens don't exceed capacity."""
        bucket = TokenBucket(rate=100.0, capacity=50)

        # Wait to ensure refill
        time.sleep(1.0)

        # Should still be at capacity
        assert bucket.available_tokens == 50

    def test_acquire_sync_blocking(self):
        """Test synchronous acquire blocks until tokens available."""
        bucket = TokenBucket(rate=20.0, capacity=10)

        # Consume all tokens
        bucket.try_acquire(10)

        # Measure blocking time
        start = time.time()
        bucket.acquire_sync(5)  # Should take ~0.25 seconds
        elapsed = time.time() - start

        assert 0.2 <= elapsed <= 0.3  # Allow for timing variance

    @pytest.mark.asyncio
    async def test_acquire_async(self):
        """Test asynchronous acquire."""
        bucket = TokenBucket(rate=20.0, capacity=10)

        # Consume all tokens
        bucket.try_acquire(10)

        # Measure async blocking time
        start = time.time()
        await bucket.acquire(5)  # Should take ~0.25 seconds
        elapsed = time.time() - start

        assert 0.2 <= elapsed <= 0.3  # Allow for timing variance

    def test_concurrent_access_sync(self):
        """Test thread-safe synchronous access."""
        bucket = TokenBucket(rate=10.0, capacity=100)
        results = []

        def acquire_tokens():
            success = bucket.try_acquire(25)
            results.append(success)

        # Run 5 threads trying to acquire 25 tokens each
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(acquire_tokens) for _ in range(5)]
            for future in futures:
                future.result()

        # Only 4 should succeed (100 tokens / 25 = 4)
        assert sum(results) == 4
        assert results.count(True) == 4
        assert results.count(False) == 1

    @pytest.mark.asyncio
    async def test_concurrent_access_async(self):
        """Test concurrent async access."""
        bucket = TokenBucket(rate=10.0, capacity=100)

        async def acquire_tokens():
            return bucket.try_acquire(25)

        # Run 5 tasks trying to acquire 25 tokens each
        tasks = [acquire_tokens() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Only 4 should succeed
        assert sum(results) == 4


class TestRateLimiter:
    """Test cases for high-level RateLimiter."""

    def test_multiple_buckets(self):
        """Test managing multiple token buckets."""
        limiter = RateLimiter()

        # Check default buckets exist
        assert "default" in limiter.buckets
        assert "api" in limiter.buckets
        assert "scrape" in limiter.buckets
        assert "batch" in limiter.buckets

    def test_configure_bucket(self):
        """Test configuring custom buckets."""
        limiter = RateLimiter()
        limiter.configure_bucket("custom", rate=5.0, capacity=25)

        assert "custom" in limiter.buckets
        assert limiter.buckets["custom"].rate == 5.0
        assert limiter.buckets["custom"].capacity == 25

    def test_limit_sync_context_manager(self):
        """Test synchronous rate limiting context manager."""
        limiter = RateLimiter()
        limiter.configure_bucket("test", rate=10.0, capacity=1)

        # First request should be immediate
        start = time.time()
        with limiter.limit_sync("test"):
            pass
        assert time.time() - start < 0.1

        # Second request should wait
        start = time.time()
        with limiter.limit_sync("test"):
            pass
        elapsed = time.time() - start
        assert 0.05 <= elapsed <= 0.15  # ~0.1 seconds

    @pytest.mark.asyncio
    async def test_limit_async_context_manager(self):
        """Test asynchronous rate limiting context manager."""
        limiter = RateLimiter()
        limiter.configure_bucket("test", rate=10.0, capacity=1)

        # First request should be immediate
        start = time.time()
        async with limiter.limit("test"):
            pass
        assert time.time() - start < 0.1

        # Second request should wait
        start = time.time()
        async with limiter.limit("test"):
            pass
        elapsed = time.time() - start
        assert 0.05 <= elapsed <= 0.15  # ~0.1 seconds

    def test_get_stats(self):
        """Test statistics reporting."""
        limiter = RateLimiter()
        stats = limiter.get_stats()

        # Check structure
        assert "default" in stats
        assert "available" in stats["default"]
        assert "capacity" in stats["default"]
        assert "rate" in stats["default"]
        assert "utilization" in stats["default"]

        # Check values
        assert stats["default"]["available"] == 10.0
        assert stats["default"]["capacity"] == 10
        assert stats["default"]["utilization"] == 0.0

        # Use some tokens
        limiter.try_acquire("default", 5)
        stats = limiter.get_stats()
        assert 4.9 <= stats["default"]["available"] <= 5.1  # Allow timing variance
        assert 0.49 <= stats["default"]["utilization"] <= 0.51


class TestGlobalInstance:
    """Test global rate limiter instance."""

    def test_singleton_pattern(self):
        """Test get_rate_limiter returns same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    @pytest.mark.asyncio
    async def test_convenience_functions(self):
        """Test convenience rate limiting functions."""
        # Configure test bucket
        limiter = get_rate_limiter()
        limiter.configure_bucket("convenience", rate=10.0, capacity=1)

        # Test async convenience
        start = time.time()
        async with rate_limit("convenience"):
            pass
        assert time.time() - start < 0.1

        # Second call should wait
        start = time.time()
        async with rate_limit("convenience"):
            pass
        elapsed = time.time() - start
        assert 0.05 <= elapsed <= 0.15


@pytest.mark.asyncio
async def test_real_world_scenario():
    """Test realistic usage scenario with mixed operations."""
    limiter = get_rate_limiter()

    # Configure buckets for different operations with tighter limits
    limiter.configure_bucket("api", rate=10.0, capacity=5)  # 10/sec but only 5 burst
    limiter.configure_bucket("scrape", rate=2.0, capacity=2)  # 2/sec with 2 burst

    # Track timing of operations
    timings = []

    async def api_call(i):
        start = time.time()
        async with limiter.limit("api", tokens=1):
            # Simulate API call
            await asyncio.sleep(0.001)
        elapsed = time.time() - start
        timings.append(("api", i, elapsed))

    async def scrape_page(i):
        start = time.time()
        async with limiter.limit("scrape", tokens=1):
            # Simulate scraping
            await asyncio.sleep(0.001)
        elapsed = time.time() - start
        timings.append(("scrape", i, elapsed))

    # Mix of operations
    tasks = []
    for i in range(10):
        if i % 3 == 0:
            tasks.append(scrape_page(i))
        else:
            tasks.append(api_call(i))

    await asyncio.gather(*tasks)

    # Verify rate limiting occurred
    api_timings = [t for t in timings if t[0] == "api"]
    scrape_timings = [t for t in timings if t[0] == "scrape"]

    # With the configured rates and burst limits, operations should show rate limiting
    api_times = [t[2] for t in api_timings]
    scrape_times = [t[2] for t in scrape_timings]

    # At least verify we collected timing data
    assert api_times
    assert scrape_times

    # Verify that operations completed (no errors)
    assert len(timings) == 10

    # With burst limits, later operations should wait
    # Check the last operations took some time (they had to wait for tokens)
    if len(api_times) > 5:
        # After burst capacity, should see some waiting
        later_api_times = sorted(api_times)[5:]
        assert any(t > 0.05 for t in later_api_times)  # Some should wait

    if len(scrape_times) > 2:
        # After burst of 2, scraping should slow down
        later_scrape_times = sorted(scrape_times)[2:]
        assert any(t > 0.1 for t in later_scrape_times)  # Should wait ~0.5s for tokens
