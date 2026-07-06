"""策略模块数据模型"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.sql import func
from backend.utils.db import Base


class StrategyPosition(Base):
    """策略持仓模型"""

    __tablename__ = 'strategy_positions'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), index=True, nullable=False)
    name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    buy_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    stop_price = Column(Float, nullable=False)
    suggested_buy_price = Column(Float)
    buy_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default='holding')  # holding/sold/timeout
    sell_price = Column(Float)
    sell_date = Column(Date)
    profit_pct = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StrategyTransaction(Base):
    """策略交易记录模型"""

    __tablename__ = 'strategy_transactions'

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(10), nullable=False)  # buy/sell
    code = Column(String(20), index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float)
    trade_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())


class StrategyCash(Base):
    """策略现金余额模型"""

    __tablename__ = 'strategy_cash'

    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, nullable=False, default=0.0)
    initial_capital = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StrategyConfig(Base):
    """策略配置模型"""

    __tablename__ = 'strategy_config'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(String(500), nullable=False)
    description = Column(String(200))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
