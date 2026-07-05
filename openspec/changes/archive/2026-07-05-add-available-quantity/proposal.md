## Why

A 股实行 T+1 交易制度，当天买入的股票当天不能卖出。当前持仓明细只显示总持仓数量，用户无法区分哪些是当天买入的（不可用）、哪些是之前持有的（可用）。需要增加"可用数量"列，让用户清晰知道当前可卖出的股数。

## What Changes

- **后端 `get_holdings()` 接口**：返回结果中新增 `available_quantity` 字段，计算规则为 `总持仓数量 - 当日买入数量`
- **前端持仓明细表格**：在"持仓数量"列之后新增"可用数量"列，展示 `available_quantity`

## Capabilities

### Modified Capabilities
- `portfolio-management`: get_holdings API 返回结果新增 `available_quantity` 字段

### New Capabilities
- (无新增 capability，仅在现有 portfolio-management 中修改)

## Impact

- `backend/services/portfolio_service.py` — `get_holdings()` 中计算 `available_quantity`
- `frontend/src/views/Portfolio.vue` — 持仓表格新增"可用数量"列