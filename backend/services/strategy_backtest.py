"""策略回测引擎

在 backtest_portfolio / backtest_transactions / backtest_cash 三张表中落库运行。
按交易日迭代：检测卖出 → 平仓 → 选股 → 买入 → 记录。

回测结果自动可在「回测管理」页面查看。
"""

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import numpy as np

from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.models.backtest import BacktestPortfolio, BacktestTransaction, BacktestCash
from backend.services.strategy_config import StrategyConfigService
from backend.services.strategies import get_strategy
from backend.services import backtest_service
from backend.services.ml.feature_engine import build_features


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
        strategy_type: str = None,
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
        self.strategy_type = strategy_type or StrategyConfigService.get('strategy_type') or 'xgboost'
        self.strategy = get_strategy(self.strategy_type)

        # ATR 参数
        self.atr_period = int(StrategyConfigService.get('atr_period') or 14)
        self.atr_profit_multiplier = float(StrategyConfigService.get('atr_profit_multiplier') or 2.0)
        self.atr_loss_multiplier = float(StrategyConfigService.get('atr_loss_multiplier') or 1.0)

        # 动态评分卖出参数
        self.dynamic_sell_enabled = (StrategyConfigService.get('dynamic_sell_enabled') or 'true').lower() == 'true'
        self.dynamic_sell_percentile_threshold = float(
            StrategyConfigService.get('dynamic_sell_percentile_threshold') or 0.30
        )
        self.dynamic_sell_score_decline_days = int(
            StrategyConfigService.get('dynamic_sell_score_decline_days') or 2
        )
        self.dynamic_sell_score_absolute_threshold = float(
            StrategyConfigService.get('dynamic_sell_score_absolute_threshold') or 0.30
        )
        self.dynamic_sell_min_hold_days = int(
            StrategyConfigService.get('dynamic_sell_min_hold_days') or 2
        )

        # 自适应参数：根据收益进度动态调整选股门槛和仓位
        self.target_annual_return = float(
            StrategyConfigService.get('target_annual_return') or 0.15
        )
        self.adaptive_thresholds = {
            'behind': float(StrategyConfigService.get('adaptive_score_threshold_behind') or 0.65),
            'near': float(StrategyConfigService.get('adaptive_score_threshold_near') or 0.50),
            'met': float(StrategyConfigService.get('adaptive_score_threshold_met') or 0.35),
        }
        self.adaptive_ratios = {
            'behind': float(StrategyConfigService.get('adaptive_position_ratio_behind') or 0.10),
            'near': float(StrategyConfigService.get('adaptive_position_ratio_near') or 0.15),
            'met': float(StrategyConfigService.get('adaptive_position_ratio_met') or 0.20),
        }
        self.adaptive_min_days = int(
            StrategyConfigService.get('adaptive_min_days') or 20
        )
        # 当前生效的自适应参数（默认=达标档）
        self._adaptive_score_threshold = self.adaptive_thresholds['met']
        self._adaptive_position_ratio = self.adaptive_ratios['met']
        self._current_tier = 'met'

        # 仅用于收益曲线，不入库
        self.daily_records = []

        # 持仓评分追踪：{code: [score_day1, score_day2, ...]} 用于检测连续下降
        self._position_scores = {}

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

    def _reset_position_scores(self):
        """重置持仓评分追踪"""
        self._position_scores = {}

    # ─── 自适应参数计算 ──────────────────────────────────

    def _compute_progress(self) -> tuple:
        """计算当前收益进度（CAGR年化 vs 目标年化）

        Returns:
            (progress, annualized, days): 进度比值、当前年化收益率、已运行交易日数
        """
        n = len(self.daily_records)
        if n == 0:
            return (1.0, 0.0, 0)

        current_equity = self.daily_records[-1]['equity']
        total_return = (current_equity - self.initial_capital) / self.initial_capital
        annualized = (1 + total_return) ** (252 / n) - 1

        if self.target_annual_return <= 0:
            progress = 1.0
        else:
            progress = annualized / self.target_annual_return

        return (progress, annualized, n)

    def _update_adaptive_params(self) -> str:
        """根据收益进度更新选股门槛和仓位比例

        Returns:
            当前档位标识：'warmup'/'behind'/'near'/'met'
        """
        progress, annualized, days = self._compute_progress()

        # 自适应仓位比例以用户设置的 position_ratio 为基准等比缩放
        # 默认 position_ratio=0.20 时，自适应档位：behind=0.10, near=0.15, met=0.20
        # 当用户设置 position_ratio=0.50 时：behind=0.25, near=0.375, met=0.50
        ratio_scale = self.position_ratio / 0.20

        # 预热期：使用达标档参数（CAGR噪声太大）
        if days < self.adaptive_min_days:
            self._adaptive_score_threshold = self.adaptive_thresholds['met']
            self._adaptive_position_ratio = round(self.adaptive_ratios['met'] * ratio_scale, 4)
            self._current_tier = 'warmup'
            return 'warmup'

        # 三档调整
        if progress < 0.5:
            self._adaptive_score_threshold = self.adaptive_thresholds['behind']
            self._adaptive_position_ratio = round(self.adaptive_ratios['behind'] * ratio_scale, 4)
            self._current_tier = 'behind'
        elif progress < 1.0:
            self._adaptive_score_threshold = self.adaptive_thresholds['near']
            self._adaptive_position_ratio = round(self.adaptive_ratios['near'] * ratio_scale, 4)
            self._current_tier = 'near'
        else:
            self._adaptive_score_threshold = self.adaptive_thresholds['met']
            self._adaptive_position_ratio = round(self.adaptive_ratios['met'] * ratio_scale, 4)
            self._current_tier = 'met'

        return self._current_tier

    # ─── 数据获取 ─────────────────────────────────────────

    @staticmethod
    def _get_stock_data_for_date(day: date) -> dict:
        """获取某日所有股票的数据，返回 {code: StockDaily}"""
        db = next(get_db())
        rows = db.query(StockDaily).filter(StockDaily.date == day).all()
        db.close()
        return {row.code: row for row in rows if row.close and row.close > 0}

    @staticmethod
    def _get_stock_data_before_date(code: str, before_date: date, days: int = 30) -> dict:
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
            'highs': [r.high for r in rows if r.high],
            'lows': [r.low for r in rows if r.low],
            'latest': rows[-1] if rows else None,
        }

    def _score_stock_for_date(self, code: str, before_date: date) -> Optional[dict]:
        """在指定日期对股票评分（基于该日期之前的数据）"""
        data = StrategyBacktest._get_stock_data_before_date(code, before_date, days=30)
        if data is None or data['latest'] is None:
            return None
        if self.strategy._is_limit_up_down(data['latest']):
            return None

        return self.strategy.score_from_data(code, data)

    def _calculate_atr(self, code: str, before_date: date) -> Optional[float]:
        """计算指定日期之前的 ATR 值
        
        Args:
            code: 股票代码
            before_date: 计算截止日期（不含）
            
        Returns:
            ATR值，数据不足时返回None
        """
        db = next(get_db())
        rows = (
            db.query(StockDaily)
            .filter(StockDaily.code == code, StockDaily.date < before_date)
            .order_by(StockDaily.date.desc())
            .limit(self.atr_period + 1)
            .all()
        )
        db.close()
        
        if len(rows) < self.atr_period + 1:
            return None
        
        rows = list(reversed(rows))
        
        tr_values = []
        for i in range(1, len(rows)):
            curr = rows[i]
            prev = rows[i-1]
            
            if not curr.high or not curr.low or not prev.close:
                continue
            
            tr1 = curr.high - curr.low
            tr2 = abs(curr.high - prev.close)
            tr3 = abs(curr.low - prev.close)
            
            tr_values.append(max(tr1, tr2, tr3))
        
        if len(tr_values) < self.atr_period:
            return None
        
        atr = sum(tr_values[-self.atr_period:]) / self.atr_period
        return round(atr, 4)

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

    @staticmethod
    def _calc_equity(day_data: dict) -> float:
        """计算当前总权益 = 现金 + 持仓市值（按当日收盘价）"""
        positions = StrategyBacktest._get_db_positions()
        cash = backtest_service.get_cash_balance()
        positions_value = 0.0
        for pos in positions:
            stock = day_data.get(pos['code'])
            if stock and stock.close:
                positions_value += stock.close * pos['quantity']
        return round(cash + positions_value, 2)

    # ─── 卖出检测 ─────────────────────────────────────────

    @staticmethod
    def _count_hold_trading_days(trading_days: list, buy_date: date, current_date: date) -> int:
        """计算从买入日到当日的持仓交易日数

        Args:
            trading_days: 排序后的交易日列表
            buy_date: 买入日期
            current_date: 当前日期

        Returns:
            持仓交易日数（不含买入日，含当前日）
        """
        if not trading_days:
            return (current_date - buy_date).days
        return sum(1 for d in trading_days if buy_date < d <= current_date)

    def _check_intraday_stop_loss(self, day: date, day_data: dict,
                                    trading_days: list = None) -> list:
        """检测日内止损：挂单 min(ATR止损, 配置止损)，日内 low 触及则当日立即卖出

        实盘对应：开盘后挂止损条件单，日内触发即成交。
        止盈/超时/动态卖出不在日内处理，收盘后再评估。

        Returns:
            [{code, quantity, sell_price, cost_price, reason}, ...]
        """
        positions = self._get_db_positions()
        sold = []

        for pos in positions:
            stock = day_data.get(pos['code'])
            if not stock or pos['buy_date'] is None:
                continue

            hold_days = self._count_hold_trading_days(trading_days, pos['buy_date'], day)
            if hold_days < 1:
                continue  # T+1 保护

            atr = self._calculate_atr(pos['code'], day)

            # 止损阈值取较大值（更贴近成本价，更易触发）
            loss_threshold_pct = pos['cost_price'] * (1 - self.stop_loss_pct)
            loss_threshold_atr = None
            if atr:
                loss_threshold_atr = pos['cost_price'] - atr * self.atr_loss_multiplier

            if not stock.low:
                continue

            # 取 max(百分比, ATR) 作为有效止损线，一次性判断
            effective_loss = loss_threshold_pct
            reason = 'stop_loss'
            if loss_threshold_atr is not None and loss_threshold_atr > effective_loss:
                effective_loss = loss_threshold_atr
                reason = 'atr_loss'

            if stock.low <= effective_loss:
                sold.append({
                    'code': pos['code'],
                    'quantity': pos['quantity'],
                    'sell_price': round(effective_loss, 2),
                    'cost_price': pos['cost_price'],
                    'reason': reason,
                })

        return sold

    def _check_close_triggers(self, day: date, day_data: dict,
                               trading_days: list = None,
                               all_scores: list = None) -> list:
        """收盘后评估止盈/超时/动态卖出 → 次日开盘价卖出

        实盘对应：收盘后冷静评估，触发条件则次日集合竞价挂单卖出。
        当日只做止损（_check_intraday_stop_loss），止盈/超时/动态卖出全部延迟到 T+1 开盘执行。

        止盈触发条件：收盘价 >= min(%止盈阈值, ATR止盈阈值)

        Returns:
            [{code, quantity, cost_price, reason}, ...]  sell_price 不在此设置，次日取 open
        """
        positions = self._get_db_positions()
        pending = []

        for pos in positions:
            stock = day_data.get(pos['code'])
            if not stock or pos['buy_date'] is None:
                continue

            hold_days = self._count_hold_trading_days(trading_days, pos['buy_date'], day)
            if hold_days < 1:
                continue

            atr = self._calculate_atr(pos['code'], day)

            # 止盈阈值取较小值（更贴近成本价，更易触发）
            profit_threshold_pct = pos['cost_price'] * (1 + self.stop_profit_pct)
            profit_threshold_atr = None
            if atr:
                profit_threshold_atr = pos['cost_price'] + atr * self.atr_profit_multiplier

            reason = None

            # 1. 止盈检测：收盘价是否达标（取 min(百分比, ATR) 作为有效止盈线）
            if stock.close:
                effective_profit = profit_threshold_pct
                profit_reason = 'take_profit'
                if profit_threshold_atr is not None and profit_threshold_atr < effective_profit:
                    effective_profit = profit_threshold_atr
                    profit_reason = 'atr_profit'

                if stock.close >= effective_profit:
                    reason = profit_reason

            # 2. 超时检测
            if reason is None:
                if hold_days >= self.max_hold_days:
                    reason = 'timeout'

            # 3. 动态评分卖出（至少持有 min_hold 天后才生效）
            if reason is None and self.dynamic_sell_enabled and all_scores:
                if hold_days >= self.dynamic_sell_min_hold_days:
                    code = pos['code']
                    current_score = None
                    for s in all_scores:
                        if s['code'] == code:
                            current_score = s['total_score']
                            break

                    if current_score is not None:
                        percentile = self._compute_score_percentile(all_scores, code)
                        if percentile is not None and percentile < self.dynamic_sell_percentile_threshold:
                            reason = 'dynamic_score_low'
                        elif self._check_score_decline(code, current_score):
                            reason = 'dynamic_score_decline'
                        elif current_score < self.dynamic_sell_score_absolute_threshold:
                            reason = 'dynamic_score_low'

            if reason:
                pending.append({
                    'code': pos['code'],
                    'quantity': pos['quantity'],
                    'cost_price': pos['cost_price'],
                    'reason': reason,
                })

        return pending

    # ─── 全市场评分 ─────────────────────────────────────────

    def _score_all_market_stocks(self, trade_date: date) -> list:
        """全市场批量评分（一次 DB 查询 + 一次 build_features + 一次 GPU 预测）

        Args:
            trade_date: 评分基准日（T日），评分使用该日及之前的数据

        Returns:
            评分列表 [{code, total_score, latest_close}, ...]，按 score 降序排列
        """
        db = next(get_db())
        codes = [row[0] for row in db.query(Stock.code).all()]
        db.close()

        score_as_of = trade_date + timedelta(days=1)
        data_start = score_as_of - timedelta(days=60)

        db = next(get_db())
        rows = (
            db.query(StockDaily)
            .filter(StockDaily.date >= data_start, StockDaily.date < score_as_of)
            .order_by(StockDaily.code, StockDaily.date)
            .all()
        )
        db.close()

        if not rows:
            return []

        df = pd.DataFrame([{
            'code': r.code, 'date': r.date,
            'open': r.open, 'high': r.high, 'low': r.low,
            'close': r.close, 'volume': r.volume,
        } for r in rows])

        df = df.groupby('code').tail(30).copy()
        code_counts = df.groupby('code').size()
        valid_codes = set(code_counts[code_counts >= 30].index)

        features = build_features(df)
        feature_cols = self.strategy._feature_cols
        last_rows = features.drop_duplicates(subset=['code'], keep='last')

        X_rows = []
        valid_records = []
        for _, row in last_rows.iterrows():
            code = row['code']
            if code not in valid_codes:
                continue
            feat = {}
            for col in feature_cols:
                v = row.get(col, 0.0)
                feat[col] = float(v) if pd.notna(v) else 0.0
            X_rows.append(feat)
            valid_records.append({'code': code, 'close': float(row.get('close', 0))})

        if not X_rows:
            return []

        X = pd.DataFrame(X_rows).fillna(0).replace([np.inf, -np.inf], 0)
        X = X.values.astype(np.float32)

        if hasattr(self.strategy, '_gpu_worker') and self.strategy._gpu_worker:
            scores = self.strategy._gpu_worker.predict(X)
        elif hasattr(self.strategy, '_cpu_model') and self.strategy._cpu_model:
            scores = self.strategy._cpu_model.predict(X)
        else:
            return []

        scored = []
        for i, rec in enumerate(valid_records):
            scored.append({
                'code': rec['code'],
                'total_score': float(scores[i]),
                'factor_scores': {'xgboost_prob': float(scores[i])},
                'latest_close': rec['close'],
            })

        scored.sort(key=lambda x: x['total_score'], reverse=True)
        return scored

    def _build_score_map(self, all_scores: list) -> dict:
        """将全市场评分列表转为 {code: total_score} 字典"""
        return {s['code']: s['total_score'] for s in all_scores}

    def _compute_score_percentile(self, all_scores: list, code: str) -> Optional[float]:
        """计算某只股票在全市场中的评分百分位（0=最差, 1=最好）

        Args:
            all_scores: 全市场评分列表（已排序）
            code: 股票代码

        Returns:
            百分位值（0~1），找不到返回 None
        """
        if not all_scores:
            return None
        score_map = {s['code']: s['total_score'] for s in all_scores}
        score = score_map.get(code)
        if score is None:
            return None
        # 统计低于当前 score 的数量
        below = sum(1 for s in all_scores if s['total_score'] < score)
        return below / len(all_scores)

    def _check_score_decline(self, code: str, current_score: float) -> bool:
        """检查持仓评分是否连续下降

        Args:
            code: 股票代码
            current_score: 当日最新评分

        Returns:
            True 表示触发连续下降卖出
        """
        scores = self._position_scores.get(code, [])
        if len(scores) < self.dynamic_sell_score_decline_days:
            return False
        # 检查最近 N 天是否连续下降
        recent = scores[-self.dynamic_sell_score_decline_days:]
        for i in range(1, len(recent)):
            if recent[i] >= recent[i - 1]:
                return False
        # 还要确认今天也比最后一天低
        return current_score < scores[-1]

    def _record_position_score(self, code: str, score: float):
        """记录持仓评分（用于检测连续下降）"""
        if code not in self._position_scores:
            self._position_scores[code] = []
        self._position_scores[code].append(score)

    # ─── 生成推荐 ─────────────────────────────────────────

    def _generate_recommendations(self, trade_date: date, available_slots: int,
                                   total_equity: float, available_cash: float,
                                   all_scores: list = None) -> list:
        """生成买入候选

        如果提供 all_scores，直接使用预计算的全市场评分（避免重复计算）；
        否则自行计算（兼容旧调用路径）。

        Args:
            trade_date: 生成推荐的交易日（T日）
            total_equity: 当前总资产
            available_cash: 当前可用现金
            all_scores: 可选，预计算的全市场评分列表
        """
        if available_slots <= 0:
            return []

        if all_scores is None:
            all_scores = self._score_all_market_stocks(trade_date)
        if not all_scores:
            return []

        db = next(get_db())
        stock_names = {s.code: s.name for s in db.query(Stock.code, Stock.name).all()}
        db.close()

        recs = []
        for s in all_scores:
            if len(recs) >= available_slots:
                break
            if s['total_score'] < self._adaptive_score_threshold:
                break
            close = s['latest_close']
            if not close or close <= 0:
                continue
            alloc = total_equity * self._adaptive_position_ratio
            if alloc < close * 100:
                continue
            recs.append({
                'code': s['code'],
                'name': stock_names.get(s['code'], ''),
                'score': s['total_score'],
                'factor_scores': s['factor_scores'],
                'prev_close': close,
                'position_ratio': self._adaptive_position_ratio,
            })
        return recs

    # ─── 执行候选买入（T+1日开盘） ────────────────────────

    def _execute_pending_buys(self, day: date, day_data: dict, pending: list) -> int:
        """执行待成交买入：以当日 open 成交（不限涨跌幅）

        每只股票的买入金额 = 总资产 × 仓位比例（同一批买入基于相同的总资产计算），
        实际买入数量必须是 100 的整数倍（A股最小交易单位），
        且总花费不超过可用现金。每笔成交后记录当日开收盘价和交易后权益。

        Args:
            day: 当前交易日（T+1）
            day_data: 当日所有股票数据 {code: StockDaily}
            pending: 候选列表（T 日生成）

        Returns:
            实际成交数量
        """
        if not pending:
            return 0

        positions = self._get_db_positions()
        used_slots = len(positions)
        available_slots = self.max_positions - used_slots
        available_cash = backtest_service.get_cash_balance()
        # 计算当前总资产 = 现金 + 持仓市值（基于当日收盘价）
        positions_value = 0.0
        for pos in positions:
            stock = day_data.get(pos['code'])
            if stock and stock.close:
                positions_value += stock.close * pos['quantity']
        total_equity = available_cash + positions_value
        executed = 0

        for rec in pending:
            if available_slots <= 0:
                break
            stock = day_data.get(rec['code'])
            if not stock or stock.open is None or stock.open <= 0:
                continue
            buy_price = stock.open
            # 每只股票的买入金额 = 总资产 × 仓位比例（同一批次独立计算，不逐只扣减）
            alloc = total_equity * rec.get('position_ratio', self.position_ratio)
            # 计算可买股数（必须是 100 的整数倍）
            quantity = int(alloc / buy_price) // 100 * 100
            if quantity < 100:
                continue
            # 确保总花费不超过可用现金（边界保护）
            total_cost = buy_price * quantity
            if total_cost > available_cash:
                quantity -= 100
                if quantity < 100:
                    continue
                total_cost = buy_price * quantity
            result = backtest_service.add_transaction(
                tx_type='buy',
                code=rec['code'],
                quantity=quantity,
                price=buy_price,
                trade_date=day.strftime('%Y-%m-%d'),
                open_price=stock.open,
                close_price=stock.close,
            )
            if 'error' not in result:
                amount = round(total_cost, 2)
                backtest_service.update_cash(-amount)
                # 买入后计算权益并更新交易记录
                equity_after = self._calc_equity(day_data)
                db = next(get_db())
                tx = db.query(BacktestTransaction).order_by(BacktestTransaction.id.desc()).first()
                if tx:
                    tx.equity_after = equity_after
                    db.commit()
                db.close()
                available_cash -= amount
                available_slots -= 1
                executed += 1

        return executed

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
        self._position_scores = {}
        sell_log = []  # 交易明细
        pending_recs = []  # T 日生成的买入候选，T+1 日开盘成交
        pending_sells = []  # T 日收盘评估触发的卖出，T+1 日开盘成交

        for i, day in enumerate(trading_days):
            day_data = self._get_stock_data_for_date(day)
            print(f'[回测] 进度: {i+1}/{len(trading_days)} [{day.strftime("%Y-%m-%d")}]')

            # 自适应参数更新：根据截至昨日的收益进度调整门槛和仓位
            tier = self._update_adaptive_params()
            progress, annualized, _ = self._compute_progress()

            # 0. 全市场评分（一次 GPU 预测，同时用于卖出检测和买入候选）
            all_scores = self._score_all_market_stocks(day)

            # ── 0a. 执行昨日收盘评估触发的卖出（T-1日触发，T日开盘价卖出）──
            for item in pending_sells:
                stock = day_data.get(item['code'])
                if not stock or stock.open is None or stock.open <= 0:
                    continue
                sell_price = stock.open
                profit_pct = round(
                    (sell_price - item['cost_price']) / item['cost_price'] * 100, 2
                )
                backtest_service.add_transaction(
                    tx_type='sell',
                    code=item['code'],
                    quantity=item['quantity'],
                    price=sell_price,
                    trade_date=day.strftime('%Y-%m-%d'),
                    open_price=stock.open,
                    close_price=stock.close,
                    profit_pct=profit_pct,
                    reason=item['reason'],
                )
                amount = round(sell_price * item['quantity'], 2)
                backtest_service.update_cash(amount)
                equity_after = self._calc_equity(day_data)
                db = next(get_db())
                tx = db.query(BacktestTransaction).order_by(BacktestTransaction.id.desc()).first()
                if tx:
                    tx.equity_after = equity_after
                    db.commit()
                db.close()

                sell_log.append({
                    'code': item['code'],
                    'buy_price': item['cost_price'],
                    'sell_price': sell_price,
                    'profit_pct': profit_pct,
                    'date': day.strftime('%Y-%m-%d'),
                    'reason': item['reason'],
                })
                self._position_scores.pop(item['code'], None)
            pending_sells = []

            # ── 1. 日内止损检测（当日 low 触及止损线 → 立即卖出）──
            stop_loss_items = self._check_intraday_stop_loss(day, day_data, trading_days)
            for item in stop_loss_items:
                stock = day_data.get(item['code'])
                profit_pct = round(
                    (item['sell_price'] - item['cost_price']) / item['cost_price'] * 100, 2
                )
                backtest_service.add_transaction(
                    tx_type='sell',
                    code=item['code'],
                    quantity=item['quantity'],
                    price=item['sell_price'],
                    trade_date=day.strftime('%Y-%m-%d'),
                    open_price=stock.open if stock else None,
                    close_price=stock.close if stock else None,
                    profit_pct=profit_pct,
                    reason=item['reason'],
                )
                amount = round(item['sell_price'] * item['quantity'], 2)
                backtest_service.update_cash(amount)
                equity_after = self._calc_equity(day_data)
                db = next(get_db())
                tx = db.query(BacktestTransaction).order_by(BacktestTransaction.id.desc()).first()
                if tx:
                    tx.equity_after = equity_after
                    db.commit()
                db.close()

                sell_log.append({
                    'code': item['code'],
                    'buy_price': item['cost_price'],
                    'sell_price': item['sell_price'],
                    'profit_pct': profit_pct,
                    'date': day.strftime('%Y-%m-%d'),
                    'reason': item['reason'],
                })
                self._position_scores.pop(item['code'], None)

            # ── 2. 执行昨日候选的买入（T+1 日开盘成交）──
            self._execute_pending_buys(day, day_data, pending_recs)
            pending_recs = []

            # ── 3. 收盘后评估：止盈/超时/动态卖出 → 生成待卖出队列（T+1 开盘执行）──
            if day != trading_days[-1]:
                pending_sells = self._check_close_triggers(day, day_data, trading_days, all_scores)

            # ── 3b. 记录持仓评分（必须在收盘评估之后，确保 _check_score_decline 用历史分数比较）──
            if all_scores:
                score_map = self._build_score_map(all_scores)
                positions = self._get_db_positions()
                sold_codes = {s['code'] for s in stop_loss_items}
                for pos in positions:
                    if pos['code'] not in sold_codes:
                        score = score_map.get(pos['code'])
                        if score is not None:
                            self._record_position_score(pos['code'], score)

            # ── 4. 生成今日买入候选（收盘后生成，留到明日开盘成交）──
            #    最后一天不再生成候选（没有 T+1 可以成交）
            if day != trading_days[-1]:
                positions = self._get_db_positions()
                available_slots = self.max_positions - len(positions)
                available_cash = backtest_service.get_cash_balance()
                positions_value = 0.0
                for pos in positions:
                    stock = day_data.get(pos['code'])
                    if stock and stock.close:
                        positions_value += stock.close * pos['quantity']
                total_equity = available_cash + positions_value
                if available_slots > 0 and available_cash > 0:
                    pending_recs = self._generate_recommendations(day, available_slots, total_equity, available_cash, all_scores)

            # ── 5. 记录当日权益 ──
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
                'tier': tier,
                'progress': round(progress, 4),
                'annualized': round(annualized, 4),
                'score_threshold': round(self._adaptive_score_threshold, 2),
                'position_ratio': round(self._adaptive_position_ratio, 2),
            })

        # ─── 清仓阶段：结束日后继续运行卖出策略，不买入，直到持仓清空 ──
        positions = self._get_db_positions()
        if positions:
            # 获取结束日之后的交易日（最多再跑30个交易日用于清仓）
            db = next(get_db())
            post_days = [
                row[0] for row in
                db.query(StockDaily.date)
                .filter(StockDaily.date > self.end_date)
                .distinct()
                .order_by(StockDaily.date)
                .limit(30)
                .all()
            ]
            db.close()

            all_trading_days = trading_days + post_days
            pending_sells = []

            for day in post_days:
                day_data = self._get_stock_data_for_date(day)
                all_scores = self._score_all_market_stocks(day)

                # 0a. 执行昨日收盘评估触发的卖出（T-1日触发，T日开盘价卖出）
                for item in pending_sells:
                    stock = day_data.get(item['code'])
                    if not stock or stock.open is None or stock.open <= 0:
                        continue
                    sell_price = stock.open
                    profit_pct = round(
                        (sell_price - item['cost_price']) / item['cost_price'] * 100, 2
                    )
                    backtest_service.add_transaction(
                        tx_type='sell', code=item['code'], quantity=item['quantity'],
                        price=sell_price, trade_date=day.strftime('%Y-%m-%d'),
                        open_price=stock.open, close_price=stock.close,
                        profit_pct=profit_pct, reason=item['reason'],
                    )
                    amount = round(sell_price * item['quantity'], 2)
                    backtest_service.update_cash(amount)
                    equity_after = self._calc_equity(day_data)
                    db = next(get_db())
                    tx = db.query(BacktestTransaction).order_by(BacktestTransaction.id.desc()).first()
                    if tx:
                        tx.equity_after = equity_after
                        db.commit()
                    db.close()
                    sell_log.append({
                        'code': item['code'], 'buy_price': item['cost_price'],
                        'sell_price': sell_price, 'profit_pct': profit_pct,
                        'date': day.strftime('%Y-%m-%d'), 'reason': item['reason'],
                    })
                    self._position_scores.pop(item['code'], None)
                pending_sells = []

                # 1. 日内止损检测
                stop_loss_items = self._check_intraday_stop_loss(day, day_data, all_trading_days)
                for item in stop_loss_items:
                    stock = day_data.get(item['code'])
                    profit_pct = round(
                        (item['sell_price'] - item['cost_price']) / item['cost_price'] * 100, 2
                    )
                    backtest_service.add_transaction(
                        tx_type='sell', code=item['code'], quantity=item['quantity'],
                        price=item['sell_price'], trade_date=day.strftime('%Y-%m-%d'),
                        open_price=stock.open if stock else None,
                        close_price=stock.close if stock else None,
                        profit_pct=profit_pct, reason=item['reason'],
                    )
                    amount = round(item['sell_price'] * item['quantity'], 2)
                    backtest_service.update_cash(amount)
                    equity_after = self._calc_equity(day_data)
                    db = next(get_db())
                    tx = db.query(BacktestTransaction).order_by(BacktestTransaction.id.desc()).first()
                    if tx:
                        tx.equity_after = equity_after
                        db.commit()
                    db.close()
                    sell_log.append({
                        'code': item['code'], 'buy_price': item['cost_price'],
                        'sell_price': item['sell_price'], 'profit_pct': profit_pct,
                        'date': day.strftime('%Y-%m-%d'), 'reason': item['reason'],
                    })
                    self._position_scores.pop(item['code'], None)

                # 2. 收盘后评估：止盈/超时/动态 → T+1 开盘卖出
                pending_sells = self._check_close_triggers(day, day_data, all_trading_days, all_scores)

                # 2b. 记录持仓评分（必须在收盘评估之后，确保 _check_score_decline 用历史分数比较）
                if all_scores:
                    score_map = self._build_score_map(all_scores)
                    positions = self._get_db_positions()
                    sold_codes = {s['code'] for s in stop_loss_items}
                    for pos in positions:
                        if pos['code'] not in sold_codes:
                            score = score_map.get(pos['code'])
                            if score is not None:
                                self._record_position_score(pos['code'], score)

                # 3. 记录当日权益
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

                if not positions:
                    break

            # 如果跑完后续数据还有持仓，以最后可用日收盘价强制清仓
            positions = self._get_db_positions()
            if positions:
                last_day = post_days[-1] if post_days else trading_days[-1]
                last_day_data = self._get_stock_data_for_date(last_day)
                for pos in positions:
                    stock = last_day_data.get(pos['code'])
                    sell_price = stock.close if stock else pos['cost_price']
                    profit_pct = round(
                        (sell_price - pos['cost_price']) / pos['cost_price'] * 100, 2
                    )
                    backtest_service.add_transaction(
                        tx_type='sell',
                        code=pos['code'],
                        quantity=pos['quantity'],
                        price=sell_price,
                        trade_date=last_day.strftime('%Y-%m-%d'),
                        open_price=stock.open if stock else None,
                        close_price=stock.close if stock else None,
                        profit_pct=profit_pct,
                        reason='force_close',
                    )
                    amount = round(sell_price * pos['quantity'], 2)
                    backtest_service.update_cash(amount)

                    sell_log.append({
                        'code': pos['code'],
                        'buy_price': pos['cost_price'],
                        'sell_price': sell_price,
                        'profit_pct': profit_pct,
                        'date': last_day.strftime('%Y-%m-%d'),
                        'reason': 'force_close',
                    })

                # 记录强制清仓后权益
                cash = backtest_service.get_cash_balance()
                self.daily_records.append({
                    'date': last_day.strftime('%Y-%m-%d'),
                    'equity': round(cash, 2),
                    'cash': round(cash, 2),
                    'positions_value': 0.0,
                    'positions_count': 0,
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

        # CAGR 年化收益率（与自适应调整口径一致）
        if total_days > 0 and final_equity > 0:
            annualized = ((final_equity / self.initial_capital) ** (252 / total_days) - 1) * 100
        else:
            annualized = 0.0
        annualized = round(annualized, 2)

        # 最大回撤
        max_drawdown = 0.0
        peak = 0.0
        for record in self.daily_records:
            eq = record['equity']
            if eq > peak:
                peak = eq
            if peak > 0:
                dd = (peak - eq) / peak * 100
                if dd > max_drawdown:
                    max_drawdown = dd
        max_drawdown = round(max_drawdown, 2)

        # 最终进度
        final_progress, _, _ = self._compute_progress()
        final_progress = round(final_progress, 4)

        return {
            'summary': {
                'start_date': self.start_date.strftime('%Y-%m-%d'),
                'end_date': self.end_date.strftime('%Y-%m-%d'),
                'initial_capital': self.initial_capital,
                'final_equity': round(final_equity, 2),
                'total_return_pct': total_return_pct,
                'annualized_return': annualized,
                'max_drawdown': max_drawdown,
                'target_annual_return': round(self.target_annual_return * 100, 2),
                'final_progress': final_progress,
                'final_tier': self._current_tier,
                'total_trades': total_count,
                'win_trades': win_count,
                'lose_trades': lose_count,
                'win_rate': round(win_count / total_count * 100, 2) if total_count > 0 else 0,
                'data_location': '回测管理页面可查看持仓和交易明细',
            },
            'daily_records': self.daily_records,
            'trades': sell_log,
        }
