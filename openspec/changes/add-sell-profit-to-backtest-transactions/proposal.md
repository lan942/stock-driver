## Why

回测管理的交易记录中，卖出记录缺少当次卖出的收益率（profit_pct），用户无法直观看到每笔卖出的盈亏情况。此前 `backtest-transaction-enhancement` 已添加了开盘价、收盘价、交易后权益等字段，但缺少最关键的卖出收益数据。

## What Changes

- `BacktestTransaction` 模型新增 `profit_pct` 字段，存储卖出交易的收益率百分比
- 回测引擎（`strategy_backtest.py`）在记录卖出交易时将已计算的收益率写入 `profit_pct`
- 回测服务（`backtest_service.py`）在交易记录查询中返回 `profit_pct` 字段
- 前端 `Backtest.vue` 交易记录表格新增「收益率」列，仅在卖出记录行显示
- 买单的 `profit_pct` 为空（NULL），前端不显示

## Capabilities

### New Capabilities
- `sell-profit-tracking`: 卖出交易收益率追踪，在交易记录中存储并展示卖出收益率

### Modified Capabilities
- `backtest-transaction-enhancement`: 在现有交易记录增强的基础上，追加 `profit_pct` 字段的存储与展示

## Impact

- `backend/models/backtest.py` — BacktestTransaction 模型新增字段
- `backend/services/strategy_backtest.py` — 回测引擎传入收益率
- `backend/services/backtest_service.py` — add_transaction / get_transactions / get_transactions_by_code 处理新字段
- `backend/api/routes.py` — 无需修改（服务层已覆盖）
- `frontend/src/views/Backtest.vue` — 交易表格新增收益率列
- 数据库迁移：需为新字段添加默认值（NULL），已有数据不受影响
