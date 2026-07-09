"""突破启动策略

核心逻辑：寻找刚突破平台、即将启动上涨的股票
- 放量突破近20日高点
- MACD金叉初期
- 波动率上升确认突破有效性
"""

from typing import Optional, Dict, Any

from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.services.strategy_config import StrategyConfigService
from .base_strategy import IStrategy


class BreakoutStrategy(IStrategy):
    """突破启动策略"""

    STRATEGY_NAME: str = "breakout"
    STRATEGY_DESCRIPTION: str = "突破启动策略：寻找放量突破平台的股票"

    DEFAULT_WEIGHTS = {
        'breakout': 0.40,
        'volume_confirm': 0.30,
        'macd_cross': 0.20,
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

    def _factor_breakout(self, data: Dict[str, Any]) -> float:
        """突破因子：是否突破近20日高点，且突破幅度有效（过滤假突破）"""
        closes = data['closes']
        highs = data['highs']
        if len(closes) < 21:
            return 0.5

        recent_highs = highs[-21:-1]
        if not recent_highs:
            return 0.5

        platform_high = max(recent_highs)
        current_close = closes[-1]
        breakout_pct = (current_close - platform_high) / platform_high

        # 收盘价需站在平台上方2%以上才算有效突破（过滤假突破）
        if breakout_pct >= 0.03:
            score = 0.8 + min((breakout_pct - 0.03) / 0.02, 0.2)
        elif breakout_pct >= 0.02:
            score = 0.6 + (breakout_pct - 0.02) / 0.01 * 0.2
        elif breakout_pct >= 0.01:
            score = 0.4
        elif breakout_pct >= 0:
            score = 0.3
        elif breakout_pct >= -0.02:
            score = 0.2
        else:
            score = 0.1

        return max(0.0, min(1.0, score))

    def _factor_volume_confirm(self, data: Dict[str, Any]) -> float:
        """成交量确认因子：突破时成交量需明显放大（≥2倍为佳）"""
        volumes = data['volumes']
        closes = data['closes']
        if len(volumes) < 21:
            return 0.5

        avg_vol_20 = sum(volumes[-21:-1]) / 20
        recent_vol = volumes[-1]

        if avg_vol_20 == 0:
            return 0.5

        vol_ratio = recent_vol / avg_vol_20

        recent_highs = [data['highs'][i] for i in range(-21, -1) if i >= -len(data['highs'])]
        platform_high = max(recent_highs) if recent_highs else closes[-1]

        is_breakout = closes[-1] >= platform_high

        # 提高成交量要求：2倍以上为有效放量
        if is_breakout and 2.0 <= vol_ratio <= 4.0:
            score = 0.85 + min((vol_ratio - 2.0) / 2.0, 0.15)
        elif is_breakout and 1.5 <= vol_ratio < 2.0:
            score = 0.5 + (vol_ratio - 1.5) / 0.5 * 0.3
        elif is_breakout and 1.2 <= vol_ratio < 1.5:
            score = 0.3
        elif is_breakout and vol_ratio > 4.0:
            score = max(0.5, 0.85 - (vol_ratio - 4.0) / 4.0 * 0.35)
        elif is_breakout:
            score = 0.2
        else:
            score = 0.2

        return max(0.0, min(1.0, score))

    def _factor_macd_cross(self, data: Dict[str, Any]) -> float:
        """MACD金叉因子：优先选择零轴附近的初期金叉（避免已经大涨后的高位金叉）"""
        closes = data['closes']
        if len(closes) < 26:
            return 0.5

        ema12 = []
        ema26 = []
        for i, close in enumerate(closes):
            if i == 0:
                ema12.append(close)
                ema26.append(close)
            else:
                ema12.append(close * (2 / (12 + 1)) + ema12[i - 1] * (1 - 2 / (12 + 1)))
                ema26.append(close * (2 / (26 + 1)) + ema26[i - 1] * (1 - 2 / (26 + 1)))

        macd_line = [ema12[i] - ema26[i] for i in range(len(ema12))]

        signal_line = []
        for i, macd in enumerate(macd_line):
            if i == 0:
                signal_line.append(macd)
            else:
                signal_line.append(macd * (2 / (9 + 1)) + signal_line[i - 1] * (1 - 2 / (9 + 1)))

        histogram = [macd_line[i] - signal_line[i] for i in range(len(macd_line))]

        if len(histogram) < 3:
            return 0.5

        prev_hist = histogram[-2]
        curr_hist = histogram[-1]
        prev_macd = macd_line[-2]
        curr_macd = macd_line[-1]

        # 归一化MACD值（相对于股价），判断金叉位置高低
        macd_pct = abs(curr_macd) / closes[-1] if closes[-1] > 0 else 0

        # 零轴附近的初期金叉最佳（macd_pct < 1%）
        if prev_hist <= 0 and curr_hist > 0 and curr_macd > 0 and macd_pct < 0.01:
            score = 0.95
        elif prev_hist <= 0 and curr_hist > 0 and curr_macd > 0 and macd_pct < 0.02:
            score = 0.8
        elif prev_hist <= 0 and curr_hist > 0 and macd_pct < 0.01:
            score = 0.7
        elif prev_hist <= 0 and curr_hist > 0:
            score = 0.5
        elif prev_macd <= 0 and curr_macd > 0 and macd_pct < 0.01:
            score = 0.65
        elif prev_macd <= 0 and curr_macd > 0:
            score = 0.45
        elif curr_hist > prev_hist and curr_hist > 0 and macd_pct < 0.02:
            score = 0.5
        elif curr_hist > prev_hist and curr_hist > 0:
            score = 0.3
        else:
            score = 0.15

        return max(0.0, min(1.0, score))

    def _factor_volatility(self, data: Dict[str, Any]) -> float:
        """波动率因子：突破时波动率是否上升"""
        records = data.get('records', [])
        if len(records) < 14:
            return 0.5

        volatilities = []
        for r in records[-14:-1]:
            if r.close and r.close > 0 and r.high and r.low:
                vol = (r.high - r.low) / r.close
                volatilities.append(vol)

        if not volatilities:
            return 0.5

        avg_vol_prev = sum(volatilities) / len(volatilities)

        latest = records[-1]
        if latest.close and latest.close > 0 and latest.high and latest.low:
            latest_vol = (latest.high - latest.low) / latest.close
        else:
            latest_vol = avg_vol_prev

        vol_ratio = latest_vol / avg_vol_prev if avg_vol_prev > 0 else 1.0

        closes = data['closes']
        recent_highs = [data['highs'][i] for i in range(-21, -1) if i >= -len(data['highs'])]
        platform_high = max(recent_highs) if recent_highs else closes[-1]
        is_breakout = closes[-1] >= platform_high

        if is_breakout and 1.2 <= vol_ratio <= 2.0:
            score = 0.7 + (vol_ratio - 1.2) / 0.8 * 0.3
        elif is_breakout and vol_ratio > 2.0:
            score = max(0.5, 1.0 - (vol_ratio - 2.0) / 2.0)
        elif is_breakout:
            score = 0.4
        else:
            score = 0.3

        return max(0.0, min(1.0, score))

    def score_stock(self, code: str) -> Optional[Dict[str, Any]]:
        """对单只股票进行突破启动评分"""
        data = self._get_stock_daily_data(code, days=30)
        if data is None or data['latest'] is None:
            return None

        if self._is_limit_up_down(data['latest']):
            return None

        weights = self.DEFAULT_WEIGHTS

        factor_scores = {
            'breakout': self._factor_breakout(data),
            'volume_confirm': self._factor_volume_confirm(data),
            'macd_cross': self._factor_macd_cross(data),
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
