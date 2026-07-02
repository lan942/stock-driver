# auto-crawler-scheduler Specification (delta)

## Purpose
（此为增量规格，基础规格见 openspec/specs/auto-crawler-scheduler/spec.md）

本增量定义手动触发实时行情更新时的强制刷新和日期指定能力。

## MODIFIED Requirements

### Requirement: Manual scheduler control via API

系统 SHALL 提供API手动控制定时任务（暂停/恢复/立即执行），并支持实时行情的强制刷新和日期指定。

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

#### Scenario: Manual realtime crawl with force flag
- **WHEN** 用户调用POST /api/crawler/update_realtime且force=true
- **THEN** 系统 SHALL 跳过当日成功记录检查
- **AND** 无论当日是否已有成功记录，都 SHALL 执行实时行情爬取
- **AND** 爬取完成后 SHALL 创建新的CrawlStatus记录

#### Scenario: Manual realtime crawl with date parameter
- **WHEN** 用户调用POST /api/crawler/update_realtime且指定了date参数
- **THEN** 系统 SHALL 使用指定的日期作为price_date保存到Stock记录中
- **AND** CrawlStatus记录的crawl_time SHALL 为当前时间
- **AND** CrawlStatus记录的success_count和fail_count SHALL 反映实际爬取结果

#### Scenario: Manual realtime crawl with both force and date
- **WHEN** 用户调用POST /api/crawler/update_realtime且force=true且指定了date
- **THEN** 系统 SHALL 跳过当日成功检查并执行爬取
- **AND** 使用指定的日期作为price_date
