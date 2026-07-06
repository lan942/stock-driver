## Why

当前系统已具备股票日线数据（OHLCV）和技术指标计算能力（indicator_engine），但缺乏一套完整的量化选股与持仓管理策略。用户需要基于现有数据，每日自动推荐买卖标的，在 T+1 约束下实现**用户可配置的期望年化收益率**。

核心思路：不追求高胜率（基于现有日线数据，胜率预期 40%~50%），而是通过**非对称的盈亏比**（止盈幅度 > 止损幅度）实现正期望收益。

## What Changes

- 新增独立的量化策略引擎模块 `backend/services/strategy_engine.py`，负责每日选股、生成买卖推荐
- 新增策略配置模型，支持可配置的**期望年化收益率**、初始资金、最大持仓只数、止盈止损比例等参数
- 新增策略执行调度，每日自动运行选股逻辑，输出推荐买入清单（含建议买入价、目标卖出价）
- 新增持仓跟踪与资金管理，自动检测持仓是否达到卖出条件，释放资金后自动推荐新股
- 新增收益跟踪与对比：实时计算实际年化收益，与用户设定的目标收益对比
- 新增策略结果 API (`/api/strategy/*`)，供前端查看推荐和持仓状态
- 前端新增策略看板页面，展示每日推荐、当前持仓、交易记录、收益统计

## Capabilities

### New Capabilities
- `strategy-engine`: 策略引擎核心，负责基于多因子模型的股票评分与筛选，输出买入推荐（标的、建议买入价、目标卖出价、止损价）
- `position-manager`: 持仓管理，跟踪当前持仓状态、监控卖出条件、管理可用资金，确保持仓只数不超过配置上限；同时跟踪实际收益并与目标收益对比
- `strategy-config`: 策略配置，支持可配置的期望年化收益率、初始资金、最大持仓只数、止盈止损比例等参数
- `strategy-api`: 策略 API 接口，提供获取每日推荐、当前持仓、交易记录、收益统计的 REST 接口

### Modified Capabilities
<!-- 不涉及现有 spec 的修改 -->

## Impact

- 新增文件: `backend/services/strategy_engine.py`, `backend/services/position_manager.py`, `backend/services/strategy_config.py`
- 新增模型: `backend/models/strategy.py` (策略持仓、策略交易记录、策略配置)
- 新增 API: `backend/api/strategy.py` (推荐、持仓、记录、统计)
- 前端新增: `frontend/src/views/StrategyBoard.vue` (策略看板)
- 依赖: 复用 `indicator_engine.py` 的技术指标计算、`stock.py` 的日线数据读取
- 可选依赖: backtrader 框架（用于更复杂的回测验证）
