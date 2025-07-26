"""
Utility module for rate limiting requests.
"""

import time
from typing import Optional

from markdown_lab.core.config import MarkdownLabConfig, get_config


class RequestThrottler:
    """Controls request rate to prevent overloading websites."""

    def __init__(
        self,
        config: Optional[MarkdownLabConfig] = None,
        requests_per_second: Optional[float] = None,
    ):
        """
        Initialize the throttler with centralized configuration.

        Args:
            config: Optional MarkdownLabConfig instance. Uses default if not provided.
            requests_per_second: Override requests per second (deprecated, use config)
        """
        self.config = config or get_config()

        # Use provided parameter or fall back to config for backward compatibility
        rate = (
            requests_per_second
            if requests_per_second is not None
            else self.config.requests_per_second
        )
        self.min_interval = 1.0 / max(0.1, rate)  # Ensure minimum delay
        self.last_request_time: float = 0.0

    def throttle(self) -> None:
        """
        Enforces the configured rate limit by pausing execution if requests are made too quickly.

        Waits as needed to ensure that the minimum interval between requests is maintained.
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)

        self.last_request_time = time.time()
