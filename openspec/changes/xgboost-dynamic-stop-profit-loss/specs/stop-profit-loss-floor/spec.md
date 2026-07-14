# stop-profit-loss-floor Specification

## Purpose
定义止盈止损底线保护机制。日内只挂止损条件单（min(ATR止损, 百分比止损)），止盈/超时/动态评分卖出均在收盘后评估、次日开盘价执行，实现实盘可操作。

## Requirements

### Requirement: 日内止损（唯一日内操作）
回测引擎 SHALL 在每个交易日对持仓股票执行日内止损检测：
1. 计算止损阈值 = max(cost_price × (1 - stop_loss_pct), cost_price - ATR × atr_loss_multiplier)
2. 若当日最低价 low ≤ 止损阈值，触发止损，当日以止损价卖出
3. 止损触发优先级最高，先于任何收盘后评估

#### Scenario: 止损触发强制卖出
- **WHEN** 持仓股票成本价10元，止损比例3%，当日最低价为9.65元
- **THEN** 触发止损卖出，卖出价为9.70元（止损阈值），原因类型为 `stop_loss`

#### Scenario: ATR止损触发
- **WHEN** 持仓股票成本价10元，ATR=0.50，atr_loss_multiplier=1.0，比例止损阈值9.70元，ATR止损阈值9.50元，当日最低价9.50元
- **THEN** ATR止损阈值9.50元高于比例止损9.70元（取更易触发的大值），当日最低价9.50元触及，触发 `atr_loss` 卖出

### Requirement: 收盘后止盈评估（次日开盘卖出）
回测引擎 SHALL 在每个交易日收盘后对未止损的持仓执行止盈评估：
1. 计算止盈阈值 = min(cost_price × (1 + stop_profit_pct), cost_price + ATR × atr_profit_multiplier)
2. 若当日收盘价 >= 止盈阈值，加入待卖出队列
3. 待卖出队列中的持仓于**次交易日开盘价**卖出

#### Scenario: 收盘价触发止盈
- **WHEN** 持仓股票成本价10元，止盈比例6%，当日收盘价10.65元（≥10.60元止盈线）
- **THEN** 加入待卖出队列，次交易日以开盘价卖出，原因类型为 `take_profit`

#### Scenario: 收盘价未触发止盈
- **WHEN** 持仓股票成本价10元，止盈比例6%，当日收盘价10.30元（<10.60元止盈线）
- **THEN** 不触发止盈，继续持有

### Requirement: 收盘后超时评估（次日开盘卖出）
回测引擎 SHALL 在每个交易日收盘后检测持仓是否超过最大持有天数 `max_hold_days`。若超过，加入待卖出队列，次交易日开盘价卖出，原因类型为 `timeout`。

#### Scenario: 持仓超时
- **WHEN** 持仓交易日数达到 max_hold_days（默认5天）
- **THEN** 次交易日以开盘价卖出，原因类型为 `timeout`

### Requirement: 收盘后动态评分评估（次日开盘卖出）
回测引擎 SHALL 在每个交易日收盘后对持仓执行动态评分检测（至少持有 `dynamic_sell_min_hold_days` 天后生效）：
1. 评分跌出全市场百分位阈值 → 触发 `dynamic_score_low`
2. 连续 N 天评分下降 → 触发 `dynamic_score_decline`
3. 评分低于绝对阈值 → 触发 `dynamic_score_low`

触发后加入待卖出队列，次交易日开盘价卖出。

### Requirement: 卖出执行时机
卖出执行 SHALL 分为两类：
- **日内执行**：止损（当日触发当日成交，以止损价卖出）
- **T+1 开盘执行**：止盈、超时、动态评分（当日收盘后评估，次日开盘价卖出，通过 pending_sells 队列实现）

#### Scenario: 当日只挂止损、其余次日执行
- **WHEN** 持仓股票当日同时满足止损和止盈条件
- **THEN** 止损先触发（日内low触及），当日以止损价卖出；止盈条件因已清仓不再生效

### Requirement: 实盘对应
- 日内操作：只在开盘后挂止损条件单（min(ATR止损, 百分比止损)），触发即成交
- 收盘后操作：冷静评估止盈/模型置信度/超时，次日集合竞价挂单卖出
- 买入：T日收盘模型评分生成候选，T+1日开盘价买入（不限涨跌幅）
