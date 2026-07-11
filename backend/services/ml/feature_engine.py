"""特征引擎

从原始 OHLCV 数据计算平稳化量化特征，用于机器学习模型输入。

核心特征：
- ret_1d / ret_5d: 对数收益率（消除价格量纲差异）
- volatility_10d: 过去 10 日收益率标准差
- vol_change_1d: 成交量相对变化率
- bias_20d: 收盘价偏离 20 日均线百分比
"""

from typing import Callable, Dict, Optional

import numpy as np
import pandas as pd


def _build_single_stock_features(df: pd.DataFrame) -> pd.DataFrame:
    """对单只股票的 DataFrame 计算特征（内部方法）"""
    df = df.copy()

    # 基础收益率特征（对数收益率，比简单收益率更平稳）
    df['ret_1d'] = np.log(df['close'] / df['close'].shift(1))
    df['ret_5d'] = np.log(df['close'] / df['close'].shift(5))

    # 波动率特征
    df['volatility_10d'] = df['ret_1d'].rolling(window=10).std()

    # 量价特征
    df['vol_change_1d'] = df['volume'] / df['volume'].shift(1) - 1

    # 均线偏离度
    sma_20 = df['close'].rolling(window=20).mean()
    df['bias_20d'] = (df['close'] - sma_20) / sma_20

    # 将 inf（除以 0 等情况）替换为 NaN，统一由 dropna 处理
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    return df.dropna()


def build_features(
    df: pd.DataFrame,
    extra_features: Optional[Dict[str, Callable[[pd.DataFrame], pd.Series]]] = None,
) -> pd.DataFrame:
    """构建 ML 特征

    输入: 包含 ['open', 'high', 'low', 'close', 'volume', 'code'] 的 DataFrame
    输出: 带有技术特征的 DataFrame（已 dropna）

    每只股票独立计算，确保跨股票滚动窗口不互相干扰。

    Args:
        df: 原始 OHLCV 数据，必须包含 code 列用于分组
        extra_features: 可选的自定义特征函数字典，key 为列名，value 为函数
                       函数接受单只股票的 DataFrame，返回 Series

    Returns:
        特征 DataFrame，包含基础 5 个特征列 + 自定义特征列
    """
    if df.empty:
        return df

    required_cols = {'open', 'high', 'low', 'close', 'volume'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要列: {missing}")

    # 按股票代码分组，独立计算特征（避免不同股票之间滚动窗口污染）
    if 'code' in df.columns:
        result = df.groupby('code', group_keys=False).apply(_build_single_stock_features)
    else:
        result = _build_single_stock_features(df)

    if result.empty:
        return result

    # 添加自定义特征
    if extra_features:
        if 'code' in df.columns:
            # 按 code 分组后应用自定义特征函数
            for name, func in extra_features.items():
                result[name] = df.groupby('code', group_keys=False).apply(
                    lambda g: func(g).reindex(g.index)
                )
                # 合并后 dropna 以处理自定义特征产生的 NaN
                result = result.dropna(subset=[name])
        else:
            for name, func in extra_features.items():
                result[name] = func(df)
                result = result.dropna(subset=[name])

    return result
