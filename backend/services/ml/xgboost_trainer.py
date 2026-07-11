"""XGBoost 训练器

GPU 加速的 XGBoost 二分类模型训练流水线：
1. 从数据库加载全量 StockDaily 数据
2. 排除涨跌停日
3. 按股票分组构建特征和标签
4. 时序切分训练/测试集
5. 训练并评估模型
6. 保存模型和元信息
"""

import json
import os
from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report

from backend.utils.db import get_db
from backend.models.stock import StockDaily
from backend.services.ml.feature_engine import build_features
from backend.services.ml.label_generator import generate_labels

# 默认特征列
DEFAULT_FEATURE_COLS = [
    'ret_1d', 'ret_5d', 'volatility_10d', 'vol_change_1d', 'bias_20d',
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


def _filter_limit_up_down(df: pd.DataFrame) -> pd.DataFrame:
    """排除涨跌停日数据（涨跌幅 >= 9.9% 或 <= -9.9%）"""
    if 'change_percent' not in df.columns:
        return df
    mask = ~(
        (df['change_percent'] >= 9.9) |
        (df['change_percent'] <= -9.9)
    )
    return df[mask].copy()


def _build_feature_label_dataframe(
    df: pd.DataFrame, lookahead: int
) -> Tuple[pd.DataFrame, list]:
    """按 code 分组构建特征和标签，返回合并后的全量特征表

    Returns:
        (全量特征 DataFrame, 缺失必要列的列名列表)
    """
    required_cols = ['open', 'high', 'low', 'close', 'volume', 'code']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"数据缺少必要列: {missing}")

    results = []
    for code, group in df.groupby('code'):
        try:
            # 特征工程
            feats = build_features(group)
            if feats.empty:
                continue
            # 标签生成
            labeled = generate_labels(feats, lookahead=lookahead)
            if labeled.empty:
                continue
            results.append(labeled)
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

    # 2. 排除涨跌停
    df = _filter_limit_up_down(df)
    print(f"   排除涨跌停后: {len(df)} 行")

    # 3. 按 code 分组构建特征和标签
    print(f"\n🔧 构建特征（lookahead={lookahead}）...")
    full, feature_cols = _build_feature_label_dataframe(df, lookahead)

    if full.empty:
        return {'error': '特征构建后无有效数据，请检查数据量和窗口参数'}

    print(f"   有效样本: {len(full)} 行, 特征数: {len(feature_cols)}")
    label_ratio = full['label'].mean()
    print(f"   标签分布: 上涨={label_ratio:.1%}, 下跌={1-label_ratio:.1%}")

    # 4. 时序切分（前 80% 训练，后 20% 测试）
    X = full[feature_cols]
    y = full['label']

    split_idx = int(len(full) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # 保险：移除 inf 值（特征工程已处理，此处二次确认）
    X_train = X_train.replace([np.inf, -np.inf], np.nan).dropna()
    y_train = y_train.loc[X_train.index]
    X_test = X_test.replace([np.inf, -np.inf], np.nan).dropna()
    y_test = y_test.loc[X_test.index]

    train_dates = (full['date'].iloc[0], full['date'].iloc[split_idx - 1])
    test_dates = (full['date'].iloc[split_idx], full['date'].iloc[-1])

    print(f"\n📅 数据集划分:")
    print(f"   训练集: {len(X_train)} 行 ({train_dates[0]} ~ {train_dates[1]})")
    print(f"   测试集: {len(X_test)} 行 ({test_dates[0]} ~ {test_dates[1]})")

    # 5. GPU 检测和模型初始化
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

    # 6. 训练模型
    print("\n🧠 模型训练中...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=100,
    )

    # 7. 评估
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print("\n📊 测试集评估报告:")
    print(classification_report(y_test, preds))

    # 特征重要性
    importances = pd.Series(model.feature_importances_, index=feature_cols)
    print("\n🔍 特征重要性排名:")
    print(importances.sort_values(ascending=False))

    # 8. 保存模型
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
        'label_positive_ratio': round(float(label_ratio), 4),
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
        'label_positive_ratio': round(float(label_ratio), 4),
        'gpu_used': gpu_available,
        'model_path': MODEL_PATH,
        'meta_path': META_PATH,
        'feature_importances': {
            name: round(float(val), 4)
            for name, val in importances.sort_values(ascending=False).items()
        },
    }
