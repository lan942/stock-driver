# ml-feature-engine Specification

## Purpose
TBD - created by archiving change add-xgboost-ml-strategy. Update Purpose after archive.
## Requirements
### Requirement: 从数据库加载 OHLCV 数据并计算特征
特征引擎 SHALL 从 `stock_daily` 表中读取所有股票的 OHLCV 数据，计算平稳化量化特征并返回特征 DataFrame。

输入字段 SHALL 包含：`open`, `high`, `low`, `close`, `volume`。

计算的初始特征列表 SHALL 包含：
- `ret_1d`：1 日对数收益率 `ln(close_t / close_{t-1})`
- `ret_5d`：5 日对数收益率 `ln(close_t / close_{t-5})`
- `volatility_10d`：过去 10 个交易日 `ret_1d` 的标准差
- `vol_change_1d`：成交量相对变化 `volume_t / volume_{t-1} - 1`
- `bias_20d`：收盘价偏离 20 日均线的百分比 `(close_t - sma_20) / sma_20`

所有滚动窗口计算 SHALL 使用 `pandas.DataFrame.rolling()` 方法，并丢弃因滚动窗口产生的 NaN 行。

#### Scenario: 正常计算特征
- **WHEN** 输入包含 60 个交易日的完整 OHLCV 数据
- **THEN** 返回包含 `ret_1d`, `ret_5d`, `volatility_10d`, `vol_change_1d`, `bias_20d` 五个特征列的 DataFrame，至少 40 行有效数据（60 - max(20, 5, 1) 窗口消耗）

#### Scenario: 数据不足时返回空
- **WHEN** 输入数据不足一个完整滚动窗口周期（如少于 21 个交易日）
- **THEN** 返回空的 DataFrame

### Requirement: 特征可扩展性
特征引擎 SHALL 支持通过 `extra_features` 参数添加自定义特征函数。每个自定义特征函数 SHALL 接受原始 DataFrame 并返回一个 Series 作为新特征列。

#### Scenario: 添加自定义特征
- **WHEN** 调用 `build_features(df, extra_features={'rsi_14': rsi_func})` 且 `rsi_func` 返回有效的 Series
- **THEN** 返回的 DataFrame 包含基础 5 个特征 + `rsi_14` 列

### Requirement: 按单只股票独立计算
特征引擎 SHALL 以每只股票为单位独立计算特征，确保跨股票的特征值不会相互干扰（不同股票的滚动窗口各自独立）。

#### Scenario: 多只股票特征计算
- **WHEN** 输入包含多只股票的混合数据，DataFrame 按 code 分组
- **THEN** 对每个 code 分组独立执行特征计算，重组后返回

