# ml-label-generator Specification

## Purpose
标签生成器采用两步式流程：先在 per-stock 层面计算未来收益率并剔除一字板，再在全市场截面分配多档标签，供 XGBoost Ranker 学习股票间的精细排序。

## Requirements
### Requirement: 两步式标签生成
标签生成器 SHALL 分为两步执行：

1. `compute_future_returns()`: per-stock 计算 `future_ret`，模拟止盈止损离场路径，剔除 T+1 一字板
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
