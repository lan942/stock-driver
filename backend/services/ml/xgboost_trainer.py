"""XGBoost 训练器

GPU 加速的 XGBoost 排序学习（Learning to Rank）训练流水线：
1. 从数据库加载全量 StockDaily 数据
2. 按股票分组构建特征并计算未来收益率（在完整时间序列上计算，避免 shift/rolling 错位）
3. 排除涨跌停日样本（在特征和收益率计算完成后进行）
4. 截面去中心化分配标签（按日期和当日全市场中位数比，剥离大盘 Beta，学选股 Alpha）
5. 时序切分训练/测试集
6. 按交易日构造 group，用 rank:pairwise 目标训练 XGBRanker（与 Top-K 选股逻辑自洽）
7. 评估并保存模型和元信息
"""

import json
import os
from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.services.ml.feature_engine import build_features
from backend.services.ml.label_generator import assign_labels, compute_future_returns
from backend.services.strategy_config import StrategyConfigService

# 默认特征列
# 量价特征（per-stock，在 build_features 中计算）
DEFAULT_FEATURE_COLS = [
    'ret_1d', 'ret_5d',
    'volatility_5d', 'volatility_10d',
    'vol_change_1d',
    'turnover', 'turnover_change_1d',
    'bias_3d', 'bias_5d', 'bias_20d',
    'amplitude', 'close_shadow',
]

# 横截面相对特征（全市场合并后计算）
CROSS_SECTIONAL_FEATURES = [
    'ret_1d_rel',          # 相对收益率 = ret_1d - 当日全市场平均
    'volatility_5d_rel',   # 相对波动率
    'volatility_10d_rel',  # 相对波动率
    'vol_change_1d_rel',   # 相对成交量变化
    'turnover_rel',        # 相对成交额（除以当日中位数）
    'amplitude_rel',       # 相对日内振幅
    'close_shadow_rel',    # 相对收盘留影
]

# 模型和元信息存储路径
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
MODEL_PATH = os.path.join(MODEL_DIR, 'xgboost_model.json')
META_PATH = os.path.join(MODEL_DIR, 'xgboost_model_meta.json')


def _detect_gpu() -> bool:
    """检测 CUDA GPU 是否可用"""
    try:
        import xgboost as xgb
        # 尝试创建 CUDA 参数测试
        try:
            params = {'tree_method': 'hist', 'device': 'cuda'}
            dtrain = xgb.DMatrix(np.array([[1.0]]), label=np.array([0]))
            xgb.train(params, dtrain, num_boost_round=1)
            return True
        except Exception:
            return False
    except ImportError:
        return False


def _load_stock_daily_data() -> pd.DataFrame:
    """从数据库加载全量 StockDaily 数据（含股票名称用于 ST 识别）"""
    db = next(get_db())
    rows = (
        db.query(StockDaily, Stock.name)
        .outerjoin(Stock, StockDaily.code == Stock.code)
        .order_by(StockDaily.date.asc())
        .all()
    )
    db.close()

    if not rows:
        return pd.DataFrame()

    records = []
    for r in rows:
        daily, name = r
        records.append({
            'code': daily.code,
            'name': name or '',
            'date': daily.date,
            'open': daily.open,
            'high': daily.high,
            'low': daily.low,
            'close': daily.close,
            'volume': daily.volume,
            'change_percent': daily.change_percent,
        })

    df = pd.DataFrame(records)
    return df


def _get_limit_pct(code: str, name: str = '') -> float:
    """根据股票代码前缀和名称返回涨跌停比例阈值（留 0.1% 容差）

    Args:
        code: 股票代码，如 '600519'、'300750'、'688981'
        name: 股票名称，用于识别 ST/*ST 股票

    Returns:
        涨跌停比例阈值（百分比）
    """
    if not isinstance(code, str) or len(code) < 2:
        return 9.9

    name_upper = str(name).upper() if name else ''
    if 'ST' in name_upper:
        return 4.9  # ST/*ST 股票 5%

    if code.startswith(('30', '68')):
        return 19.9  # 创业板、科创板 20%
    if code.startswith(('8', '4')):
        return 29.9  # 北交所 30%
    return 9.9  # 主板 10%


