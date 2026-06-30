# stock-realtime-crawler Specification

## Purpose
TBD - created by archiving change stock-crawler-base. Update Purpose after archive.
## Requirements
### Requirement: Fetch realtime quotes for multiple stocks

The crawler SHALL fetch realtime market data for specified stock codes using akshare `stock_zh_a_spot_em` interface.

#### Scenario: Successful fetch for single stock
- **WHEN** the crawler is invoked with a single stock code
- **THEN** it SHALL return realtime data including open, close, volume, turnover, change_percent

#### Scenario: Batch fetch for multiple stocks
- **WHEN** the crawler is invoked with multiple stock codes
- **THEN** it SHALL return realtime data for all specified stocks

### Requirement: Core fields with standardized units

The crawler SHALL return the following fields with standardized units:

| Field | Unit | Source Note |
|-------|------|-------------|
| code | - | Stock code, e.g., "600519" |
| open | 元 | Opening price |
| close | 元 | Closing price (latest price) |
| volume | 股 | Trading volume |
| turnover | 元 | Trading amount |
| turnover_rate | % | Turnover rate (0-100) |
| change_percent | % | Price change percentage (-100 to 100) |

#### Scenario: Units are standardized
- **WHEN** data is returned from the crawler
- **THEN** all units SHALL be in the standardized format as specified above

### Requirement: Rate limit handling

The crawler SHALL respect rate limits and implement automatic retry with exponential backoff.

#### Scenario: Rate limit detected (HTTP 429)
- **WHEN** the API returns HTTP 429
- **THEN** the crawler SHALL wait with exponential backoff (1s, 2s, 4s, ...) up to 60s max
- **AND** retry the request up to 3 times before switching to backup interface

#### Scenario: All interfaces rate limited
- **WHEN** all available interfaces for realtime data are rate limited
- **THEN** the crawler SHALL raise `RateLimitError` with appropriate message

