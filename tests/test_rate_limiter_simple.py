import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing rate limiter imports...")
from backend.services.crawler.rate_limiter import (
    SlidingWindowCounter,
    ExponentialBackoff,
    RateLimiter,
    RateLimitConfig,
)
print("Rate limiter imports OK")

print("\nTesting SlidingWindowCounter...")
counter = SlidingWindowCounter(max_requests=5, window_seconds=10)
assert counter.can_make_request() is True, "should be able to make request"
for _ in range(5):
    counter.record_request()
assert counter.can_make_request() is False, "should NOT be able to make request"
assert counter.current_count == 5, "count should be 5"
print("SlidingWindowCounter OK")

print("\nTesting ExponentialBackoff...")
backoff = ExponentialBackoff(base_wait=1.0, max_wait=60.0, max_retries=3)
assert backoff.has_more_retries is True
assert backoff.next_wait_time() == 1.0
assert backoff.next_wait_time() == 2.0
assert backoff.next_wait_time() == 4.0
assert backoff.has_more_retries is False
backoff.reset()
assert backoff.attempt_count == 0
assert backoff.has_more_retries is True
print("ExponentialBackoff OK")

print("\nTesting RateLimiter...")
config = RateLimitConfig(
    max_retries=5,
    base_wait=2.0,
    max_wait=30.0,
    requests_per_window=20,
    window_seconds=120.0,
)
limiter = RateLimiter(config)
assert limiter.config.max_retries == 5
assert limiter.config.base_wait == 2.0
assert limiter.can_make_request() is True
limiter.reset_backoff()
assert limiter.has_more_retries is True
print("RateLimiter OK")

print("\n" + "="*50)
print("All rate limiter tests passed!")
print("="*50)
