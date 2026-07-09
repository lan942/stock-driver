"""趋势跟随策略（原策略）

核心逻辑：追踪已经启动的上涨趋势
- MA5上穿MA20
- RSI处于适中偏强区域
- 放量上涨确认趋势
"""

from typing import Optional, Dict, Any

from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.services.strategy_config import StrategyConfigService
from .base_strategy import IStrategy


class TrendFollowingStrategy(IStrategy):
    """趋势跟随策略"""

    STRATEGY_NAME: str = "trend_following"
    STRATEGY_DESCRIPTION: str = "趋势跟随策略：追踪已经启动的上涨趋势"

    DEFAULT_WEIGHTS = {
        'trend': 0.30,
        'momentum': 0.25,
        'volume': 0.20,
        'reversal': 0.15,
        'volatility': 0.10,
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

    def _factor_trend(self, data: Dict[str, Any]) -> float:
        """趋势因子：MA5 与 MA20 乖离率"""
        closes = data['closes']
        if len(closes) < 20:
            return 0.5

        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        if ma20 == 0:
            return 0.5

        bias = (ma5 - ma20) / ma20

        score = (bias + 0.05) / 0.10
        return max(0.0, min(1.0, score))

    def _factor_momentum(self, data: Dict[str, Any]) -> float:
        """动量因子：基于 RSI 和近期涨跌幅"""
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

        if rsi > 80:
            score = 0.3
        elif rsi > 60:
            score = 0.5 + (rsi - 60) / 40
        elif rsi > 40:
            score = 0.3 + (rsi - 40) / 100
        elif rsi > 20:
            score = 0.1 + (rsi - 20) / 200
        else:
            score = 0.1

        return max(0.0, min(1.0, score))

    def _factor_volume(self, data: Dict[str, Any]) -> float:
        """成交量因子：当日量 / 20日均量"""
        volumes = data['volumes']
        if len(volumes) < 21:
            return 0.5

        latest_vol = volumes[-1]
        avg_vol_20 = sum(volumes[-21:-1]) / 20

        if avg_vol_20 == 0:
            return 0.5

        ratio = latest_vol / avg_vol_20

        if 1.0 <= ratio <= 1.5:
            score = 0.5 + (ratio - 1.0)
        elif ratio > 1.5:
            score = 1.0 - min((ratio - 1.5) / 3, 0.5)
        else:
            score = 0.2 + ratio * 0.3

        return max(0.0, min(1.0, score))

    def _factor_reversal(self, data: Dict[str, Any]) -> float:
        """反转因子：近3日涨跌幅，寻找超跌反弹机会"""
        closes = data['closes']
        if len(closes) < 4:
            return 0.5

        return_3d = (closes[-1] - closes[-4]) / closes[-4]

        if return_3d <= -0.10:
            score = 0.0
        elif return_3d <= -0.03:
            score = 0.3 + (return_3d + 0.10) / 0.07 * 0.5
        elif return_3d <= 0:
            score = 0.8 - return_3d / 0.03 * 0.3
        elif return_3d <= 0.03:
            score = 0.5 - return_3d / 0.03 * 0.3
        else:
            score = 0.2

        return max(0.0, min(1.0, score))

    def _factor_volatility(self, data: Dict[str, Any]) -> float:
        """波动率因子：基于日振幅和收盘价"""
        records = data.get('records', [])
        if len(records) < 14:
            return 0.5

        volatilities = []
        for r in records[-14:]:
            if r.close and r.close > 0 and r.high and r.low:
                vol = (r.high - r.low) / r.close
                volatilities.append(vol)

        if not volatilities:
            return 0.5

        avg_vol = sum(volatilities) / len(volatilities)

        if 0.02 <= avg_vol <= 0.05:
            score = 0.6 + (avg_vol - 0.02) / 0.03 * 0.4
        elif avg_vol < 0.02:
            score = 0.3 + avg_vol / 0.02 * 0.3
        else:
            score = 1.0 - min((avg_vol - 0.05) / 0.05, 0.5)

        return max(0.0, min(1.0, score))

    def score_stock(self, code: str) -> Optional[Dict[str, Any]]:
        """对单只股票进行综合评分"""
        data = self._get_stock_daily_data(code, days=30)
        if data is None or data['latest'] is None:
            return None

        if self._is_limit_up_down(data['latest']):
            return None

        weights = self.DEFAULT_WEIGHTS

        factor_scores = {
            'trend': self._factor_trend(data),
            'momentum': self._factor_momentum(data),
            'volume': self._factor_volume(data),
            'reversal': self._factor_reversal(data),
            'volatility': self._factor_volatility(data),
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
