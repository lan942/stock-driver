"""回测管理服务：处理回测持仓、交易记录和现金余额的业务逻辑"""
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import func
from backend.models.backtest import BacktestPortfolio, BacktestTransaction, BacktestCash
from backend.models.stock import Stock, StockDaily
from backend.utils.db import get_db

logger = logging.getLogger(__name__)


def get_portfolio_overview() -> Dict[str, Any]:
    """获取回测总览"""
    db = next(get_db())

    cash_balance = db.query(BacktestCash).first()
    cash = cash_balance.balance if cash_balance else 0.0

    holdings = db.query(BacktestPortfolio).all()
    total_market_value = 0.0
    total_cost = 0.0
    total_profit = 0.0

    latest_prices = _get_latest_prices(db)

    for holding in holdings:
        cost = holding.quantity * holding.cost_price
        total_cost += cost

        current_price = latest_prices.get(holding.code)
        if current_price:
            market_value = holding.quantity * current_price
            profit = market_value - cost
            total_market_value += market_value
            total_profit += profit

    total_value = cash + total_market_value
    total_profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0.0

    db.close()

    return {
        'total_value': round(total_value, 2),
        'cash_balance': round(cash, 2),
        'market_value': round(total_market_value, 2),
        'total_profit': round(total_profit, 2),
        'total_profit_rate': round(total_profit_rate, 2),
        'holdings_count': len(holdings)
    }


def get_holdings() -> List[Dict[str, Any]]:
    """获取回测持仓明细列表"""
    db = next(get_db())

    holdings = db.query(BacktestPortfolio).all()
    latest_prices = _get_latest_prices(db)

    # 查询当天买入数量（T+1 规则）
    today = date.today()
    today_buy_rows = db.query(
        BacktestTransaction.code,
        func.sum(BacktestTransaction.quantity)
    ).filter(
        BacktestTransaction.type == 'buy',
        BacktestTransaction.trade_date == today
    ).group_by(BacktestTransaction.code).all()
    today_buy_quantities = {code: qty or 0 for code, qty in today_buy_rows}

    result = []
    for holding in holdings:
        stock = db.query(Stock).filter(Stock.code == holding.code).first()
        stock_name = stock.name if stock else holding.code

        current_price = latest_prices.get(holding.code)
        cost = holding.quantity * holding.cost_price

        if current_price:
            market_value = holding.quantity * current_price
            profit = market_value - cost
            profit_rate = (profit / cost * 100) if cost > 0 else 0.0
        else:
            current_price = 0.0
            market_value = 0.0
            profit = 0.0
            profit_rate = 0.0

        today_buy = today_buy_quantities.get(holding.code, 0)
        available_quantity = holding.quantity - today_buy

        result.append({
            'id': holding.id,
            'code': holding.code,
            'name': stock_name,
            'quantity': holding.quantity,
            'available_quantity': available_quantity,
            'cost_price': round(holding.cost_price, 2),
            'current_price': round(current_price, 2),
            'market_value': round(market_value, 2),
            'profit': round(profit, 2),
            'profit_rate': round(profit_rate, 2)
        })

    db.close()
    return result


def add_holding(code: str, quantity: int, cost_price: float) -> Dict[str, Any]:
    """添加回测持仓"""
    # 验证数量必须是100的整数倍
    if quantity % 100 != 0:
        return {'error': '数量必须是100的整数倍'}
    
    db = next(get_db())

    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        db.close()
        return {'error': f'股票代码 {code} 不存在'}

    existing = db.query(BacktestPortfolio).filter(BacktestPortfolio.code == code).first()
    if existing:
        db.close()
        return {'error': f'股票 {code} 已存在于持仓中'}

    holding = BacktestPortfolio(
        code=code,
        quantity=quantity,
        cost_price=cost_price
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)

    stock_name = stock.name

    latest_prices = _get_latest_prices(db)
    current_price = latest_prices.get(code, 0.0)
    market_value = quantity * current_price
    profit = market_value - (quantity * cost_price)
    profit_rate = (profit / (quantity * cost_price) * 100) if (quantity * cost_price) > 0 else 0.0

    db.close()

    return {
        'id': holding.id,
        'code': holding.code,
        'name': stock_name,
        'quantity': holding.quantity,
        'cost_price': round(holding.cost_price, 2),
        'current_price': round(current_price, 2),
        'market_value': round(market_value, 2),
        'profit': round(profit, 2),
        'profit_rate': round(profit_rate, 2)
    }


