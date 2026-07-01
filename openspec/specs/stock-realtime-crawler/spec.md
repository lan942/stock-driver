# stock-realtime-crawler Specification

## Purpose
TBD - created by archiving change stock-crawler-base. Update Purpose after archive.
## Requirements
### Requirement: Fetch realtime quotes for multiple stocks

爬虫 SHALL 仅使用东方财富数据源（akshare `stock_zh_a_spot_em`），禁用新浪数据源切换逻辑。

#### Scenario: Successful fetch using Eastmoney only
- **WHEN** 爬虫被调用获取实时行情
- **THEN** 爬虫 SHALL 直接调用akshare `stock_zh_a_spot_em`接口
- **AND** 若接口返回错误（ConnectionError/RemoteDisconnected），SHALL 直接抛出异常，不尝试切换到新浪数据源

#### Scenario: Eastmoney API failure
- **WHEN** 东方财富API返回错误（ConnectionError/RemoteDisconnected）
- **THEN** 爬虫 SHALL 抛出CrawlerError异常
- **AND** 错误信息SHALL 记录到CrawlStatus的error_message字段

### Requirement: Core fields with standardized units

The crawler SHALL return the following fields with standardized units:

| Field | Unit | Source Note |
|-------|------|-------------|
| code | - | Stock code, e.g., "600519" |
| name | - | Stock name |
| open | 元 | Opening price |
| close | 元 | Closing price (latest price) |
| high | 元 | Highest price |
| low | 元 | Lowest price |
| volume | 股 | Trading volume |
| turnover | 元 | Trading amount |
| turnover_rate | % | Turnover rate (0-100) |
| change_percent | % | Price change percentage (-100 to 100) |
| pe | - | Price-to-earnings ratio (动态市盈率) |
| pb | - | Price-to-book ratio |
| market_cap | 元 | Total market capitalization |

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

### Requirement: Update Stock price_date on realtime crawl

系统 SHALL 在每次实时行情爬取成功后，更新Stock记录的price_date字段。

#### Scenario: price_date updated on successful crawl
- **WHEN** 实时行情爬取成功获取股票价格数据
- **THEN** 系统 SHALL 更新Stock记录的price_date为当前日期（Date类型，不含时间戳）
- **AND** 同时更新price、change_percent、volume、turnover等字段

#### Scenario: price_date not updated on failed crawl
- **WHEN** 实时行情爬取失败
- **THEN** 系统 SHALL NOT 更新Stock记录的price_date
- **AND** 保持price_date为上次成功爬取的日期或NULL

