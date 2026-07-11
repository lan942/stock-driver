from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from backend.utils.db import Base


class BacktestPortfolio(Base):
    """回测持仓模型"""

    __tablename__ = 'backtest_portfolio'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    cost_price = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('code', name='uq_backtest_portfolio_code'),
        {'sqlite_autoincrement': True},
    )


class BacktestTransaction(Base):
    """回测交易记录模型"""

    __tablename__ = 'backtest_transactions'

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(10), nullable=False)
    code = Column(String(20), index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float)
    trade_date = Column(Date, default=func.current_date())
    open_price = Column(Float)
    close_price = Column(Float)
    equity_after = Column(Float)
    profit_pct = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class BacktestCash(Base):
    """回测现金余额模型"""

    __tablename__ = 'backtest_cash'

    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
