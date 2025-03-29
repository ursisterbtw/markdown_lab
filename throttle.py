"""
Utility module for rate limiting requests.
"""

import time


class RequestThrottler:
    """Controls request rate to prevent overloading websites."""

    def __init__(self, requests_per_second: float = 1.0):
        """
        Initialize the throttler.

        Args:
            requests_per_second: Maximum number of requests per second
        """
        self.min_interval = 1.0 / max(0.1, requests_per_second)  # Ensure minimum delay
        self.last_request_time: float = 0.0

    def throttle(self) -> None:
        """Wait if necessary to maintain the rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)

        self.last_request_time = time.time()
