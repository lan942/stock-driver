# auto-crawler-scheduler Specification

## Purpose
实现定时任务调度器，自动执行股票列表更新和实时行情爬取，减少手动操作，提高数据更新效率。

## ADDED Requirements

### Requirement: Automatic stock list update

系统 SHALL 每日自动执行股票列表更新任务，使用cron触发器在00:30执行。

#### Scenario: Daily stock list update at scheduled time
- **WHEN** 系统时钟到达每日00:30
- **THEN** 系统 SHALL 自动触发StockListCrawler执行股票列表爬取
- **AND** 创建CrawlStatus记录，crawl_type='list'

#### Scenario: Stock list update creates crawl status
- **WHEN** 股票列表更新任务执行完成
- **THEN** 系统 SHALL 创建CrawlStatus记录，记录爬取结果
- **AND** 若爬取失败，记录错误信息到error_message

### Requirement: Automatic realtime quote crawl

系统 SHALL 每5分钟自动执行实时行情爬取任务，使用interval触发器。

#### Scenario: Periodic realtime crawl every 5 minutes
- **WHEN** 系统时钟到达每5分钟间隔点
- **THEN** 系统 SHALL 自动触发StockRealtimeCrawler执行实时行情爬取
- **AND** 创建CrawlStatus记录，crawl_type='realtime'

#### Scenario: Realtime crawl updates price_date
- **WHEN** 实时行情爬取任务成功获取股票价格
- **THEN** 系统 SHALL 更新Stock记录的price_date为当前日期
- **AND** 更新Stock记录的price、change_percent、volume、turnover等字段

### Requirement: Scheduler integration with Flask

定时任务调度器 SHALL 使用APScheduler的BackgroundScheduler，集成到Flask应用启动流程。

#### Scenario: Scheduler starts with Flask app
- **WHEN** Flask应用启动（执行app.run()）
- **THEN** BackgroundScheduler SHALL 自动启动
- **AND** 所有定时任务（股票列表更新、实时行情爬取）SHALL 处于运行状态

#### Scenario: Scheduler shuts down with Flask app
- **WHEN** Flask应用停止（收到SIGTERM或SIGINT信号）
- **THEN** BackgroundScheduler SHALL 安全关闭
- **AND** 正在执行的任务SHALL 完成后才关闭调度器（不强制中断）

### Requirement: Scheduler task configuration

定时任务配置 SHALL 如下：

| 任务名称 | 触发器类型 | 执行时间 | 爬取类型 |
|----------|-----------|----------|----------|
| stock_list_update | cron | 每日00:30 | list |
| realtime_quotes_update | interval | 每5分钟 | realtime |

#### Scenario: Task configuration loaded correctly
- **WHEN** 调度器初始化
- **THEN** 两个定时任务 SHALL 按上述配置正确注册
- **AND** 任务执行时SHALL 调用对应的爬虫模块

### Requirement: Manual scheduler control via API

系统 SHALL 提供API手动控制定时任务（暂停/恢复/立即执行）。

#### Scenario: Pause scheduler via API
- **WHEN** 用户调用暂停API（如POST /api/scheduler/pause）
- **THEN** 调度器 SHALL 暂停所有定时任务
- **AND** 返回成功响应

#### Scenario: Resume scheduler via API
- **WHEN** 用户调用恢复API（如POST /api/scheduler/resume）
- **THEN** 调度器 SHALL 恢复所有定时任务
- **AND** 返回成功响应

#### Scenario: Trigger immediate crawl via API
- **WHEN** 用户调用立即执行API（如POST /api/scheduler/run/<task_name>）
- **THEN** 调度器 SHALL 立即执行指定任务
- **AND** 创建对应的CrawlStatus记录