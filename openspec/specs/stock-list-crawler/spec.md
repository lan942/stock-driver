# stock-list-crawler Specification

## Purpose
股票列表爬虫：从多个数据源获取A股股票代码和名称列表，支持主备源自动切换，确保列表数据的准确性和完整性。

## Requirements
### Requirement: Fetch stock list from primary source

The crawler SHALL fetch the complete list of A-share stocks from the primary akshare interface (`stock_info_a_code_name`)，该接口从新浪数据源获取数据。

#### Scenario: Successful fetch from primary source
- **WHEN** the crawler is invoked with no arguments
- **THEN** it SHALL return a list of all A-share stocks with their codes and names
- **AND** 数据来源为新浪（akshare stock_info_a_code_name接口）

#### Scenario: Primary source rate limited
- **WHEN** the primary source returns HTTP 429 or rate limit error
- **THEN** the crawler SHALL trigger the rate limiter to retry with exponential backoff

### Requirement: Fallback to secondary source

主源失败时，爬虫 SHALL 自动切换到备用源（东方财富实时快照接口stock_zh_a_spot_em）获取股票列表。

#### Scenario: Fallback to Eastmoney snapshot
- **WHEN** 主源（新浪）爬取失败（网络错误/超时/返回空数据）
- **THEN** 爬虫 SHALL 自动切换到东方财富实时快照接口（stock_zh_a_spot_em）
- **AND** 从实时快照数据中提取code和name字段作为股票列表

#### Scenario: Both sources failed
- **WHEN** 主源和备用源均失败
- **THEN** 爬虫 SHALL 抛出CrawlerError异常
- **AND** 错误信息SHALL 记录到CrawlStatus的error_message字段

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
- **AND** code字段 SHALL 为纯数字字符串（不含前缀）

### Requirement: Handle fetch errors gracefully

The crawler SHALL log errors and raise exceptions for critical failures without crashing the entire process.

#### Scenario: Network error occurs
- **WHEN** a network error occurs during fetch
- **THEN** the crawler SHALL raise a `CrawlerError` with descriptive message

#### Scenario: Empty data from all sources
- **WHEN** 所有数据源返回空数据
- **THEN** 爬虫 SHALL 抛出CrawlerError异常，错误信息为"所有数据源返回空数据"

### Requirement: Rate limit handling

The crawler SHALL implement rate limiting to avoid being blocked by data sources.

#### Scenario: Rate limit detected
- **WHEN** 数据源返回速率限制错误（HTTP 429/请求过于频繁）
- **THEN** 爬虫 SHALL 使用指数退避策略重试
- **AND** 最大重试等待时间不超过60秒
