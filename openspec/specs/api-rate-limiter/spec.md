# api-rate-limiter Specification

## Purpose
API 速率限制器：提供滑动窗口计数与指数退避原语，防止爬虫超过数据源速率限制被封禁。本模块仅提供限流原语，多源切换与重试编排由 `CrawlerBase` 负责。

## Requirements

### Requirement: Track request count and timing

The rate limiter SHALL track requests to prevent exceeding API limits. It SHALL use a sliding window approach (`SlidingWindowCounter`) to count requests.

#### Scenario: Request within limit
- **WHEN** a request is made and the rate limit has not been exceeded
- **THEN** the request SHALL be allowed immediately (via `wait_for_slot`)

#### Scenario: Request exceeds limit
- **WHEN** a request is made and the rate limit would be exceeded
- **THEN** `wait_for_slot` SHALL block until the window slides enough to free a slot

### Requirement: Exponential backoff primitive

The rate limiter SHALL provide an `ExponentialBackoff` primitive computing wait times (1s, 2s, 4s, ...) capped by `max_wait`.

**Note**: 实际重试编排由 `CrawlerBase._fetch_with_retry` 调用 `time.sleep` 完成，`RateLimiter.handle_rate_limit_error` 仅作为备用同步原语。

#### Scenario: Backoff sequence
- **WHEN** `next_wait_time` is called repeatedly
- **THEN** the returned values SHALL be 1, 2, 4, 8, ... capped by `max_wait`

### Requirement: Configurable parameters

The rate limiter SHALL accept configurable parameters via `RateLimitConfig`:
- `max_retries`: Maximum retry attempts (default: 3)
- `base_wait`: Initial wait time in seconds (default: 1.0)
- `max_wait`: Maximum wait time in seconds (default: 60.0)
- `requests_per_window`: Maximum requests per time window (default: 10)
- `window_seconds`: Time window in seconds (default: 60.0)

#### Scenario: Default configuration applied
- **WHEN** a rate limiter is created without explicit configuration
- **THEN** default values SHALL be used for all parameters

#### Scenario: Custom configuration applied
- **WHEN** a rate limiter is created with custom `RateLimitConfig`
- **THEN** the custom values SHALL override defaults
- **AND** unspecified values SHALL fall back to defaults

### Requirement: Multi-source switching (delegated to CrawlerBase)

`CrawlerBase` SHALL orchestrate source switching using the rate limiter as a primitive.

#### Scenario: Primary interface fails consistently
- **WHEN** the primary source raises a non-rate-limit exception
- **THEN** `CrawlerBase` SHALL switch to the next available source via `_switch_to_next_source`

#### Scenario: All interfaces exhausted
- **WHEN** all configured sources have failed
- **THEN** `CrawlerBase.fetch` SHALL return a `CrawlerResult` with `success=False` and the last error message
