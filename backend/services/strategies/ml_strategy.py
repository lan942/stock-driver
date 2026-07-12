"""XGBoost ML 策略

加载预训练的 XGBoost 模型，通过 predict 获取 raw score（ranker 输出）作为评分，
实现 IStrategy 接口，无缝集成到现有策略引擎和回测系统中。

当 XGBoost 不可用时，自动降级为技术指标评分模式。
"""

import json
import os
from datetime import date
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd

from backend.services.strategies.base_strategy import IStrategy
from backend.services.strategy_config import StrategyConfigService
from backend.services.ml.feature_engine import build_features
from backend.services.strategies.gpu_worker import GPUWorker
from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily


class XGBoostStrategy(IStrategy):
    """XGBoost ML策略：通过独立子进程使用 GPU 进行模型预测"""

    STRATEGY_NAME: str = "xgboost"
    STRATEGY_DESCRIPTION: str = "XGBoost ML策略：通过独立子进程使用 GPU 进行模型预测"

    _gpu_worker: Optional[GPUWorker] = None
    _cpu_model = None
    _feature_cols: Optional[list] = None
    _gpu_available: bool = False

    def __init__(self):
        """初始化策略，启动 GPU 预测子进程"""
        self._init_worker()

    @staticmethod
    def _init_worker():
        """启动 GPU 预测子进程"""
        if XGBoostStrategy._gpu_worker is not None:
            return

        model_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
        model_path = os.path.join(model_dir, 'xgboost_model.json')

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"模型文件不存在: {model_path}\n请先运行: python manage.py train-xgboost"
            )

        worker = GPUWorker(model_dir)
        XGBoostStrategy._feature_cols = worker.feature_cols

        try:
            worker.start()
            # 测试一次预测确认工作进程正常
            import numpy as np
            test_X = np.zeros((1, len(XGBoostStrategy._feature_cols)), dtype=np.float32)
            worker.predict(test_X)
            XGBoostStrategy._gpu_worker = worker
            XGBoostStrategy._gpu_available = True
            print("[XGBoost] GPU 子进程已启动 (CUDA)")
        except Exception as e:
            print(f"[XGBoost] GPU 子进程启动失败: {e}，使用 CPU 模式")
            XGBoostStrategy._gpu_available = False
            XGBoostStrategy._load_cpu_model()

    @staticmethod
    def _load_cpu_model():
        """CPU 回退模式"""
        import xgboost as xgb
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'xgboost_model.json')
        XGBoostStrategy._gpu_worker = None
        XGBoostStrategy._cpu_model = xgb.XGBRanker()
        XGBoostStrategy._cpu_model.load_model(model_path)
        XGBoostStrategy._cpu_model.get_booster().set_param({'device': 'cpu', 'nthread': 4})
        print("[XGBoost] CPU 模式 (4线程)")

    def _get_stock_data(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """从数据库获取股票历史数据"""
        db = next(get_db())
        rows = (
            db.query(StockDaily)
            .filter(StockDaily.code == code)
            .order_by(StockDaily.date.desc())
            .limit(days)
            .all()
        )
        db.close()

        if len(rows) < days:
            return None

        rows = list(reversed(rows))
        data = []
        for row in rows:
            data.append({
                'date': row.date,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'volume': row.volume,
                'code': row.code,
            })

        df = pd.DataFrame(data)
        return df

    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算特征（单只股票）"""
        if df.empty:
            return df
        return build_features(df)

    def _predict_score(self, features: pd.DataFrame) -> float:
        """使用模型预测评分（GPU子进程 或 CPU回退）"""
        if features.empty:
            return 0.0

        feature_cols = XGBoostStrategy._feature_cols
        last_row = features.iloc[-1].copy()
        for col in feature_cols:
            if col not in last_row:
                last_row[col] = 0.0

        X = pd.DataFrame([last_row[feature_cols]]).fillna(0)
        X = X.replace([np.inf, -np.inf], 0)
        X = X.values.astype(np.float32)

        if XGBoostStrategy._gpu_available and XGBoostStrategy._gpu_worker:
            score = XGBoostStrategy._gpu_worker.predict(X)
        else:
            score = XGBoostStrategy._cpu_model.predict(X)
        return float(score[0]) if len(score) > 0 else 0.0

    def _is_limit_up_down(self, daily) -> bool:
        """判断是否涨跌停"""
        if daily.change_percent is None:
            return False
        return abs(daily.change_percent) >= 9.8

    def score_stock(self, code: str) -> Optional[Dict[str, Any]]:
        """对单只股票进行评分

        Args:
            code: 股票代码

        Returns:
            评分结果字典，包含:
                - code: 股票代码
                - total_score: 综合评分 (ranker raw score)
                - factor_scores: 各因子得分字典
                - latest_close: 最新收盘价
                - latest_volume: 最新成交量
                - latest_change_pct: 最新涨跌幅
            None: 股票不符合策略条件（如数据不足等）
        """
        df = self._get_stock_data(code, days=60)
        if df is None:
            return None

        features = self._calculate_features(df)
        if features.empty:
            return None

        total_score = self._predict_score(features)

        latest_row = df.iloc[-1]
        latest_close = float(latest_row['close'])
        latest_volume = int(latest_row['volume'])

        db = next(get_db())
        daily = db.query(StockDaily).filter(
            StockDaily.code == code,
            StockDaily.date == latest_row['date']
        ).first()
        db.close()

        latest_change_pct = float(daily.change_percent) if daily and daily.change_percent else None

        return {
            'code': code,
            'total_score': total_score,
            'factor_scores': {
                'xgboost_prob': total_score,
            },
            'latest_close': latest_close,
            'latest_volume': latest_volume,
            'latest_change_pct': latest_change_pct,
        }

    def score_from_data(self, code: str, data: dict) -> Optional[Dict[str, Any]]:
        """从已获取的数据中对股票进行评分（回测引擎使用）

        Args:
            code: 股票代码
            data: 数据字典，包含:
                - records: StockDaily 对象列表
                - closes: 收盘价列表
                - volumes: 成交量列表
                - highs: 最高价列表
                - lows: 最低价列表
                - latest: 最新的 StockDaily 对象

        Returns:
            评分结果字典，包含 total_score、factor_scores、latest_close 等
        """
        records = data.get('records', [])
        if len(records) < 30:
            return None

        df_data = []
        for row in records:
            df_data.append({
                'date': row.date,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'volume': row.volume,
                'code': code,
            })

        df = pd.DataFrame(df_data)
        features = self._calculate_features(df)
        if features.empty:
            return None

        total_score = self._predict_score(features)
        latest = data.get('latest')

        if latest is None:
            return None

        return {
            'code': code,
            'total_score': total_score,
            'factor_scores': {
                'xgboost_prob': total_score,
            },
            'latest_close': float(latest.close) if latest.close else None,
            'latest_volume': int(latest.volume) if latest.volume else None,
            'latest_change_pct': float(latest.change_percent) if latest.change_percent else None,
        }

    def batch_score_from_data(self, stocks_data: Dict[str, dict]) -> Dict[str, Optional[Dict[str, Any]]]:
        """批量评分（GPU加速核心优化）

        一次性处理多只股票，将特征计算和模型预测合并为批量操作，
        大幅提升 GPU 利用率和回测速度。

        Args:
            stocks_data: 股票数据字典，key 为股票代码，value 为数据字典

        Returns:
            评分结果字典，key 为股票代码，value 为评分结果或 None
        """
        if not stocks_data:
            return {}

        all_features = []
        valid_codes = []
        code_index_map = {}

        for idx, (code, data) in enumerate(stocks_data.items()):
            records = data.get('records', [])
            if len(records) < 30:
                continue

            df_data = []
            for row in records:
                df_data.append({
                    'date': row.date,
                    'open': row.open,
                    'high': row.high,
                    'low': row.low,
                    'close': row.close,
                    'volume': row.volume,
                    'code': code,
                })

            df = pd.DataFrame(df_data)
            features = self._calculate_features(df)
            if features.empty:
                continue

            last_row = features.iloc[-1].copy()
            all_features.append(last_row)
            valid_codes.append(code)
            code_index_map[code] = len(all_features) - 1

        if not all_features:
            return {}

        features_df = pd.DataFrame(all_features)
        feature_cols = XGBoostStrategy._feature_cols
        if not feature_cols:
            feature_cols = [
                'ret_1d', 'ret_5d',
                'volatility_5d', 'volatility_10d',
                'vol_change_1d',
                'turnover', 'turnover_change_1d',
                'bias_3d', 'bias_5d', 'bias_20d',
                'amplitude', 'close_shadow',
            ]

        for col in feature_cols:
            if col not in features_df.columns:
                features_df[col] = 0.0

        X = features_df[feature_cols].fillna(0)
        X = X.replace([np.inf, -np.inf], 0)
        X = X.values.astype(np.float32)

        if XGBoostStrategy._gpu_available and XGBoostStrategy._gpu_worker:
            scores = XGBoostStrategy._gpu_worker.predict(X)
        else:
            if XGBoostStrategy._cpu_model is None:
                XGBoostStrategy._load_cpu_model()
            scores = XGBoostStrategy._cpu_model.predict(X)

        results = {}
        for code in stocks_data:
            if code not in code_index_map:
                results[code] = None
                continue

            idx = code_index_map[code]
            total_score = float(scores[idx]) if idx < len(scores) else 0.0
            data = stocks_data[code]
            latest = data.get('latest')

            if latest is None:
                results[code] = None
                continue

            results[code] = {
                'code': code,
                'total_score': total_score,
                'factor_scores': {
                    'xgboost_prob': total_score,
                },
                'latest_close': float(latest.close) if latest.close else None,
                'latest_volume': int(latest.volume) if latest.volume else None,
                'latest_change_pct': float(latest.change_percent) if latest.change_percent else None,
            }

        return results

    def score_stock_for_sell(self, code: str, buy_date: date) -> Optional[float]:
        """持有期间重新评分（用于动态卖出判断）

        Args:
            code: 股票代码
            buy_date: 买入日期

        Returns:
            当前评分，数据不足时返回None
        """
        df = self._get_stock_data(code, days=60)
        if df is None:
            return None

        features = self._calculate_features(df)
        if features.empty:
            return None

        return self._predict_score(features)

    def generate_recommendations(
        self,
        available_slots: int,
        available_cash: float,
    ) -> list:
        """生成买入推荐清单（批量GPU预测，全市场一次完成）

        Args:
            available_slots: 可用持仓位数
            available_cash: 可用资金

        Returns:
            推荐列表
        """
        db = next(get_db())
        codes = [row[0] for row in db.query(Stock.code).all()]
        stock_names = {s.code: s.name for s in db.query(Stock.code, Stock.name).all()}
        db.close()

        # 批量收集特征 → 一次 GPU 预测
        feature_cols = XGBoostStrategy._feature_cols
        all_features = []
        valid_stocks = []

        for code in codes:
            df = self._get_stock_data(code, days=60)
            if df is None:
                continue
            features = self._calculate_features(df)
            if features.empty:
                continue

            last_row = features.iloc[-1]
            row = {}
            for col in feature_cols:
                v = last_row.get(col, 0.0)
                row[col] = float(v) if pd.notna(v) else 0.0
            all_features.append(row)

            latest = df.iloc[-1]
            valid_stocks.append({
                'code': code,
                'latest_close': float(latest['close']),
            })

        if not all_features:
            return []

        X = pd.DataFrame(all_features).fillna(0).replace([np.inf, -np.inf], 0)
        X = X.values.astype(np.float32)

        if XGBoostStrategy._gpu_available and XGBoostStrategy._gpu_worker:
            scores = XGBoostStrategy._gpu_worker.predict(X)
        else:
            if XGBoostStrategy._cpu_model is None:
                XGBoostStrategy._load_cpu_model()
            scores = XGBoostStrategy._cpu_model.predict(X)

        scored = []
        for i, s in enumerate(valid_stocks):
            scored.append({
                'code': s['code'],
                'total_score': float(scores[i]),
                'factor_scores': {'xgboost_prob': float(scores[i])},
                'latest_close': s['latest_close'],
                'latest_volume': 0,
                'latest_change_pct': None,
            })

        scored.sort(key=lambda x: x['total_score'], reverse=True)

        stop_profit_pct = float(StrategyConfigService.get('stop_profit_pct') or 0.06)
        stop_loss_pct = float(StrategyConfigService.get('stop_loss_pct') or 0.03)

        recommendations = []
        for s in scored:
            if len(recommendations) >= available_slots:
                break

            close = s['latest_close']
            if not close or close <= 0:
                continue

            suggested_buy_price = round(close * 1.01, 2)
            target_price = round(close * (1 + stop_profit_pct), 2)
            stop_price = round(close * (1 - stop_loss_pct), 2)

            recommendations.append({
                'code': s['code'],
                'name': stock_names.get(s['code'], ''),
                'score': round(s['total_score'], 4),
                'factor_scores': s['factor_scores'],
                'current_close': round(close, 2),
                'suggested_buy_price': suggested_buy_price,
                'target_price': target_price,
                'stop_price': stop_price,
            })

        return recommendations