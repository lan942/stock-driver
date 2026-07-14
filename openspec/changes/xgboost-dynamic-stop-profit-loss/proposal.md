## Why

当前策略在盘中同时判断止盈、止损和动态评分卖出，实盘中无法实现（同一持仓只能挂一个条件单，不能同时挂止盈单和止损单）。将卖出拆分为日内止损（唯一日内操作）和收盘后评估（止盈/超时/动态评分延迟到次日开盘卖出），使策略完全可操作。

同时去掉买入的1%涨跌幅限制——实盘中T+1集合竞价买入无法控制开盘价。

## What Changes

- 拆分卖出逻辑为 `_check_intraday_stop_loss`（日内止损）和 `_check_close_triggers`（收盘后评估）
- 止盈/超时/动态评分统一收盘后评估，通过 `pending_sells` 队列次日开盘价卖出
- 买入去掉1%涨跌幅限制，T+1 开盘直接成交
- 训练标签生成器 `compute_future_returns` 同步更新离场路径（移除 `force_close_method`）
- 更新 strategy_backtest.py、label_generator.py、xgboost_trainer.py、strategy_config.py

## Capabilities

### New Capabilities
- `xgboost-dynamic-score-sell`: XGBoost动态评分卖出机制，收盘后评估、次日开盘卖出
- `stop-profit-loss-floor`: 止盈止损底线保护，日内止损 + 收盘后止盈评估

### Modified Capabilities
- `ml-strategy`: 更新买卖规则，买入不限涨跌幅，卖出拆分为日内止损 + 次日开盘
- `ml-label-generator`: 训练标签离场路径同步更新，移除 `force_close_method`

## Impact

- **backend/services/strategy_backtest.py**: 拆分卖出逻辑、新增 pending_sells 队列、去掉买入限价
- **backend/services/ml/label_generator.py**: 同步更新离场路径模拟
- **backend/services/ml/xgboost_trainer.py**: 移除 force_close_method 调用
- **backend/services/strategy_config.py**: 更新配置描述
