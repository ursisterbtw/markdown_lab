"""
Advanced rate limiting with token bucket algorithm.

This module provides sophisticated rate limiting with burst support,
per-domain limits, and async compatibility for high-performance
request throttling.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class TokenBucketConfig:
    """Configuration for token bucket rate limiting."""
    rate: float = 1.0  # tokens per second
    burst_size: int = 10  # maximum burst tokens
    per_domain_limit: Optional[float] = None  # per-domain rate limit
    per_domain_burst: Optional[int] = None  # per-domain burst size


class TokenBucket:
    """Token bucket implementation for rate limiting with burst support.

    The token bucket algorithm allows for burst traffic up to the bucket size
    while maintaining the overall rate limit over time.
    """

    def __init__(self, rate: float, bucket_size: int):
        """Initialize token bucket.

        Args:
            rate: Rate at which tokens are added (tokens per second)
            bucket_size: Maximum number of tokens in bucket (burst capacity)
        """
        self.rate = rate
        self.bucket_size = bucket_size
        self.tokens = float(bucket_size)  # Start with full bucket
        self.last_update = time.time()

        logger.debug(f"TokenBucket initialized: {rate} tokens/sec, burst: {bucket_size}")

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until requested tokens will be available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Time in seconds until tokens will be available
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        needed_tokens = tokens - self.tokens
        return needed_tokens / self.rate

    def _refill(self) -> None:
        """Refill bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.rate
        self.tokens = min(self.bucket_size, self.tokens + new_tokens)

        self.last_update = now


class AsyncTokenBucket(TokenBucket):
    """Async version of TokenBucket for use with asyncio."""

    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """Wait until tokens are available and consume them.

        Args:
            tokens: Number of tokens to consume
        """
        while True:
            if self.consume(tokens):
                return

            wait_time = self.time_until_available(tokens)
            if wait_time > 0:
                await asyncio.sleep(wait_time)


class TokenBucketThrottler:
    """Advanced rate limiting with burst support and per-domain limits.

    This throttler uses the token bucket algorithm to provide:
    - Burst traffic support (up to bucket size)
    - Per-domain rate limiting
    - Efficient async operation
    - Automatic token refill based on configured rate
    """

    def __init__(self, config: TokenBucketConfig):
        """Initialize throttler with configuration.

        Args:
            config: Token bucket configuration
        """
        self.config = config

        # Global rate limiting bucket
        self.global_bucket = TokenBucket(config.rate, config.burst_size)

        # Per-domain buckets
        self.domain_buckets: Dict[str, TokenBucket] = {}

        logger.info(
            f"TokenBucketThrottler initialized: "
            f"global {config.rate} req/sec (burst: {config.burst_size}), "
            f"per-domain: {config.per_domain_limit} req/sec"
        )

    def throttle(self, url: Optional[str] = None, tokens: int = 1) -> None:
        """Synchronous throttling with token consumption.

        Args:
            url: Optional URL for domain-specific throttling
            tokens: Number of tokens to consume
        """
        # Global throttling
        while not self.global_bucket.consume(tokens):
            wait_time = self.global_bucket.time_until_available(tokens)
            time.sleep(wait_time)

        # Per-domain throttling
        if url and self.config.per_domain_limit:
            domain = urlparse(url).netloc
            domain_bucket = self._get_domain_bucket(domain)

            while not domain_bucket.consume(tokens):
                wait_time = domain_bucket.time_until_available(tokens)
                time.sleep(wait_time)

    def can_proceed(self, url: Optional[str] = None, tokens: int = 1) -> bool:
        """Check if request can proceed without waiting.

        Args:
            url: Optional URL for domain-specific checking
            tokens: Number of tokens needed

        Returns:
            True if request can proceed immediately
        """
        # Check global bucket
        if not self.global_bucket.consume(tokens):
            return False

        # Check domain bucket
        if url and self.config.per_domain_limit:
            domain = urlparse(url).netloc
            domain_bucket = self._get_domain_bucket(domain)
            if not domain_bucket.consume(tokens):
                # Return tokens to global bucket since domain is limiting
                self.global_bucket.tokens += tokens
                return False

        return True

    def time_until_ready(self, url: Optional[str] = None, tokens: int = 1) -> float:
        """Calculate time until request can proceed.

        Args:
            url: Optional URL for domain-specific calculation
            tokens: Number of tokens needed

        Returns:
            Time in seconds until request can proceed
        """
        global_wait = self.global_bucket.time_until_available(tokens)

        if url and self.config.per_domain_limit:
            domain = urlparse(url).netloc
            domain_bucket = self._get_domain_bucket(domain)
            domain_wait = domain_bucket.time_until_available(tokens)
            return max(global_wait, domain_wait)

        return global_wait

    def _get_domain_bucket(self, domain: str) -> TokenBucket:
        """Get or create token bucket for domain.

        Args:
            domain: Domain name

        Returns:
            TokenBucket for the domain
        """
        if domain not in self.domain_buckets:
            rate = self.config.per_domain_limit or self.config.rate
            burst = self.config.per_domain_burst or self.config.burst_size

            self.domain_buckets[domain] = TokenBucket(rate, burst)
            logger.debug(f"Created domain bucket for {domain}: {rate} req/sec, burst: {burst}")

        return self.domain_buckets[domain]


