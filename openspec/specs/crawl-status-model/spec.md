# crawl-status-model Specification

## Purpose
爬取状态管理：记录每次爬取任务的执行结果，支持按类型和时间查询历史记录。

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
- **AND** fail_count为预期爬取数量（列表爬取为5000+，实时行情和日线为已入库股票数）
- **AND** error_message记录完整错误信息

### Requirement: Crawl status data model

CrawlStatus模型 SHALL 包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| crawl_type | String | 爬取类型：'list'、'realtime'、'daily' |
| status | String | 状态：'success'、'partial'、'failed' |
| crawl_time | DateTime | 爬取开始时间 |
| success_count | Integer | 成功数量，默认0 |
| fail_count | Integer | 失败数量，默认0 |
| error_message | Text | 错误信息或摘要信息（failed 记录错误详情；partial 可记录新增/更新条数等摘要；success 可为 NULL） |

#### Scenario: CrawlStatus fields validation
- **WHEN** 创建CrawlStatus记录
- **THEN** crawl_type SHALL 为'list'、'realtime'或'daily'
- **AND** status SHALL 为'success'、'partial'或'failed'
- **AND** crawl_time SHALL 记录爬取完成时间（调用record_crawl_status时的时间戳）

### Requirement: Query crawl status history

系统 SHALL 提供API查询爬取状态历史，支持按爬取类型和时间范围过滤。

#### Scenario: Query recent crawl status
- **WHEN** 用户请求查询最近N次爬取状态
- **THEN** 系统 SHALL 返回按crawl_time降序排列的CrawlStatus记录列表
- **AND** 每条记录包含所有字段信息

#### Scenario: Filter by crawl type
- **WHEN** 用户请求查询特定爬取类型的状态（如'realtime'、'daily'）
- **THEN** 系统 SHALL 仅返回crawl_type匹配的CrawlStatus记录

#### Scenario: Filter by time range
- **WHEN** 用户请求查询指定时间范围内的爬取状态
- **THEN** 系统 SHALL 返回crawl_time在范围内的CrawlStatus记录

### Requirement: Crawl type definitions

crawl_type字段 SHALL 支持以下三种爬取类型：

| 类型 | 说明 | 触发时机 |
|------|------|----------|
| list | 股票列表更新 | 每周一00:30定时任务 |
| realtime | 实时行情爬取 | 交易日15:15-15:59每5分钟定时任务 |
| daily | 日线数据更新（腾讯源） | 交易日16:00定时任务 |

#### Scenario: Daily crawl type
- **WHEN** 日线数据爬取任务执行
- **THEN** 系统 SHALL 创建CrawlStatus记录，crawl_type='daily'
- **AND** 记录爬取成功/失败数量及错误信息
