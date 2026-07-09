"""均值回归策略

核心逻辑：寻找股价偏离均值后有望回归的机会
- 布林带下轨附近买入
- RSI超卖区域
- 超跌后企稳信号
"""

from typing import Optional, Dict, Any

from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.services.strategy_config import StrategyConfigService
from .base_strategy import IStrategy


class MeanReversionStrategy(IStrategy):
    """均值回归策略"""

    STRATEGY_NAME: str = "mean_reversion"
    STRATEGY_DESCRIPTION: str = "均值回归策略：寻找超跌反弹机会"

    DEFAULT_WEIGHTS = {
        'bollinger': 0.35,
        'rsi': 0.25,
        'oversold': 0.25,
        'stabilization': 0.15,
    }

    def _get_stock_daily_data(self, code: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """获取单只股票最近 N 日数据"""
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
        highs = [r.high for r in records if r.high]
        lows = [r.low for r in records if r.low]

        return {
            'code': code,
            'records': records,
            'closes': closes,
            'volumes': volumes,
            'change_pcts': change_pcts,
            'highs': highs,
            'lows': lows,
            'latest': records[-1] if records else None,
        }

    def _is_limit_up_down(self, latest: StockDaily) -> bool:
        """判断是否涨跌停"""
        if latest.change_percent is None:
            return False
        return abs(latest.change_percent) >= 9.9

    def _factor_bollinger(self, data: Dict[str, Any]) -> float:
        """布林带因子：股价距离下轨的距离，越接近下轨得分越高"""
        closes = data['closes']
        if len(closes) < 20:
            return 0.5

        ma20 = sum(closes[-20:]) / 20
        std = (sum((c - ma20) ** 2 for c in closes[-20:]) / 20) ** 0.5

        if std == 0:
            return 0.5

        lower_band = ma20 - 2 * std
        current_price = closes[-1]

        distance_to_lower = (lower_band - current_price) / ma20

        if distance_to_lower >= 0:
            score = 0.5 + min(distance_to_lower / 0.03, 0.5)
        elif distance_to_lower >= -0.02:
            score = 0.3 + (1 + distance_to_lower / 0.02) * 0.2
        else:
            score = max(0.1, 0.3 - (-distance_to_lower - 0.02) / 0.03 * 0.2)

        return max(0.0, min(1.0, score))

    def _factor_rsi(self, data: Dict[str, Any]) -> float:
        """RSI因子：RSI越低得分越高（超卖区域）"""
        closes = data['closes']
        if len(closes) < 14:
            return 0.5

        gains = 0
        losses = 0
        for i in range(-14, 0):
            diff = closes[i] - closes[i - 1]
            if diff > 0:
                gains += diff
            else:
                losses += abs(diff)

        if losses == 0:
            rsi = 100
        else:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))

        if rsi <= 20:
            score = 0.8 + (20 - rsi) / 20 * 0.2
        elif rsi <= 30:
            score = 0.5 + (30 - rsi) / 10 * 0.3
        elif rsi <= 50:
            score = 0.3 + (50 - rsi) / 20 * 0.2
        elif rsi <= 70:
            score = 0.1 + (70 - rsi) / 20 * 0.2
        else:
            score = 0.1

        return max(0.0, min(1.0, score))

    def _factor_oversold(self, data: Dict[str, Any]) -> float:
        """超跌因子：近5日累计跌幅，跌幅越大得分越高（但需控制风险）"""
        closes = data['closes']
        if len(closes) < 6:
            return 0.5

        return_5d = (closes[-1] - closes[-6]) / closes[-6]

        if return_5d <= -0.15:
            score = 0.2
        elif return_5d <= -0.10:
            score = 0.4 + (-0.10 - return_5d) / 0.05 * 0.3
        elif return_5d <= -0.05:
            score = 0.5 + (-0.05 - return_5d) / 0.05 * 0.3
        elif return_5d <= 0:
            score = 0.7 + (-return_5d) / 0.05 * 0.2
        elif return_5d <= 0.05:
            score = 0.5 - return_5d / 0.05 * 0.3
        else:
            score = 0.2

        return max(0.0, min(1.0, score))

    def _factor_stabilization(self, data: Dict[str, Any]) -> float:
        """企稳因子：近2日是否有企稳迹象（缩量或小幅反弹）"""
        closes = data['closes']
        volumes = data['volumes']
        if len(closes) < 3:
            return 0.5

        recent_change = closes[-1] - closes[-2]
        prev_change = closes[-2] - closes[-3]

        if len(volumes) >= 3:
            vol_ratio = volumes[-1] / volumes[-2] if volumes[-2] > 0 else 1.0
        else:
            vol_ratio = 1.0

        if prev_change < 0 and recent_change >= 0 and vol_ratio <= 1.2:
            score = 0.9
        elif prev_change < 0 and recent_change >= -closes[-2] * 0.01 and vol_ratio <= 1.3:
            score = 0.7
        elif prev_change < 0 and recent_change >= -closes[-2] * 0.02:
            score = 0.5
        else:
            score = 0.2

        return max(0.0, min(1.0, score))

    def score_stock(self, code: str) -> Optional[Dict[str, Any]]:
        """对单只股票进行均值回归评分"""
        data = self._get_stock_daily_data(code, days=30)
        if data is None or data['latest'] is None:
            return None

        if self._is_limit_up_down(data['latest']):
            return None

        weights = self.DEFAULT_WEIGHTS

        factor_scores = {
            'bollinger': self._factor_bollinger(data),
            'rsi': self._factor_rsi(data),
            'oversold': self._factor_oversold(data),
            'stabilization': self._factor_stabilization(data),
        }

        total_score = sum(
            factor_scores[name] * weights.get(name, 0)
            for name in factor_scores
        )

        return {
            'code': code,
            'total_score': round(total_score, 4),
            'factor_scores': {k: round(v, 4) for k, v in factor_scores.items()},
            'latest_close': data['latest'].close,
            'latest_volume': data['latest'].volume,
            'latest_change_pct': data['latest'].change_percent,
        }

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

        stop_profit_pct = float(StrategyConfigService.get('stop_profit_pct') or 0.05)
        stop_loss_pct = float(StrategyConfigService.get('stop_loss_pct') or 0.03)
        position_ratio = float(StrategyConfigService.get('position_ratio') or 0.2)

        recommendations = []
        for s in scored:
            if len(recommendations) >= available_slots:
                break

            close = s['latest_close']
            if close is None or close <= 0:
                continue

            suggested_buy_price = round(close * 1.005, 2)
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
