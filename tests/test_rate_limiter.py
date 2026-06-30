import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import time
from backend.services.crawler.rate_limiter import (
    SlidingWindowCounter,
    ExponentialBackoff,
    RateLimiter,
    RateLimitConfig,
)


class TestSlidingWindowCounter(unittest.TestCase):
    def test_can_make_request_when_empty(self):
        counter = SlidingWindowCounter(max_requests=5, window_seconds=10)
        self.assertTrue(counter.can_make_request())

    def test_can_make_request_under_limit(self):
        counter = SlidingWindowCounter(max_requests=5, window_seconds=10)
        for _ in range(3):
            counter.record_request()
        self.assertTrue(counter.can_make_request())

    def test_cannot_make_request_at_limit(self):
        counter = SlidingWindowCounter(max_requests=3, window_seconds=10)
        for _ in range(3):
            counter.record_request()
        self.assertFalse(counter.can_make_request())

    def test_current_count(self):
        counter = SlidingWindowCounter(max_requests=10, window_seconds=10)
        self.assertEqual(counter.current_count, 0)
        counter.record_request()
        counter.record_request()
        self.assertEqual(counter.current_count, 2)

    def test_wait_time_zero_when_available(self):
        counter = SlidingWindowCounter(max_requests=10, window_seconds=10)
        self.assertEqual(counter.wait_time_for_next_slot(), 0.0)

    def test_requests_expire_after_window(self):
        counter = SlidingWindowCounter(max_requests=3, window_seconds=0.5)
        counter.record_request()
        counter.record_request()
        counter.record_request()
        self.assertFalse(counter.can_make_request())
        time.sleep(0.6)
        self.assertTrue(counter.can_make_request())


class TestExponentialBackoff(unittest.TestCase):
    def test_initial_state(self):
        backoff = ExponentialBackoff(base_wait=1.0, max_wait=60.0, max_retries=3)
        self.assertEqual(backoff.attempt_count, 0)
        self.assertTrue(backoff.has_more_retries)

    def test_first_wait(self):
        backoff = ExponentialBackoff(base_wait=1.0, max_wait=60.0, max_retries=3)
        wait = backoff.next_wait_time()
        self.assertEqual(wait, 1.0)
        self.assertEqual(backoff.attempt_count, 1)

    def test_exponential_increase(self):
        backoff = ExponentialBackoff(base_wait=1.0, max_wait=60.0, max_retries=5)
        self.assertEqual(backoff.next_wait_time(), 1.0)
        self.assertEqual(backoff.next_wait_time(), 2.0)
        self.assertEqual(backoff.next_wait_time(), 4.0)
        self.assertEqual(backoff.next_wait_time(), 8.0)

    def test_max_wait_cap(self):
        backoff = ExponentialBackoff(base_wait=1.0, max_wait=10.0, max_retries=10)
        for _ in range(5):
            backoff.next_wait_time()
        wait = backoff.next_wait_time()
        self.assertLessEqual(wait, 10.0)

    def test_has_more_retries(self):
        backoff = ExponentialBackoff(base_wait=1.0, max_wait=60.0, max_retries=3)
        self.assertTrue(backoff.has_more_retries)
        backoff.next_wait_time()
        self.assertTrue(backoff.has_more_retries)
        backoff.next_wait_time()
        self.assertTrue(backoff.has_more_retries)
        backoff.next_wait_time()
        self.assertFalse(backoff.has_more_retries)

    def test_reset(self):
        backoff = ExponentialBackoff(base_wait=1.0, max_wait=60.0, max_retries=3)
        backoff.next_wait_time()
        backoff.next_wait_time()
        backoff.reset()
        self.assertEqual(backoff.attempt_count, 0)
        self.assertTrue(backoff.has_more_retries)


class TestRateLimiter(unittest.TestCase):
    def test_initial_config(self):
        config = RateLimitConfig(
            max_retries=5,
            base_wait=2.0,
            max_wait=30.0,
            requests_per_window=20,
            window_seconds=120.0,
        )
        limiter = RateLimiter(config)
        self.assertEqual(limiter.config.max_retries, 5)
        self.assertEqual(limiter.config.base_wait, 2.0)
        self.assertEqual(limiter.config.requests_per_window, 20)

    def test_can_make_request(self):
        limiter = RateLimiter(RateLimitConfig(
            requests_per_window=10,
            window_seconds=60.0,
        ))
        self.assertTrue(limiter.can_make_request())

    def test_wait_for_slot_no_wait(self):
        limiter = RateLimiter(RateLimitConfig(
            requests_per_window=10,
            window_seconds=60.0,
        ))
        start = time.time()
        limiter.wait_for_slot()
        elapsed = time.time() - start
        self.assertLess(elapsed, 0.1)

    def test_reset_backoff(self):
        limiter = RateLimiter()
        limiter.handle_rate_limit_error()
        limiter.reset_backoff()
        self.assertTrue(limiter.has_more_retries)


if __name__ == "__main__":
    unittest.main()
