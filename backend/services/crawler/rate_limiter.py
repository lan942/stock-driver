from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    max_retries: int = 3
    base_wait: float = 1.0
    max_wait: float = 60.0
    requests_per_window: int = 10
    window_seconds: float = 60.0


class SlidingWindowCounter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: deque[float] = deque()
        self._lock = threading.Lock()

    def can_make_request(self) -> bool:
        now = time.time()
        with self._lock:
            cutoff = now - self._window_seconds
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            return len(self._requests) < self._max_requests

    def record_request(self) -> None:
        now = time.time()
        with self._lock:
            self._requests.append(now)

    def wait_time_for_next_slot(self) -> float:
        now = time.time()
        with self._lock:
            if len(self._requests) < self._max_requests:
                return 0.0
            cutoff = now - self._window_seconds
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            if len(self._requests) < self._max_requests:
                return 0.0
            earliest = self._requests[0]
            return max(0.0, earliest + self._window_seconds - now)

    @property
    def current_count(self) -> int:
        now = time.time()
        with self._lock:
            cutoff = now - self._window_seconds
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            return len(self._requests)


class ExponentialBackoff:
    def __init__(
        self,
        base_wait: float = 1.0,
        max_wait: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        self._base_wait = base_wait
        self._max_wait = max_wait
        self._max_retries = max_retries
        self._attempt = 0

    def reset(self) -> None:
        self._attempt = 0

    def next_wait_time(self) -> float:
        wait_time = min(self._base_wait * (2 ** self._attempt), self._max_wait)
        self._attempt += 1
        return wait_time

    @property
    def has_more_retries(self) -> bool:
        return self._attempt < self._max_retries

    @property
    def attempt_count(self) -> int:
        return self._attempt


class RateLimiter:
    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self._config = config or RateLimitConfig()
        self._counter = SlidingWindowCounter(
            max_requests=self._config.requests_per_window,
            window_seconds=self._config.window_seconds,
        )
        self._backoff = ExponentialBackoff(
            base_wait=self._config.base_wait,
            max_wait=self._config.max_wait,
            max_retries=self._config.max_retries,
        )

    def wait_for_slot(self) -> None:
        wait_time = self._counter.wait_time_for_next_slot()
        if wait_time > 0:
            logger.info("Rate limit reached, waiting %.1fs for next slot", wait_time)
            time.sleep(wait_time)
        self._counter.record_request()

    def can_make_request(self) -> bool:
        return self._counter.can_make_request()

    def handle_rate_limit_error(self) -> float:
        wait_time = self._backoff.next_wait_time()
        logger.warning(
            "Rate limit error, attempt %d/%d, waiting %.1fs",
            self._backoff.attempt_count,
            self._config.max_retries,
            wait_time,
        )
        time.sleep(wait_time)
        return wait_time

    def reset_backoff(self) -> None:
        self._backoff.reset()

    @property
    def has_more_retries(self) -> bool:
        return self._backoff.has_more_retries

    @property
    def current_request_count(self) -> int:
        return self._counter.current_count

    @property
    def config(self) -> RateLimitConfig:
        return self._config
