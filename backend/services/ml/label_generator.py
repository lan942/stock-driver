"""标签生成器

根据未来 N 日涨跌生成多档排序标签，用于 XGBoost Ranker 学习。

核心规则：
- 买入价 = T+1 日开盘价（信号在 T 日收盘后产生，T+1 开盘才能成交）
- 卖出价 = 实际离场价（可能提前触发止盈止损，或持有到期）
- future_ret = 实际离场价 / 买入价 - 1
- 必须先完成特征构建（build_features）后再调用 compute_future_returns
- T+1 一字涨停的样本会被剔除（实盘无法买入）
- 模拟动态止盈止损离场路径，让模型学习目标与实盘一致

两步式标签生成：
1. compute_future_returns (per-stock): 计算 future_ret（含止盈止损模拟），剔除一字板
2. assign_labels (全市场 concat 后): 按日期截面分配多档标签

标签分配策略：
- cross_sectional_qcut（默认）: 将截面 future_ret 分成多档（如 5 档），0-4
  多档标签让 XGBRanker 能构建更丰富的偏序对，学习股票间的精细排序
- cross_sectional_median: future_ret > 当日全市场中位数 → label=1（二分类，兼容旧版）
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


def compute_future_returns(
    df: pd.DataFrame,
    lookahead: int = 5,
    stop_profit_pct: float = 0.06,
    stop_loss_pct: float = 0.03
) -> pd.DataFrame:
    """计算未来收益率（含动态止盈止损模拟）并剔除 T+1 一字板样本（per-stock）

    在 build_features 之后调用。返回带 'future_ret' 列的 DataFrame（已 dropna）。
    不分配 label —— label 需要在全市场数据合并后通过 assign_labels 截面分配。

    T+1 一字涨停的样本会被剔除：实盘中无法以涨停价买入，
    保留这些样本会让模型学到虚假的"神仙球"收益。

    模拟动态止盈止损离场路径：
    - T+1 开盘买入
    - T+1 至 T+lookahead 逐日扫描 high/low
    - 最高价触及止盈线 → 当日以 high 卖出（扣除摩擦成本）
    - 最低价触及止损线 → 当日以 low 卖出（扣除摩擦成本）
    - 未触发 → T+lookahead 以 close 卖出（扣除摩擦成本）

    Args:
        df: 包含 'close', 'open', 'high', 'low' 列的特征 DataFrame（单只股票）
        lookahead: 预测窗口，未来 N 个交易日，默认 5
        stop_profit_pct: 止盈比例，默认 6%
        stop_loss_pct: 止损比例，默认 3%

    Returns:
        新增 'future_ret' 列的 DataFrame（已 dropna，无 label 列）
    """
    if df.empty:
        return df

    for col in ('close', 'open', 'high', 'low'):
        if col not in df.columns:
            raise ValueError(f"DataFrame 缺少 '{col}' 列")

    # 需要 lookahead+1 天的未来数据
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

    # T+1 开盘买入价（含买入摩擦成本）
    buy_price = df['open'].shift(-1) * (1 + 0.0015)

    # 模拟动态止盈止损离场路径
    # 构建未来 lookahead 天的价格矩阵
    future_high = []
    future_low = []
    future_close = []
    for i in range(1, lookahead + 1):
        future_high.append(df['high'].shift(-i))
        future_low.append(df['low'].shift(-i))
        future_close.append(df['close'].shift(-i))

    # 转换为 DataFrame，每行对应 T 日，每列对应 T+i 日
    future_high_df = pd.DataFrame(future_high).T
    future_low_df = pd.DataFrame(future_low).T
    future_close_df = pd.DataFrame(future_close).T

    # 逐行计算实际离场价
    exit_prices = []
    for idx, row in df.iterrows():
        bp = buy_price.loc[idx]
        if pd.isna(bp):
            exit_prices.append(pd.NA)
            continue

        stop_profit_price = bp * (1 + stop_profit_pct)
        stop_loss_price = bp * (1 - stop_loss_pct)

        exited = False
        exit_price = None

        # 逐日扫描 T+1 至 T+lookahead
        for i in range(lookahead):
            high_t = future_high_df.iloc[future_high_df.index.get_loc(idx), i]
            low_t = future_low_df.iloc[future_low_df.index.get_loc(idx), i]

            if pd.isna(high_t) or pd.isna(low_t):
                continue

            # 触及止盈
            if high_t >= stop_profit_price:
                exit_price = high_t
                exited = True
                break

            # 触及止损
            if low_t <= stop_loss_price:
                exit_price = low_t
                exited = True
                break

        # 未触发，到期以收盘价卖出
        if not exited:
            exit_price = future_close_df.iloc[future_close_df.index.get_loc(idx), lookahead - 1]

        exit_prices.append(exit_price)

    # 计算实际收益率（含卖出摩擦成本）
    exit_prices_series = pd.Series(exit_prices, index=df.index)
    sell_price = exit_prices_series * (1 - 0.0015)
    df['future_ret'] = sell_price / buy_price - 1

    # 丢弃最后 lookahead+1 天无法计算未来收益的行
    return df.dropna()


def assign_labels(
    df: pd.DataFrame,
    method: str = 'cross_sectional_qcut',
    qcut_bins: int = 5
) -> pd.DataFrame:
    """分配排序标签（需要全市场数据，在 concat 后调用）

    A 股"牛短熊长、同涨同跌"，用绝对收益 future_ret > 0 做标签会让模型学大盘择时（Beta）
    而非选股（Alpha）。截面去中心化（和当天市场中位数比）能剥离 Beta，让模型专注选股。

    多档标签相比二分类的优势：
    - XGBRanker 使用 rank:pairwise 进行成对比较
    - 二分类只有 0/1，大量同类样本无法构建有效偏序对
    - 多档标签让模型学习更精细的股票排序关系

    Args:
        df: 包含 'future_ret' 和 'date' 列的全市场 DataFrame
        method: 标签分配方法
            - 'cross_sectional_qcut': 将截面 future_ret 分成 qcut_bins 档，0 最差，qcut_bins-1 最好（默认，推荐）
            - 'cross_sectional_median': future_ret > 当日全市场中位数 → label=1（二分类，兼容旧版）
            - 'absolute': future_ret > 0 → label=1（会学大盘择时，不推荐）
        qcut_bins: 分档数量，默认 5 档（0-4）

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

    if method == 'cross_sectional_qcut':
        if 'date' not in df.columns:
            raise ValueError("cross_sectional_qcut 方法需要 'date' 列")

        def assign_qcut(group):
            try:
                return pd.qcut(
                    group['future_ret'],
                    q=qcut_bins,
                    labels=range(qcut_bins),
                    duplicates='drop'
                )
            except ValueError:
                return pd.Series([0] * len(group), index=group.index)

        df['label'] = df.groupby('date', group_keys=False).apply(assign_qcut).astype(int)

    elif method == 'cross_sectional_median':
        if 'date' not in df.columns:
            raise ValueError("cross_sectional_median 方法需要 'date' 列")
        # 按日期截面去中心化：和当天全市场中位数比，剥离大盘 Beta
        daily_median = df.groupby('date')['future_ret'].transform('median')
        df['label'] = (df['future_ret'] > daily_median).astype(int)

    elif method == 'absolute':
        df['label'] = (df['future_ret'] > 0).astype(int)

    else:
        raise ValueError(
            f"未知 label method: {method}，支持 'cross_sectional_qcut' / 'cross_sectional_median' / 'absolute'"
        )

    return df
