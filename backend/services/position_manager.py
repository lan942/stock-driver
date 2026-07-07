"""策略持仓管理服务

管理策略持仓的完整生命周期：开仓 → 监控卖出条件 → 平仓。
同时跟踪资金、计算收益统计。
"""

import json
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func
from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.models.strategy import (
    StrategyPosition,
    StrategyTransaction,
    StrategyCash,
    StrategyConfig,
)
from backend.services.strategy_config import StrategyConfigService
from backend.services import portfolio_service


class PositionManager:
    """策略持仓管理器"""

    # ─── 现金管理 ─────────────────────────────────────────

    @staticmethod
    def _get_cash() -> StrategyCash:
        """获取或创建现金记录，自动同步配置中的 initial_capital"""
        db = next(get_db())
        cash = db.query(StrategyCash).first()
        config_initial = float(StrategyConfigService.get('initial_capital') or 100000)
        if not cash:
            cash = StrategyCash(balance=config_initial, initial_capital=config_initial)
            db.add(cash)
            db.commit()
        elif cash.initial_capital != config_initial:
            # 配置已变更，同步到 StrategyCash 表
            diff = config_initial - cash.initial_capital
            cash.initial_capital = config_initial
            cash.balance = round(cash.balance + diff, 2)
            db.commit()
        db.close()
        db = next(get_db())
        cash = db.query(StrategyCash).first()
        db.close()
        return cash

    @staticmethod
    def get_available_cash() -> float:
        """获取可用资金"""
        cash = PositionManager._get_cash()
        return cash.balance

    @staticmethod
    def _update_cash(amount: float) -> None:
        """更新现金（正数增加，负数减少）"""
        db = next(get_db())
        cash = db.query(StrategyCash).first()
        if cash:
            cash.balance = round(cash.balance + amount, 2)
            db.commit()
        db.close()

    # ─── 持仓操作 ─────────────────────────────────────────

    @staticmethod
    def execute_recommendation(
        code: str,
        name: str,
        quantity: int,
        buy_price: float,
        suggested_buy_price: float,
        target_price: float,
        stop_price: float,
        buy_date: date,
    ) -> dict:
        """执行买入推荐：同时写入 portfolio 和 strategy_positions 两套系统
        
        - portfolio:  持仓管理页面可见的实际持仓
        - strategy:   策略跟踪（含止盈止损目标和状态机）
        """
        # 1. 写入 portfolio 系统（现有的持仓管理页面可见）
        tx_result = portfolio_service.add_transaction(
            tx_type='buy',
            code=code,
            quantity=quantity,
            price=buy_price,
            trade_date=buy_date.strftime('%Y-%m-%d'),
        )
        if 'error' in tx_result:
            return tx_result

        # 2. 更新 portfolio 系统的现金余额
        amount = round(buy_price * quantity, 2)
        portfolio_service.update_cash_balance(-amount)

        # 3. 写入 strategy 系统（策略跟踪）
        db = next(get_db())
        try:
            position = StrategyPosition(
                code=code,
                name=name,
                quantity=quantity,
                buy_price=buy_price,
                target_price=target_price,
                stop_price=stop_price,
                suggested_buy_price=suggested_buy_price,
                buy_date=buy_date,
                status='holding',
            )
            db.add(position)

            tx = StrategyTransaction(
                type='buy',
                code=code,
                quantity=quantity,
                price=buy_price,
                amount=amount,
                trade_date=buy_date,
            )
            db.add(tx)
            db.commit()
            pos_id = position.id
        finally:
            db.close()

        # 4. 更新 strategy 系统的现金
        PositionManager._update_cash(-amount)

        return {
            'position_id': pos_id,
            'portfolio_transaction_id': tx_result.get('id'),
            'code': code,
            'buy_price': buy_price,
            'quantity': quantity,
            'amount': amount,
        }

    @staticmethod
    def close_position(
        position_id: int,
        sell_price: float,
        sell_date: date,
        status: str = 'sold',
    ) -> dict:
        """平仓：更新持仓状态、回笼资金、计算盈亏，同时同步到 portfolio 系统"""
        db = next(get_db())
        try:
            position = db.query(StrategyPosition).filter(
                StrategyPosition.id == position_id
            ).first()

            if not position:
                return {'error': '持仓记录不存在'}
            if position.status != 'holding':
                return {'error': f'持仓状态为 {position.status}，无法平仓'}

            profit_pct = round(
                (sell_price - position.buy_price) / position.buy_price * 100, 2
            )
            amount = round(sell_price * position.quantity, 2)

            position.status = status
            position.sell_price = sell_price
            position.sell_date = sell_date
            position.profit_pct = profit_pct

            # 记录 strategy 交易
            tx = StrategyTransaction(
                type='sell',
                code=position.code,
                quantity=position.quantity,
                price=sell_price,
                amount=amount,
                trade_date=sell_date,
            )
            db.add(tx)
            db.commit()

            code = position.code
            quantity = position.quantity
            result = {
                'position_id': position_id,
                'code': code,
                'sell_price': sell_price,
                'profit_pct': profit_pct,
                'amount': amount,
            }
        finally:
            db.close()

        # 回笼 strategy 系统资金
        PositionManager._update_cash(amount)

        # 同步到 portfolio 系统（持仓管理页面可见）
        sell_tx = portfolio_service.add_transaction(
            tx_type='sell',
            code=code,
            quantity=quantity,
            price=sell_price,
            trade_date=sell_date.strftime('%Y-%m-%d'),
        )
        portfolio_service.update_cash_balance(amount)

        if 'error' in sell_tx:
            result['portfolio_sync_error'] = sell_tx['error']
        else:
            result['portfolio_transaction_id'] = sell_tx.get('id')

        return result

    @staticmethod
    def check_sell_conditions(today: date) -> dict:
        """检测所有 holding 持仓的卖出条件

        Returns:
            {sold: [...], holding: N}
        """
        db = next(get_db())
        positions = db.query(StrategyPosition).filter(
            StrategyPosition.status == 'holding'
        ).all()
        db.close()

        max_hold_days = int(StrategyConfigService.get('max_hold_days') or 5)

        sold_list = []
        for pos in positions:
            # T+1 保护：买入当天不检测
            if pos.buy_date == today:
                continue

            # 获取当日收盘价
            db = next(get_db())
            daily = (
                db.query(StockDaily)
                .filter(
                    StockDaily.code == pos.code,
                    StockDaily.date == today,
                )
                .first()
            )
            db.close()

            close_price = daily.close if daily else None
            if close_price is None:
                continue

            # 检测卖出条件（按优先级）
            sell_reason = None

            # 1. 止盈
            if close_price >= pos.target_price:
                sell_reason = 'sold'

            # 2. 止损
            elif close_price <= pos.stop_price:
                sell_reason = 'sold'

            # 3. 超时
            elif (today - pos.buy_date).days >= max_hold_days:
                sell_reason = 'timeout'

            if sell_reason:
                result = PositionManager.close_position(
                    pos.id, close_price, today, sell_reason
                )
                if 'error' not in result:
                    sold_list.append(result)

        remaining = len(positions) - len(sold_list)
        return {'sold': sold_list, 'remaining_holding': max(remaining, 0)}

    @staticmethod
    def get_available_slots() -> int:
        """返回可用持仓数"""
        max_positions = int(StrategyConfigService.get('max_positions') or 5)
        db = next(get_db())
        holding_count = (
            db.query(func.count(StrategyPosition.id))
            .filter(StrategyPosition.status == 'holding')
            .scalar()
        )
        db.close()
        return max(0, max_positions - (holding_count or 0))

    # ─── 持仓查询 ─────────────────────────────────────────

    @staticmethod
    def get_positions(status: str = None) -> list:
        """获取持仓列表"""
        db = next(get_db())
        query = db.query(StrategyPosition)
        if status:
            query = query.filter(StrategyPosition.status == status)

        positions = query.order_by(StrategyPosition.buy_date.desc()).all()

        # 获取最新收盘价计算浮动盈亏
        result = []
        for pos in positions:
            latest = (
                db.query(StockDaily)
                .filter(StockDaily.code == pos.code)
                .order_by(StockDaily.date.desc())
                .first()
            )
            latest_close = latest.close if latest else None

            hold_days = (date.today() - pos.buy_date).days if pos.buy_date else 0

            unrealized_pl = None
            unrealized_pl_pct = None
            if pos.status == 'holding' and latest_close and pos.buy_price:
                unrealized_pl = round(
                    (latest_close - pos.buy_price) * pos.quantity, 2
                )
                unrealized_pl_pct = round(
                    (latest_close - pos.buy_price) / pos.buy_price * 100, 2
                )

            result.append({
                'id': pos.id,
                'code': pos.code,
                'name': pos.name,
                'quantity': pos.quantity,
                'buy_price': pos.buy_price,
                'current_price': latest_close,
                'target_price': pos.target_price,
                'stop_price': pos.stop_price,
                'suggested_buy_price': pos.suggested_buy_price,
                'buy_date': pos.buy_date.strftime('%Y-%m-%d') if pos.buy_date else None,
                'sell_price': pos.sell_price,
                'sell_date': pos.sell_date.strftime('%Y-%m-%d') if pos.sell_date else None,
                'status': pos.status,
                'profit_pct': pos.profit_pct,
                'hold_days': hold_days,
                'unrealized_pl': unrealized_pl,
                'unrealized_pl_pct': unrealized_pl_pct,
            })

        db.close()
        return result

    @staticmethod
    def get_transactions(code: str = None, page: int = 1, page_size: int = 20) -> dict:
        """分页获取交易记录"""
        db = next(get_db())
        query = db.query(StrategyTransaction)

        if code:
            query = query.filter(StrategyTransaction.code == code)

        total = query.count()
        items = (
            query.order_by(StrategyTransaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        result = [
            {
                'id': tx.id,
                'type': tx.type,
                'code': tx.code,
                'quantity': tx.quantity,
                'price': tx.price,
                'amount': tx.amount,
                'trade_date': tx.trade_date.strftime('%Y-%m-%d') if tx.trade_date else None,
                'created_at': tx.created_at.strftime('%Y-%m-%d %H:%M:%S') if tx.created_at else None,
            }
            for tx in items
        ]
        db.close()

        return {
            'data': result,
            'total': total,
            'page': page,
            'page_size': page_size,
        }

    # ─── 收益统计 ─────────────────────────────────────────

    @staticmethod
    def get_stats() -> dict:
        """获取策略绩效统计"""
        db = next(get_db())

        # 已平仓交易
        closed = (
            db.query(StrategyPosition)
            .filter(StrategyPosition.status.in_(['sold', 'timeout']))
            .all()
        )

        # 持仓中
        holding = (
            db.query(StrategyPosition)
            .filter(StrategyPosition.status == 'holding')
            .all()
        )

        # 现金
        cash_obj = db.query(StrategyCash).first()
        available_cash = cash_obj.balance if cash_obj else 0.0
        initial_capital = cash_obj.initial_capital if cash_obj else 100000.0

        # 已实现盈亏
        total_trades = len(closed)
        win_trades = sum(1 for p in closed if p.profit_pct and p.profit_pct > 0)
        lose_trades = sum(1 for p in closed if p.profit_pct and p.profit_pct <= 0)
        win_rate = round(win_trades / total_trades * 100, 2) if total_trades > 0 else 0

        avg_profit = round(
            sum(p.profit_pct for p in closed if p.profit_pct and p.profit_pct > 0)
            / max(win_trades, 1), 2
        )
        avg_loss = round(
            sum(abs(p.profit_pct) for p in closed if p.profit_pct and p.profit_pct <= 0)
            / max(lose_trades, 1), 2
        )

        realized_return = sum(p.profit_pct or 0 for p in closed) / initial_capital * 100 if initial_capital else 0

        # 浮动盈亏
        unrealized_return = 0.0
        total_market_value = 0.0
        for pos in holding:
            latest = (
                db.query(StockDaily)
                .filter(StockDaily.code == pos.code)
                .order_by(StockDaily.date.desc())
                .first()
            )
            if latest and latest.close and pos.buy_price:
                mv = latest.close * pos.quantity
                total_market_value += mv
                unrealized_return += (latest.close - pos.buy_price) * pos.quantity

        unrealized_return_pct = (
            unrealized_return / initial_capital * 100 if initial_capital else 0
        )

        total_return_pct = realized_return + unrealized_return_pct
        total_equity = available_cash + total_market_value

        # 年化收益
        first_tx = (
            db.query(func.min(StrategyTransaction.created_at))
            .scalar()
        )
        if first_tx:
            days = max((datetime.utcnow() - first_tx).days, 1)
        else:
            days = 1
        annualized_return = round(total_return_pct / (days / 252), 2) if days > 0 else 0

        # 目标对比
        target = float(StrategyConfigService.get('target_annual_return') or 0.15) * 100
        on_track = annualized_return >= target

        db.close()

        return {
            'total_trades': total_trades,
            'win_trades': win_trades,
            'lose_trades': lose_trades,
            'win_rate': win_rate,
            'avg_profit_pct': avg_profit,
            'avg_loss_pct': avg_loss,
            'realized_return': round(realized_return, 2),
            'unrealized_return': round(unrealized_return_pct, 2),
            'total_return': round(total_return_pct, 2),
            'annualized_return': annualized_return,
            'target_annual_return': round(target, 2),
            'on_track': on_track,
            'available_cash': round(available_cash, 2),
            'total_equity': round(total_equity, 2),
            'initial_capital': round(initial_capital, 2),
            'positions_count': len(holding),
            'running_days': days,
        }
