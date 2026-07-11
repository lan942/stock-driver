# ml-label-generator Specification

## Purpose
TBD - created by archiving change add-xgboost-ml-strategy. Update Purpose after archive.
## Requirements
### Requirement: 基于未来 N 日涨跌生成二分类标签
标签生成器 SHALL 根据 `lookahead` 参数计算未来 N 个交易日后的收益率，并生成二分类标签：上涨（future_ret > 0）标为 1，下跌标为 0。

SHALL 使用 `close.shift(-lookahead) / close - 1` 计算未来收益率，丢弃因 shift 产生的最后 N 行 NaN 数据。

#### Scenario: 正常生成标签
- **WHEN** 输入包含 50 个交易日数据的特征 DataFrame，`lookahead=5`
- **THEN** 返回新增 `future_ret` 和 `label` 列的 DataFrame，有效行数 = 原始行数 - 5

#### Scenario: 数据不足时返回空
- **WHEN** 输入数据行数 <= lookahead
- **THEN** 返回空的 DataFrame

### Requirement: 严禁数据穿越
标签生成器 SHALL 严格确保 `future_ret` 的计算使用未来价格对齐到当前日期，不得将未来信息泄漏到特征中。`shift(-lookahead)` 操作 SHALL 在特征已经完全计算完毕后执行（即先执行 `build_features` 再执行 `generate_labels`）。

#### Scenario: 验证时序对齐
- **WHEN** 2024-01-10 的 `feature` 列 `ret_1d` 使用 2024-01-10 与 2024-01-09 的收盘价
- **THEN** 2024-01-10 的 `label` 使用 2024-01-15 与 2024-01-10 的收盘价计算 future_ret，且 `feature` 计算不涉及 2024-01-11 之后的数据

### Requirement: lookahead 参数可配置
`generate_labels()` 函数 SHALL 接受 `lookahead` 参数（默认值 5），允许调整预测窗口。lookahead SHALL 为正整数。

#### Scenario: 使用不同的预测窗口
- **WHEN** 调用 `generate_labels(df, lookahead=10)`
- **THEN** 标签基于未来 10 个交易日的涨跌生成

