# xgboost-dynamic-score-sell Specification

## Purpose
定义XGBoost动态评分卖出机制，持有期间每日重新评分，评分低于阈值时触发卖出。

## Requirements

### Requirement: 持有期间重评方法
策略 SHALL 提供 `score_stock_for_sell(code, buy_date)` 方法，用于持有期间重新评分。该方法 SHALL 基于买入日期之后的最新数据计算特征并预测上涨概率。

#### Scenario: 持有期间正常重评
- **WHEN** 持有股票 `000001` 超过1个交易日，调用 `score_stock_for_sell('000001', '2024-01-01')`
- **THEN** 返回当前日期的上涨概率评分（0~1之间）

#### Scenario: 数据不足时返回None
- **WHEN** 买入日期之后数据不足30个交易日
- **THEN** 返回 `None`

### Requirement: 动态卖出评分阈值配置
策略配置 SHALL 包含 `dynamic_sell_score_threshold` 参数，默认值为 `0.5`。当持有期间重评分数低于该阈值时，触发动态卖出。

#### Scenario: 配置默认阈值
- **WHEN** 未显式设置 `dynamic_sell_score_threshold`
- **THEN** 使用默认值 `0.5`

#### Scenario: 自定义阈值
- **WHEN** 设置 `dynamic_sell_score_threshold=0.4`
- **THEN** 评分低于 `0.4` 时触发动态卖出

### Requirement: 动态卖出判断逻辑
回测引擎 SHALL 在每个交易日对持仓股票执行动态卖出判断：
1. 调用 `score_stock_for_sell()` 获取当前评分
2. 若评分低于 `dynamic_sell_score_threshold`，触发动态卖出
3. 动态卖出价格为当日开盘价（与止盈止损卖出一致）

#### Scenario: 评分低于阈值触发卖出
- **WHEN** 持仓股票当日重评分数为 `0.45`，阈值为 `0.5`
- **THEN** 触发动态卖出，记录卖出原因类型为 `dynamic_score`

#### Scenario: 评分高于阈值不卖出
- **WHEN** 持仓股票当日重评分数为 `0.55`，阈值为 `0.5`
- **THEN** 不触发动态卖出，继续持有
