"""标签生成器

根据未来 N 日涨跌生成二分类标签，用于监督学习。

核心规则：
- 买入价 = T+1 日开盘价（信号在 T 日收盘后产生，T+1 开盘才能成交）
- 卖出价 = T+lookahead 日收盘价
- future_ret = close_{t+lookahead} / open_{t+1} - 1
- 必须先完成特征构建（build_features）后再调用 compute_future_returns
- T+1 一字涨停的样本会被剔除（实盘无法买入）

两步式标签生成：
1. compute_future_returns (per-stock): 计算 future_ret，剔除一字板
2. assign_labels (全市场 concat 后): 按日期截面去中心化分配 label

标签分配策略：
- cross_sectional_median（默认）: future_ret > 当日全市场中位数 → label=1
  A 股"牛短熊长、同涨同跌"，绝对收益高度依赖大盘 Beta。
  截面去中心化剥离 Beta，让模型学选股 Alpha；类别自然 50/50 平衡。
- absolute: future_ret > 0 → label=1（会学到大盘择时，不推荐）
"""

import pandas as pd


def _get_limit_up_pct(code: str, name: str = '') -> float:
    """根据股票代码前缀和名称返回涨停比例阈值（留 0.2% 容差）

    Args:
        code: 股票代码，如 '600519'、'300750'、'688981'
        name: 股票名称，用于识别 ST/*ST 股票

    Returns:
        涨停比例阈值，达到即视为涨停
    """
    if not isinstance(code, str) or len(code) < 2:
        return 0.098

    name_upper = str(name).upper() if name else ''
    if 'ST' in name_upper:
        return 0.048  # ST/*ST 股票 5%

    if code.startswith(('30', '68')):
        return 0.198  # 创业板、科创板 20%
    if code.startswith(('8', '4')):
        return 0.298  # 北交所 30%
    return 0.098  # 主板 10%


def compute_future_returns(df: pd.DataFrame, lookahead: int = 5) -> pd.DataFrame:
    """计算未来收益率并剔除 T+1 一字板样本（per-stock）

    在 build_features 之后调用。返回带 'future_ret' 列的 DataFrame（已 dropna）。
    不分配 label —— label 需要在全市场数据合并后通过 assign_labels 截面分配。

    T+1 一字涨停的样本会被剔除：实盘中无法以涨停价买入，
    保留这些样本会让模型学到虚假的"神仙球"收益。

    Args:
        df: 包含 'close' 和 'open' 列的特征 DataFrame（单只股票）
        lookahead: 预测窗口，未来 N 个交易日，默认 5

    Returns:
        新增 'future_ret' 列的 DataFrame（已 dropna，无 label 列）
    """
    if df.empty:
        return df

    for col in ('close', 'open'):
        if col not in df.columns:
            raise ValueError(f"DataFrame 缺少 '{col}' 列")

    # 需要 lookahead+1 天的未来数据（shift(-1) 取 T+1 开盘，shift(-lookahead) 取 T+lookahead 收盘）
    if len(df) <= lookahead + 1:
        return pd.DataFrame()

    df = df.copy()

    # 判定 T+1 是否涨停：open_{t+1} / close_t - 1 >= 涨停阈值 → 一字板，无法买入
    t1_open_ret = df['open'].shift(-1) / df['close'] - 1
    if 'code' in df.columns:
        if 'name' in df.columns:
            limit_up_pct = df.apply(
                lambda row: _get_limit_up_pct(row['code'], row['name']),
                axis=1
            )
        else:
            limit_up_pct = df['code'].map(_get_limit_up_pct)
    else:
        limit_up_pct = 0.098

    tradable = t1_open_ret < limit_up_pct
    df = df[tradable].copy()

    if len(df) <= lookahead + 1:
        return pd.DataFrame()

    # T 日产生信号 → T+1 开盘买入 → T+lookahead 收盘卖出
    # future_ret = 卖出价 / 买入价 - 1
    df['future_ret'] = df['close'].shift(-lookahead) / df['open'].shift(-1) - 1

    # 丢弃最后 lookahead+1 天无法计算未来收益的行
    return df.dropna()


def assign_labels(
    df: pd.DataFrame, method: str = 'cross_sectional_median'
) -> pd.DataFrame:
    """分配二分类标签（需要全市场数据，在 concat 后调用）

    A 股"牛短熊长、同涨同跌"，用绝对收益 future_ret > 0 做标签会让模型学大盘择时（Beta）
    而非选股（Alpha）。牛市时 80%+ 标签为 1，熊市时 80%+ 为 0，类别分布随市场漂移。
    截面去中心化（和当天市场中位数比）能剥离 Beta，让模型专注选股，且类别自然 50/50 平衡。

    Args:
        df: 包含 'future_ret' 和 'date' 列的全市场 DataFrame
        method: 标签分配方法
            - 'cross_sectional_median': future_ret > 当日全市场中位数 → label=1（默认，推荐）
            - 'absolute': future_ret > 0 → label=1（原始方式，会学大盘择时，不推荐）

    Returns:
        新增 'label' 列的 DataFrame
    """
    if df.empty:
        return df

    if 'future_ret' not in df.columns:
        raise ValueError(
            "DataFrame 缺少 'future_ret' 列，请先调用 compute_future_returns"
        )

    df = df.copy()

    if method == 'cross_sectional_median':
        if 'date' not in df.columns:
            raise ValueError("cross_sectional_median 方法需要 'date' 列")
        # 按日期截面去中心化：和当天全市场中位数比，剥离大盘 Beta
        daily_median = df.groupby('date')['future_ret'].transform('median')
        df['label'] = (df['future_ret'] > daily_median).astype(int)
    elif method == 'absolute':
        df['label'] = (df['future_ret'] > 0).astype(int)
    else:
        raise ValueError(
            f"未知 label method: {method}，支持 'cross_sectional_median' / 'absolute'"
        )

    return df
