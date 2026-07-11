"""XGBoost ML 策略

加载预训练的 XGBoost 模型，通过 predict_proba 获取上涨概率作为评分，
实现 IStrategy 接口，无缝集成到现有策略引擎和回测系统中。
"""

import json
import os
from typing import Any, Dict, Optional

import numpy as np

from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.services.strategies.base_strategy import IStrategy
from backend.services.ml.feature_engine import build_features
from backend.services.strategy_config import StrategyConfigService

# 模型文件路径
_MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
_MODEL_PATH = os.path.join(_MODEL_DIR, 'xgboost_model.json')
_META_PATH = os.path.join(_MODEL_DIR, 'xgboost_model_meta.json')


class XGBoostStrategy(IStrategy):
    """XGBoost 机器学习策略"""

    STRATEGY_NAME: str = "xgboost"
    STRATEGY_DESCRIPTION: str = "XGBoost ML策略：基于GPU训练的机器学习模型选股"

    # ML 策略不按因子评分，但接口要求 DEFAULT_WEIGHTS 存在
    DEFAULT_WEIGHTS: Dict[str, float] = {}

    def __init__(self):
        self._model = None
        self._feature_cols = []
        self._meta = {}
        self._load_model()

    def _load_model(self) -> None:
        """加载预训练模型和元信息"""
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                f"模型文件不存在: {_MODEL_PATH}\n"
                f"请先运行 'python manage.py train-xgboost' 训练模型"
            )

        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("xgboost 未安装，请运行: pip install xgboost")

        self._model = xgb.XGBClassifier()
        self._model.load_model(_MODEL_PATH)

        if os.path.exists(_META_PATH):
            with open(_META_PATH, 'r', encoding='utf-8') as f:
                self._meta = json.load(f)
            self._feature_cols = self._meta.get('feature_cols', [])

        if not self._feature_cols:
            # 如果元信息缺失，用默认特征列
            self._feature_cols = [
                'ret_1d', 'ret_5d', 'volatility_10d',
                'vol_change_1d', 'bias_20d',
            ]

    def _get_stock_daily_data(self, code: str, days: int = 60) -> Optional[Dict[str, Any]]:
        """获取单只股票最近 N 日 OHLCV 数据"""
        db = next(get_db())
        records = (
            db.query(StockDaily)
            .filter(StockDaily.code == code)
            .order_by(StockDaily.date.desc())
            .limit(days)
            .all()
        )
        db.close()

        if len(records) < days:
            return None

        records = list(reversed(records))
        closes = [r.close for r in records if r.close]
        volumes = [r.volume for r in records if r.volume]
        change_pcts = [r.change_percent for r in records if r.change_percent is not None]

        return {
            'code': code,
            'records': records,
            'closes': closes,
            'volumes': volumes,
            'change_pcts': change_pcts,
            'latest': records[-1] if records else None,
        }

    @staticmethod
    def _is_limit_up_down(latest: StockDaily) -> bool:
        """判断是否涨跌停"""
        if latest.change_percent is None:
            return False
        return abs(latest.change_percent) >= 9.9

    def _data_to_features(self, data: Dict[str, Any]) -> Optional[np.ndarray]:
        """将 OHLCV 数据字典转为特征向量"""
        records = data.get('records', [])
        if not records:
            return None

        df_data = []
        for r in records:
            df_data.append({
                'code': data['code'],
                'open': r.open,
                'high': r.high,
                'low': r.low,
                'close': r.close,
                'volume': r.volume,
            })

        import pandas as pd
        df = pd.DataFrame(df_data)

        try:
            feats = build_features(df)
        except Exception:
            return None

        if feats.empty:
            return None

        # 取最新一行的特征
        latest = feats.iloc[-1:][self._feature_cols]
        if latest.isna().any().any():
            return None

        return latest.values

    def score_stock(self, code: str) -> Optional[Dict[str, Any]]:
        """对单只股票进行 ML 评分（实盘/API 调用入口）"""
        data = self._get_stock_daily_data(code, days=60)
        return self._score_from_data(code, data)

    def score_from_data(self, code: str, data: dict) -> Optional[Dict[str, Any]]:
        """基于已拉取的历史数据评分（回测引擎调用入口）

        Args:
            code: 股票代码
            data: backtest 预拉取的数据字典，格式与 _get_stock_data_before_date 一致

        Returns:
            评分结果字典，或 None
        """
        if self._model is None:
            return None
        if data is None or data.get('latest') is None:
            return None

        features = self._data_to_features(data)
        if features is None:
            return None

        try:
            proba = self._model.predict_proba(features)
            score = float(proba[0, 1])
        except Exception:
            return None

        return {
            'code': code,
            'total_score': round(score, 4),
            'factor_scores': {'xgboost_prob': round(score, 4)},
            'latest_close': data['latest'].close,
            'latest_volume': data['latest'].volume,
            'latest_change_pct': data['latest'].change_percent,
        }

    def _score_from_data(self, code: str, data: Optional[dict]) -> Optional[Dict[str, Any]]:
        """内部评分方法：实盘和回测共用"""
        if self._model is None:
            return None
        if data is None or data.get('latest') is None:
            return None

        if self._is_limit_up_down(data['latest']):
            return None

        return self.score_from_data(code, data)

    def generate_recommendations(
        self,
        available_slots: int,
        available_cash: float,
    ) -> list:
        """生成买入推荐清单"""
        if available_slots <= 0:
            return []

        db = next(get_db())
        codes = [row[0] for row in db.query(Stock.code).all()]
        stock_names = {s.code: s.name for s in db.query(Stock.code, Stock.name).all()}
        db.close()

        scored = []
        for code in codes:
            result = self.score_stock(code)
            if result is not None:
                scored.append(result)

        scored.sort(key=lambda x: x['total_score'], reverse=True)

        stop_profit_pct = float(StrategyConfigService.get('stop_profit_pct') or 0.06)
        stop_loss_pct = float(StrategyConfigService.get('stop_loss_pct') or 0.03)
        position_ratio = float(StrategyConfigService.get('position_ratio') or 0.2)

        recommendations = []
        for s in scored:
            if len(recommendations) >= available_slots:
                break

            close = s['latest_close']
            if close is None or close <= 0:
                continue

            suggested_buy_price = round(close * 1.01, 2)
            target_price = round(suggested_buy_price * (1 + stop_profit_pct), 2)
            stop_price = round(suggested_buy_price * (1 - stop_loss_pct), 2)

            required_cash = suggested_buy_price * 100
            alloc_cash = available_cash * position_ratio
            if alloc_cash < required_cash:
                continue

            recommendations.append({
                'code': s['code'],
                'name': stock_names.get(s['code'], ''),
                'score': s['total_score'],
                'factor_scores': s['factor_scores'],
                'suggested_buy_price': suggested_buy_price,
                'target_price': target_price,
                'stop_price': stop_price,
                'current_close': close,
                'current_change_pct': s['latest_change_pct'],
            })

        return recommendations
