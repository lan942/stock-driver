## Why

目前系统仅支持实盘持仓管理（portfolio 交易记录），缺少量化策略回测的独立模块。新增回测管理模块，结构完全与实盘持仓管理一致（三表：持仓/交易/现金），但使用独立表名防止数据污染，为后续接入回测引擎提供数据基础。

## What Changes

- 新增 `backtest_portfolio` / `backtest_transactions` / `backtest_cash` 三张数据库表，结构完全镜像 portfolio/transactions/cash_balance
- 新增后端服务层 `backtest_service.py`，提供与 `portfolio_service.py` 相同的 CRUD 操作
- 新增 API 端点组 `/api/backtest/*`（完全镜像 `/api/portfolio/*`）
- 新增前端页面 `/backtest`（回测管理），为 Portfolio.vue 的精确副本
- 在导航栏和路由中注册新页面
- 在 `migrate_db.py` 中添加建表迁移步骤

## Capabilities

### New Capabilities
- `backtest-management`: 回测持仓管理能力，包含持仓明细管理、交易记录管理、现金余额管理，与实盘持仓管理功能完全平行

### Modified Capabilities
- `cli-management`: 无需修改

## Impact

- `backend/models/` — 新增 `backtest.py` 模型文件（3 个模型类）
- `backend/services/` — 新增 `backtest_service.py`
- `backend/api/routes.py` — 新增回测相关路由（镜像 portfolio 路由）
- `frontend/src/views/` — 新增 `Backtest.vue`（Portfolio.vue 的精确副本）
- `frontend/src/router/index.js` — 新增路由
- `frontend/src/App.vue` — 新增导航链接
- `backend/utils/migrate_db.py` — 新增建表迁移步骤
- `frontend/src/api/stock.js` — 新增 9 个 API 方法