def _filter_limit_up_down(df: pd.DataFrame) -> pd.DataFrame:
    """排除涨跌停日数据（按板块和是否 ST 使用不同涨跌停阈值）"""
    if 'change_percent' not in df.columns or 'code' not in df.columns:
        return df

    limit_pct = df['code'].map(_get_limit_pct)
    if 'name' in df.columns:
        st_mask = df['name'].str.upper().str.contains('ST', na=False)
        limit_pct = limit_pct.where(~st_mask, 4.9)

    mask = ~(
        (df['change_percent'] >= limit_pct) |
        (df['change_percent'] <= -limit_pct)
    )
    return df[mask].copy()


def _ndcg_at_k(labels_sorted_by_score: np.ndarray, k: int) -> float:
    """单日 NDCG@K

    Args:
        labels_sorted_by_score: 当日样本的 0/1 相关性标签数组，已按预测 score 降序排列
        k: Top-K 位置

    Returns:
        NDCG@K 值（0~1），当日无正样本时返回 0
    """
    if len(labels_sorted_by_score) == 0:
        return 0.0
    dcg_labels = labels_sorted_by_score[:k]
    dcg = (dcg_labels / np.log2(np.arange(2, len(dcg_labels) + 2))).sum()
    ideal = np.sort(labels_sorted_by_score)[::-1][:k]
    idcg = (ideal / np.log2(np.arange(2, len(ideal) + 2))).sum()
    return float(dcg / idcg) if idcg > 0 else 0.0


def _build_group_array(dates: pd.Series) -> np.ndarray:
    """按日期构造 XGBRanker 所需的 group 数组

    XGBRanker.fit() 的 group 参数要求：每个 group 的样本数，且 X/y 必须按 group 顺序连续排列。
    调用前必须确保 dates 已升序排列（同一日期样本连续）。

    Args:
        dates: 已排序的日期 Series（与 X 行顺序一致）

    Returns:
        group 数组，长度等于唯一日期数
    """
    return dates.groupby(dates.values, sort=False).size().values


def _validate_group_order(dates: pd.Series, group: np.ndarray, dataset_name: str) -> bool:
    """校验 Group 排序的正确性（XGBRanker 训练的关键前提）

    XGBRanker 使用 Pairwise Loss 时，要求：
    1. 数据必须按日期严格升序排列（同一日期样本连续）
    2. group 数组的顺序必须与日期出现顺序一致
    3. group 数组的累加和必须等于总样本数
    4. 不允许跨日期的偏序对（今天的样本不能穿插在昨天的样本中间）

    Args:
        dates: 日期 Series（与 X/y 行顺序一致）
        group: 构造的 group 数组
        dataset_name: 数据集名称（训练集/测试集）

    Returns:
        校验通过返回 True，失败返回 False（打印错误信息）
    """
    if dates.empty:
        print(f"❌ [{dataset_name}] 日期序列为空")
        return False

    if len(group) == 0:
        print(f"❌ [{dataset_name}] group 数组为空")
        return False

    total_samples = len(dates)
    group_sum = int(group.sum())
    if group_sum != total_samples:
        print(f"❌ [{dataset_name}] group 累加和不一致: group_sum={group_sum}, total_samples={total_samples}")
        return False

    unique_dates = dates.unique()
    if len(unique_dates) != len(group):
        print(f"❌ [{dataset_name}] 唯一日期数与 group 长度不匹配: unique_dates={len(unique_dates)}, group_len={len(group)}")
        return False

    is_sorted = dates.is_monotonic_increasing
    if not is_sorted:
        print(f"❌ [{dataset_name}] 日期序列未严格升序排列")
        return False

    group_idx = 0
    start_idx = 0
    date_boundaries = []
    for i, date in enumerate(dates):
        if i >= start_idx + group[group_idx]:
            date_boundaries.append((dates.iloc[start_idx], dates.iloc[i - 1]))
            group_idx += 1
            start_idx = i
            if group_idx >= len(group):
                break

    if group_idx < len(group):
        date_boundaries.append((dates.iloc[start_idx], dates.iloc[-1]))

    if len(date_boundaries) != len(group):
        print(f"❌ [{dataset_name}] 边界数与 group 长度不匹配: boundaries={len(date_boundaries)}, group_len={len(group)}")
        return False

    for i, (start_date, end_date) in enumerate(date_boundaries):
        if start_date != end_date:
            print(f"❌ [{dataset_name}] 第 {i} 个 group 存在日期跨越: {start_date} ~ {end_date}")
            return False

    dates_in_group_order = dates.iloc[np.cumsum(group) - 1].values
    unique_dates_sorted = np.sort(unique_dates)
    if not np.array_equal(dates_in_group_order, unique_dates_sorted):
        print(f"❌ [{dataset_name}] group 顺序与日期排序不一致")
        return False

    expected_group = dates.groupby(dates.values, sort=False).size().values
    if not np.array_equal(group, expected_group):
        print(f"❌ [{dataset_name}] group 数组与实际分组不符")
        return False

    print(f"✅ [{dataset_name}] Group 排序校验通过: {len(group)} 个交易日, {total_samples} 个样本")
    return True


