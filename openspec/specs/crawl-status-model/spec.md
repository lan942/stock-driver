# crawl-status-model Specification

## Purpose
TBD - created by archiving change disable-sina-auto-crawler. Update Purpose after archive.
## Requirements
### Requirement: Record crawl task status

系统 SHALL 为每次爬取任务创建CrawlStatus记录，包含爬取类型、状态、时间、成功/失败数量和错误信息。

#### Scenario: Successful crawl task
- **WHEN** 爬取任务成功完成
- **THEN** 系统 SHALL 创建CrawlStatus记录，status='success'
- **AND** 记录success_count为成功爬取的股票数量
- **AND** fail_count为0
- **AND** error_message为NULL

#### Scenario: Partially successful crawl task
- **WHEN** 爬取任务部分成功（部分股票数据获取失败）
- **THEN** 系统 SHALL 创建CrawlStatus记录，status='partial'
- **AND** 记录success_count和fail_count
- **AND** error_message记录失败原因摘要

#### Scenario: Failed crawl task
- **WHEN** 爬取任务完全失败（API连接失败或返回错误）
- **THEN** 系统 SHALL 创建CrawlStatus记录，status='failed'
- **AND** success_count为0
- **AND** fail_count为预期爬取数量（列表爬取为5000+，实时行情为已入库股票数）
- **AND** error_message记录完整错误信息

### Requirement: Crawl status data model

CrawlStatus模型 SHALL 包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| crawl_type | String | 爬取类型：'list'或'realtime' |
| status | String | 状态：'success'、'partial'、'failed' |
| crawl_time | DateTime | 爬取开始时间 |
| success_count | Integer | 成功数量，默认0 |
| fail_count | Integer | 失败数量，默认0 |
| error_message | Text | 错误信息（仅失败时记录） |

#### Scenario: CrawlStatus fields validation
- **WHEN** 创建CrawlStatus记录
- **THEN** crawl_type SHALL 为'list'或'realtime'
- **AND** status SHALL 为'success'、'partial'或'failed'
- **AND** crawl_time SHALL 记录爬取开始时间（不是结束时间）

### Requirement: Query crawl status history

系统 SHALL 提供API查询爬取状态历史，支持按爬取类型和时间范围过滤。

#### Scenario: Query recent crawl status
- **WHEN** 用户请求查询最近N次爬取状态
- **THEN** 系统 SHALL 返回按crawl_time降序排列的CrawlStatus记录列表
- **AND** 每条记录包含所有字段信息

#### Scenario: Filter by crawl type
- **WHEN** 用户请求查询特定爬取类型的状态（如'realtime'）
- **THEN** 系统 SHALL 仅返回crawl_type匹配的CrawlStatus记录

#### Scenario: Filter by time range
- **WHEN** 用户请求查询指定时间范围内的爬取状态
- **THEN** 系统 SHALL 返回crawl_time在范围内的CrawlStatus记录

### Requirement: Stock model price_date field

Stock模型 SHALL 增加price_date字段，记录价格数据的日期。

| 字段 | 类型 | 说明 |
|------|------|------|
| price_date | Date | 价格数据日期（不含时间） |

#### Scenario: Update price_date on realtime crawl
- **WHEN** 爬取任务成功获取股票实时价格
- **THEN** 系统 SHALL 更新Stock记录的price_date为当前日期
- **AND** price_date仅记录日期（如'2026-07-01'），不含时间戳

#### Scenario: price_date reflects data freshness
- **WHEN** 用户查询股票信息
- **THEN** price_date SHALL 指示价格数据的新鲜度
- **AND** 若price_date为NULL，表示该股票从未爬取实时数据

