# ml-label-generator Specification

## Purpose
标签生成器采用两步式流程：先在 per-stock 层面计算未来收益率并剔除一字板，再在全市场截面分配多档标签，供 XGBoost Ranker 学习股票间的精细排序。

离场路径与回测引擎逻辑完全一致：日内只止损（low 触及即卖），止盈/动态离场/超时均在收盘后评估、次日开盘价卖出。

## Requirements
### Requirement: 两步式标签生成
标签生成器 SHALL 分为两步执行：

1. `compute_future_returns()`: per-stock 计算 `future_ret`，模拟止盈止损离场路径（与回测引擎一致），剔除 T+1 一字板
2. `assign_labels()`: 全市场 concat 后，按日期截面分配多档标签

#### Scenario: 正常两步式流程
- **WHEN** 先调用 `compute_future_returns(df, lookahead=5)` 计算 per-stock 的 future_ret
- **THEN** 返回新增 `future_ret` 列的 DataFrame，一字板样本被标记为 NaN

#### Scenario: 截面分配标签
- **WHEN** 将所有股票的 compute_future_returns 结果 concat，调用 `assign_labels(full, method='cross_sectional_qcut', qcut_bins=5)`
- **THEN** 按日期截面将 future_ret 等分为 5 档，label 值为 0-4

### Requirement: 严禁数据穿越
特征构建 SHALL 在调用 `compute_future_returns` 之前完成。`compute_future_returns` 使用 `open.shift(-1)` 作为 T+1 买入价，确保不使用未来信息。

#### Scenario: 验证时序对齐
- **WHEN** 2024-01-10 的特征使用 2024-01-10 及之前的数据计算
- **THEN** 2024-01-10 的 `future_ret` 使用 T+1 开盘价买入、模拟持仓后的实际收益率，且特征计算不涉及 2024-01-11 之后的数据

### Requirement: lookahead 参数可配置
`compute_future_returns()` 函数 SHALL 接受 `lookahead` 参数（默认值 5），允许调整预测窗口。lookahead SHALL 为正整数。

#### Scenario: 使用不同的预测窗口
- **WHEN** 调用 `compute_future_returns(df, lookahead=10)`
- **THEN** 标签基于未来 10 个交易日的模拟持仓收益生成

### Requirement: 模拟离场路径（与回测引擎一致）
`compute_future_returns()` SHALL 模拟以下离场路径，与回测引擎 `_check_intraday_stop_loss` 和 `_check_close_triggers` 逻辑一致：

1. T+1 开盘买入（含买入摩擦 0.15%）
2. T+1 至 T+lookahead 逐日扫描：
   - **日内止损**：当日 low 触及止损线 → 以 low 价卖出（唯一日内操作，扣除卖出摩擦 0.15%）
   - **收盘后止盈**：当日 close >= 止盈线 → **次日开盘价**卖出
   - **收盘后动态离场**：连续 N 天日收益为负 → **次日开盘价**卖出
3. 未触发 → 强制时间平仓：T+lookahead+1 **开盘价**卖出

#### Scenario: 止损离场
- **WHEN** T+3 日最低价触及止损线（buy_price * (1 - stop_loss_pct)）
- **THEN** future_ret = (low / buy_price * 0.9985) - 1

#### Scenario: 止盈离场（收盘评估，次日开盘卖）
- **WHEN** T+2 日收盘价 >= 止盈线（buy_price * (1 + stop_profit_pct)）
- **THEN** future_ret = (T+3_open / buy_price * 0.9985) - 1

#### Scenario: 动态离场（收盘评估，次日开盘卖）
- **WHEN** 连续 2 天日收益为负
- **THEN** 次日开盘价卖出，future_ret = (next_open / buy_price * 0.9985) - 1

#### Scenario: 到期平仓（次日开盘卖）
- **WHEN** 持有至 T+5 未触发任何条件
- **THEN** future_ret = (T+6_open / buy_price * 0.9985) - 1

### Requirement: T+1 一字涨停剔除
当 T+1 开盘涨幅 >= 板块涨停阈值时，该样本 SHALL 被剔除（实盘中无法以涨停价买入）。

#### Scenario: 剔除非ST主板一字涨停样本
- **WHEN** open_t+1 / close_t - 1 >= 0.098
- **THEN** 删除该行

### Requirement: 一字跌停离场惩罚
离场日若为一字跌停（open ≈ high ≈ low ≈ close），SHALL 尝试顺延一天以次日开盘价卖出。若次日仍锁死，标记 `_limit_down_exit=True`，`assign_labels` 强制设为最差档。

#### Scenario: 一字跌停可顺延
- **WHEN** 离场日一字跌停，次日未锁死
- **THEN** 以次日开盘价卖出，不标记惩罚

#### Scenario: 一字跌停无法顺延
- **WHEN** 离场日一字跌停，次日仍锁死
- **THEN** 标记 `_limit_down_exit=True`，assign_labels 将 label 强制设为 0
