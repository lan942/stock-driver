## Why

当前策略使用固定的止盈止损比例（如6%止盈、3%止损），无法根据市场变化和股票状态动态调整。引入XGBoost动态止盈止损机制，让模型根据实时特征评分来决定是否卖出，同时保留配置的止盈止损比例作为保底保护，既能提高收益又能控制风险。

## What Changes

- 新增XGBoost动态卖出评分机制：持有期间每天用模型重新评分，评分低于阈值时触发卖出
- 修改卖出逻辑：动态评分卖出与配置止盈止损并行，满足任一条件即卖出
- 新增配置项：动态卖出评分阈值（默认0.5）
- 更新回测引擎：支持动态卖出逻辑
- 更新策略看板：展示动态评分和卖出原因

## Capabilities

### New Capabilities
- `xgboost-dynamic-score-sell`: XGBoost动态评分卖出机制，持有期间每日重新评分，评分低于阈值触发卖出
- `stop-profit-loss-floor`: 止盈止损底线保护，配置的止盈止损比例作为保底，达到即强制卖出

### Modified Capabilities
- `ml-strategy`: 扩展XGBoost策略，增加持有期间重评功能
- `backtest-engine`: 修改回测引擎卖出逻辑，支持动态评分卖出

## Impact

- **backend/services/strategies/ml_strategy.py**: 增加持有期间重评方法
- **backend/services/strategy_backtest.py**: 修改卖出逻辑，增加动态评分判断
- **backend/services/strategy_config.py**: 新增动态卖出评分阈值配置项
- **frontend/src/views/StrategyBoard.vue**: 展示动态评分和卖出原因
