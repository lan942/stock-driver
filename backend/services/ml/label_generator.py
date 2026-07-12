"""标签生成器

根据未来 N 日涨跌生成多档排序标签，用于 XGBoost Ranker 学习。

核心规则：
- 买入价 = T+1 日开盘价（信号在 T 日收盘后产生，T+1 开盘才能成交）
- 卖出价 = 实际离场价（可能提前触发止盈止损，或持有到期）
- future_ret = 实际离场价 / 买入价 - 1
- 必须先完成特征构建（build_features）后再调用 compute_future_returns
- T+1 一字涨停的样本会被剔除（实盘无法买入）
- 离场日一字跌停的样本会被标记，在 assign_labels 中强制惩罚
- 模拟动态止盈止损离场路径，让模型学习目标与实盘一致

两步式标签生成：
1. compute_future_returns (per-stock): 计算 future_ret（含止盈止损模拟），剔除一字板，标记一字跌停
2. assign_labels (全市场 concat 后): 按日期截面分配多档标签，一字跌停样本强制设为最差档

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
    stop_loss_pct: float = 0.03,
    force_close_method: str = 'day_n_close'
) -> pd.DataFrame:
    """计算未来收益率（含动态止盈止损模拟）并剔除 T+1 一字板样本（per-stock）

    在 build_features 之后调用。返回带 'future_ret' 和 '_limit_down_exit' 列的 DataFrame（已 dropna）。
    不分配 label —— label 需要在全市场数据合并后通过 assign_labels 截面分配。

    T+1 一字涨停的样本会被剔除：实盘中无法以涨停价买入，
    保留这些样本会让模型学到虚假的"神仙球"收益。

    模拟动态止盈止损离场路径：
    - T+1 开盘买入
    - T+1 至 T+lookahead 逐日扫描 high/low
    - 最高价触及止盈线 → 当日以 high 卖出（扣除摩擦成本）
    - 最低价触及止损线 → 当日以 low 卖出（扣除摩擦成本）
    - 未触发 → 强制时间平仓（见 force_close_method）

    一字跌停离场处理：
    - 离场日如果开盘≈最高≈最低≈收盘（完全锁死），判定为一字跌停
    - 尝试顺延一天以次日开盘价卖出
    - 如果次日仍锁死，标记 _limit_down_exit=True（assign_labels 会强制惩罚）

    强制时间平仓（确保模型学习的时间周期与实盘策略完全一致）：
    - day_n_close: 第 T+lookahead 天的收盘价（默认）
    - day_n_plus_1_open: 第 T+lookahead+1 天的开盘价

    Args:
        df: 包含 'close', 'open', 'high', 'low' 列的特征 DataFrame（单只股票）
        lookahead: 预测窗口，未来 N 个交易日，默认 5
        stop_profit_pct: 止盈比例，默认 6%
        stop_loss_pct: 止损比例，默认 3%
        force_close_method: 强制平仓方式
            - 'day_n_close': 第 N 天收盘价（默认）
            - 'day_n_plus_1_open': 第 N+1 天开盘价

    Returns:
        新增 'future_ret' 和 '_limit_down_exit' 列的 DataFrame（已 dropna，无 label 列）
    """
    if df.empty:
        return df

    for col in ('close', 'open', 'high', 'low'):
        if col not in df.columns:
            raise ValueError(f"DataFrame 缺少 '{col}' 列")

    required_future_days = lookahead + 2 if force_close_method == 'day_n_plus_1_open' else lookahead + 1
    if len(df) <= required_future_days:
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

    if len(df) <= required_future_days:
        return pd.DataFrame()

    # T+1 开盘买入价（含买入摩擦成本）
    buy_price = df['open'].shift(-1) * (1 + 0.0015)

    # 获取该股票的跌停阈值（用于判定一字跌停的跌幅门槛）
    code_for_limit = df['code'].iloc[0] if 'code' in df.columns else '000000'
    name_for_limit = df['name'].iloc[0] if 'name' in df.columns else ''
    board_limit_down_pct = _get_limit_up_pct(code_for_limit, name_for_limit)

    # 模拟动态止盈止损离场路径
    # 构建未来 lookahead+2 天的价格矩阵（+1 天用于 day_n_plus_1_open，再 +1 天用于一字跌停顺延卖出）
    future_high = []
    future_low = []
    future_close = []
    future_open = []
    for i in range(1, lookahead + 3):
        future_high.append(df['high'].shift(-i))
        future_low.append(df['low'].shift(-i))
        future_close.append(df['close'].shift(-i))
        future_open.append(df['open'].shift(-i))

    # 转换为 DataFrame，每行对应 T 日，每列对应 T+i 日
    future_high_df = pd.DataFrame(future_high).T
    future_low_df = pd.DataFrame(future_low).T
    future_close_df = pd.DataFrame(future_close).T
    future_open_df = pd.DataFrame(future_open).T

    # 逐行计算实际离场价
    exit_prices = []
    limit_down_exit_flags = []
    for idx, row in df.iterrows():
        bp = buy_price.loc[idx]
        if pd.isna(bp):
            exit_prices.append(pd.NA)
            limit_down_exit_flags.append(False)
            continue

        stop_profit_price = bp * (1 + stop_profit_pct)
        stop_loss_price = bp * (1 - stop_loss_pct)

        exited = False
        exit_price = None
        exit_day_idx = -1

        pos = future_high_df.index.get_loc(idx)

        # 逐日扫描 T+1 至 T+lookahead
        for i in range(lookahead):
            high_t = future_high_df.iloc[pos, i]
            low_t = future_low_df.iloc[pos, i]

            if pd.isna(high_t) or pd.isna(low_t):
                continue

            # 触及止盈
            if high_t >= stop_profit_price:
                exit_price = high_t
                exit_day_idx = i
                exited = True
                break

            # 触及止损
            if low_t <= stop_loss_price:
                exit_price = low_t
                exit_day_idx = i
                exited = True
                break

        # 未触发，到期强制平仓
        if not exited:
            if force_close_method == 'day_n_plus_1_open':
                exit_day_idx = lookahead
                exit_price = future_open_df.iloc[pos, lookahead]
            else:
                exit_day_idx = lookahead - 1
                exit_price = future_close_df.iloc[pos, lookahead - 1]

        # 检测离场日是否为一字跌停（实盘无法卖出）
        limit_down_exit = False
        if exit_price is not None and not pd.isna(exit_price) and exit_day_idx >= 0:
            exit_high = future_high_df.iloc[pos, exit_day_idx]
            exit_low = future_low_df.iloc[pos, exit_day_idx]
            exit_open_t = future_open_df.iloc[pos, exit_day_idx]
            exit_close_t = future_close_df.iloc[pos, exit_day_idx]

            # 一字跌停判定：开盘≈最高≈最低≈收盘（完全锁死无流动性），且相对买入价大幅下跌
            if not pd.isna(exit_open_t) and not pd.isna(exit_close_t):
                is_locked = (
                    abs(exit_open_t - exit_high) < 0.01 and
                    abs(exit_high - exit_low) < 0.01 and
                    abs(exit_low - exit_close_t) < 0.01
                )
                decline_pct = (exit_price / bp - 1)
                is_limit_down = is_locked and decline_pct < -board_limit_down_pct

                if is_limit_down:
                    # 尝试顺延一天卖出（以次日开盘价卖出）
                    next_day = exit_day_idx + 1
                    limit_down_exit = True
                    if next_day < future_high_df.shape[1]:
                        next_open = future_open_df.iloc[pos, next_day]
                        next_high = future_high_df.iloc[pos, next_day]
                        next_low = future_low_df.iloc[pos, next_day]
                        next_close = future_close_df.iloc[pos, next_day]

                        if (not pd.isna(next_open) and not pd.isna(next_low) and
                            not pd.isna(next_high) and not pd.isna(next_close)):
                            next_locked = (
                                abs(next_open - next_high) < 0.01 and
                                abs(next_high - next_low) < 0.01 and
                                abs(next_low - next_close) < 0.01
                            )
                            if not next_locked:
                                exit_price = next_open
                                limit_down_exit = False

        exit_prices.append(exit_price)
        limit_down_exit_flags.append(limit_down_exit)

    # 计算实际收益率（含卖出摩擦成本）
    exit_prices_series = pd.Series(exit_prices, index=df.index)
    sell_price = exit_prices_series * (1 - 0.0015)
    df['future_ret'] = sell_price / buy_price - 1
    df['_limit_down_exit'] = limit_down_exit_flags

    # 丢弃最后 lookahead+2 天无法计算未来收益的行
    return df.dropna(subset=['future_ret'])


def assign_labels(
    df: pd.DataFrame,
    method: str = 'cross_sectional_qcut',
    qcut_bins: int = 5
) -> pd.DataFrame:
    """分配排序标签（需要全市场数据，在 concat 后调用）

    A 股"牛短熊长、同涨同跌"，用绝对收益 future_ret > 0 做标签会让模型学大盘择时（Beta）
    而非选股（Alpha）。截面去中心化（和当天市场中位数比）能剥离 Beta，让模型专注选股。

    一字跌停离场惩罚：
    - compute_future_returns 会在离场日一字跌停时标记 _limit_down_exit=True
    - 本函数检测该标记，将对应样本强制设为 label=0（最差档）
    - 目的：让模型学会避开那些容易被连续跌停"核按钮"的高位股

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

    # 一字跌停离场样本：把 future_ret 替换为极小值，确保 qcut 落入最差档
    has_limit_down_flag = '_limit_down_exit' in df.columns
    if has_limit_down_flag:
        limit_down_mask = df['_limit_down_exit'] == True
        limit_down_count = limit_down_mask.sum()
        if limit_down_count > 0:
            if method == 'cross_sectional_qcut':
                # 将 future_ret 替换为一个远小于截面最小值的数，保证 qcut 落入第 0 档
                min_ret = df['future_ret'].min()
                df.loc[limit_down_mask, 'future_ret'] = min_ret - abs(min_ret) * 0.1 - 0.01
            elif method == 'cross_sectional_median':
                # 强制 future_ret = 一个极小的负数，确保低于中位数
                df.loc[limit_down_mask, 'future_ret'] = -999.0
            # absolute 方法：跌停必然 future_ret < 0，天然归为 label=0

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
        daily_median = df.groupby('date')['future_ret'].transform('median')
        df['label'] = (df['future_ret'] > daily_median).astype(int)

    elif method == 'absolute':
        df['label'] = (df['future_ret'] > 0).astype(int)

    else:
        raise ValueError(
            f"未知 label method: {method}，支持 'cross_sectional_qcut' / 'cross_sectional_median' / 'absolute'"
        )

    # 最终确认：一字跌停样本强制 label=0（二次保险）
    if has_limit_down_flag and limit_down_mask.sum() > 0:
        df.loc[df['_limit_down_exit'] == True, 'label'] = 0

    return df