def _add_cross_sectional_features(df: pd.DataFrame) -> pd.DataFrame:
    """添加横截面相对特征（全市场合并后计算）

    A 股是典型的资金博弈市，单纯的绝对特征不如相对特征有区分度。
    通过将个股特征除以当日全市场中位数，人为制造出"横截面相对强弱"特征。

    Args:
        df: 全市场特征 DataFrame（已按 date 排序）

    Returns:
        新增横截面相对特征列的 DataFrame
    """
    if df.empty or 'date' not in df.columns:
        return df

    result = df.copy()
    grouped = result.groupby('date')

    # 相对收益率 = 个股收益率 - 当日市场平均收益率
    if 'ret_1d' in result.columns:
        daily_mean_ret = grouped['ret_1d'].transform('mean')
        result['ret_1d_rel'] = result['ret_1d'] - daily_mean_ret

    # 相对波动率 = 个股波动率 / 当日市场中位数波动率
    for col in ['volatility_5d', 'volatility_10d']:
        if col in result.columns:
            daily_median = grouped[col].transform('median')
            result[f'{col}_rel'] = result[col] / daily_median.replace(0, np.nan)

    # 相对成交量变化
    if 'vol_change_1d' in result.columns:
        daily_mean = grouped['vol_change_1d'].transform('mean')
        result['vol_change_1d_rel'] = result['vol_change_1d'] - daily_mean

    # 相对成交额（除以当日中位数，无量纲化）
    if 'turnover' in result.columns:
        daily_median = grouped['turnover'].transform('median')
        result['turnover_rel'] = result['turnover'] / daily_median.replace(0, np.nan)

    # 相对日内振幅
    if 'amplitude' in result.columns:
        daily_mean = grouped['amplitude'].transform('mean')
        result['amplitude_rel'] = result['amplitude'] - daily_mean

    # 相对收盘留影
    if 'close_shadow' in result.columns:
        daily_mean = grouped['close_shadow'].transform('mean')
        result['close_shadow_rel'] = result['close_shadow'] - daily_mean

    return result.dropna()


def _build_feature_label_dataframe(
    df: pd.DataFrame, lookahead: int
) -> Tuple[pd.DataFrame, list]:
    """按 code 分组构建特征并计算未来收益率，返回合并后的全量特征表

    注意：本函数不分配 label。label 需要在过滤涨跌停、确定可交易 universe 后，
    通过 assign_labels 截面分配（和当天全市场中位数比）。

    Returns:
        (全量特征 DataFrame [含 future_ret，无 label], 可用特征列名列表)
    """
    required_cols = ['open', 'high', 'low', 'close', 'volume', 'code']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"数据缺少必要列: {missing}")

    results = []
    for code, group in df.groupby('code'):
        try:
            group = group.copy()
            suspension_mask = group['volume'] == 0
            if suspension_mask.any():
                group.loc[suspension_mask, ['open', 'high', 'low', 'close', 'volume']] = np.nan

            feats = build_features(group)
            if feats.empty:
                continue

            stop_profit_pct = float(StrategyConfigService.get('stop_profit_pct') or 0.06)
            stop_loss_pct = float(StrategyConfigService.get('stop_loss_pct') or 0.03)
            dynamic_sell_enabled = (StrategyConfigService.get('dynamic_sell_enabled') or 'true').lower() == 'true'
            dynamic_sell_decline_days = int(StrategyConfigService.get('dynamic_sell_score_decline_days') or 2)
            with_returns = compute_future_returns(
                feats,
                lookahead=lookahead,
                stop_profit_pct=stop_profit_pct,
                stop_loss_pct=stop_loss_pct,
                dynamic_sell_enabled=dynamic_sell_enabled,
                dynamic_sell_decline_days=dynamic_sell_decline_days,
            )
            if with_returns.empty:
                continue
            results.append(with_returns)
        except Exception:
            continue

    if not results:
        return pd.DataFrame(), []

    full = pd.concat(results, ignore_index=True)
    full = full.sort_values('date').reset_index(drop=True)

    # 添加横截面相对特征（全市场合并后计算）
    full = _add_cross_sectional_features(full)

    # 确定实际可用的特征列
    available_features = [c for c in DEFAULT_FEATURE_COLS if c in full.columns]
    available_features.extend([c for c in CROSS_SECTIONAL_FEATURES if c in full.columns])
    return full, available_features


