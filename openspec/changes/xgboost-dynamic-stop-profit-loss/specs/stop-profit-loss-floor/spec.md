# stop-profit-loss-floor Specification

## Purpose
定义止盈止损底线保护机制，配置的止盈止损比例作为保底，达到即强制卖出，与动态评分卖出并行。

## Requirements

### Requirement: 止盈止损底线保护逻辑
回测引擎 SHALL 在每个交易日对持仓股票执行止盈止损判断，作为保底保护：
1. 计算当前价格相对于买入价格的收益率
2. 若收益率 ≥ `take_profit_pct`（配置的止盈比例），强制卖出
3. 若收益率 ≤ `-stop_loss_pct`（配置的止损比例），强制卖出

止盈止损触发优先级高于动态评分卖出，确保风险可控。

#### Scenario: 止盈触发强制卖出
- **WHEN** 持仓股票收益率为 `7%`，配置的止盈比例为 `6%`
- **THEN** 强制触发止盈卖出，记录卖出原因类型为 `take_profit`

#### Scenario: 止损触发强制卖出
- **WHEN** 持仓股票收益率为 `-4%`，配置的止损比例为 `3%`
- **THEN** 强制触发止损卖出，记录卖出原因类型为 `stop_loss`

### Requirement: 三种卖出原因类型
卖出记录 SHALL 包含 `sell_reason` 字段，用于区分卖出原因：
- `take_profit`: 止盈触发
- `stop_loss`: 止损触发
- `dynamic_score`: 动态评分触发

#### Scenario: 记录卖出原因
- **WHEN** 触发任意类型的卖出
- **THEN** 交易记录中包含 `sell_reason` 字段，值为对应类型

### Requirement: 卖出优先级
卖出触发优先级 SHALL 为：
1. 止损触发（最高优先级，保护本金）
2. 止盈触发（第二优先级，锁定收益）
3. 动态评分触发（第三优先级，模型决策）

#### Scenario: 多种条件同时满足
- **WHEN** 持仓股票收益率为 `8%`（超过6%止盈）且动态评分为 `0.4`（低于0.5阈值）
- **THEN** 优先触发止盈卖出，`sell_reason` 为 `take_profit`
