# stock-list-crawler Specification

## Purpose
TBD - created by archiving change stock-crawler-base. Update Purpose after archive.
## Requirements
### Requirement: Fetch stock list from primary source

The crawler SHALL fetch the complete list of A-share stocks from the primary akshare interface (`stock_info_a_code_name`).

#### Scenario: Successful fetch
- **WHEN** the crawler is invoked with no arguments
- **THEN** it SHALL return a list of all A-share stocks with their codes and names

#### Scenario: Primary source rate limited
- **WHEN** the primary source returns HTTP 429 or rate limit error
- **THEN** the crawler SHALL trigger the rate limiter to retry with exponential backoff

### Requirement: Return normalized data format

The crawler SHALL return stock list data in a standardized format:
```python
{
    "code": str,   # Stock code, e.g., "600519"
    "name": str,   # Stock name, e.g., "贵州茅台"
}
```

#### Scenario: Data returned in normalized format
- **WHEN** the crawler successfully fetches stock list
- **THEN** each item SHALL contain only `code` and `name` fields

### Requirement: Handle fetch errors gracefully

The crawler SHALL log errors and raise exceptions for critical failures without crashing the entire process.

#### Scenario: Network error occurs
- **WHEN** a network error occurs during fetch
- **THEN** the crawler SHALL raise a `CrawlerError` with descriptive message

