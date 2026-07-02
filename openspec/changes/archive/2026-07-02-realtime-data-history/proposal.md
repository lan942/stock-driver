## Why

当前实时行情爬取只更新 Stock 表的字段（price/open/high/low 等），每次爬取覆盖上次数据，没有按日期保存历史快照。用户无法查询历史某一天的行情数据进行分析（如涨跌幅趋势、PE 变化等）。需要改造存储逻辑，让每天爬取的实时行情数据作为按日快照持久化保存，前端可按日期查询。

## What Changes

- **新增 StockDaily 表字段**：pe, pb, market_cap（当前 StockDaily 表缺少这 3 个字段，需要补充）
- **改造 save_realtime_quotes**：在更新 Stock 表最新快照的同时，向 StockDaily 表插入当日的行情记录
- **新增 API**：`GET /api/stocks/daily?date=YYYY-MM-DD` 按日期查询当日所有股票的行情快照，`GET /api/stocks/<code>/daily?days=N` 支持多日查询
- **前端改造**：股票列表页添加日期选择器，默认显示最新日期数据，可切换查看历史日期

## Capabilities

### New Capabilities
- `realtime-data-history`: 实时行情按日期持久化存储，支持按日期查询历史快照

### Modified Capabilities
- `stock-list-crawler`: StockDaily 模型新增 pe/pb/market_cap 字段
- `data-normalizer`: save_realtime_quotes 存储逻辑扩展为双写（Stock 更新 + StockDaily 插入）

## Impact

- **数据库**：StockDaily 表新增 pe/pb/market_cap 三列（需要 DDL 迁移），Stock 表更新逻辑不变
- **后端 API**：新增股票历史快照查询接口，不影响现有接口
- **前端**：股票列表页新增日期选择组件，不影响现有功能
