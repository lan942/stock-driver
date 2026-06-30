import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("Manual Test 7.5: Rate Limit Retry & Interface Switching")
print("=" * 60)

from backend.services.crawler.base import CrawlerBase, CrawlerResult, RateLimitError
from backend.services.crawler.rate_limiter import RateLimiter, RateLimitConfig

class MockCrawler(CrawlerBase):
    def __init__(self, sources, rate_limiter=None):
        super().__init__(sources=sources, rate_limiter=rate_limiter)
        self.call_count = 0
        self.fail_times = {}

    def _fetch_from_source(self, source, **kwargs):
        self.call_count += 1
        src_name = source["name"]
        fail_count = self.fail_times.get(src_name, 0)
        max_fail = source.get("mock_fail", 0)

        if fail_count < max_fail:
            self.fail_times[src_name] = fail_count + 1
            if source.get("mock_rate_limit", False):
                raise Exception("429 Too Many Requests")
            else:
                raise Exception(f"Mock error from {src_name}")

        return [{"code": "000001", "name": f"data_from_{src_name}"}]

    def _is_rate_limit_error(self, exc):
        return "429" in str(exc) or "rate limit" in str(exc).lower()

print("\n[1/4] Test: Single source with rate limit retries...")
sources = [
    {"name": "src1", "mock_fail": 2, "mock_rate_limit": True, "max_retries": 3, "base_wait": 0.01, "max_wait": 0.1},
]
crawler = MockCrawler(sources)
result = crawler.fetch()
print(f"  Success: {result.success}")
print(f"  Source: {result.source}")
print(f"  Call count: {crawler.call_count}")
print(f"  Expected: success=True, source=src1, calls=3 (2 fail + 1 success)")
passed = result.success and result.source == "src1" and crawler.call_count == 3
print(f"  Result: {'PASSED' if passed else 'FAILED'}")

print("\n[2/4] Test: Single source rate limit exhausted (all retries fail)...")
sources2 = [
    {"name": "src1", "mock_fail": 5, "mock_rate_limit": True, "max_retries": 3, "base_wait": 0.01, "max_wait": 0.1},
]
crawler2 = MockCrawler(sources2)
result2 = crawler2.fetch()
print(f"  Success: {result2.success}")
print(f"  Call count: {crawler2.call_count}")
print(f"  Expected: success=False, calls=3 (all retries)")
passed2 = not result2.success and crawler2.call_count == 3
print(f"  Result: {'PASSED' if passed2 else 'FAILED'}")

print("\n[3/4] Test: Multi-source - primary fails, secondary succeeds...")
sources3 = [
    {"name": "src1", "mock_fail": 5, "mock_rate_limit": False, "max_retries": 1, "base_wait": 0.01, "max_wait": 0.1},
    {"name": "src2", "mock_fail": 0, "max_retries": 3, "base_wait": 0.01, "max_wait": 0.1},
]
crawler3 = MockCrawler(sources3)
result3 = crawler3.fetch()
print(f"  Success: {result3.success}")
print(f"  Source: {result3.source}")
print(f"  Current source index: {crawler3._current_source_idx}")
print(f"  Expected: success=True, source=src2, switched to index 1")
passed3 = result3.success and result3.source == "src2" and crawler3._current_source_idx == 1
print(f"  Result: {'PASSED' if passed3 else 'FAILED'}")

print("\n[4/4] Test: All sources fail...")
sources4 = [
    {"name": "src1", "mock_fail": 5, "max_retries": 1, "base_wait": 0.01, "max_wait": 0.1},
    {"name": "src2", "mock_fail": 5, "max_retries": 1, "base_wait": 0.01, "max_wait": 0.1},
]
crawler4 = MockCrawler(sources4)
result4 = crawler4.fetch()
print(f"  Success: {result4.success}")
print(f"  Has error: {result4.error is not None}")
print(f"  Expected: success=False, has error message")
passed4 = not result4.success and result4.error is not None
print(f"  Result: {'PASSED' if passed4 else 'FAILED'}")

print("\n" + "=" * 60)
all_passed = passed and passed2 and passed3 and passed4
print(f"Test 7.5 Complete - {'ALL PASSED' if all_passed else 'SOME FAILED'}")
print("=" * 60)