def train_model(lookahead: int = 5) -> dict:
    """执行完整的模型训练流水线

    Args:
        lookahead: 预测窗口，未来 N 个交易日

    Returns:
        包含训练结果和评估指标的字典
    """
    # 1. 加载全量数据
    print("📊 加载 StockDaily 数据...")
    df = _load_stock_daily_data()
    if df.empty:
        return {'error': '数据库中没有 StockDaily 数据'}

    print(f"   原始数据: {len(df)} 行, {df['code'].nunique()} 只股票")
    print(f"   日期范围: {df['date'].min()} ~ {df['date'].max()}")

    # 2. 按 code 分组构建特征并计算未来收益率（在完整时间序列上计算，避免 shift/rolling 错位）
    print(f"\n🔧 构建特征（lookahead={lookahead}）...")
    full, feature_cols = _build_feature_label_dataframe(df, lookahead)

    if full.empty:
        return {'error': '特征构建后无有效数据，请检查数据量和窗口参数'}

    print(f"   特征构建完成: {len(full)} 行, 特征数: {len(feature_cols)}")

    # 3. 排除涨跌停日样本（在特征和收益率计算完成后进行，避免时间序列错位）
    before_filter = len(full)
    full = _filter_limit_up_down(full)
    print(f"   排除涨跌停后: {len(full)} 行 (剔除 {before_filter - len(full)} 行)")

    if full.empty:
        return {'error': '排除涨跌停后无有效数据'}

    # 4. 截面去中心化分配多档标签：将截面 future_ret 分成 5 档，让 XGBRanker 学习精细排序
    label_method = 'cross_sectional_qcut'
    full = assign_labels(full, method=label_method, qcut_bins=5)
    label_dist = full['label'].value_counts().sort_index()
    print(f"   标签分配 (method={label_method}, bins=5):")
    for bin_val, count in label_dist.items():
        pct = count / len(full) * 100
        print(f"     档{bin_val}: {count} 行 ({pct:.1f}%)")

    # 5. 时序切分（前 80% 训练，后 20% 测试）
    #    训练集和测试集之间必须留出 lookahead 天的空白隔离期：
    #    训练集最后 lookahead 天的标签通过 shift(-lookahead) 用到了未来数据，
    #    这些未来数据会落入测试集范围，构成数据泄漏。
    split_idx = int(len(full) * 0.8)
    split_date = full['date'].iloc[split_idx]

    unique_dates = sorted(full['date'].unique())
    split_date_pos = unique_dates.index(split_date)

    # 训练集和测试集之间留出 lookahead 天隔离期，防止标签穿越
    # 统一按日期切分，保证同一天的所有股票在同一个集合里
    if split_date_pos > lookahead:
        gap_start_date = unique_dates[split_date_pos - lookahead]
    else:
        gap_start_date = split_date  # 退化：交易日不足，不留隔离期

    train_mask = full['date'] < gap_start_date
    test_mask = full['date'] >= split_date

    X_train = full.loc[train_mask, feature_cols]
    y_train = full.loc[train_mask, 'label']
    X_test = full.loc[test_mask, feature_cols]
    y_test = full.loc[test_mask, 'label']

    # 保险：移除 inf 值（特征工程已处理，此处二次确认）
    X_train = X_train.replace([np.inf, -np.inf], np.nan).dropna()
    y_train = y_train.loc[X_train.index]
    X_test = X_test.replace([np.inf, -np.inf], np.nan).dropna()
    y_test = y_test.loc[X_test.index]

    # XGBRanker 要求 X/y 按 group 连续排列：按 date 升序排序，构造每个交易日的 group 数组
    # 使用 sort_values 确保严格的日期升序排列（argsort 可能在日期相同时产生不稳定结果）
    train_full = pd.DataFrame({
        'date': full.loc[X_train.index, 'date'].values,
        'label': y_train.values,
    })
    train_full[feature_cols] = X_train.values
    train_full = train_full.sort_values('date').reset_index(drop=True)
    X_train = train_full[feature_cols]
    y_train = train_full['label']
    train_dates_series = train_full['date']
    train_groups = _build_group_array(train_dates_series)

    test_full = pd.DataFrame({
        'date': full.loc[X_test.index, 'date'].values,
        'label': y_test.values,
    })
    test_full[feature_cols] = X_test.values
    test_full = test_full.sort_values('date').reset_index(drop=True)
    X_test = test_full[feature_cols]
    y_test = test_full['label']
    test_dates_series = test_full['date']
    test_groups = _build_group_array(test_dates_series)

    train_dates = (train_dates_series.min(), train_dates_series.max())
    test_dates = (test_dates_series.min(), test_dates_series.max())

    print(f"\n📅 数据集划分 (lookahead={lookahead}, 隔离期={lookahead} 个交易日):")
    print(f"   训练集: {len(X_train)} 行 ({train_dates[0]} ~ {train_dates[1]}), {len(train_groups)} 个交易日")
    print(f"   测试集: {len(X_test)} 行 ({test_dates[0]} ~ {test_dates[1]}), {len(test_groups)} 个交易日")

    # 关键校验：确保 Group 排序正确（XGBRanker 训练的核心前提）
    print("\n🔍 Group 排序校验...")
    train_valid = _validate_group_order(train_dates_series, train_groups, '训练集')
    test_valid = _validate_group_order(test_dates_series, test_groups, '测试集')

    if not train_valid or not test_valid:
        return {'error': 'Group 排序校验失败，请检查数据排序逻辑'}

    print(f"   训练集: {len(train_groups)} 个 group, 累计 {train_groups.sum()} 个样本")
    print(f"   测试集: {len(test_groups)} 个 group, 累计 {test_groups.sum()} 个样本")

    # 6. GPU 检测和模型初始化
    gpu_available = _detect_gpu()
    if gpu_available:
        print("\n🚀 初始化 XGBRanker（启用 GPU 加速，objective=rank:pairwise）...")
        device = 'cuda'
    else:
        print("\n⚠️  GPU 不可用，降级到 CPU 训练...")
        device = 'cpu'

    try:
        import xgboost as xgb
    except ImportError:
        print("❌ xgboost 未安装，请运行: pip install xgboost")
        return {'error': 'xgboost 未安装'}

    model = xgb.XGBRanker(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        tree_method='hist',
        device=device,
        objective='rank:pairwise',
        eval_metric=['ndcg', 'auc'],
        random_state=42,
    )

    # 7. 训练模型（按交易日 group 训练，让模型学日内相对排序）
    print("\n🧠 模型训练中...")
    model.fit(
        X_train, y_train,
        group=train_groups,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        eval_group=[train_groups, test_groups],
        verbose=100,
    )

    # 8. 评估：ranker 的 predict 返回 raw score，用于排序（非概率）
    scores = model.predict(X_test)

    # 多分类 AUC：使用 OVR 方式
    try:
        auc = roc_auc_score(y_test, scores, multi_class='ovr')
    except ValueError:
        auc = None

    # Top-K Precision：按日期分组，每日取 score 最高的 K 只股票
    # 多档标签下，看 top K 中高档次（>= 中位数档）的比例
    score_df = pd.DataFrame({
        'date': test_dates_series.values,
        'score': scores,
        'label': y_test.values,
    })

    topk_results = {}
    ndcg_results = {}
    for k in [5, 10, 20]:
        daily_precisions = []
        daily_ndcgs = []
        for day, group in score_df.groupby('date'):
            if len(group) < k:
                continue
            top_k = group.nlargest(k, 'score')
            # 多档标签下，看 top K 中高档次（>= 中位数档）的比例
            high_quality_ratio = (top_k['label'] >= 3).mean()
            daily_precisions.append(high_quality_ratio)
            sorted_labels = group.sort_values('score', ascending=False)['label'].values
            daily_ndcgs.append(_ndcg_at_k(sorted_labels, k))
        topk_results[f'top_{k}_precision'] = round(
            float(np.mean(daily_precisions)), 4
        ) if daily_precisions else 0.0
        ndcg_results[f'ndcg_{k}'] = round(
            float(np.mean(daily_ndcgs)), 4
        ) if daily_ndcgs else 0.0

    print("\n📊 测试集评估报告 (Ranking):")
    print(f"   AUC:              {auc:.4f}" if auc is not None else "   AUC:              N/A")
    print(f"   Top-5 Precision:  {topk_results['top_5_precision']:.4f}")
    print(f"   Top-10 Precision: {topk_results['top_10_precision']:.4f}")
    print(f"   Top-20 Precision: {topk_results['top_20_precision']:.4f}")
    print(f"   NDCG@5:           {ndcg_results['ndcg_5']:.4f}")
    print(f"   NDCG@10:          {ndcg_results['ndcg_10']:.4f}")
    print(f"   NDCG@20:          {ndcg_results['ndcg_20']:.4f}")

    # 特征重要性
    importances = pd.Series(model.feature_importances_, index=feature_cols)
    print("\n🔍 特征重要性排名:")
    print(importances.sort_values(ascending=False))

    # 9. 保存模型
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_model(MODEL_PATH)

    # 训练元信息
    meta = {
        'model_type': 'ranker',
        'objective': 'rank:pairwise',
        'feature_cols': feature_cols,
        'lookahead': lookahead,
        'train_date_range': [
            str(train_dates[0]),
            str(train_dates[1]),
        ],
        'test_date_range': [
            str(test_dates[0]),
            str(test_dates[1]),
        ],
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'train_groups': int(len(train_groups)),
        'test_groups': int(len(test_groups)),
        'auc': round(float(auc), 4) if auc is not None else None,
        'top_5_precision': topk_results['top_5_precision'],
        'top_10_precision': topk_results['top_10_precision'],
        'top_20_precision': topk_results['top_20_precision'],
        'ndcg_5': ndcg_results['ndcg_5'],
        'ndcg_10': ndcg_results['ndcg_10'],
        'ndcg_20': ndcg_results['ndcg_20'],
        'label_positive_ratio': None,
        'label_distribution': {str(k): int(v) for k, v in label_dist.items()},
        'label_method': label_method,
        'trained_at': datetime.now().isoformat(),
        'gpu_used': gpu_available,
        'n_estimators': 200,
        'max_depth': 5,
        'learning_rate': 0.05,
    }

    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n💾 模型已保存: {MODEL_PATH}")
    print(f"   元信息已保存: {META_PATH}")

    return {
        'success': True,
        'model_type': 'ranker',
        'objective': 'rank:pairwise',
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'feature_cols': feature_cols,
        'auc': round(float(auc), 4) if auc is not None else None,
        'top_5_precision': topk_results['top_5_precision'],
        'top_10_precision': topk_results['top_10_precision'],
        'top_20_precision': topk_results['top_20_precision'],
        'ndcg_5': ndcg_results['ndcg_5'],
        'ndcg_10': ndcg_results['ndcg_10'],
        'ndcg_20': ndcg_results['ndcg_20'],
        'label_positive_ratio': None,
        'label_distribution': {str(k): int(v) for k, v in label_dist.items()},
        'label_method': label_method,
        'gpu_used': gpu_available,
        'model_path': MODEL_PATH,
        'meta_path': META_PATH,
        'feature_importances': {
            name: round(float(val), 4)
            for name, val in importances.sort_values(ascending=False).items()
        },
    }
