"""标签生成器

根据未来 N 日涨跌生成二分类标签，用于监督学习。

核心规则：
- 使用 close.shift(-lookahead) 将未来价格对齐到今天，严格避免数据穿越
- future_ret > 0 → label=1（上涨），否则 label=0（下跌）
- 必须先完成特征构建（build_features）后再调用本函数
"""

import pandas as pd


def generate_labels(df: pd.DataFrame, lookahead: int = 5) -> pd.DataFrame:
    """构建预测目标（Target）：未来 N 个交易日的绝对收益率是否大于 0

    严禁在 build_features 之前调用！标签计算涉及 shift(-N) 操作，
    必须确保所有特征都已基于历史数据计算完毕。

    Args:
        df: 包含 'close' 列的特征 DataFrame
        lookahead: 预测窗口，未来 N 个交易日，默认 5

    Returns:
        新增 'future_ret' 和 'label' 列的 DataFrame（已 dropna）
    """
    if df.empty:
        return df

    if 'close' not in df.columns:
        raise ValueError("DataFrame 缺少 'close' 列")

    if len(df) <= lookahead:
        return pd.DataFrame()

    df = df.copy()

    # 将未来价格对齐到今天：close_{t+N} / close_t - 1
    # 注意：这是极易发生"未来函数"泄露的地方，必须确保不提前调用
    df['future_ret'] = df['close'].shift(-lookahead) / df['close'] - 1

    # 二分类标签：上涨=1，下跌=0
    df['label'] = (df['future_ret'] > 0).astype(int)

    # 丢弃最后 N 天无法计算未来收益的行
    return df.dropna()
