## Why

新浪数据源缺少关键股票字段（换手率、市盈率、市净率、市值），无法满足全市场分析需求。同时，股票价格数据缺少日期追踪，无法确定数据的时效性，也没有爬取状态记录，导致无法监控爬取进度和重试失败的爬取任务。此外，系统缺乏定时任务机制，需要手动触发爬取，效率低下。

## What Changes

- **BREAKING**: 禁用新浪数据源，StockRealtimeCrawler 仅使用东方财富数据源
- Stock 模型增加 `price_date` 字段，记录价格数据的日期
- 新增 CrawlStatus 模型，记录每次爬取的状态、时间、成功/失败数量
- 新增定时任务调度器，自动执行股票列表更新和实时行情爬取
- 爬取失败时记录错误信息到 CrawlStatus，支持手动重试

## Capabilities

### New Capabilities

- `crawl-status-model`: 爬取状态记录模型，记录每次爬取的类型、状态、时间、成功/失败数量、错误信息
- `auto-crawler-scheduler`: 定时任务调度器，自动执行股票列表更新（每日一次）和实时行情爬取（交易日每5分钟）

### Modified Capabilities

- `stock-realtime-crawler`: 修改数据源优先级，禁用新浪源，仅使用东方财富源，并在保存数据时更新 price_date 字段

## Impact

- **Backend**:
  - `backend/services/crawler/stock_realtime.py`: 移除新浪数据源切换逻辑
  - `backend/models/stock.py`: Stock 模型增加 price_date 字段
  - `backend/models/crawl_status.py`: 新增爬取状态模型
  - `backend/services/scheduler.py`: 新增定时任务调度器
  - `backend/api/routes.py`: 新增爬取状态查询 API

- **Database**:
  - stocks 表增加 price_date 列
  - 新增 crawl_status 表

- **Dependencies**:
  - 新增 APScheduler 库用于定时任务调度