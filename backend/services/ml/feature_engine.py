"""特征引擎

从原始 OHLCV 数据计算平稳化量化特征，用于机器学习模型输入。

核心特征：
- ret_1d / ret_5d: 对数收益率（消除价格量纲差异）
- volatility_5d / volatility_10d: 过去 N 日收益率标准差
- vol_change_1d: 成交量相对变化率
- turnover: 成交额 = close * volume（流动性代理指标）
- turnover_change_1d: 成交额变化率
- bias_3d / bias_5d / bias_20d: 收盘价偏离 N 日均线百分比
- amplitude: 日内振幅 (high - low) / prev_close
- close_shadow: 收盘留影 (close - open) / (high - low)
"""

from typing import Callable, Dict, Optional

import numpy as np
import pandas as pd


def build_features(
    df: pd.DataFrame,
    extra_features: Optional[Dict[str, Callable[[pd.DataFrame], pd.Series]]] = None,
) -> pd.DataFrame:
    """构建 ML 特征（向量化实现）

    输入: 包含 ['open', 'high', 'low', 'close', 'volume', 'code'] 的 DataFrame
    输出: 带有技术特征的 DataFrame（已 dropna）

    每只股票独立计算，确保跨股票滚动窗口不互相干扰。
    通过 groupby + shift/rolling 向量化操作替代 apply，性能提升 10 倍以上。

    Args:
        df: 原始 OHLCV 数据，可选包含 code 列用于分组
        extra_features: 可选的自定义特征函数字典，key 为列名，value 为函数
                       函数接受单只股票的 DataFrame，返回 Series

    Returns:
        特征 DataFrame，包含基础 7 个特征列 + 自定义特征列
    """
    if df.empty:
        return df

    required_cols = {'open', 'high', 'low', 'close', 'volume', 'date'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要列: {missing}")

    result = df.copy()
    has_code = 'code' in result.columns

    if has_code:
        # 按 code, date 排序，保证 shift/rolling 的正确性
        result = result.sort_values(['code', 'date']).reset_index(drop=True)
        grouped = result.groupby('code')

        # 基础收益率特征（对数收益率）
        result['ret_1d'] = np.log(result['close'] / grouped['close'].shift(1))
        result['ret_5d'] = np.log(result['close'] / grouped['close'].shift(5))

        # 波动率特征：groupby + rolling 返回 MultiIndex，droplevel 对齐回原索引
        result['volatility_5d'] = (
            grouped['ret_1d'].rolling(window=5).std().droplevel(0)
        )
        result['volatility_10d'] = (
            grouped['ret_1d'].rolling(window=10).std().droplevel(0)
        )

        # 量价特征
        result['vol_change_1d'] = result['volume'] / grouped['volume'].shift(1) - 1

        # 成交额特征（流动性代理指标）
        result['turnover'] = result['close'] * result['volume']
        result['turnover_change_1d'] = result['turnover'] / grouped['turnover'].shift(1) - 1

        # 均线偏离度（多时间窗口）
        sma_3 = grouped['close'].rolling(window=3).mean().droplevel(0)
        sma_5 = grouped['close'].rolling(window=5).mean().droplevel(0)
        sma_20 = grouped['close'].rolling(window=20).mean().droplevel(0)
        result['bias_3d'] = (result['close'] - sma_3) / sma_3
        result['bias_5d'] = (result['close'] - sma_5) / sma_5
        result['bias_20d'] = (result['close'] - sma_20) / sma_20

        # 日内特征
        prev_close = grouped['close'].shift(1)
        # 日内振幅：(high - low) / prev_close，反映当日价格波动剧烈程度
        result['amplitude'] = (result['high'] - result['low']) / prev_close
        # 收盘留影：(close - open) / (high - low)，反映多空力量对比
        # 值域 [-1, 1]：正值表示收阳，负值表示收阴；绝对值越大多空力量越一边倒
        day_range = result['high'] - result['low']
        result['close_shadow'] = (result['close'] - result['open']) / day_range.replace(0, np.nan)
    else:
        # 单只股票：直接 shift/rolling
        result['ret_1d'] = np.log(result['close'] / result['close'].shift(1))
        result['ret_5d'] = np.log(result['close'] / result['close'].shift(5))
        result['volatility_5d'] = result['ret_1d'].rolling(window=5).std()
        result['volatility_10d'] = result['ret_1d'].rolling(window=10).std()
        result['vol_change_1d'] = result['volume'] / result['volume'].shift(1) - 1

        # 成交额特征
        result['turnover'] = result['close'] * result['volume']
        result['turnover_change_1d'] = result['turnover'] / result['turnover'].shift(1) - 1

        # 均线偏离度（多时间窗口）
        sma_3 = result['close'].rolling(window=3).mean()
        sma_5 = result['close'].rolling(window=5).mean()
        sma_20 = result['close'].rolling(window=20).mean()
        result['bias_3d'] = (result['close'] - sma_3) / sma_3
        result['bias_5d'] = (result['close'] - sma_5) / sma_5
        result['bias_20d'] = (result['close'] - sma_20) / sma_20

        # 日内特征
        prev_close = result['close'].shift(1)
        result['amplitude'] = (result['high'] - result['low']) / prev_close
        day_range = result['high'] - result['low']
        result['close_shadow'] = (result['close'] - result['open']) / day_range.replace(0, np.nan)

    # 将 inf 替换为 NaN，统一由 dropna 处理
    result.replace([np.inf, -np.inf], np.nan, inplace=True)
    result = result.dropna()

    if result.empty:
        return result

    # 添加自定义特征
    if extra_features:
        if has_code:
            for name, func in extra_features.items():
                result[name] = (
                    result.groupby('code', group_keys=False)
                    .apply(lambda g: func(g).reindex(g.index))
                )
                result = result.dropna(subset=[name])
        else:
            for name, func in extra_features.items():
                result[name] = func(df)
                result = result.dropna(subset=[name])

    return result