def update_holding(holding_id: int, quantity: Optional[int] = None, cost_price: Optional[float] = None) -> Dict[str, Any]:
    """更新回测持仓"""
    db = next(get_db())

    holding = db.query(BacktestPortfolio).filter(BacktestPortfolio.id == holding_id).first()
    if not holding:
        db.close()
        return {'error': '持仓不存在'}

    if quantity is not None:
        holding.quantity = quantity
    if cost_price is not None:
        holding.cost_price = cost_price

    db.commit()
    db.refresh(holding)

    stock = db.query(Stock).filter(Stock.code == holding.code).first()
    stock_name = stock.name if stock else holding.code

    latest_prices = _get_latest_prices(db)
    current_price = latest_prices.get(holding.code, 0.0)
    market_value = holding.quantity * current_price
    profit = market_value - (holding.quantity * holding.cost_price)
    profit_rate = (profit / (holding.quantity * holding.cost_price) * 100) if (holding.quantity * holding.cost_price) > 0 else 0.0

    db.close()

    return {
        'id': holding.id,
        'code': holding.code,
        'name': stock_name,
        'quantity': holding.quantity,
        'cost_price': round(holding.cost_price, 2),
        'current_price': round(current_price, 2),
        'market_value': round(market_value, 2),
        'profit': round(profit, 2),
        'profit_rate': round(profit_rate, 2)
    }


def delete_holding(holding_id: int) -> Dict[str, Any]:
    """删除回测持仓"""
    db = next(get_db())

    holding = db.query(BacktestPortfolio).filter(BacktestPortfolio.id == holding_id).first()
    if not holding:
        db.close()
        return {'error': '持仓不存在'}

    db.delete(holding)
    db.commit()
    db.close()

    return {'success': True, 'message': '持仓已删除'}


