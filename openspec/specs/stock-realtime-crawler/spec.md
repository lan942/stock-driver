# stock-realtime-crawler Specification

## Purpose
实时行情爬虫：使用东方财富数据源爬取A股全市场实时行情，支持多源自动切换和速率限制处理。

## Requirements
### Requirement: Fetch realtime quotes for multiple stocks with fallback

爬虫 SHALL 优先使用直连东方财富push2 HTTP API获取实时行情，主源失败时自动切换到akshare封装的东方财富接口（stock_zh_a_spot_em）。

#### Scenario: Successful fetch using Eastmoney direct HTTP
- **WHEN** 爬虫被调用获取实时行情
- **THEN** 爬虫 SHALL 优先调用直连东方财富push2 API（https://push2.eastmoney.com/api/qt/clist/get）
- **AND** 若接口返回成功，SHALL 返回标准化后的行情数据

#### Scenario: Fallback to akshare on direct HTTP failure
- **WHEN** 直连东方财富HTTP API失败（ConnectionError/RemoteDisconnected/超时）
- **THEN** 爬虫 SHALL 自动切换到akshare的stock_zh_a_spot_em接口重试
- **AND** 若akshare接口成功，SHALL 返回标准化后的行情数据

#### Scenario: All sources failed
- **WHEN** 直连HTTP和akshare接口均失败
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

#### Scenario: Rate limit detected (HTTP 429 or connection reset)
- **WHEN** the API returns HTTP 429 or connection reset error
- **THEN** the crawler SHALL wait with exponential backoff (1s, 2s, 4s, ...) up to 60s max
- **AND** retry the request up to 3 times before switching to backup interface

#### Scenario: All interfaces rate limited
- **WHEN** all available interfaces for realtime data are rate limited
- **THEN** the crawler SHALL raise `RateLimitError` with appropriate message

### Requirement: Real-time data saved to StockDaily table

系统 SHALL 在每次实时行情爬取成功后，将数据写入StockDaily表（而非Stock表），以支持历史数据回溯。

#### Scenario: realtime data saved to StockDaily
- **WHEN** 实时行情爬取成功获取股票价格数据
- **THEN** 系统 SHALL 将数据写入StockDaily表，包含open、close、high、low、volume、turnover、turnover_rate、change_percent、pe、pb、market_cap字段
- **AND** date字段设置为当前日期（Date类型，不含时间戳）

#### Scenario: data not saved on failed crawl
- **WHEN** 实时行情爬取失败
- **THEN** 系统 SHALL NOT 写入StockDaily表
- **AND** 创建failed状态的CrawlStatus记录
