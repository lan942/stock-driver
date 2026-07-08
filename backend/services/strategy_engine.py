"""多因子量化选股引擎

基于用户可配置的因子权重，每日对所有股票进行综合评分，
输出 TOP N 买入推荐（含建议买入价、目标止盈价、止损价）。
"""

from typing import Optional

from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.services.strategy_config import StrategyConfigService


class StrategyEngine:
    """多因子评分选股引擎"""

    # 默认因子权重
    DEFAULT_WEIGHTS = {
        'trend': 0.30,
        'momentum': 0.25,
        'volume': 0.20,
        'reversal': 0.15,
        'volatility': 0.10,
    }

    @staticmethod
    def _get_all_codes() -> list:
        """获取所有股票代码"""
        db = next(get_db())
        codes = [row[0] for row in db.query(Stock.code).all()]
        db.close()
        return codes

    @staticmethod
    def _get_stock_daily_data(code: str, days: int = 30) -> dict:
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
        """判断是否涨跌停（±9.9%）"""
        if latest.change_percent is None:
            return False
        return abs(latest.change_percent) >= 9.9

    # ─── 因子计算 ─────────────────────────────────────────

    @staticmethod
    def _factor_trend(data: dict) -> float:
        """趋势因子：MA5 与 MA20 乖离率"""
        closes = data['closes']
        if len(closes) < 20:
            return 0.5

        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        if ma20 == 0:
            return 0.5

        bias = (ma5 - ma20) / ma20  # 乖离率，正值表示短线上行

        # 映射到 0~1：bias 在 -0.05 到 0.05 之间线性映射
        # bias > 0: 趋势向上（高分），bias < 0: 趋势向下（低分）
        score = (bias + 0.05) / 0.10
        return max(0.0, min(1.0, score))

    @staticmethod
    def _factor_momentum(data: dict) -> float:
        """动量因子：基于 RSI 和近期涨跌幅"""
        closes = data['closes']
        change_pcts = data.get('change_pcts', [])
        if len(closes) < 14:
            return 0.5

        # 简单 RSI 近似
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

        # RSI 映射到 0~1：
        # RSI 40-60 为中性区域，> 60 偏强，< 40 偏弱
        # 但过高（>80）意味着超买，要扣分
        if rsi > 80:
            score = 0.3
        elif rsi > 60:
            score = 0.5 + (rsi - 60) / 40  # 0.5 ~ 1.0
        elif rsi > 40:
            score = 0.3 + (rsi - 40) / 100  # 0.3 ~ 0.5
        elif rsi > 20:
            score = 0.1 + (rsi - 20) / 200  # 0.1 ~ 0.3
        else:
            score = 0.1

        return max(0.0, min(1.0, score))

    @staticmethod
    def _factor_volume(data: dict) -> float:
        """成交量因子：当日量 / 20日均量"""
        volumes = data['volumes']
        if len(volumes) < 21:
            return 0.5

        latest_vol = volumes[-1]
        avg_vol_20 = sum(volumes[-21:-1]) / 20

        if avg_vol_20 == 0:
            return 0.5

        ratio = latest_vol / avg_vol_20

        # volume ratio 映射到 0~1：
        # 1.0~1.5 放量最佳，过高可能是异常
        if 1.0 <= ratio <= 1.5:
            score = 0.5 + (ratio - 1.0)  # 0.5 ~ 1.0
        elif ratio > 1.5:
            score = 1.0 - min((ratio - 1.5) / 3, 0.5)  # 1.0 ~ 0.5
        else:
            score = 0.2 + ratio * 0.3  # 0.2 ~ 0.5

        return max(0.0, min(1.0, score))

    @staticmethod
    def _factor_reversal(data: dict) -> float:
        """反转因子：近3日涨跌幅，寻找超跌反弹机会"""
        closes = data['closes']
        if len(closes) < 4:
            return 0.5

        return_3d = (closes[-1] - closes[-4]) / closes[-4]

        # 反转逻辑：近3日跌幅大 → 高分（超跌反弹预期）
        # return_3d 在 -0.10 到 0 之间高分
        if return_3d <= -0.10:
            score = 0.0  # 跌幅过大，风险高
        elif return_3d <= -0.03:
            score = 0.3 + (return_3d + 0.10) / 0.07 * 0.5  # 0.3 ~ 0.8
        elif return_3d <= 0:
            score = 0.8 - return_3d / 0.03 * 0.3  # 0.8 ~ 0.5
        elif return_3d <= 0.03:
            score = 0.5 - return_3d / 0.03 * 0.3  # 0.5 ~ 0.2
        else:
            score = 0.2

        return max(0.0, min(1.0, score))

    @staticmethod
    def _factor_volatility(data: dict) -> float:
        """波动率因子：基于日振幅和收盘价"""
        records = data.get('records', [])
        if len(records) < 14:
            return 0.5

        # 使用日振幅 (high - low) / close 作为波动率度量的简化版
        volatilities = []
        for r in records[-14:]:
            if r.close and r.close > 0 and r.high and r.low:
                vol = (r.high - r.low) / r.close
                volatilities.append(vol)

        if not volatilities:
            return 0.5

        avg_vol = sum(volatilities) / len(volatilities)

        # 波动率映射到 0~1：
        # 适中波动（2%~5%）最好，太高太低都不佳
        if 0.02 <= avg_vol <= 0.05:
            score = 0.6 + (avg_vol - 0.02) / 0.03 * 0.4  # 0.6 ~ 1.0
        elif avg_vol < 0.02:
            score = 0.3 + avg_vol / 0.02 * 0.3  # 0.3 ~ 0.6
        else:
            score = 1.0 - min((avg_vol - 0.05) / 0.05, 0.5)  # 1.0 ~ 0.5

        return max(0.0, min(1.0, score))

    # ─── 主流程 ───────────────────────────────────────────

    @staticmethod
    def score_stock(code: str) -> Optional[dict]:
        """对单只股票进行综合评分"""
        data = StrategyEngine._get_stock_daily_data(code, days=30)
        if data is None or data['latest'] is None:
            return None

        # 排除涨跌停
        if StrategyEngine._is_limit_up_down(data['latest']):
            return None

        # 获取因子权重
        weights = StrategyConfigService.get('factor_weights') or StrategyEngine.DEFAULT_WEIGHTS

        # 计算各因子得分
        factor_scores = {
            'trend': StrategyEngine._factor_trend(data),
            'momentum': StrategyEngine._factor_momentum(data),
            'volume': StrategyEngine._factor_volume(data),
            'reversal': StrategyEngine._factor_reversal(data),
            'volatility': StrategyEngine._factor_volatility(data),
        }

        # 加权总分
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

    @staticmethod
    def generate_recommendations(
        available_slots: int,
        available_cash: float,
    ) -> list:
        """生成买入推荐清单

        Args:
            available_slots: 可用持仓位数
            available_cash: 可用资金

        Returns:
            推荐列表，每项含 code, name, score, suggested_buy_price, target_price, stop_price
        """
        if available_slots <= 0:
            return []

        codes = StrategyEngine._get_all_codes()

        # 评分
        scored = []
        for code in codes:
            result = StrategyEngine.score_stock(code)
            if result is not None:
                scored.append(result)

        # 按总分降序排序
        scored.sort(key=lambda x: x['total_score'], reverse=True)

        # 获取配置
        stop_profit_pct = float(StrategyConfigService.get('stop_profit_pct') or 0.06)
        stop_loss_pct = float(StrategyConfigService.get('stop_loss_pct') or 0.03)
        position_ratio = float(StrategyConfigService.get('position_ratio') or 0.2)

        # 获取股票名称
        db = next(get_db())
        stock_names = {
            s.code: s.name
            for s in db.query(Stock.code, Stock.name).all()
        }
        db.close()

        # 生成推荐
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

            # 计算所需资金 = 建议买入价 × 100股 × (position_ratio标定)
            required_cash = suggested_buy_price * 100  # 最小单位 100 股
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
