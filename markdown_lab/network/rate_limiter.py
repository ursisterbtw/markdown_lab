"""
Token bucket rate limiter for sophisticated request throttling.

This module implements a token bucket algorithm that allows:
- Burst capacity for short periods of high activity
- Smooth rate limiting over time
- Configurable rates and capacities
- Both sync and async interfaces
"""

import asyncio
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    The token bucket algorithm allows for burst capacity while maintaining
    an average rate limit over time. Tokens are added at a constant rate
    up to a maximum capacity, and requests consume tokens.

    Args:
        rate: Number of tokens added per second
        capacity: Maximum number of tokens that can be stored
        tokens: Initial number of tokens (defaults to full capacity)
        last_update: Last time tokens were updated
    """

    rate: float  # tokens per second
    capacity: int  # maximum burst size
    tokens: float = field(init=False)
    last_update: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _async_lock: Optional[asyncio.Lock] = field(default=None, repr=False)

    def __post_init__(self):
        # Initialize with full capacity
        self.tokens = float(self.capacity)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        # Add new tokens based on time elapsed
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now

    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def acquire_sync(self, tokens: int = 1) -> None:
        """
        Acquire tokens, blocking until available.

        Args:
            tokens: Number of tokens to acquire
        """
        while True:
            with self._lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Calculate wait time
                needed = tokens - self.tokens
                wait_time = needed / self.rate

            # Sleep outside the lock
            time.sleep(wait_time)

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens asynchronously, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire
        """
        # Lazy initialization of async lock
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()

        while True:
            async with self._async_lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Calculate wait time
                needed = tokens - self.tokens
                wait_time = needed / self.rate

            # Sleep outside the lock
            await asyncio.sleep(wait_time)

    @property
    def available_tokens(self) -> float:
        """Get current number of available tokens."""
        with self._lock:
            self._refill()
            return self.tokens

    def time_until_tokens(self, tokens: int = 1) -> float:
        """Calculate time until specified tokens are available."""
        with self._lock:
            self._refill()

            return 0.0 if self.tokens >= tokens else (tokens - self.tokens) / self.rate


class RateLimiter:
    """
    High-level rate limiter with multiple token buckets for different operations.
    """

    def __init__(self):
        # Different buckets for different operations
        self.buckets = {
            "default": TokenBucket(rate=1.0, capacity=10),
            "api": TokenBucket(rate=10.0, capacity=50),
            "scrape": TokenBucket(rate=2.0, capacity=20),
            "batch": TokenBucket(rate=100.0, capacity=500),
        }

    def configure_bucket(self, name: str, rate: float, capacity: int) -> None:
        """
        Configure or create a token bucket.

        Args:
            name: Name of the bucket
            rate: Tokens per second
            capacity: Maximum burst capacity
        """
        self.buckets[name] = TokenBucket(rate=rate, capacity=capacity)

    @contextmanager
    def limit_sync(self, bucket_name: str = "default", tokens: int = 1):
        """
        Context manager for synchronous rate limiting.

        Example:
            with rate_limiter.limit_sync('api'):
                response = requests.get(url)
        """
        bucket = self.buckets.get(bucket_name, self.buckets["default"])
        bucket.acquire_sync(tokens)
        yield

    @asynccontextmanager
    async def limit(self, bucket_name: str = "default", tokens: int = 1):
        """
        Async context manager for rate limiting.

        Example:
            async with rate_limiter.limit('api'):
                response = await client.get(url)
        """
        bucket = self.buckets.get(bucket_name, self.buckets["default"])
        await bucket.acquire(tokens)
        yield

    def try_acquire(self, bucket_name: str = "default", tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking."""
        bucket = self.buckets.get(bucket_name, self.buckets["default"])
        return bucket.try_acquire(tokens)

    def get_stats(self) -> dict:
        """Get current statistics for all buckets."""
        return {
            name: {
                "available": bucket.available_tokens,
                "capacity": bucket.capacity,
                "rate": bucket.rate,
                "utilization": (
                    1 - (bucket.available_tokens / bucket.capacity)
                    if bucket.capacity > 0
                    else 0.0
                ),
            }
            for name, bucket in self.buckets.items()
        }


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# Convenience functions
@asynccontextmanager
async def rate_limit(bucket_name: str = "default", tokens: int = 1):
    """Convenience function for async rate limiting."""
    limiter = get_rate_limiter()
    async with limiter.limit(bucket_name, tokens):
        yield


@contextmanager
def rate_limit_sync(bucket_name: str = "default", tokens: int = 1):
    """Convenience function for sync rate limiting."""
    limiter = get_rate_limiter()
    with limiter.limit_sync(bucket_name, tokens):
        yield
