# xgboost-dynamic-score-sell Specification

## Purpose
定义XGBoost动态评分卖出机制。持仓期间每日收盘后重新评分，评分恶化时次日开盘价卖出。

## Requirements

### Requirement: 持有期间重评方法
策略 SHALL 提供全市场评分方法 `_score_all_market_stocks()`，在回测主循环中每个交易日执行一次 GPU 批量预测，得到全市场所有股票的评分。该方法同时用于买入选股和持仓卖出检测。

#### Scenario: 每日全市场重评
- **WHEN** 回测运行到交易日 T
- **THEN** 对全市场所有股票执行一次批量预测，获取评分列表

#### Scenario: 数据不足时跳过
- **WHEN** 某只股票数据不足30个交易日
- **THEN** 该股票不参与评分

### Requirement: 动态卖出评分阈值配置
策略配置 SHALL 包含以下动态卖出参数：

| 配置键 | 默认值 | 说明 |
|---|---|---|
| `dynamic_sell_enabled` | `true` | 启用动态评分卖出 |
| `dynamic_sell_percentile_threshold` | `0.30` | 百分位阈值（评分跌出全市场前 1-N 则卖出） |
| `dynamic_sell_score_decline_days` | `2` | 连续下降天数阈值 |
| `dynamic_sell_score_absolute_threshold` | `0.30` | 绝对分阈值 |
| `dynamic_sell_min_hold_days` | `2` | 最小持仓天数（T+1后至少再持N天） |

### Requirement: 动态卖出判断逻辑
回测引擎 SHALL 在每个交易日收盘后对持仓股票执行动态卖出判断（至少持有 `dynamic_sell_min_hold_days` 天后生效）：

三项条件任意满足即触发——使用 `_check_close_triggers` 方法在收盘后评估：
1. 评分跌出全市场百分位阈值 → `dynamic_score_low`
2. 连续 N 天评分下降 → `dynamic_score_decline`
3. 评分低于绝对阈值 → `dynamic_score_low`

触发后加入 `pending_sells` 队列，**次交易日开盘价**卖出。

#### Scenario: 评分低于百分位阈值触发卖出
- **WHEN** 持仓股票评分处于全市场底部 30%（百分位 < 0.30）
- **THEN** 加入 pending_sells 队列，次交易日开盘价卖出，原因类型为 `dynamic_score_low`

#### Scenario: 连续下降触发卖出
- **WHEN** 持仓股票连续 2 天评分下降，且当日评分低于最后一天
- **THEN** 加入 pending_sells 队列，次交易日开盘价卖出，原因类型为 `dynamic_score_decline`

#### Scenario: 评分正常不卖出
- **WHEN** 持仓股票评分高于所有阈值、不在底部百分位、评分未连续下降
- **THEN** 不触发动态卖出，继续持有

### Requirement: 实盘对应
- 收盘后获取当日全市场模型评分
- 评分恶化的股票加入次日集合竞价卖出清单
- 不参与日内操作，与止损条件单互不冲突