class AsyncTokenBucketThrottler:
    """Async version of TokenBucketThrottler for high-performance async operations."""

    def __init__(self, config: TokenBucketConfig):
        """Initialize async throttler with configuration.

        Args:
            config: Token bucket configuration
        """
        self.config = config

        # Global rate limiting bucket
        self.global_bucket = AsyncTokenBucket(config.rate, config.burst_size)

        # Per-domain buckets
        self.domain_buckets: Dict[str, AsyncTokenBucket] = {}

        logger.info(
            f"AsyncTokenBucketThrottler initialized: "
            f"global {config.rate} req/sec (burst: {config.burst_size}), "
            f"per-domain: {config.per_domain_limit} req/sec"
        )

    async def acquire(self, url: Optional[str] = None, tokens: int = 1) -> None:
        """Async token acquisition with waiting.

        Args:
            url: Optional URL for domain-specific throttling
            tokens: Number of tokens to acquire
        """
        # Global throttling
        await self.global_bucket.wait_for_tokens(tokens)

        # Per-domain throttling
        if url and self.config.per_domain_limit:
            domain = urlparse(url).netloc
            domain_bucket = self._get_domain_bucket(domain)
            await domain_bucket.wait_for_tokens(tokens)

    async def acquire_many(self, urls: list[str], tokens_per_url: int = 1) -> None:
        """Acquire tokens for multiple URLs efficiently.

        Args:
            urls: List of URLs to acquire tokens for
            tokens_per_url: Tokens needed per URL
        """
        # Group by domain for efficient processing
        domain_groups: Dict[str, int] = {}
        for url in urls:
            domain = urlparse(url).netloc
            domain_groups[domain] = domain_groups.get(domain, 0) + 1

        total_tokens = len(urls) * tokens_per_url

        # Acquire global tokens
        await self.global_bucket.wait_for_tokens(total_tokens)

        # Acquire per-domain tokens if needed
        if self.config.per_domain_limit:
            for domain, count in domain_groups.items():
                domain_bucket = self._get_domain_bucket(domain)
                domain_tokens = count * tokens_per_url
                await domain_bucket.wait_for_tokens(domain_tokens)

    def can_proceed_immediately(self, url: Optional[str] = None, tokens: int = 1) -> bool:
        """Check if request can proceed without async waiting.

        Args:
            url: Optional URL for domain-specific checking
            tokens: Number of tokens needed

        Returns:
            True if request can proceed immediately
        """
        # Check global bucket
        if not self.global_bucket.consume(tokens):
            return False

        # Check domain bucket
        if url and self.config.per_domain_limit:
            domain = urlparse(url).netloc
            domain_bucket = self._get_domain_bucket(domain)
            if not domain_bucket.consume(tokens):
                # Return tokens to global bucket since domain is limiting
                self.global_bucket.tokens += tokens
                return False

        return True

    def _get_domain_bucket(self, domain: str) -> AsyncTokenBucket:
        """Get or create async token bucket for domain.

        Args:
            domain: Domain name

        Returns:
            AsyncTokenBucket for the domain
        """
        if domain not in self.domain_buckets:
            rate = self.config.per_domain_limit or self.config.rate
            burst = self.config.per_domain_burst or self.config.burst_size

            self.domain_buckets[domain] = AsyncTokenBucket(rate, burst)
            logger.debug(f"Created async domain bucket for {domain}: {rate} req/sec, burst: {burst}")

        return self.domain_buckets[domain]


# Convenience functions for creating throttlers
def create_throttler(
    rate: float = 1.0,
    burst_size: int = 10,
    per_domain_limit: Optional[float] = None,
    per_domain_burst: Optional[int] = None
) -> TokenBucketThrottler:
    """Create a synchronous token bucket throttler.

    Args:
        rate: Global requests per second
        burst_size: Maximum burst requests
        per_domain_limit: Optional per-domain rate limit
        per_domain_burst: Optional per-domain burst size

    Returns:
        Configured TokenBucketThrottler
    """
    config = TokenBucketConfig(
        rate=rate,
        burst_size=burst_size,
        per_domain_limit=per_domain_limit,
        per_domain_burst=per_domain_burst
    )
    return TokenBucketThrottler(config)


def create_async_throttler(
    rate: float = 1.0,
    burst_size: int = 10,
    per_domain_limit: Optional[float] = None,
    per_domain_burst: Optional[int] = None
) -> AsyncTokenBucketThrottler:
    """Create an asynchronous token bucket throttler.

    Args:
        rate: Global requests per second
        burst_size: Maximum burst requests
        per_domain_limit: Optional per-domain rate limit
        per_domain_burst: Optional per-domain burst size

    Returns:
        Configured AsyncTokenBucketThrottler
    """
    config = TokenBucketConfig(
        rate=rate,
        burst_size=burst_size,
        per_domain_limit=per_domain_limit,
        per_domain_burst=per_domain_burst
    )
    return AsyncTokenBucketThrottler(config)


# Default configurations for common use cases
DEFAULT_CONFIG = TokenBucketConfig(rate=2.0, burst_size=10)

CONSERVATIVE_CONFIG = TokenBucketConfig(
    rate=0.5,
    burst_size=3,
    per_domain_limit=0.2,
    per_domain_burst=2
)

AGGRESSIVE_CONFIG = TokenBucketConfig(
    rate=10.0,
    burst_size=50,
    per_domain_limit=5.0,
    per_domain_burst=20
)


# Backward compatibility with existing RequestThrottler
class RequestThrottler:
    """Backward compatible wrapper around TokenBucketThrottler."""

    def __init__(self, requests_per_second: float = 1.0):
        """Initialize with simple rate limit.

        Args:
            requests_per_second: Maximum requests per second
        """
        config = TokenBucketConfig(
            rate=requests_per_second,
            burst_size=max(1, int(requests_per_second * 2))  # Allow some burst
        )
        self._throttler = TokenBucketThrottler(config)

    def throttle(self) -> None:
        """Throttle request (backward compatible method)."""
        self._throttler.throttle()