def get_transactions(limit: int = 50) -> List[Dict[str, Any]]:
    """获取回测交易记录列表（按交易日期正序）"""
    db = next(get_db())

    transactions = db.query(BacktestTransaction).order_by(
        BacktestTransaction.trade_date.asc(),
        BacktestTransaction.id.asc(),
    ).limit(limit).all()

    result = []
    for tx in transactions:
        stock = db.query(Stock).filter(Stock.code == tx.code).first()
        stock_name = stock.name if stock else tx.code

        result.append({
            'id': tx.id,
            'type': tx.type,
            'code': tx.code,
            'name': stock_name,
            'quantity': tx.quantity,
            'price': round(tx.price, 2),
            'amount': round(tx.amount, 2) if tx.amount else round(tx.quantity * tx.price, 2),
            'trade_date': tx.trade_date.strftime('%Y-%m-%d') if tx.trade_date else '',
            'open_price': round(tx.open_price, 2) if tx.open_price is not None else None,
            'close_price': round(tx.close_price, 2) if tx.close_price is not None else None,
            'equity_after': round(tx.equity_after, 2) if tx.equity_after is not None else None,
            'created_at': tx.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    db.close()
    return result


def add_transaction(
    tx_type: str,
    code: str,
    quantity: int,
    price: float,
    trade_date: Optional[str] = None,
    open_price: Optional[float] = None,
    close_price: Optional[float] = None,
    equity_after: Optional[float] = None,
) -> Dict[str, Any]:
    """添加回测交易记录"""
    # 验证数量必须是100的整数倍
    if quantity % 100 != 0:
        return {'error': '数量必须是100的整数倍'}
    
    db = next(get_db())

    if tx_type not in ('buy', 'sell'):
        db.close()
        return {'error': '交易类型必须是 buy 或 sell'}

    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        db.close()
        return {'error': f'股票代码 {code} 不存在'}

    stock_name = stock.name

    # 如果是卖出，验证持仓数量
    if tx_type == 'sell':
        holding = db.query(BacktestPortfolio).filter(BacktestPortfolio.code == code).first()
        if not holding:
            db.close()
            return {'error': f'股票 {code} 没有持仓，无法卖出'}
        if quantity > holding.quantity:
            db.close()
            return {'error': f'卖出数量不能超过持仓数量 ({holding.quantity} 股)'}

    # 处理交易日期
    if trade_date:
        try:
            parsed_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
        except ValueError:
            db.close()
            return {'error': '交易日期格式无效，应为 YYYY-MM-DD'}
    else:
        parsed_date = date.today()

    amount = quantity * price

    # 更新持仓
    holding = db.query(BacktestPortfolio).filter(BacktestPortfolio.code == code).first()
    if tx_type == 'buy':
        if holding:
            # 已有持仓：加权平均成本价
            total_cost = holding.quantity * holding.cost_price + quantity * price
            holding.quantity += quantity
            holding.cost_price = total_cost / holding.quantity
        else:
            # 新建持仓
            holding = BacktestPortfolio(
                code=code,
                quantity=quantity,
                cost_price=price
            )
            db.add(holding)
    elif tx_type == 'sell':
        if holding:
            holding.quantity -= quantity
            # 如果持仓数量为0，删除该持仓
            if holding.quantity == 0:
                db.delete(holding)

    transaction = BacktestTransaction(
        type=tx_type,
        code=code,
        quantity=quantity,
        price=price,
        amount=amount,
        trade_date=parsed_date,
        open_price=open_price,
        close_price=close_price,
        equity_after=equity_after,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    db.close()

    return {
        'id': transaction.id,
        'type': transaction.type,
        'code': transaction.code,
        'name': stock_name,
        'quantity': transaction.quantity,
        'price': round(transaction.price, 2),
        'amount': round(transaction.amount, 2),
        'trade_date': transaction.trade_date.strftime('%Y-%m-%d') if transaction.trade_date else '',
        'open_price': round(transaction.open_price, 2) if transaction.open_price is not None else None,
        'close_price': round(transaction.close_price, 2) if transaction.close_price is not None else None,
        'equity_after': round(transaction.equity_after, 2) if transaction.equity_after is not None else None,
        'created_at': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }


def get_cash_balance() -> float:
    """获取回测现金余额"""
    db = next(get_db())
    cash_balance = db.query(BacktestCash).first()
    balance = cash_balance.balance if cash_balance else 0.0
    db.close()
    return round(balance, 2)


def update_cash(amount: float) -> Dict[str, Any]:
    """更新回测现金余额"""
    db = next(get_db())

    cash_balance = db.query(BacktestCash).first()
    if not cash_balance:
        cash_balance = BacktestCash(balance=0.0)
        db.add(cash_balance)

    cash_balance.balance += amount
    new_balance = cash_balance.balance

    db.commit()
    db.close()

    return {'balance': round(new_balance, 2)}


def clear_all_transactions() -> Dict[str, Any]:
    """清除所有回测交易记录"""
    db = next(get_db())

    count = db.query(BacktestTransaction).count()
    db.query(BacktestTransaction).delete()
    db.commit()
    db.close()

    return {'success': True, 'message': f'已清除 {count} 条交易记录', 'deleted_count': count}


def _get_latest_prices(db) -> Dict[str, float]:
    """获取所有股票的最新收盘价"""
    max_date = db.query(func.max(StockDaily.date)).scalar()
    if not max_date:
        return {}

    prices = db.query(StockDaily.code, StockDaily.close).filter(
        StockDaily.date == max_date
    ).all()

    return {p.code: p.close for p in prices}
