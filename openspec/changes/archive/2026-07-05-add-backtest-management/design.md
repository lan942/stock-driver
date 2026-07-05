## Context

项目当前已有实盘持仓管理模块（模型 `Portfolio` / `Transaction` / `CashBalance`，服务 `portfolio_service.py`，前端 `Portfolio.vue`）。回测管理作为独立模块，结构与之完全平行但独立。

## Goals / Non-Goals

**Goals:**
- 新建 `backtest_portfolio` / `backtest_transactions` / `backtest_cash` 三表，结构完全镜像实盘表
- 提供 RESTful API 用于持仓 CRUD、交易记录 CRUD、现金余额管理
- 前端展示概览卡片（总资产/现金/市值/收益）+ 持仓明细表格 + 交易记录表格
- 导航栏新增"回测管理"入口

**Non-Goals:**
- 不实现回测引擎本身（暂为数据管理，后续可接入 backtrader 引擎）
- 不涉及策略定义或可视化策略编辑器
- 不涉及实时交易信号生成

## Decisions

### Decision 1: 独立模型和表，不复用实盘 portfolio 表

**选择**: 新建三张独立表（`backtest_portfolio` / `backtest_transactions` / `backtest_cash`），与实盘表完全独立。

**理由**: 回测与实盘是两类不同数据，混合会污染实盘数据。使用独立表可以自由操作回测数据而不影响实盘记录。

**替代方案**: 复用实盘表加 type 字段区分 — 查询复杂，误操作风险高，被拒绝。

### Decision 2: 表结构与实盘保持一致

**选择**: `backtest_portfolio` 字段与 `portfolio` 一致（code, quantity, cost_price），`backtest_transactions` 字段与 `transactions` 一致（type, code, quantity, price, amount, trade_date），`backtest_cash` 字段与 `cash_balance` 一致（balance）。

**理由**: 用户明确要求"表结构也要求一样，但是表名需要不同"。保持结构一致便于后续回测引擎的对接和代码复用。

### Decision 3: 前端作为 Portfolio.vue 的精确副本

**选择**: `Backtest.vue` 为 `Portfolio.vue` 的精确副本，仅 API 调用端点不同。

**理由**: 用户多次要求"页面内容和持仓管理的完全一样"。保持 UI 完全一致，降低用户认知负担。

### Decision 4: 回测引擎暂不实现

**选择**: 当前仅提供数据 CRUD 能力，回测引擎作为独立任务后续开发。

**理由**: 回测引擎开发是独立大任务，不应混入本变更。

## Risks / Trade-offs

- [Risk] 目前仅数据管理，用户可能困惑回测如何运行 → 页面标题明确为"回测管理"，后续接入回测引擎后展示运行结果
- [Risk] 代码与实盘持仓管理大量重复 → 有意为之，保持模块独立性和清晰边界。后续可考虑抽象公共层