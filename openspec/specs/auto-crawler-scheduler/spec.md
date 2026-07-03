# auto-crawler-scheduler Specification

## Purpose
定时任务调度器：自动执行股票列表更新、实时行情爬取和日线数据更新任务，支持幂等性检查和非交易日处理。

## Requirements
### Requirement: Weekly stock list update

系统 SHALL 每周一自动执行股票列表更新任务，使用cron触发器在00:30执行。

#### Scenario: Weekly stock list update at scheduled time
- **WHEN** 系统时钟到达每周一00:30
- **THEN** 系统 SHALL 自动触发StockListCrawler执行股票列表爬取
- **AND** 创建CrawlStatus记录，crawl_type='list'

#### Scenario: Stock list update creates crawl status
- **WHEN** 股票列表更新任务执行完成
- **THEN** 系统 SHALL 创建CrawlStatus记录，记录爬取结果
- **AND** 若爬取失败，记录错误信息到error_message

### Requirement: Automatic realtime quote crawl with idempotency

系统 SHALL 在每个交易日15:15起每5分钟执行一次实时行情爬取，使用cron触发器（15:15-15:59）。每次执行前检查当天是否已有成功记录，若有则跳过；若非交易日则标记为已完成（成功数0）。

#### Scenario: Skip if already succeeded today
- **WHEN** 定时任务触发实时行情爬取
- **AND** 当天已有success/partial状态的realtime爬取记录
- **THEN** 系统 SHALL 直接跳过，不执行爬取
- **AND** 不创建新的CrawlStatus记录

#### Scenario: Non-trading day marks as completed
- **WHEN** 定时任务触发实时行情爬取
- **AND** 当天为非交易日（周末/节假日，且非调休工作日）
- **THEN** 系统 SHALL 创建一条success状态的CrawlStatus记录
- **AND** success_count=0, fail_count=0
- **AND** error_message="非交易日，无需爬取"

#### Scenario: Trading day executes crawl
- **WHEN** 定时任务触发实时行情爬取
- **AND** 当天为交易日
- **AND** 当天没有成功的爬取记录
- **THEN** 系统 SHALL 执行实时行情爬取（东方财富直连HTTP为主源，akshare为备用）
- **AND** 爬取成功后创建success/partial状态的CrawlStatus记录
- **AND** 将数据写入StockDaily表（而非Stock表）

#### Scenario: Crawl failure triggers retry on next interval
- **WHEN** 实时行情爬取失败
- **THEN** 系统 SHALL 创建一条failed状态的CrawlStatus记录用于排查
- **AND** 不标记为"已完成"，下一个5分钟间隔会继续重试

### Requirement: Daily quote update (Tencent source)

系统 SHALL 在每个交易日16:00执行日线数据更新任务（腾讯源），增量更新当日数据。

#### Scenario: Skip if already succeeded today
- **WHEN** 定时任务触发日线数据更新
- **AND** 当天已有success/partial状态的daily爬取记录
- **THEN** 系统 SHALL 直接跳过，不执行爬取

#### Scenario: Non-trading day marks as completed
- **WHEN** 定时任务触发日线数据更新
- **AND** 当天为非交易日
- **THEN** 系统 SHALL 创建一条success状态的CrawlStatus记录
- **AND** success_count=0, fail_count=0

#### Scenario: Trading day executes daily update
- **WHEN** 定时任务触发日线数据更新
- **AND** 当天为交易日
- **AND** 当天没有成功的daily爬取记录
- **THEN** 系统 SHALL 使用TencentStockDailyCrawler爬取当日所有股票日线数据
- **AND** 将数据写入StockDaily表（UPSERT语义）
- **AND** 创建success/partial状态的CrawlStatus记录

### Requirement: Scheduler integration with Flask

定时任务调度器 SHALL 使用APScheduler的BackgroundScheduler，集成到Flask应用启动流程。

#### Scenario: Scheduler starts with Flask app
- **WHEN** Flask应用启动（执行app.run()）
- **THEN** BackgroundScheduler SHALL 自动启动
- **AND** 所有定时任务（股票列表更新、实时行情爬取、日线数据更新）SHALL 处于运行状态

#### Scenario: Scheduler shuts down with Flask app
- **WHEN** Flask应用停止（收到SIGTERM或SIGINT信号）
- **THEN** BackgroundScheduler SHALL 安全关闭
- **AND** 正在执行的任务SHALL 完成后才关闭调度器（不强制中断）

### Requirement: Scheduler task configuration

定时任务配置 SHALL 如下：

| 任务名称 | 触发器类型 | 执行时间 | 爬取类型 | 说明 |
|----------|-----------|----------|----------|------|
| stock_list_update | cron | 每周一00:30 | list | 更新股票列表（新浪为主源，东方财富为备用） |
| realtime_quotes_update | cron | 每日15:15-15:59 每5分钟 | realtime | 实时行情爬取（东方财富直连HTTP为主源，akshare为备用） |
| daily_quotes_update | cron | 每日16:00 | daily | 日线数据更新（腾讯源） |

#### Scenario: Task configuration loaded correctly
- **WHEN** 调度器初始化
- **THEN** 三个定时任务 SHALL 按上述配置正确注册
- **AND** 任务执行时SHALL 调用对应的爬虫模块

### Requirement: Manual scheduler control via API

系统 SHALL 提供API手动控制定时任务（暂停/恢复/立即执行）。

#### Scenario: Pause scheduler via API
- **WHEN** 用户调用暂停API（POST /api/scheduler/pause）
- **THEN** 调度器 SHALL 暂停所有定时任务
- **AND** 返回成功响应

#### Scenario: Resume scheduler via API
- **WHEN** 用户调用恢复API（POST /api/scheduler/resume）
- **THEN** 调度器 SHALL 恢复所有定时任务
- **AND** 返回成功响应

#### Scenario: Trigger immediate crawl via API
- **WHEN** 用户调用立即执行API（POST /api/scheduler/run/<task_id>）
- **THEN** 调度器 SHALL 立即执行指定任务
- **AND** 创建对应的CrawlStatus记录
