# api-rate-limiter Specification

## Purpose
TBD - created by archiving change stock-crawler-base. Update Purpose after archive.
## Requirements
### Requirement: Track request count and timing

The rate limiter SHALL track requests to prevent exceeding API limits. It SHALL use a sliding window approach to count requests.

#### Scenario: Request within limit
- **WHEN** a request is made and the rate limit has not been exceeded
- **THEN** the request SHALL be allowed immediately

#### Scenario: Request exceeds limit
- **WHEN** a request is made and the rate limit would be exceeded
- **THEN** the request SHALL be blocked until the window slides

### Requirement: Exponential backoff on rate limit errors

When a rate limit error (HTTP 429) is detected, the rate limiter SHALL implement exponential backoff.

#### Scenario: Rate limit error received
- **WHEN** an HTTP 429 response is received
- **THEN** the rate limiter SHALL wait 1 second before retry
- **AND** if the retry also fails, wait 2 seconds
- **AND** if that fails, wait 4 seconds
- **AND** continue doubling until max wait of 60 seconds is reached

### Requirement: Automatic interface fallback

The rate limiter SHALL maintain a list of backup interfaces and automatically switch when the primary interface is consistently failing.

#### Scenario: Primary interface fails consistently
- **WHEN** the primary interface fails 3 consecutive times
- **THEN** the rate limiter SHALL automatically switch to the next available interface

#### Scenario: All interfaces exhausted
- **WHEN** all configured interfaces have failed
- **THEN** the rate limiter SHALL raise `RateLimitError` and reset interface availability

### Requirement: Configurable parameters

The rate limiter SHALL accept configurable parameters:
- `max_retries`: Maximum retry attempts (default: 3)
- `base_wait`: Initial wait time in seconds (default: 1)
- `max_wait`: Maximum wait time in seconds (default: 60)
- `requests_per_window`: Maximum requests per time window (default: 10)
- `window_seconds`: Time window in seconds (default: 60)

#### Scenario: Default configuration applied
- **WHEN** a rate limiter is created without explicit configuration
- **THEN** default values SHALL be used for all parameters

#### Scenario: Custom configuration applied
- **WHEN** a rate limiter is created with custom `RateLimitConfig`
- **THEN** the custom values SHALL override defaults
- **AND** unspecified values SHALL fall back to defaults

