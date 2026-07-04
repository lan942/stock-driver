## Why

当前前端页面缺少查看数据库中每日数据条数的功能，用户无法直观了解哪些日期的数据完整、哪些日期需要补充，导致数据补全工作缺乏目标性。

## What Changes

- 新增后端 API 接口，按日期统计 StockDaily 表中的数据条数
- 新增前端数据概览页面，以日历热力图或表格形式展示每日数据覆盖情况
- 支持按日期范围筛选，快速定位缺失数据的日期

## Capabilities

### New Capabilities

- `daily-data-summary`: 每日数据统计功能，包括后端 API 和前端展示组件

### Modified Capabilities

- 无

## Impact

- **Backend**: 新增 `api/stock.py` 路由，新增 `services/stock_service.py` 方法
- **Frontend**: 新增 `src/views/DataSummary.vue` 页面，新增 `src/api/stock.js` API 调用
- **Database**: 无需变更表结构，仅新增查询逻辑