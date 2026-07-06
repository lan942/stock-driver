"""策略回测引擎

在 backtest_portfolio / backtest_transactions / backtest_cash 三张表中落库运行。
按交易日迭代：检测卖出 → 平仓 → 选股 → 买入 → 记录。

回测结果自动可在「回测管理」页面查看。
"""

from datetime import date, timedelta
from typing import Optional

from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.models.backtest import BacktestPortfolio, BacktestTransaction, BacktestCash
from backend.services.strategy_engine import StrategyEngine
from backend.services.strategy_config import StrategyConfigService
from backend.services import backtest_service


class StrategyBacktest:
    """落库回测引擎"""

    def __init__(
        self,
        start_date: date,
        end_date: date,
        initial_capital: float = None,
        max_positions: int = None,
        stop_profit_pct: float = None,
        stop_loss_pct: float = None,
        max_hold_days: int = None,
        position_ratio: float = None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital or float(
            StrategyConfigService.get('initial_capital') or 100000
        )
        self.max_positions = max_positions or int(
            StrategyConfigService.get('max_positions') or 5
        )
        self.stop_profit_pct = stop_profit_pct or float(
            StrategyConfigService.get('stop_profit_pct') or 0.06
        )
        self.stop_loss_pct = stop_loss_pct or float(
            StrategyConfigService.get('stop_loss_pct') or 0.03
        )
        self.max_hold_days = max_hold_days or int(
            StrategyConfigService.get('max_hold_days') or 5
        )
        self.position_ratio = position_ratio or float(
            StrategyConfigService.get('position_ratio') or 0.2
        )

        # 仅用于收益曲线，不入库
        self.daily_records = []

    # ─── 清空历史回测数据 ──────────────────────────────────

    @staticmethod
    def clear_all() -> dict:
        """清空所有回测数据（持仓、交易记录、现金）"""
        db = next(get_db())
        tx_count = db.query(BacktestTransaction).count()
        pos_count = db.query(BacktestPortfolio).count()
        db.query(BacktestTransaction).delete()
        db.query(BacktestPortfolio).delete()
        db.query(BacktestCash).delete()
        db.commit()
        db.close()
        return {
            'deleted_positions': pos_count,
            'deleted_transactions': tx_count,
        }

    # ─── 数据获取 ─────────────────────────────────────────

    @staticmethod
    def _get_stock_data_for_date(day: date) -> dict:
        """获取某日所有股票的数据，返回 {code: StockDaily}"""
        db = next(get_db())
        rows = db.query(StockDaily).filter(StockDaily.date == day).all()
        db.close()
        return {row.code: row for row in rows if row.close and row.close > 0}

    @staticmethod
    def _get_stock_data_before_date(code: str, before_date: date, days: int = 60) -> dict:
        """获取某日之前最近 N 日数据（用于因子计算）"""
        db = next(get_db())
        rows = (
            db.query(StockDaily)
            .filter(StockDaily.code == code, StockDaily.date < before_date)
            .order_by(StockDaily.date.desc())
            .limit(days)
            .all()
        )
        db.close()
        if len(rows) < days:
            return None
        rows = list(reversed(rows))
        return {
            'code': code,
            'records': rows,
            'closes': [r.close for r in rows if r.close],
            'volumes': [r.volume for r in rows if r.volume],
            'change_pcts': [r.change_percent for r in rows if r.change_percent is not None],
            'latest': rows[-1] if rows else None,
        }

    @staticmethod
    def _score_stock_for_date(code: str, before_date: date) -> Optional[dict]:
        """在指定日期对股票评分（基于该日期之前的数据）"""
        data = StrategyBacktest._get_stock_data_before_date(code, before_date, days=60)
        if data is None or data['latest'] is None:
            return None
        if StrategyEngine._is_limit_up_down(data['latest']):
            return None

        weights = StrategyConfigService.get('factor_weights') or StrategyEngine.DEFAULT_WEIGHTS
        factor_scores = {
            'trend': StrategyEngine._factor_trend(data),
            'momentum': StrategyEngine._factor_momentum(data),
            'volume': StrategyEngine._factor_volume(data),
            'reversal': StrategyEngine._factor_reversal(data),
            'volatility': StrategyEngine._factor_volatility(data),
        }
        total_score = sum(factor_scores[n] * weights.get(n, 0) for n in factor_scores)
        return {
            'code': code,
            'total_score': round(total_score, 4),
            'factor_scores': {k: round(v, 4) for k, v in factor_scores.items()},
            'latest_close': data['latest'].close,
        }

    # ─── 持仓查询 ─────────────────────────────────────────

    @staticmethod
    def _get_db_positions() -> list:
        """从 DB 获取当前回测持仓（含买入日期信息）"""
        db = next(get_db())
        positions = db.query(BacktestPortfolio).all()
        # 从交易记录反推买入日期
        result = []
        for pos in positions:
            # 找最近一次 buy 记录
            buy_tx = (
                db.query(BacktestTransaction)
                .filter(
                    BacktestTransaction.code == pos.code,
                    BacktestTransaction.type == 'buy',
                )
                .order_by(BacktestTransaction.trade_date.desc())
                .first()
            )
            result.append({
                'code': pos.code,
                'quantity': pos.quantity,
                'cost_price': pos.cost_price,
                'buy_date': buy_tx.trade_date if buy_tx else None,
            })
        db.close()
        return result

    # ─── 卖出检测 ─────────────────────────────────────────

    def _check_sell_for_day(self, day: date, day_data: dict) -> list:
        """检测当日持仓是否触发卖出（使用 high/low）"""
        positions = self._get_db_positions()
        sold = []

        for pos in positions:
            stock = day_data.get(pos['code'])
            if not stock or pos['buy_date'] is None:
                continue

            hold_days = (day - pos['buy_date']).days
            if hold_days < 1:
                continue  # T+1 保护

            sell_price = None
            reason = None

            if stock.high and stock.high >= pos['cost_price'] * (1 + self.stop_profit_pct):
                sell_price = round(pos['cost_price'] * (1 + self.stop_profit_pct), 2)
                reason = 'sold'
            elif stock.low and stock.low <= pos['cost_price'] * (1 - self.stop_loss_pct):
                sell_price = round(pos['cost_price'] * (1 - self.stop_loss_pct), 2)
                reason = 'sold'
            elif hold_days >= self.max_hold_days:
                sell_price = stock.close
                reason = 'timeout'

            if sell_price:
                sold.append({
                    'code': pos['code'],
                    'quantity': pos['quantity'],
                    'sell_price': sell_price,
                    'cost_price': pos['cost_price'],
                    'reason': reason,
                })

        return sold

    # ─── 生成推荐 ─────────────────────────────────────────

    def _generate_recommendations(self, before_date: date, available_slots: int, available_cash: float) -> list:
        """生成买入推荐"""
        if available_slots <= 0:
            return []

        db = next(get_db())
        codes = [row[0] for row in db.query(Stock.code).all()]
        stock_names = {s.code: s.name for s in db.query(Stock.code, Stock.name).all()}
        db.close()

        scored = []
        for code in codes:
            r = self._score_stock_for_date(code, before_date)
            if r:
                scored.append(r)
        scored.sort(key=lambda x: x['total_score'], reverse=True)

        recs = []
        for s in scored:
            if len(recs) >= available_slots:
                break
            close = s['latest_close']
            if not close or close <= 0:
                continue
            buy_price = round(close * 1.01, 2)
            alloc = available_cash * self.position_ratio
            if alloc < buy_price * 100:
                continue
            recs.append({
                'code': s['code'],
                'name': stock_names.get(s['code'], ''),
                'score': s['total_score'],
                'factor_scores': s['factor_scores'],
                'buy_price': buy_price,
                'close': close,
            })
        return recs

    # ─── 主循环 ───────────────────────────────────────────

    def run(self) -> dict:
        """执行回测：清空旧数据 → 逐日迭代 → 写入 backtest_* 表"""

        # 清空历史数据
        self.clear_all()

        # 初始化资金
        backtest_service.update_cash(self.initial_capital)

        # 获取交易日列表
        db = next(get_db())
        trading_days = [
            row[0] for row in
            db.query(StockDaily.date)
            .filter(StockDaily.date >= self.start_date, StockDaily.date <= self.end_date)
            .distinct()
            .order_by(StockDaily.date)
            .all()
        ]
        db.close()

        if not trading_days:
            return {'error': '指定日期范围内无交易数据'}

        self.daily_records = []
        sell_log = []  # 交易明细

        for day in trading_days:
            day_data = self._get_stock_data_for_date(day)
            available_cash = backtest_service.get_cash_balance()

            # 1. 检测卖出
            sell_items = self._check_sell_for_day(day, day_data)
            for item in sell_items:
                backtest_service.add_transaction(
                    tx_type='sell',
                    code=item['code'],
                    quantity=item['quantity'],
                    price=item['sell_price'],
                    trade_date=day.strftime('%Y-%m-%d'),
                )
                amount = round(item['sell_price'] * item['quantity'], 2)
                backtest_service.update_cash(amount)

                profit_pct = round(
                    (item['sell_price'] - item['cost_price']) / item['cost_price'] * 100, 2
                )
                sell_log.append({
                    'code': item['code'],
                    'buy_price': item['cost_price'],
                    'sell_price': item['sell_price'],
                    'profit_pct': profit_pct,
                    'date': day.strftime('%Y-%m-%d'),
                    'reason': item['reason'],
                })

            # 2. 可用仓位
            positions = self._get_db_positions()
            available_slots = self.max_positions - len(positions)
            available_cash = backtest_service.get_cash_balance()

            # 3. 生成推荐并买入
            if available_slots > 0 and available_cash > 0:
                recs = self._generate_recommendations(day, available_slots, available_cash)
                for rec in recs:
                    result = backtest_service.add_transaction(
                        tx_type='buy',
                        code=rec['code'],
                        quantity=100,
                        price=rec['buy_price'],
                        trade_date=day.strftime('%Y-%m-%d'),
                    )
                    if 'error' not in result:
                        amount = round(rec['buy_price'] * 100, 2)
                        backtest_service.update_cash(-amount)

            # 4. 记录当日权益
            positions = self._get_db_positions()
            cash = backtest_service.get_cash_balance()
            positions_value = 0.0
            for pos in positions:
                stock = day_data.get(pos['code'])
                if stock:
                    positions_value += stock.close * pos['quantity']

            self.daily_records.append({
                'date': day.strftime('%Y-%m-%d'),
                'equity': round(cash + positions_value, 2),
                'cash': round(cash, 2),
                'positions_value': round(positions_value, 2),
                'positions_count': len(positions),
            })

        return self._build_summary(sell_log)

    def _build_summary(self, sell_log: list) -> dict:
        """构建回测汇总"""
        win_count = sum(1 for s in sell_log if s['profit_pct'] > 0)
        lose_count = sum(1 for s in sell_log if s['profit_pct'] <= 0)
        total_count = len(sell_log)

        final_equity = self.daily_records[-1]['equity'] if self.daily_records else self.initial_capital
        total_return_pct = round(
            (final_equity - self.initial_capital) / self.initial_capital * 100, 2
        )
        total_days = len(self.daily_records)
        annualized = round(total_return_pct / (total_days / 252), 2) if total_days > 0 else 0

        return {
            'summary': {
                'start_date': self.start_date.strftime('%Y-%m-%d'),
                'end_date': self.end_date.strftime('%Y-%m-%d'),
                'initial_capital': self.initial_capital,
                'final_equity': round(final_equity, 2),
                'total_return_pct': total_return_pct,
                'annualized_return': annualized,
                'total_trades': total_count,
                'win_trades': win_count,
                'lose_trades': lose_count,
                'win_rate': round(win_count / total_count * 100, 2) if total_count > 0 else 0,
                'data_location': '回测管理页面可查看持仓和交易明细',
            },
            'daily_records': self.daily_records,
            'trades': sell_log,
        }
