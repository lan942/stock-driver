## MODIFIED Requirements

### Requirement: Fetch stock list from primary source

The crawler SHALL fetch the A-share stock list from a primary source that combines the Shanghai Stock Exchange direct interface (`stock_info_sh_name_code(symbol='主板A股')`) and the Shenzhen Stock Exchange direct interface (`stock_info_sz_name_code(symbol='A股列表')`), merging and de-duplicating by `code`. This replaces the previous aggregate interface `stock_info_a_code_name` which transitively depends on the Beijing Stock Exchange endpoint and fails when BSE is unreachable.

#### Scenario: Successful fetch from SH+SZ direct sources
- **WHEN** the crawler is invoked with no arguments
- **AND** both `stock_info_sh_name_code` and `stock_info_sz_name_code` return non-empty DataFrames
- **THEN** it SHALL return the merged list of SH + SZ A-share stocks with their codes and names
- **AND** duplicates (same `code` appearing in both exchanges) SHALL be removed keeping the first occurrence
- **AND** 数据来源标记为 `akshare_sh_sz`

#### Scenario: SH succeeds but SZ fails (or vice versa)
- **WHEN** one of SH / SZ direct interfaces raises an exception or returns an empty DataFrame
- **AND** the other returns a non-empty DataFrame
- **THEN** the primary source SHALL still be considered successful
- **AND** the returned list SHALL contain only the successful side's stocks
- **AND** a WARN log SHALL be recorded for the failed side

#### Scenario: Primary source rate limited
- **WHEN** the primary source returns HTTP 429 or rate limit error
- **THEN** the crawler SHALL trigger the rate limiter to retry with exponential backoff

### Requirement: Fallback to secondary source

主源（沪深直连合并）失败时，爬虫 SHALL 自动切换到备用源（东方财富实时快照接口 `stock_zh_a_spot_em`）获取股票列表。

#### Scenario: Fallback to Eastmoney snapshot
- **WHEN** 主源（沪深直连）爬取失败（SH 与 SZ 同时失败，或合并后结果为空）
- **THEN** 爬虫 SHALL 自动切换到东方财富实时快照接口（`stock_zh_a_spot_em`）
- **AND** 从实时快照数据中提取 `code` 和 `name` 字段作为股票列表

#### Scenario: Both sources failed
- **WHEN** 主源和备用源均失败
- **THEN** 爬虫 SHALL 抛出 `CrawlerError` 异常
- **AND** 错误信息 SHALL 包含最近一次异常的描述
- **AND** 调用方 SHALL 将错误信息记录到 `CrawlStatus.error_message` 字段

## ADDED Requirements

### Requirement: Beijing Stock Exchange as optional supplementary source

In the primary source (`akshare_sh_sz`), AFTER successfully fetching the SH+SZ merged list, the crawler SHALL attempt to fetch Beijing Stock Exchange stocks via `stock_info_bj_name_code()` and append them to the result. BJ fetch failure SHALL NOT cause the primary source to fail.

#### Scenario: BJ source succeeds
- **WHEN** SH+SZ merged list is non-empty
- **AND** `stock_info_bj_name_code()` returns a non-empty DataFrame
- **THEN** BJ stocks SHALL be appended to the result list
- **AND** the final list SHALL contain SH + SZ + BJ stocks (de-duplicated by `code`)

#### Scenario: BJ source fails
- **WHEN** SH+SZ merged list is non-empty
- **AND** `stock_info_bj_name_code()` raises an exception or returns empty
- **THEN** the primary source SHALL still return the SH+SZ list as a successful result
- **AND** a WARN log SHALL be recorded with the BJ failure reason
- **AND** the success SHALL NOT be downgraded

#### Scenario: BJ source skipped when SH+SZ empty
- **WHEN** SH+SZ merged list is empty (both failed)
- **THEN** the crawler SHALL NOT attempt BJ fetch
- **AND** the primary source SHALL be considered failed (delegated to fallback)

### Requirement: Structured error response from API endpoint

The `POST /api/crawler/update_list` endpoint SHALL catch `CrawlerError` raised by the crawler and return a structured error response instead of an HTTP 500 with a generic message.

#### Scenario: Crawler raises CrawlerError
- **WHEN** `crawler.fetch_stock_list_df()` raises `CrawlerError`
- **THEN** the endpoint SHALL return HTTP 503
- **AND** the response body SHALL contain `error` field with the exception message
- **AND** the response body SHALL contain `sources_tried` field listing attempted source names
- **AND** `record_crawl_status` SHALL be called with `status='failed'` and `error_message=str(e)`

#### Scenario: Empty DataFrame returned
- **WHEN** `crawler.fetch_stock_list_df()` returns an empty DataFrame without raising
- **THEN** the endpoint SHALL return HTTP 503
- **AND** the response body SHALL contain `error: '获取股票列表为空'`
- **AND** `record_crawl_status` SHALL be called with `status='failed'` and the empty-data reason

#### Scenario: Successful crawl
- **WHEN** the crawler returns a non-empty DataFrame
- **THEN** the endpoint SHALL return HTTP 200 with `success_count`, `fail_count`, `elapsed`
- **AND** `record_crawl_status` SHALL be called with `status='success'` or `status='partial'` based on `fail_count`

### Requirement: Per-source logging

The `StockListCrawler` SHALL emit structured logs for each source attempt to aid debugging.

#### Scenario: Source starts
- **WHEN** a source is about to be fetched
- **THEN** an INFO log SHALL be emitted with the source name

#### Scenario: Source fails
- **WHEN** a source raises an exception
- **THEN** an ERROR log SHALL be emitted with the source name and exception message

#### Scenario: Source succeeds
- **WHEN** a source returns data
- **THEN** an INFO log SHALL be emitted with the source name and the count of normalized rows
