"""XGBoost 训练器

GPU 加速的 XGBoost 二分类模型训练流水线：
1. 从数据库加载全量 StockDaily 数据
2. 按股票分组构建特征并计算未来收益率（在完整时间序列上计算，避免 shift/rolling 错位）
3. 排除涨跌停日样本（在特征和收益率计算完成后进行）
4. 截面去中心化分配标签（按日期和当日全市场中位数比，剥离大盘 Beta，学选股 Alpha）
5. 时序切分训练/测试集
6. 训练并评估模型
7. 保存模型和元信息
"""

import json
import os
from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score, precision_score

from backend.utils.db import get_db
from backend.models.stock import StockDaily
from backend.services.ml.feature_engine import build_features
from backend.services.ml.label_generator import assign_labels, compute_future_returns

# 默认特征列
DEFAULT_FEATURE_COLS = [
    'ret_1d', 'ret_5d', 'volatility_10d', 'vol_change_1d', 'bias_20d',
    'amplitude', 'close_shadow',
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
    """从数据库加载全量 StockDaily 数据"""
    db = next(get_db())
    rows = (
        db.query(StockDaily)
        .order_by(StockDaily.date.asc())
        .all()
    )
    db.close()

    if not rows:
        return pd.DataFrame()

    records = []
    for r in rows:
        records.append({
            'code': r.code,
            'date': r.date,
            'open': r.open,
            'high': r.high,
            'low': r.low,
            'close': r.close,
            'volume': r.volume,
            'change_percent': r.change_percent,
        })

    df = pd.DataFrame(records)
    return df


def _get_limit_pct(code: str) -> float:
    """根据股票代码前缀返回涨跌停比例阈值（留 0.1% 容差）

    Args:
        code: 股票代码，如 '600519'、'300750'、'688981'

    Returns:
        涨跌停比例阈值
    """
    if not isinstance(code, str) or len(code) < 2:
        return 9.9
    if code.startswith(('30', '68')):
        return 19.9  # 创业板、科创板 20%
    if code.startswith(('8', '4')):
        return 29.9  # 北交所 30%
    return 9.9  # 主板 10%


def _filter_limit_up_down(df: pd.DataFrame) -> pd.DataFrame:
    """排除涨跌停日数据（按板块使用不同涨跌停阈值）"""
    if 'change_percent' not in df.columns or 'code' not in df.columns:
        return df
    limit_pct = df['code'].map(_get_limit_pct)
    mask = ~(
        (df['change_percent'] >= limit_pct) |
        (df['change_percent'] <= -limit_pct)
    )
    return df[mask].copy()


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
            # 清洗停牌日（volume == 0），避免昨收盘填充的虚假数据污染 shift/rolling
            group = group[group['volume'] > 0]
            if group.empty:
                continue
            # 特征工程
            feats = build_features(group)
            if feats.empty:
                continue
            # 计算未来收益率（per-stock，剔除 T+1 一字板，不分配 label）
            with_returns = compute_future_returns(feats, lookahead=lookahead)
            if with_returns.empty:
                continue
            results.append(with_returns)
        except Exception:
            continue

    if not results:
        return pd.DataFrame(), []

    full = pd.concat(results, ignore_index=True)
    full = full.sort_values('date').reset_index(drop=True)

    # 确定实际可用的特征列
    available_features = [c for c in DEFAULT_FEATURE_COLS if c in full.columns]
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

    # 4. 截面去中心化分配标签：和当天全市场中位数比，剥离大盘 Beta，学选股 Alpha
    label_method = 'cross_sectional_median'
    full = assign_labels(full, method=label_method)
    label_ratio = full['label'].mean()
    print(f"   标签分配 (method={label_method}): 跑赢中位数={label_ratio:.1%}, 跑输={1-label_ratio:.1%}")

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

    train_dates = (full.loc[train_mask, 'date'].min(), full.loc[train_mask, 'date'].max())
    test_dates = (full.loc[test_mask, 'date'].min(), full.loc[test_mask, 'date'].max())

    print(f"\n📅 数据集划分 (lookahead={lookahead}, 隔离期={lookahead} 个交易日):")
    print(f"   训练集: {len(X_train)} 行 ({train_dates[0]} ~ {train_dates[1]})")
    print(f"   测试集: {len(X_test)} 行 ({test_dates[0]} ~ {test_dates[1]})")

    # 6. GPU 检测和模型初始化
    gpu_available = _detect_gpu()
    if gpu_available:
        print("\n🚀 初始化 XGBoost 模型（启用 GPU 加速）...")
        device = 'cuda'
    else:
        print("\n⚠️  GPU 不可用，降级到 CPU 训练...")
        device = 'cpu'

    try:
        import xgboost as xgb
    except ImportError:
        print("❌ xgboost 未安装，请运行: pip install xgboost")
        return {'error': 'xgboost 未安装'}

    model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.05,
        tree_method='hist',
        device=device,
        objective='binary:logistic',
        eval_metric='auc',
        random_state=42,
    )

    # 7. 训练模型
    print("\n🧠 模型训练中...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=100,
    )

    # 8. 评估
    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, preds)
    auc = roc_auc_score(y_test, proba)
    precision = precision_score(y_test, preds, zero_division=0)

    # Top-K Precision：按日期分组，每日取概率最高的 K 只股票，看实际上涨比例
    test_dates_series = full.loc[X_test.index, 'date']
    proba_df = pd.DataFrame({
        'date': test_dates_series.values,
        'proba': proba,
        'label': y_test.values,
    })

    topk_results = {}
    for k in [5, 10, 20]:
        daily_precisions = []
        for day, group in proba_df.groupby('date'):
            if len(group) < k:
                continue
            top_k = group.nlargest(k, 'proba')
            daily_precisions.append(top_k['label'].mean())
        topk_results[f'top_{k}_precision'] = round(
            float(np.mean(daily_precisions)), 4
        ) if daily_precisions else 0.0

    print("\n📊 测试集评估报告:")
    print(classification_report(y_test, preds))
    print(f"   AUC: {auc:.4f}")
    print(f"   Precision: {precision:.4f}")
    print(f"   Top-5 Precision:  {topk_results['top_5_precision']:.4f}")
    print(f"   Top-10 Precision: {topk_results['top_10_precision']:.4f}")
    print(f"   Top-20 Precision: {topk_results['top_20_precision']:.4f}")

    # 特征重要性
    importances = pd.Series(model.feature_importances_, index=feature_cols)
    print("\n🔍 特征重要性排名:")
    print(importances.sort_values(ascending=False))

    # 9. 保存模型
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_model(MODEL_PATH)

    # 训练元信息
    meta = {
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
        'train_accuracy': round(acc, 4),
        'auc': round(float(auc), 4),
        'precision': round(float(precision), 4),
        'top_5_precision': topk_results['top_5_precision'],
        'top_10_precision': topk_results['top_10_precision'],
        'top_20_precision': topk_results['top_20_precision'],
        'label_positive_ratio': round(float(label_ratio), 4),
        'label_method': label_method,
        'trained_at': datetime.now().isoformat(),
        'gpu_used': gpu_available,
        'n_estimators': 500,
        'max_depth': 5,
        'learning_rate': 0.05,
    }

    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n💾 模型已保存: {MODEL_PATH}")
    print(f"   元信息已保存: {META_PATH}")

    return {
        'success': True,
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'feature_cols': feature_cols,
        'train_accuracy': round(acc, 4),
        'auc': round(float(auc), 4),
        'precision': round(float(precision), 4),
        'top_5_precision': topk_results['top_5_precision'],
        'top_10_precision': topk_results['top_10_precision'],
        'top_20_precision': topk_results['top_20_precision'],
        'label_positive_ratio': round(float(label_ratio), 4),
        'label_method': label_method,
        'gpu_used': gpu_available,
        'model_path': MODEL_PATH,
        'meta_path': META_PATH,
        'feature_importances': {
            name: round(float(val), 4)
            for name, val in importances.sort_values(ascending=False).items()
        },
    }
